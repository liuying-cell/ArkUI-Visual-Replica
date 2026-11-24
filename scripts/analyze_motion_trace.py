#!/usr/bin/env python3
"""Analyze a motion capture and emit timeline metrics, a report, and a contact sheet."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

try:
    import imageio.v3 as iio
    import imageio_ffmpeg
except ImportError:
    iio = None
    imageio_ffmpeg = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@dataclass
class FrameSample:
    index: int
    timestamp_ms: float
    image: Image.Image
    source: str


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid capture JSON: {exc}") from exc
    if data.get("kind") != "motion-capture":
        raise ValueError(f"not a motion capture manifest: {path}")
    return data


def resolve_frame_path(base: Path, manifest: dict[str, Any], name: str) -> Path:
    frame_dir = base / str(manifest.get("frameDirectory") or "frames")
    candidate = frame_dir / name
    if not candidate.is_file():
        raise FileNotFoundError(f"capture frame not found: {candidate}")
    return candidate


def load_capture_frames(manifest_path: Path) -> tuple[dict[str, Any], list[FrameSample]]:
    manifest = load_manifest(manifest_path)
    base = manifest_path.parent
    samples: list[FrameSample] = []
    for frame in manifest.get("frames", []):
        image = Image.open(resolve_frame_path(base, manifest, frame["file"])).convert("RGB")
        samples.append(FrameSample(int(frame["index"]), float(frame["timestampMs"]), image, "image"))
    if samples:
        return manifest, samples

    artifacts = manifest.get("artifacts", {})
    video_name = artifacts.get("video")
    if not video_name or iio is None:
        raise ValueError("capture has neither image frames nor a decodable video artifact")
    video_path = base / video_name
    if not video_path.is_file():
        raise FileNotFoundError(video_path)
    fps = float(artifacts.get("videoFps") or manifest.get("coverage", {}).get("nominalFps") or 60)
    trigger_offset_ms = float(artifacts.get("triggerOffsetMs") or manifest.get("preRollMs") or 0)
    for index, array in enumerate(iio.imiter(video_path, plugin="FFMPEG")):
        timestamp_ms = index * 1000.0 / fps - trigger_offset_ms
        samples.append(FrameSample(index, timestamp_ms, Image.fromarray(array).convert("RGB"), "video"))
    return manifest, samples


def parse_roi(value: str | None, width: int, height: int) -> tuple[int, int, int, int]:
    if not value:
        return 0, 0, width, height
    try:
        values = [float(item.strip()) for item in value.split(",")]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("ROI must be X,Y,W,H") from exc
    if len(values) != 4:
        raise argparse.ArgumentTypeError("ROI must be X,Y,W,H")
    if all(0.0 <= item <= 1.0 for item in values):
        x, y, w, h = (
            int(round(values[0] * width)),
            int(round(values[1] * height)),
            int(round(values[2] * width)),
            int(round(values[3] * height)),
        )
    else:
        x, y, w, h = (int(round(item)) for item in values)
    if w <= 0 or h <= 0:
        raise ValueError("ROI width and height must be positive")
    if x < 0 or y < 0 or x + w > width or y + h > height:
        raise ValueError(f"ROI {x},{y},{w},{h} is outside {width}x{height}")
    return x, y, w, h


def prepare_gray(image: Image.Image, roi: tuple[int, int, int, int], max_width: int) -> np.ndarray:
    cropped = image.crop((roi[0], roi[1], roi[0] + roi[2], roi[1] + roi[3]))
    if cropped.width > max_width:
        ratio = max_width / cropped.width
        cropped = cropped.resize((max_width, max(1, round(cropped.height * ratio))), Image.Resampling.BILINEAR)
    return np.asarray(cropped.convert("L"), dtype=np.float32)


def percentile(values: list[float], q: float, default: float = 0.0) -> float:
    if not values:
        return default
    return float(np.percentile(np.asarray(values, dtype=np.float64), q))


def recommend_threshold(
    energies: list[float | None],
    timestamps: list[float],
    trigger_ms: float,
    explicit: float | None,
) -> tuple[float, float]:
    pre = [
        float(value)
        for value, timestamp in zip(energies, timestamps)
        if value is not None and timestamp < trigger_ms - 20
    ]
    if pre:
        pre_median = statistics.median(pre)
        pre_mad = statistics.median(abs(value - pre_median) for value in pre)
        adaptive = max(0.2, pre_median + 6.0 * pre_mad + 0.15)
    else:
        adaptive = 0.35
    if explicit is not None:
        return explicit, pre_median if pre else 0.0
    return adaptive, pre_median if pre else 0.0


def group_events(
    timestamps: list[float],
    energies: list[float | None],
    threshold: float,
    trigger_ms: float,
    gap_ms: float,
) -> list[dict[str, Any]]:
    active = [
        index
        for index, value in enumerate(energies)
        if value is not None and value >= threshold and timestamps[index] >= trigger_ms - gap_ms
    ]
    if not active:
        return []
    groups: list[list[int]] = [[active[0]]]
    for index in active[1:]:
        if timestamps[index] - timestamps[groups[-1][-1]] <= gap_ms:
            groups[-1].append(index)
        else:
            groups.append([index])
    events: list[dict[str, Any]] = []
    for group in groups:
        peak_index = max(group, key=lambda item: float(energies[item] or 0.0))
        previous_index = max(0, group[0] - 1)
        next_index = min(len(timestamps) - 1, group[-1] + 1)
        start_ms = timestamps[group[0]]
        if group[0] > 0 and timestamps[group[0]] - timestamps[previous_index] <= gap_ms:
            start_ms = timestamps[previous_index]
        end_ms = timestamps[group[-1]]
        if group[-1] < len(timestamps) - 1 and timestamps[next_index] - timestamps[group[-1]] <= gap_ms:
            end_ms = timestamps[next_index]
        events.append(
            {
                "startMs": round(start_ms, 3),
                "activeStartMs": round(timestamps[group[0]], 3),
                "peakMs": round(timestamps[peak_index], 3),
                "activeEndMs": round(timestamps[group[-1]], 3),
                "endMs": round(end_ms, 3),
                "peakEnergy": round(float(energies[peak_index] or 0.0), 4),
                "frameIndices": group,
            }
        )
    return events


def choose_contact_frames(
    samples: list[FrameSample],
    timestamps: list[float],
    energies: list[float | None],
    events: list[dict[str, Any]],
    trigger_ms: float,
    limit: int = 12,
) -> list[int]:
    selected: set[int] = set()
    pre_indices = [index for index, timestamp in enumerate(timestamps) if timestamp < trigger_ms]
    if pre_indices:
        selected.add(pre_indices[-1])
    for event in events[:4]:
        selected.add(min(range(len(timestamps)), key=lambda i: abs(timestamps[i] - event["startMs"])))
        selected.add(min(range(len(timestamps)), key=lambda i: abs(timestamps[i] - event["peakMs"])))
        selected.add(min(range(len(timestamps)), key=lambda i: abs(timestamps[i] - event["endMs"])))
    if timestamps:
        selected.add(len(timestamps) - 1)
    if len(selected) < limit:
        ranked = sorted(
            range(len(timestamps)),
            key=lambda index: float(energies[index] or 0.0),
            reverse=True,
        )
        for index in ranked:
            selected.add(index)
            if len(selected) >= limit:
                break
    if len(selected) > limit:
        must_keep = sorted(selected)[: max(1, limit - 1)]
        remaining = sorted(selected - set(must_keep))
        sample_count = limit - len(must_keep)
        if sample_count > 0 and remaining:
            stride = max(1, len(remaining) // sample_count)
            must_keep.extend(remaining[::stride][:sample_count])
        selected = set(must_keep[:limit])
    return sorted(selected)


def make_contact_sheet(
    samples: list[FrameSample],
    indices: list[int],
    timestamps: list[float],
    events: list[dict[str, Any]],
    output_path: Path,
) -> None:
    if not indices:
        return
    thumb_width = 260
    thumb_height = 560
    label_height = 44
    columns = 4
    rows = math.ceil(len(indices) / columns)
    sheet = Image.new("RGB", (columns * thumb_width, rows * (thumb_height + label_height)), (14, 17, 19))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    event_peaks = {round(event["peakMs"], 3) for event in events}
    for slot, index in enumerate(indices):
        image = samples[index].image
        contained = ImageOps.contain(image, (thumb_width - 12, thumb_height - 12), Image.Resampling.LANCZOS)
        x = (slot % columns) * thumb_width + (thumb_width - contained.width) // 2
        y = (slot // columns) * (thumb_height + label_height) + (thumb_height - contained.height) // 2
        sheet.paste(contained, (x, y))
        marker = " PEAK" if round(timestamps[index], 3) in event_peaks else ""
        label = f"{timestamp_label(timestamps[index])}{marker}  #{samples[index].index}"
        draw.text(
            ((slot % columns) * thumb_width + 10, (slot // columns) * (thumb_height + label_height) + thumb_height + 8),
            label,
            fill=(215, 255, 87),
            font=font,
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=88)


def timestamp_label(timestamp_ms: float) -> str:
    sign = "+" if timestamp_ms >= 0 else "-"
    return f"t{sign}{abs(timestamp_ms):.0f}ms"


def nearest_frame_index(timestamps: list[float], target_ms: float) -> int | None:
    if not timestamps:
        return None
    return min(range(len(timestamps)), key=lambda index: abs(timestamps[index] - target_ms))


def analyze(args: argparse.Namespace) -> int:
    manifest_path = args.capture.expanduser().resolve()
    manifest, samples = load_capture_frames(manifest_path)
    if not samples:
        raise ValueError("capture contains no frames")
    if args.max_frames and len(samples) > args.max_frames:
        stride = max(1, math.ceil(len(samples) / args.max_frames))
        samples = samples[::stride]
        if samples[-1].index != manifest.get("frames", [{}])[-1].get("index", samples[-1].index):
            samples.append(FrameSample(
                int(manifest["frames"][-1]["index"]),
                float(manifest["frames"][-1]["timestampMs"]),
                Image.open(resolve_frame_path(manifest_path.parent, manifest, manifest["frames"][-1]["file"])).convert("RGB"),
                "image",
            ))
    width, height = samples[0].image.size
    roi = parse_roi(args.roi, width, height)
    grays = [prepare_gray(sample.image, roi, args.max_analyze_width) for sample in samples]
    timestamps = [sample.timestamp_ms for sample in samples]
    trigger_ms = float(args.trigger_ms if args.trigger_ms is not None else 0.0)

    energies: list[float | None] = [None]
    baseline_diffs: list[float | None] = [None]
    pre_indices = [index for index, timestamp in enumerate(timestamps) if timestamp < trigger_ms - 20]
    baseline_indices = pre_indices[-max(1, args.baseline_frames):] if pre_indices else [0]
    baseline = np.median(np.stack([grays[index] for index in baseline_indices]), axis=0)
    for index in range(1, len(grays)):
        energies.append(float(np.mean(np.abs(grays[index] - grays[index - 1]))))
        baseline_diffs.append(float(np.mean(np.abs(grays[index] - baseline))))
    if len(energies) > 1:
        energies[0] = energies[1]
        baseline_diffs[0] = baseline_diffs[1] if baseline_diffs[1] is not None else 0.0

    threshold, pre_median = recommend_threshold(energies, timestamps, trigger_ms, args.threshold)
    intervals = [timestamps[index] - timestamps[index - 1] for index in range(1, len(timestamps))]
    positive_intervals = [value for value in intervals if value > 0]
    coverage_fps = 1000.0 / statistics.median(positive_intervals) if positive_intervals else None
    median_interval_for_gap = statistics.median(positive_intervals) if positive_intervals else 120.0
    event_gap_ms = args.event_gap_ms if args.event_gap_ms is not None else max(80.0, min(400.0, median_interval_for_gap * 2.5))
    events = group_events(timestamps, energies, threshold, trigger_ms, event_gap_ms)

    first_motion_ms = events[0]["startMs"] if events else None
    last_motion_ms = events[-1]["endMs"] if events else None
    peak_event = max(events, key=lambda event: event["peakEnergy"]) if events else None
    peak_motion_ms = peak_event["peakMs"] if peak_event else None
    motion_duration_ms = (
        max(0.0, float(last_motion_ms) - float(first_motion_ms))
        if first_motion_ms is not None and last_motion_ms is not None
        else None
    )

    metrics = [
        {
            "index": sample.index,
            "file": manifest.get("frames", [])[position].get("file") if position < len(manifest.get("frames", [])) else None,
            "timestampMs": round(timestamps[position], 3),
            "energy": round(float(energies[position] or 0.0), 4),
            "baselineDifference": round(float(baseline_diffs[position] or 0.0), 4),
            "active": bool(energies[position] is not None and energies[position] >= threshold and timestamps[position] >= trigger_ms - event_gap_ms),
        }
        for position, sample in enumerate(samples)
    ]

    checkpoint_metrics: dict[str, Any] = {}
    for checkpoint in args.checkpoint or []:
        index = nearest_frame_index(timestamps, checkpoint)
        if index is not None:
            checkpoint_metrics[str(checkpoint)] = {
                "frameIndex": samples[index].index,
                "timestampMs": round(timestamps[index], 3),
                "energy": round(float(energies[index] or 0.0), 4),
                "baselineDifference": round(float(baseline_diffs[index] or 0.0), 4),
            }

    contact_indices = choose_contact_frames(samples, timestamps, energies, events, trigger_ms)
    contact_sheet = manifest_path.parent / args.contact_sheet
    make_contact_sheet(samples, contact_indices, timestamps, events, contact_sheet)

    result = {
        "schemaVersion": 1,
        "kind": "motion-timing-analysis",
        "analyzedAt": utc_now(),
        "captureManifest": str(manifest_path),
        "scene": manifest.get("scene") or manifest.get("url") or manifest.get("device"),
        "source": manifest.get("source"),
        "threshold": {
            "energy": round(threshold, 4),
            "preTriggerMedian": round(pre_median, 4),
            "eventGapMs": round(event_gap_ms, 3),
            "mode": "explicit" if args.threshold is not None else "adaptive",
        },
        "coverage": {
            "frameCount": len(samples),
            "captureFrameCount": len(manifest.get("frames", [])),
            "medianIntervalMs": round(statistics.median(positive_intervals), 3) if positive_intervals else None,
            "effectiveFps": round(coverage_fps, 2) if coverage_fps else None,
            "timestampBasis": sorted({str(frame.get("timeBasis")) for frame in manifest.get("frames", [])}),
            "limitations": [
                "Effective FPS describes capture coverage, not application rendering performance.",
                "Snapshot-mode timestamps are host capture-window midpoints and include command latency.",
            ],
        },
        "roi": {"x": roi[0], "y": roi[1], "width": roi[2], "height": roi[3], "sourceSize": [width, height]},
        "summary": {
            "firstMotionMs": first_motion_ms,
            "peakMotionMs": peak_motion_ms,
            "lastMotionMs": last_motion_ms,
            "motionDurationMs": round(motion_duration_ms, 3) if motion_duration_ms is not None else None,
            "eventCount": len(events),
        },
        "events": events,
        "checkpointMetrics": checkpoint_metrics,
        "frameMetrics": metrics,
        "artifacts": {
            "contactSheet": args.contact_sheet,
        },
    }
    analysis_path = manifest_path.parent / args.json_output
    analysis_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Motion Timing Analysis",
        "",
        f"- Capture: {manifest_path}",
        f"- Source: {result['source']}",
        f"- Frames analyzed: {len(samples)}",
        f"- Capture coverage: {result['coverage']['effectiveFps']} effective FPS",
        f"- Activity threshold: {result['threshold']['energy']} ({result['threshold']['mode']})",
        "",
        "## Summary",
        "",
        f"- First motion: {first_motion_ms if first_motion_ms is not None else 'not detected'} ms",
        f"- Peak motion: {peak_motion_ms if peak_motion_ms is not None else 'not detected'} ms",
        f"- Last motion: {last_motion_ms if last_motion_ms is not None else 'not detected'} ms",
        f"- Motion duration: {result['summary']['motionDurationMs'] if result['summary']['motionDurationMs'] is not None else 'not detected'} ms",
        "",
        "## Events",
        "",
    ]
    if events:
        for index, event in enumerate(events, start=1):
            lines.append(
                f"{index}. start {event['startMs']} ms, peak {event['peakMs']} ms, "
                f"end {event['endMs']} ms, peak energy {event['peakEnergy']}"
            )
    else:
        lines.append("No activity crossed the threshold.")
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- This report measures visible frame changes, not semantic property values.",
            "- Capture coverage is not a performance claim.",
            "- Snapshot capture cannot establish 60 FPS behavior; use a high-rate recording or device trace for that claim.",
            "",
            f"Contact sheet: {contact_sheet}",
        ]
    )
    (manifest_path.parent / args.markdown_output).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "analysis": str(analysis_path), "contactSheet": str(contact_sheet)}, ensure_ascii=False))
    return 0


def load_analysis(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("kind") != "motion-timing-analysis":
        raise ValueError(f"not a timing analysis: {path}")
    return data


def compare(args: argparse.Namespace) -> int:
    reference = load_analysis(args.reference.expanduser().resolve())
    target = load_analysis(args.target.expanduser().resolve())
    tolerance = args.tolerance_ms
    known_keys = {
        "firstMotionMs": "firstMotion",
        "peakMotionMs": "peakMotion",
        "lastMotionMs": "lastMotion",
    }
    requested = [item.strip() for item in args.checkpoints.split(",") if item.strip()]
    unknown = [item for item in requested if item not in known_keys]
    if unknown:
        raise ValueError(f"unknown compare checkpoints: {unknown}; choose from {sorted(known_keys)}")
    keys = tuple((key, known_keys[key]) for key in requested)
    rows: list[dict[str, Any]] = []
    passed = True
    for key, label in keys:
        ref_value = reference.get("summary", {}).get(key)
        target_value = target.get("summary", {}).get(key)
        if ref_value is None or target_value is None:
            rows.append(
                {
                    "checkpoint": label,
                    "referenceMs": ref_value,
                    "targetMs": target_value,
                    "deltaMs": None,
                    "withinTolerance": False,
                    "note": "one side was not detected",
                }
            )
            passed = False
            continue
        delta = float(target_value) - float(ref_value)
        within = abs(delta) <= tolerance
        passed = passed and within
        rows.append(
            {
                "checkpoint": label,
                "referenceMs": ref_value,
                "targetMs": target_value,
                "deltaMs": round(delta, 3),
                "withinTolerance": within,
            }
        )
    result = {
        "schemaVersion": 1,
        "kind": "motion-timing-comparison",
        "comparedAt": utc_now(),
        "reference": str(args.reference),
        "target": str(args.target),
        "toleranceMs": tolerance,
        "passed": passed,
        "rows": rows,
        "limitations": [
            "Cross-source timestamps include capture latency differences.",
            "A pass at coarse capture coverage only verifies ordering and approximate anchors.",
        ],
    }
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if passed or args.allow_failure else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subcommands.add_parser("analyze", help="Analyze one capture")
    analyze_parser.add_argument("capture", type=Path, help="Path to capture.json")
    analyze_parser.add_argument("--roi", help="Analysis ROI as X,Y,W,H; values in 0..1 are normalized")
    analyze_parser.add_argument("--trigger-ms", type=float, default=0.0, help="Trigger timestamp inside the trace")
    analyze_parser.add_argument("--threshold", type=float, help="Explicit mean absolute frame-energy threshold")
    analyze_parser.add_argument("--event-gap-ms", type=float, help="Gap that separates two motion events")
    analyze_parser.add_argument("--baseline-frames", type=int, default=3, help="Pre-trigger frames used for the baseline")
    analyze_parser.add_argument("--checkpoint", type=float, action="append", help="Timestamp in ms to report; repeatable")
    analyze_parser.add_argument("--max-analyze-width", type=int, default=320, help="Resize width used for metrics")
    analyze_parser.add_argument("--max-frames", type=int, default=0, help="Optional frame cap for very long captures")
    analyze_parser.add_argument("--json-output", default="analysis.json")
    analyze_parser.add_argument("--markdown-output", default="analysis.md")
    analyze_parser.add_argument("--contact-sheet", default="contact-sheet.jpg")
    analyze_parser.set_defaults(handler=analyze)

    compare_parser = subcommands.add_parser("compare", help="Compare two timing reports")
    compare_parser.add_argument("reference", type=Path, help="Reference analysis.json")
    compare_parser.add_argument("target", type=Path, help="Target analysis.json")
    compare_parser.add_argument("--tolerance-ms", type=float, default=50.0, help="Absolute anchor tolerance")
    compare_parser.add_argument(
        "--checkpoints",
        default="firstMotionMs,peakMotionMs,lastMotionMs",
        help="Comma-separated anchors to compare",
    )
    compare_parser.add_argument("--output", type=Path, default=Path("comparison.json"))
    compare_parser.add_argument("--allow-failure", action="store_true", help="Return success even when anchors miss tolerance")
    compare_parser.set_defaults(handler=compare)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return int(args.handler(args))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
