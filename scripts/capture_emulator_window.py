#!/usr/bin/env python3
"""Record a HarmonyOS emulator window at a high frame rate on Windows."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import psutil
except ImportError:
    psutil = None

try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None


DEFAULT_HDC_CANDIDATES = (
    r"D:\DevEcoStudio6.0\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe",
    r"C:\Program Files\Huawei\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe",
)
WM_CLASS_NAME = 0
WM_GET_TITLE = 1


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


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
    raise FileNotFoundError("hdc not found; pass --hdc")


def run(command: list[str], timeout: float = 30.0) -> subprocess.CompletedProcess[str]:
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
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(command)}\n{result.stdout}{result.stderr}")
    return result


def find_emulator_process(model: str | None) -> Any:
    if psutil is None:
        raise RuntimeError("psutil is required for emulator window capture")
    matches = []
    for process in psutil.process_iter(["pid", "name", "cmdline"]):
        info = process.info
        if (info.get("name") or "").lower() != "emulator.exe":
            continue
        command_line = " ".join(info.get("cmdline") or [])
        if model and model.lower() not in command_line.lower():
            continue
        matches.append(process)
    if not matches:
        label = f" for model {model!r}" if model else ""
        raise RuntimeError(f"no running Emulator.exe process found{label}")
    if len(matches) > 1:
        details = ", ".join(str(process.info["pid"]) for process in matches)
        raise RuntimeError(f"multiple Emulator.exe processes match; pass --model or --pid ({details})")
    return matches[0]


def get_emulator_window(pid: int) -> int:
    user32 = ctypes.windll.user32
    found: list[int] = []
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def callback(hwnd: int, _lparam: int) -> bool:
        process_id = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
        if process_id.value != pid or not user32.IsWindowVisible(hwnd):
            return True
        title_length = user32.GetWindowTextLengthW(hwnd)
        title = ctypes.create_unicode_buffer(title_length + 1)
        user32.GetWindowTextW(hwnd, title, title_length + 1)
        class_name = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_name, 256)
        if class_name.value.startswith("Qt") and title.value == "Emulator":
            found.append(int(hwnd))
            return False
        return True

    user32.EnumWindows(callback_type(callback), 0)
    if not found:
        raise RuntimeError(f"no visible Emulator window found for pid {pid}")
    return found[0]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


def window_rect(hwnd: int) -> tuple[int, int, int, int]:
    dwmapi = ctypes.windll.dwmapi
    rect = RECT()
    result = dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(rect), ctypes.sizeof(rect))
    if result != 0:
        user32 = ctypes.windll.user32
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            raise RuntimeError("could not read emulator window bounds")
    return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top


def bring_emulator_to_front(hwnd: int) -> dict[str, Any]:
    user32 = ctypes.windll.user32
    previous_foreground = int(user32.GetForegroundWindow() or 0)
    was_minimized = bool(user32.IsIconic(hwnd))
    user32.ShowWindow(hwnd, 9)
    user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.6)
    return {
        "previousForeground": previous_foreground,
        "wasMinimized": was_minimized,
    }


def restore_emulator_window(hwnd: int, state: dict[str, Any]) -> None:
    user32 = ctypes.windll.user32
    user32.SetWindowPos(hwnd, -2, 0, 0, 0, 0, 0x0001 | 0x0002)
    if state.get("wasMinimized"):
        user32.ShowWindow(hwnd, 6)
    previous = int(state.get("previousForeground") or 0)
    if previous and previous != hwnd:
        user32.SetForegroundWindow(previous)


def parse_pair(value: str) -> tuple[int, int]:
    parts = value.split(",")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("expected X,Y")
    return int(round(float(parts[0]))), int(round(float(parts[1])))


def parse_quad(value: str) -> tuple[int, int, int, int]:
    parts = value.split(",")
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("expected X1,Y1,X2,Y2")
    return tuple(int(round(float(part))) for part in parts)  # type: ignore[return-value]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", help="Emulator model text, for example 'Mate 90 Pro'")
    parser.add_argument("--pid", type=int, help="Explicit Emulator.exe process id")
    parser.add_argument("--serial", required=True, help="HDC target serial")
    parser.add_argument("--hdc", help="Path to hdc executable")
    parser.add_argument("--output", type=Path, required=True, help="Output directory")
    parser.add_argument("--fps", type=int, default=60)
    parser.add_argument("--pre-roll-ms", type=int, default=500)
    parser.add_argument("--duration-ms", type=int, default=2000)
    parser.add_argument("--trigger-click", type=parse_pair)
    parser.add_argument("--trigger-swipe", type=parse_quad)
    parser.add_argument("--swipe-velocity", type=int, default=800)
    parser.add_argument("--trigger-shell")
    parser.add_argument("--crop", type=parse_quad, help="Crop inside the emulator window: X,Y,W,H")
    parser.add_argument("--crf", type=int, default=18)
    parser.add_argument("--preset", default="ultrafast")
    args = parser.parse_args()

    if os.name != "nt":
        raise RuntimeError("emulator window capture is currently Windows-only")
    if imageio_ffmpeg is None:
        raise RuntimeError("imageio-ffmpeg is required")
    if args.fps <= 0 or args.pre_roll_ms < 0 or args.duration_ms <= 0:
        raise ValueError("fps and duration must be positive; pre-roll must be non-negative")

    process = find_emulator_process(args.model) if not args.pid else psutil.Process(args.pid)
    pid = int(process.pid)
    hwnd = get_emulator_window(pid)
    window_state = bring_emulator_to_front(hwnd)
    x, y, width, height = window_rect(hwnd)
    if args.crop:
        crop_x, crop_y, crop_w, crop_h = args.crop
        x += crop_x
        y += crop_y
        width = crop_w
        height = crop_h
    width -= width % 2
    height -= height % 2
    if width <= 1 or height <= 1:
        raise RuntimeError(f"invalid capture size {width}x{height}")

    output_dir = args.output.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    video_name = "trace.mp4"
    video_path = output_dir / video_name
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    total_seconds = (args.pre_roll_ms + args.duration_ms) / 1000.0
    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "gdigrab",
        "-framerate",
        str(args.fps),
        "-offset_x",
        str(max(0, x)),
        "-offset_y",
        str(max(0, y)),
        "-video_size",
        f"{width}x{height}",
        "-i",
        "desktop",
        "-t",
        f"{total_seconds:.3f}",
        "-c:v",
        "libx264",
        "-preset",
        args.preset,
        "-crf",
        str(args.crf),
        "-pix_fmt",
        "yuv420p",
        str(video_path),
    ]
    hdc = find_hdc(args.hdc)
    targets = run([str(hdc), "list", "targets"], timeout=15).stdout.split()
    if args.serial not in targets:
        raise RuntimeError(f"device {args.serial} not connected; targets={targets}")

    trigger_state: dict[str, Any] = {"type": "none"}
    capture_process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    capture_start_epoch = time.time()
    try:
        time.sleep(args.pre_roll_ms / 1000.0)
        trigger_state["sentEpoch"] = time.time()
        trigger_state["sentOffsetMs"] = round((trigger_state["sentEpoch"] - capture_start_epoch) * 1000.0, 3)
        if args.trigger_click:
            trigger_state["type"] = "tap"
            trigger_state["coordinates"] = list(args.trigger_click)
            command_text = f"uitest uiInput click {args.trigger_click[0]} {args.trigger_click[1]}"
            run([str(hdc), "-t", args.serial, "shell", command_text], timeout=20)
        elif args.trigger_swipe:
            trigger_state["type"] = "swipe"
            trigger_state["coordinates"] = list(args.trigger_swipe)
            command_text = (
                f"uitest uiInput swipe {args.trigger_swipe[0]} {args.trigger_swipe[1]} "
                f"{args.trigger_swipe[2]} {args.trigger_swipe[3]} {args.swipe_velocity}"
            )
            run([str(hdc), "-t", args.serial, "shell", command_text], timeout=20)
        elif args.trigger_shell:
            trigger_state["type"] = "shell"
            trigger_state["command"] = args.trigger_shell
            run([str(hdc), "-t", args.serial, "shell", args.trigger_shell], timeout=20)
        trigger_state["completedEpoch"] = time.time()
        trigger_state["completedOffsetMs"] = round((trigger_state["completedEpoch"] - capture_start_epoch) * 1000.0, 3)
        trigger_state["referenceEpoch"] = trigger_state["completedEpoch"]
        trigger_state["referenceOffsetMs"] = trigger_state["completedOffsetMs"]
        stdout, stderr = capture_process.communicate(timeout=max(10, total_seconds + 10))
        if capture_process.returncode != 0:
            raise RuntimeError(f"ffmpeg failed ({capture_process.returncode}): {stderr}")
    finally:
        if capture_process.poll() is None:
            capture_process.kill()
        restore_emulator_window(hwnd, window_state)

    manifest = {
        "schemaVersion": 1,
        "kind": "motion-capture",
        "source": "emulator-window",
        "capturedAt": utc_now(),
        "device": {
            "serial": args.serial,
            "emulatorPid": pid,
            "emulatorWindow": hwnd,
            "captureRect": [max(0, x), max(0, y), width, height],
        },
        "preRollMs": args.pre_roll_ms,
        "durationMs": args.duration_ms,
        "trigger": trigger_state,
        "coverage": {
            "frameCount": 0,
            "nominalFps": args.fps,
        },
        "frameDirectory": "frames",
        "frames": [],
        "artifacts": {
            "video": video_name,
            "videoFps": args.fps,
            "triggerOffsetMs": trigger_state.get("referenceOffsetMs", args.pre_roll_ms),
        },
        "notes": [
            "The emulator window is recorded from the Windows desktop, not from the HDC still-frame path.",
            "Window capture includes host compositor timing and any always-on-top overlays.",
            "Use HDC snapshots as a visual fallback when another window overlaps the emulator.",
        ],
    }
    (output_dir / "capture.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "manifest": str(output_dir / "capture.json"), "video": str(video_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
