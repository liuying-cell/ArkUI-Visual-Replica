#!/usr/bin/env python3
"""Collect RenderService hitch and frame counters around one HarmonyOS trigger."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_HDC_CANDIDATES = (
    r"D:\DevEcoStudio6.0\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe",
    r"C:\Program Files\Huawei\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe",
)


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


def run(command: list[str], timeout: float = 30.0) -> str:
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
        raise RuntimeError(f"command failed ({result.returncode})\n{result.stdout}{result.stderr}")
    return result.stdout + result.stderr


def shell(hdc: Path, serial: str, command: str, timeout: float = 30.0) -> str:
    return run([str(hdc), "-t", serial, "shell", command], timeout=timeout)


def parse_hitchs(output: str) -> dict[str, int] | None:
    match = re.search(
        r"window \[(?P<name>[^\]]*)\].*?more than 66 ms\s+(?P<over66>\d+).*?"
        r"more than 33 ms\s+(?P<over33>\d+).*?more than 16\.67 ms\s+(?P<over16>\d+)",
        output,
        re.S,
    )
    if not match:
        return None
    return {
        "over66ms": int(match.group("over66")),
        "over33ms": int(match.group("over33")),
        "over16_67ms": int(match.group("over16")),
    }


def parse_fps_series(output: str, surface: str) -> list[int]:
    marker = f"surface [{surface}]"
    position = output.find(marker)
    if position < 0:
        return []
    values = []
    for line in output[position + len(marker) :].splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("-----") or stripped.startswith("RSProcessDump"):
            break
        if re.fullmatch(r"-?\d+(?:\.\d+)?", stripped):
            values.append(int(float(stripped)))
        elif values:
            break
    return values


def parse_refresh_rates(output: str) -> list[dict[str, Any]]:
    rows = []
    for match in re.finditer(r"Refresh Rate:(\d+(?:\.\d+)?), Count:(\d+)", output):
        rows.append({"refreshRate": float(match.group(1)), "count": int(match.group(2))})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--surface", required=True, help="RenderService surface/window name")
    parser.add_argument("--hdc")
    parser.add_argument("--wait-ms", type=int, default=1400)
    parser.add_argument("--trigger-click", help="Device tap coordinates X,Y")
    parser.add_argument("--trigger-swipe", help="Device swipe coordinates X1,Y1,X2,Y2")
    parser.add_argument("--swipe-velocity", type=int, default=800)
    parser.add_argument("--trigger-shell")
    parser.add_argument("--output", type=Path, help="Optional JSON output path")
    args = parser.parse_args()
    if args.wait_ms < 0:
        raise ValueError("wait-ms must be non-negative")

    hdc = find_hdc(args.hdc)
    targets = run([str(hdc), "list", "targets"], timeout=15).split()
    if args.serial not in targets:
        raise RuntimeError(f"device {args.serial} not connected; targets={targets}")

    before: dict[str, Any] = {
        "hitchs": shell(hdc, args.serial, f'hidumper -s RenderService -a "hitchs {args.surface}"'),
        "fps": shell(hdc, args.serial, f'hidumper -s RenderService -a "fps {args.surface}"'),
        "fpsCount": shell(hdc, args.serial, 'hidumper -s RenderService -a "fpsCount"'),
    }
    shell(hdc, args.serial, f'hidumper -s RenderService -a "fpsClear {args.surface}"')
    shell(hdc, args.serial, 'hidumper -s RenderService -a "flushJankStatsRs"')

    trigger: dict[str, Any] = {"type": "none"}
    if args.trigger_click:
        x, y = (int(round(float(value))) for value in args.trigger_click.split(","))
        trigger = {"type": "tap", "coordinates": [x, y]}
        shell(hdc, args.serial, f"uitest uiInput click {x} {y}", timeout=20)
    elif args.trigger_swipe:
        values = [int(round(float(value))) for value in args.trigger_swipe.split(",")]
        if len(values) != 4:
            raise ValueError("trigger-swipe must be X1,Y1,X2,Y2")
        trigger = {"type": "swipe", "coordinates": values, "velocity": args.swipe_velocity}
        shell(
            hdc,
            args.serial,
            f"uitest uiInput swipe {values[0]} {values[1]} {values[2]} {values[3]} {args.swipe_velocity}",
            timeout=20,
        )
    elif args.trigger_shell:
        trigger = {"type": "shell", "command": args.trigger_shell}
        shell(hdc, args.serial, args.trigger_shell, timeout=20)

    time.sleep(args.wait_ms / 1000.0)
    hitchs_output = shell(hdc, args.serial, f'hidumper -s RenderService -a "hitchs {args.surface}"')
    fps_output = shell(hdc, args.serial, f'hidumper -s RenderService -a "fps {args.surface}"')
    fps_count_output = shell(hdc, args.serial, 'hidumper -s RenderService -a "fpsCount"')
    hitch_counts = parse_hitchs(hitchs_output)
    fps_series = parse_fps_series(fps_output, args.surface)
    nonzero_fps = [value for value in fps_series if value > 0]
    result = {
        "schemaVersion": 1,
        "kind": "render-service-probe",
        "capturedAt": utc_now(),
        "device": {"serial": args.serial, "hdc": str(hdc)},
        "surface": args.surface,
        "trigger": trigger,
        "waitMs": args.wait_ms,
        "hitchCounts": hitch_counts,
        "fpsSeries": fps_series,
        "refreshRateCounts": parse_refresh_rates(fps_count_output),
        "status": {
            "hitchs": "available" if hitch_counts is not None else "unavailable",
            "appFps": "available" if nonzero_fps else "unavailable-or-zero",
        },
        "limitations": [
            "fpsCount reports system refresh-rate transitions, not application view FPS.",
            "Hitch counters do not prove sustained frame rate.",
            "Use a high-rate recording or a dedicated trace for a sustained performance claim.",
        ],
        "raw": {
            "hitchsBefore": before["hitchs"],
            "hitchsAfter": hitchs_output,
            "fpsBefore": before["fps"],
            "fpsAfter": fps_output,
        },
    }
    if args.output:
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
