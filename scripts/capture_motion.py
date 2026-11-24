#!/usr/bin/env python3
"""Capture timestamped motion frames from a browser or HarmonyOS device."""

from __future__ import annotations

import argparse
import base64
import json
import math
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import websocket
except ImportError:
    websocket = None


DEFAULT_HDC_CANDIDATES = (
    r"D:\DevEcoStudio6.0\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe",
    r"C:\Program Files\Huawei\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe",
)
BROWSER_CANDIDATES = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def run_command(command: list[str], timeout: float = 30.0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stdout + result.stderr).strip()
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(command)}\n{detail}")
    return result


def find_hdc(explicit: str | None) -> Path:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    if os.environ.get("DEVECO_HOME"):
        candidates.append(Path(os.environ["DEVECO_HOME"]) / "sdk/default/openharmony/toolchains/hdc.exe")
    on_path = shutil.which("hdc")
    if on_path:
        candidates.append(Path(on_path))
    candidates.extend(Path(path) for path in DEFAULT_HDC_CANDIDATES)
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError("hdc not found; pass --hdc or install the HarmonyOS toolchain")


def find_browser(explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit)
        if path.is_file():
            return path.resolve()
        raise FileNotFoundError(f"browser not found: {path}")
    for candidate in BROWSER_CANDIDATES:
        path = Path(candidate)
        if path.is_file():
            return path.resolve()
    raise FileNotFoundError("Chromium browser not found; pass --browser")


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


class CdpConnection:
    def __init__(self, websocket_url: str) -> None:
        if websocket is None:
            raise RuntimeError("websocket-client is required for browser capture")
        self.ws = websocket.create_connection(
            websocket_url,
            timeout=8,
            suppress_origin=True,
            http_proxy_host=None,
        )
        self.next_id = 1
        self.events: list[dict[str, Any]] = []

    def close(self) -> None:
        try:
            self.ws.close()
        except Exception:
            pass

    def send(self, method: str, params: dict[str, Any] | None = None) -> int:
        message_id = self.next_id
        self.next_id += 1
        self.ws.send(json.dumps({"id": message_id, "method": method, "params": params or {}}))
        return message_id

    def receive(self, timeout: float) -> dict[str, Any] | None:
        self.ws.settimeout(max(0.001, timeout))
        try:
            raw = self.ws.recv()
        except websocket.WebSocketTimeoutException:
            return None
        if not raw:
            return None
        return json.loads(raw)

    def call(self, method: str, params: dict[str, Any] | None = None, timeout: float = 10.0) -> dict[str, Any]:
        message_id = self.send(method, params)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            message = self.receive(min(0.25, max(0.01, deadline - time.monotonic())))
            if message is None:
                continue
            if message.get("id") == message_id:
                if "error" in message:
                    raise RuntimeError(f"{method} failed: {message['error']}")
                return message.get("result", {})
            self.events.append(message)
        raise TimeoutError(f"no response for {method}")

    def pop_event(self, method: str) -> dict[str, Any] | None:
        for index, event in enumerate(self.events):
            if event.get("method") == method:
                return self.events.pop(index)
        return None


def wait_devtools_page(port: int, timeout: float = 12.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=1) as response:
                pages = json.load(response)
            for page in pages:
                if page.get("type") == "page" and page.get("webSocketDebuggerUrl"):
                    return page
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
        time.sleep(0.1)
    raise TimeoutError(f"DevTools did not expose a page: {last_error}")


def wait_page_ready(cdp: CdpConnection, timeout: float = 8.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = cdp.call(
            "Runtime.evaluate",
            {"expression": "document.readyState", "returnByValue": True},
            timeout=2,
        )
        value = result.get("result", {}).get("value")
        if value in {"interactive", "complete"}:
            return
        time.sleep(0.05)
    raise TimeoutError("page did not reach interactive/complete")


def normalize_trigger_js(value: str | None) -> str | None:
    if not value:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return f"(async () => {{ {stripped} }})()"


def capture_browser(args: argparse.Namespace) -> int:
    browser = find_browser(args.browser)
    output_dir = args.output.expanduser().resolve()
    frames_dir = output_dir / "frames"
    output_dir.mkdir(parents=True, exist_ok=True)
    frames_dir.mkdir(parents=True, exist_ok=True)
    port = free_port()
    profile_context = tempfile.TemporaryDirectory(prefix="motion-browser-")
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process = subprocess.Popen(
        [
            str(browser),
            "--headless=new",
            "--disable-gpu",
            "--disable-extensions",
            "--hide-scrollbars",
            "--no-first-run",
            "--no-default-browser-check",
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile_context.name}",
            "--window-size=" + f"{args.width},{args.height}",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creation_flags,
    )
    cdp: CdpConnection | None = None
    frames: list[dict[str, Any]] = []
    trigger: dict[str, Any] = {"type": "js" if args.trigger_js else "none"}
    notes: list[str] = []
    try:
        page = wait_devtools_page(port)
        cdp = CdpConnection(page["webSocketDebuggerUrl"])
        cdp.call("Page.enable")
        cdp.call("Runtime.enable")
        cdp.call(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": args.width,
                "height": args.height,
                "deviceScaleFactor": args.scale,
                "mobile": args.mobile,
                "screenWidth": args.width,
                "screenHeight": args.height,
            },
        )
        cdp.call("Page.navigate", {"url": args.url})
        wait_page_ready(cdp)
        time.sleep(max(0.0, args.settle_before_ms / 1000.0))
        cdp.call(
            "Page.startScreencast",
            {
                "format": "jpeg",
                "quality": args.quality,
                "maxWidth": args.width * args.scale,
                "maxHeight": args.height * args.scale,
                "everyNthFrame": 1,
            },
        )

        capture_start = time.monotonic()
        capture_start_epoch = time.time()
        total_seconds = (args.pre_roll_ms + args.duration_ms) / 1000.0
        deadline = capture_start + total_seconds
        trigger_due = capture_start + args.pre_roll_ms / 1000.0
        trigger_epoch_start: float | None = None
        trigger_epoch_end: float | None = None
        trigger_epoch_mid: float | None = None
        triggered = args.trigger_js is None
        frame_index = 0
        first_metadata_epoch: float | None = None
        first_receive_mono: float | None = None
        while time.monotonic() < deadline:
            now = time.monotonic()
            if not triggered and now >= trigger_due:
                trigger_epoch_start = time.time()
                cdp.call(
                    "Runtime.evaluate",
                    {
                        "expression": normalize_trigger_js(args.trigger_js),
                        "awaitPromise": False,
                        "returnByValue": True,
                    },
                )
                trigger_epoch_end = time.time()
                trigger_epoch_mid = (trigger_epoch_start + trigger_epoch_end) / 2.0
                trigger = {
                    "type": "js",
                    "expression": args.trigger_js,
                    "sentEpoch": trigger_epoch_start,
                    "completedEpoch": trigger_epoch_end,
                    "referenceEpoch": trigger_epoch_mid,
                }
                triggered = True

            event = cdp.pop_event("Page.screencastFrame")
            if event is None:
                event = cdp.receive(0.01)
                if event is not None:
                    if event.get("method") == "Page.screencastFrame":
                        pass
                    else:
                        cdp.events.append(event)
                        continue
            if event is None:
                continue
            params = event.get("params", {})
            metadata = params.get("metadata", {})
            payload = base64.b64decode(params.get("data", ""))
            receive_mono = time.monotonic()
            frame_name = f"browser_{frame_index:05d}.jpg"
            frame_path = frames_dir / frame_name
            frame_path.write_bytes(payload)
            timestamp_epoch = float(metadata.get("timestamp") or 0.0)
            if first_metadata_epoch is None and timestamp_epoch > 0:
                first_metadata_epoch = timestamp_epoch
                first_receive_mono = receive_mono
            if trigger_epoch_mid is not None and timestamp_epoch > 0:
                timestamp_ms = (timestamp_epoch - trigger_epoch_mid) * 1000.0
                time_basis = "cdp-metadata"
            elif trigger_epoch_mid is not None:
                timestamp_ms = (receive_mono - trigger_due) * 1000.0
                time_basis = "receive-monotonic"
            else:
                timestamp_ms = (receive_mono - capture_start) * 1000.0 - args.pre_roll_ms
                time_basis = "receive-monotonic"
            frames.append(
                {
                    "index": frame_index,
                    "file": frame_name,
                    "timestampMs": round(timestamp_ms, 3),
                    "receivedAtEpoch": round(time.time(), 6),
                    "timeBasis": time_basis,
                    "size": len(payload),
                    "metadata": {
                        "timestamp": metadata.get("timestamp"),
                        "pageScaleFactor": metadata.get("pageScaleFactor"),
                        "offsetTop": metadata.get("offsetTop"),
                        "scrollOffsetX": metadata.get("scrollOffsetX"),
                        "scrollOffsetY": metadata.get("scrollOffsetY"),
                    },
                }
            )
            frame_index += 1
            try:
                cdp.call("Page.screencastFrameAck", {"sessionId": params.get("sessionId")}, timeout=2)
            except Exception as exc:
                notes.append(f"screencast ack failed at frame {frame_index - 1}: {exc}")

        try:
            cdp.call("Page.stopScreencast", timeout=3)
        except Exception:
            pass

        if trigger_epoch_mid is None and trigger_epoch_start is not None:
            trigger_epoch_mid = (trigger_epoch_start + (trigger_epoch_end or trigger_epoch_start)) / 2.0
        if not frames:
            raise RuntimeError("browser capture produced no frames")
        if trigger_epoch_mid is not None:
            for frame in frames:
                metadata_epoch = frame["metadata"].get("timestamp")
                if frame["timeBasis"] == "cdp-metadata" and metadata_epoch and first_metadata_epoch:
                    frame["timestampMs"] = round((float(metadata_epoch) - trigger_epoch_mid) * 1000.0, 3)
                else:
                    received = float(frame["receivedAtEpoch"])
                    frame["timestampMs"] = round((received - trigger_epoch_mid) * 1000.0, 3)

        intervals = [
            frames[index]["timestampMs"] - frames[index - 1]["timestampMs"]
            for index in range(1, len(frames))
        ]
        positive_intervals = [value for value in intervals if value > 0]
        median_interval = sorted(positive_intervals)[len(positive_intervals) // 2] if positive_intervals else None
        manifest = {
            "schemaVersion": 1,
            "kind": "motion-capture",
            "source": "browser-screencast",
            "capturedAt": utc_now(),
            "url": args.url,
            "browser": str(browser),
            "viewport": {
                "width": args.width,
                "height": args.height,
                "deviceScaleFactor": args.scale,
            },
            "preRollMs": args.pre_roll_ms,
            "durationMs": args.duration_ms,
            "trigger": trigger,
            "coverage": {
                "frameCount": len(frames),
                "medianIntervalMs": round(median_interval, 3) if median_interval is not None else None,
                "effectiveFps": round(1000.0 / median_interval, 2) if median_interval else None,
                "firstTimestampMs": frames[0]["timestampMs"],
                "lastTimestampMs": frames[-1]["timestampMs"],
            },
            "frameDirectory": "frames",
            "frames": frames,
            "notes": notes,
        }
        atomic_write_json(output_dir / "capture.json", manifest)
        print(json.dumps({"ok": True, "manifest": str(output_dir / "capture.json"), "frames": len(frames)}, ensure_ascii=False))
        return 0
    finally:
        if cdp is not None:
            cdp.close()
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        profile_context.cleanup()


@dataclass
class HarmonyFrame:
    index: int
    file: str
    capture_start_epoch: float
    capture_end_epoch: float
    latency_ms: float
    size: int


def parse_pair(value: str) -> tuple[float, float]:
    parts = value.split(",")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("expected X,Y")
    return float(parts[0]), float(parts[1])


def parse_quad(value: str) -> tuple[float, float, float, float]:
    parts = value.split(",")
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("expected X1,Y1,X2,Y2")
    return tuple(float(part) for part in parts)  # type: ignore[return-value]


def trigger_harmony(
    hdc: Path,
    serial: str,
    args: argparse.Namespace,
    trigger_state: dict[str, Any],
) -> None:
    trigger_state["sentEpoch"] = time.time()
    try:
        if args.trigger_click:
            x, y = args.trigger_click
            command = f"uitest uiInput click {x:g} {y:g}"
            trigger_state["type"] = "tap"
            trigger_state["coordinates"] = [x, y]
        elif args.trigger_swipe:
            x1, y1, x2, y2 = args.trigger_swipe
            command = f"uitest uiInput swipe {x1:g} {y1:g} {x2:g} {y2:g} {args.swipe_velocity}"
            trigger_state["type"] = "swipe"
            trigger_state["coordinates"] = [x1, y1, x2, y2]
            trigger_state["velocity"] = args.swipe_velocity
        elif args.trigger_shell:
            command = args.trigger_shell
            trigger_state["type"] = "shell"
            trigger_state["command"] = command
        else:
            trigger_state["type"] = "manual"
            trigger_state["completedEpoch"] = time.time()
            return
        result = run_command([str(hdc), "-t", serial, "shell", command], timeout=20)
        trigger_state["commandOutput"] = (result.stdout + result.stderr).strip()
    except Exception as exc:
        trigger_state["error"] = str(exc)
    finally:
        trigger_state["completedEpoch"] = time.time()


def capture_harmony(args: argparse.Namespace) -> int:
    hdc = find_hdc(args.hdc)
    serial = args.serial
    targets = run_command([str(hdc), "list", "targets"], timeout=15).stdout.split()
    if serial not in targets:
        raise RuntimeError(f"device {serial} not connected; targets={targets}")
    output_dir = args.output.expanduser().resolve()
    frames_dir = output_dir / "frames"
    output_dir.mkdir(parents=True, exist_ok=True)
    frames_dir.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex[:10]
    remote_path = f"/data/local/tmp/motion_{token}.png"
    frames: list[HarmonyFrame] = []
    trigger_state: dict[str, Any] = {}
    notes: list[str] = [
        "Frame times are host-side capture-window midpoints; snapshot command latency is reported per frame.",
        "Use this mode for checkpoint and ordering evidence. Use emulator-window for high-rate visual sampling.",
    ]
    timer = threading.Timer(
        max(0.0, args.pre_roll_ms / 1000.0),
        trigger_harmony,
        args=(hdc, serial, args, trigger_state),
    )
    total_seconds = (args.pre_roll_ms + args.duration_ms) / 1000.0
    deadline = time.monotonic() + total_seconds
    frame_index = 0
    timer.start()
    try:
        while time.monotonic() < deadline:
            capture_start_epoch = time.time()
            start_mono = time.monotonic()
            remote_frame = remote_path if frame_index == 0 else f"{remote_path[:-4]}_{frame_index:04d}.png"
            run_command(
                [
                    str(hdc),
                    "-t",
                    serial,
                    "shell",
                    f"snapshot_display -f {remote_frame} -h {args.height} -w {args.width} -t png",
                ],
                timeout=20,
            )
            local_name = f"harmony_{frame_index:05d}.png"
            local_path = frames_dir / local_name
            run_command(
                [str(hdc), "-t", serial, "file", "recv", remote_frame, str(local_path.resolve())],
                timeout=20,
            )
            capture_end_epoch = time.time()
            latency_ms = (time.monotonic() - start_mono) * 1000.0
            if not local_path.is_file():
                raise RuntimeError(f"snapshot was not received: {local_path}")
            frames.append(
                HarmonyFrame(
                    index=frame_index,
                    file=local_name,
                    capture_start_epoch=capture_start_epoch,
                    capture_end_epoch=capture_end_epoch,
                    latency_ms=latency_ms,
                    size=local_path.stat().st_size,
                )
            )
            frame_index += 1
    finally:
        timer.join(timeout=5)

    if trigger_state.get("error"):
        notes.append(f"trigger error: {trigger_state['error']}")
    if trigger_state.get("sentEpoch") and trigger_state.get("completedEpoch"):
        trigger_reference = float(trigger_state["completedEpoch"])
        trigger_state["referenceEpoch"] = trigger_reference
        trigger_state["commandLatencyMs"] = round(
            (trigger_state["completedEpoch"] - trigger_state["sentEpoch"]) * 1000.0, 3
        )
    else:
        trigger_reference = float(trigger_state.get("sentEpoch") or time.time())
        trigger_state["referenceEpoch"] = trigger_reference

    frame_records: list[dict[str, Any]] = []
    for frame in frames:
        midpoint = (frame.capture_start_epoch + frame.capture_end_epoch) / 2.0
        frame_records.append(
            {
                "index": frame.index,
                "file": frame.file,
                "timestampMs": round((midpoint - trigger_reference) * 1000.0, 3),
                "captureStartEpoch": round(frame.capture_start_epoch, 6),
                "captureEndEpoch": round(frame.capture_end_epoch, 6),
                "timeBasis": "host-capture-window-midpoint",
                "latencyMs": round(frame.latency_ms, 3),
                "size": frame.size,
            }
        )
    intervals = [
        frame_records[index]["timestampMs"] - frame_records[index - 1]["timestampMs"]
        for index in range(1, len(frame_records))
    ]
    positive_intervals = [value for value in intervals if value > 0]
    median_interval = sorted(positive_intervals)[len(positive_intervals) // 2] if positive_intervals else None
    manifest = {
        "schemaVersion": 1,
        "kind": "motion-capture",
        "source": "harmony-snapshots",
        "capturedAt": utc_now(),
        "device": {
            "serial": serial,
            "hdc": str(hdc),
            "requestedWidth": args.width,
            "requestedHeight": args.height,
        },
        "preRollMs": args.pre_roll_ms,
        "durationMs": args.duration_ms,
        "trigger": trigger_state,
        "coverage": {
            "frameCount": len(frame_records),
            "medianIntervalMs": round(median_interval, 3) if median_interval is not None else None,
            "effectiveFps": round(1000.0 / median_interval, 2) if median_interval else None,
            "firstTimestampMs": frame_records[0]["timestampMs"] if frame_records else None,
            "lastTimestampMs": frame_records[-1]["timestampMs"] if frame_records else None,
        },
        "frameDirectory": "frames",
        "frames": frame_records,
        "notes": notes,
    }
    try:
        run_command(
            [str(hdc), "-t", serial, "shell", f"rm -f /data/local/tmp/motion_{token}*.png"],
            timeout=10,
        )
    except Exception:
        pass
    if not frame_records:
        raise RuntimeError("harmony capture produced no frames")
    atomic_write_json(output_dir / "capture.json", manifest)
    print(json.dumps({"ok": True, "manifest": str(output_dir / "capture.json"), "frames": len(frame_records)}, ensure_ascii=False))
    return 0


def capture_snapshot(
    hdc: Path,
    serial: str,
    width: int,
    height: int,
    remote_path: str,
    local_path: Path,
) -> tuple[float, float, float]:
    capture_start_epoch = time.time()
    start_mono = time.monotonic()
    run_command(
        [
            str(hdc),
            "-t",
            serial,
            "shell",
            f"snapshot_display -f {remote_path} -h {height} -w {width} -t png",
        ],
        timeout=20,
    )
    run_command(
        [str(hdc), "-t", serial, "file", "recv", remote_path, str(local_path.resolve())],
        timeout=20,
    )
    capture_end_epoch = time.time()
    latency_ms = (time.monotonic() - start_mono) * 1000.0
    if not local_path.is_file():
        raise RuntimeError(f"snapshot was not received: {local_path}")
    return capture_start_epoch, capture_end_epoch, latency_ms


def capture_harmony_sweep(args: argparse.Namespace) -> int:
    hdc = find_hdc(args.hdc)
    serial = args.serial
    targets = run_command([str(hdc), "list", "targets"], timeout=15).stdout.split()
    if serial not in targets:
        raise RuntimeError(f"device {serial} not connected; targets={targets}")
    output_dir = args.output.expanduser().resolve()
    frames_dir = output_dir / "frames"
    output_dir.mkdir(parents=True, exist_ok=True)
    frames_dir.mkdir(parents=True, exist_ok=True)

    phases = sorted({float(value) for value in args.phase})
    if not phases or any(value < 0 for value in phases):
        raise ValueError("phase sweep needs one or more non-negative --phase values")
    token = uuid.uuid4().hex[:10]
    remote_path = f"/data/local/tmp/motion_sweep_{token}.png"
    estimated_latency_ms = float(args.capture_latency_ms or 650.0)
    raw_records: list[dict[str, Any]] = []
    trigger_records: list[dict[str, Any]] = []
    file_index = 0
    trial_index = 0

    try:
        for phase in phases:
            for repeat in range(args.trials):
                baseline_name = f"sweep_{file_index:05d}.png"
                baseline_path = frames_dir / baseline_name
                baseline_start, baseline_end, baseline_latency = capture_snapshot(
                    hdc, serial, args.width, args.height, remote_path, baseline_path
                )
                file_index += 1
                estimated_latency_ms = baseline_latency

                trigger_state: dict[str, Any] = {"trial": trial_index, "requestedPhaseMs": phase}
                trigger_harmony(hdc, serial, args, trigger_state)
                if trigger_state.get("error"):
                    raise RuntimeError(f"trial {trial_index} trigger failed: {trigger_state['error']}")
                if trigger_state.get("type") == "manual":
                    raise ValueError("phase sweep requires --trigger-click, --trigger-swipe, or --trigger-shell")
                trigger_reference = float(trigger_state["completedEpoch"])
                baseline_midpoint = (baseline_start + baseline_end) / 2.0
                raw_records.append(
                    {
                        "trial": trial_index,
                        "repeat": repeat,
                        "requestedPhaseMs": phase,
                        "role": "baseline",
                        "file": baseline_name,
                        "timestampMs": round((baseline_midpoint - trigger_reference) * 1000.0, 3),
                        "captureStartEpoch": round(baseline_start, 6),
                        "captureEndEpoch": round(baseline_end, 6),
                        "latencyMs": round(baseline_latency, 3),
                        "timeBasis": "host-capture-window-midpoint",
                        "size": baseline_path.stat().st_size,
                    }
                )

                target_epoch = trigger_reference + phase / 1000.0
                capture_call_epoch = target_epoch - estimated_latency_ms / 2000.0
                wait_seconds = capture_call_epoch - time.time()
                if wait_seconds > 0:
                    time.sleep(wait_seconds)
                phase_name = f"sweep_{file_index:05d}.png"
                phase_path = frames_dir / phase_name
                phase_start, phase_end, phase_latency = capture_snapshot(
                    hdc, serial, args.width, args.height, remote_path, phase_path
                )
                file_index += 1
                estimated_latency_ms = (estimated_latency_ms + phase_latency) / 2.0
                midpoint = (phase_start + phase_end) / 2.0
                raw_records.append(
                    {
                        "trial": trial_index,
                        "repeat": repeat,
                        "requestedPhaseMs": phase,
                        "role": "phase",
                        "file": phase_name,
                        "timestampMs": round((midpoint - trigger_reference) * 1000.0, 3),
                        "captureStartEpoch": round(phase_start, 6),
                        "captureEndEpoch": round(phase_end, 6),
                        "latencyMs": round(phase_latency, 3),
                        "timeBasis": "host-capture-window-midpoint",
                        "size": phase_path.stat().st_size,
                    }
                )
                trigger_records.append(
                    {
                        "trial": trial_index,
                        "requestedPhaseMs": phase,
                        "type": trigger_state.get("type"),
                        "coordinates": trigger_state.get("coordinates"),
                        "sentEpoch": round(float(trigger_state["sentEpoch"]), 6),
                        "completedEpoch": round(float(trigger_state["completedEpoch"]), 6),
                        "referenceEpoch": round(trigger_reference, 6),
                        "commandLatencyMs": round(
                            (float(trigger_state["completedEpoch"]) - float(trigger_state["sentEpoch"])) * 1000.0,
                            3,
                        ),
                    }
                )
                trial_index += 1
                if args.settle_ms > 0:
                    time.sleep(args.settle_ms / 1000.0)

        raw_records.sort(key=lambda item: (item["timestampMs"], item["trial"], item["role"]))
        frames: list[dict[str, Any]] = []
        for index, record in enumerate(raw_records):
            record["index"] = index
            frames.append(record)
        timestamps = [float(record["timestampMs"]) for record in frames]
        intervals = [timestamps[index] - timestamps[index - 1] for index in range(1, len(timestamps))]
        positive_intervals = [value for value in intervals if value > 0]
        median_interval = sorted(positive_intervals)[len(positive_intervals) // 2] if positive_intervals else None
        manifest = {
            "schemaVersion": 1,
            "kind": "motion-capture",
            "source": "harmony-phase-sweep",
            "capturedAt": utc_now(),
            "device": {
                "serial": serial,
                "hdc": str(hdc),
                "requestedWidth": args.width,
                "requestedHeight": args.height,
            },
            "sweep": {
                "phasesMs": phases,
                "trialsPerPhase": args.trials,
                "settleMs": args.settle_ms,
                "estimatedCaptureLatencyMs": round(estimated_latency_ms, 3),
            },
            "trigger": {"type": "repeated", "trials": trigger_records},
            "coverage": {
                "frameCount": len(frames),
                "medianIntervalMs": round(median_interval, 3) if median_interval is not None else None,
                "effectiveFps": round(1000.0 / median_interval, 2) if median_interval else None,
                "firstTimestampMs": frames[0]["timestampMs"],
                "lastTimestampMs": frames[-1]["timestampMs"],
            },
            "frameDirectory": "frames",
            "frames": frames,
            "notes": [
                "Phase sweep repeats a deterministic trigger for each requested delay and samples one frame near that delay.",
                "Baseline frames precede each trigger; timestamps are relative to each trigger command midpoint.",
                "Use only for scenes that return to the same settled state between trials.",
            ],
        }
        atomic_write_json(output_dir / "capture.json", manifest)
        print(json.dumps({"ok": True, "manifest": str(output_dir / "capture.json"), "frames": len(frames)}, ensure_ascii=False))
        return 0
    finally:
        try:
            run_command(
                [str(hdc), "-t", serial, "shell", f"rm -f /data/local/tmp/motion_sweep_{token}*.png"],
                timeout=10,
            )
        except Exception:
            pass


def add_common_capture_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output", type=Path, required=True, help="Output directory for capture.json and frames")
    parser.add_argument("--pre-roll-ms", type=int, default=500, help="Capture time before trigger")
    parser.add_argument("--duration-ms", type=int, default=1800, help="Capture time after trigger")


def add_trigger_args(parser: argparse.ArgumentParser, *, harmony: bool) -> None:
    if harmony:
        parser.add_argument("--trigger-click", type=parse_pair, help="Tap device coordinates X,Y")
        parser.add_argument("--trigger-swipe", type=parse_quad, help="Swipe device coordinates X1,Y1,X2,Y2")
        parser.add_argument("--swipe-velocity", type=int, default=800, help="Velocity for --trigger-swipe")
        parser.add_argument("--trigger-shell", help="Device shell command used as the trigger")
        parser.add_argument("--serial", required=True, help="HDC target serial or name")
        parser.add_argument("--hdc", help="Path to hdc executable")
    else:
        parser.add_argument("--trigger-js", help="JavaScript expression executed after pre-roll")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    browser = subcommands.add_parser("browser", help="Capture browser motion through the Chrome DevTools Protocol")
    browser.add_argument("--url", required=True, help="HTTP URL or file URI")
    browser.add_argument("--browser", help="Explicit Chromium browser executable")
    browser.add_argument("--width", type=int, default=390, help="Reference viewport width")
    browser.add_argument("--height", type=int, default=844, help="Reference viewport height")
    browser.add_argument("--scale", type=int, default=1, help="Device scale factor")
    browser.add_argument("--mobile", action="store_true", help="Expose a mobile viewport")
    browser.add_argument("--quality", type=int, default=90, help="JPEG quality")
    browser.add_argument("--settle-before-ms", type=int, default=500, help="Wait after page ready before capture")
    add_common_capture_args(browser)
    add_trigger_args(browser, harmony=False)
    browser.set_defaults(handler=capture_browser)

    harmony = subcommands.add_parser("harmony", help="Capture time-stamped HarmonyOS snapshots over HDC")
    harmony.add_argument("--width", type=int, default=360, help="Snapshot width")
    harmony.add_argument("--height", type=int, default=720, help="Snapshot height")
    add_common_capture_args(harmony)
    add_trigger_args(harmony, harmony=True)
    harmony.set_defaults(handler=capture_harmony)

    sweep = subcommands.add_parser(
        "harmony-sweep",
        help="Repeat a deterministic HarmonyOS trigger and sample requested phase offsets",
    )
    sweep.add_argument("--width", type=int, default=360, help="Snapshot width")
    sweep.add_argument("--height", type=int, default=720, help="Snapshot height")
    sweep.add_argument("--phase", type=float, action="append", required=True, help="Target offset in ms; repeatable")
    sweep.add_argument("--trials", type=int, default=1, help="Repeated triggers per phase")
    sweep.add_argument("--settle-ms", type=int, default=1000, help="Quiet time between trials")
    sweep.add_argument("--capture-latency-ms", type=float, help="Initial snapshot latency estimate")
    sweep.add_argument("--output", type=Path, required=True, help="Output directory for capture.json and frames")
    add_trigger_args(sweep, harmony=True)
    sweep.set_defaults(handler=capture_harmony_sweep)

    return parser


def validate_args(args: argparse.Namespace) -> None:
    if args.command in {"browser", "harmony"} and (args.pre_roll_ms < 0 or args.duration_ms <= 0):
        raise ValueError("pre-roll must be non-negative and duration must be positive")
    if args.command == "browser":
        if args.width <= 0 or args.height <= 0 or args.scale <= 0:
            raise ValueError("browser viewport and scale must be positive")
        if not 1 <= args.quality <= 100:
            raise ValueError("JPEG quality must be between 1 and 100")
    if args.command in {"harmony", "harmony-sweep"}:
        if args.width <= 0 or args.height <= 0:
            raise ValueError("snapshot dimensions must be positive")
    if args.command == "harmony-sweep":
        if args.trials <= 0 or args.settle_ms < 0:
            raise ValueError("trials must be positive and settle time must be non-negative")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        validate_args(args)
        return int(args.handler(args))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
