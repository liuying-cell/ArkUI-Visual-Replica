#!/usr/bin/env python3
"""Compare a reference screenshot with an ArkUI screenshot."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageEnhance
except ImportError as exc:  # pragma: no cover - dependency failure path
    raise SystemExit("Pillow is required: python -m pip install Pillow") from exc


def parse_grid(value: str) -> tuple[int, int]:
    try:
        cols_raw, rows_raw = value.lower().split("x", 1)
        cols, rows = int(cols_raw), int(rows_raw)
    except (ValueError, AttributeError) as exc:
        raise argparse.ArgumentTypeError("Grid must look like 8x16.") from exc
    if cols <= 0 or rows <= 0:
        raise argparse.ArgumentTypeError("Grid dimensions must be positive.")
    return cols, rows


def parse_background(value: str) -> tuple[int, int, int]:
    raw = value.lstrip("#")
    if len(raw) != 6:
        raise argparse.ArgumentTypeError("Background must be a six-digit hex color.")
    try:
        return tuple(int(raw[index : index + 2], 16) for index in (0, 2, 4))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Background must be a six-digit hex color.") from exc


def parse_crop(value: str) -> tuple[int, int, int, int]:
    try:
        x, y, width, height = (int(item) for item in value.split(","))
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError("Expected X,Y,WIDTH,HEIGHT.") from exc
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("Crop dimensions must be positive.")
    return x, y, width, height


def flatten(image: Image.Image, background: tuple[int, int, int]) -> Image.Image:
    image = image.convert("RGBA")
    canvas = Image.new("RGBA", image.size, (*background, 255))
    canvas.alpha_composite(image)
    return canvas.convert("RGB")


def load_region_config(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Could not read region config: {path}") from exc


def region_crop(
    value: object,
    name: str,
    image_size: tuple[int, int],
) -> tuple[int, int, int, int]:
    if not isinstance(value, list) or len(value) != 4:
        raise SystemExit(f"Region {name}: crop must be [x, y, width, height].")
    try:
        x, y, width, height = (int(item) for item in value)
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"Region {name}: crop values must be integers.") from exc
    if x < 0 or y < 0 or width <= 0 or height <= 0:
        raise SystemExit(
            f"Region {name}: crop requires non-negative x/y and positive width/height."
        )
    if x + width > image_size[0] or y + height > image_size[1]:
        raise SystemExit(
            f"Region {name}: crop {value} exceeds image size {list(image_size)}."
        )
    return x, y, width, height


def resolve_companion_path(
    value: object,
    fallback: Path,
    config_dir: Path,
) -> Path:
    path = Path(str(value)) if value else fallback
    if not path.is_absolute():
        path = config_dir / path
    return path.resolve()


def make_gate(
    label: str,
    mismatch_percent: float,
    worst_cell_mismatch_percent: float,
    mean_channel_error: float,
    fail_over: object,
    max_worst_cell: object,
    max_mean_error: object,
) -> dict:
    criteria = []
    limits = [
        ("regionMismatchPercent", mismatch_percent, fail_over, 100),
        ("worstCellMismatchPercent", worst_cell_mismatch_percent, max_worst_cell, 100),
        ("meanChannelError", mean_channel_error, max_mean_error, 255),
    ]
    for name, actual, maximum, upper in limits:
        if maximum is None:
            continue
        if isinstance(maximum, bool):
            raise SystemExit(f"{label}: {name} limit must be numeric.")
        try:
            limit = float(maximum)
        except (TypeError, ValueError) as exc:
            raise SystemExit(f"{label}: {name} limit must be numeric.") from exc
        if not math.isfinite(limit) or not 0 <= limit <= upper:
            raise SystemExit(f"{label}: {name} limit must be between 0 and {upper}.")
        criteria.append({
            "name": name,
            "actual": round(actual, 3),
            "maximum": round(limit, 3),
            "pass": actual <= limit,
        })
    if not criteria:
        return {
            "maxMismatchPercent": None,
            "maxWorstCellMismatchPercent": None,
            "maxMeanChannelError": None,
            "checks": [],
            "status": "not-configured",
        }
    def maximum_for(name: str):
        return next((x["maximum"] for x in criteria if x["name"] == name), None)
    return {
        "maxMismatchPercent": maximum_for("regionMismatchPercent"),
        "maxWorstCellMismatchPercent": maximum_for("worstCellMismatchPercent"),
        "maxMeanChannelError": maximum_for("meanChannelError"),
        "checks": criteria,
        "status": "pass" if all(x["pass"] for x in criteria) else "fail",
    }


def region_compare(
    region: dict,
    reference_path: Path,
    actual_path: Path,
    background: tuple[int, int, int],
    default_grid: tuple[int, int],
    default_fail_over: float | None,
    default_max_worst_cell: float | None,
    default_max_mean_error: float | None,
) -> dict:
    name = str(region.get("name") or "region")
    safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "-", name).strip("-") or "region"
    reference = flatten(Image.open(reference_path), background)
    actual = flatten(Image.open(actual_path), background)
    if "referenceCrop" not in region or "actualCrop" not in region:
        raise SystemExit(f"Region {name}: referenceCrop and actualCrop are required.")
    reference_box = region_crop(
        region["referenceCrop"],
        f"{name}.reference",
        reference.size,
    )
    actual_box = region_crop(
        region["actualCrop"],
        f"{name}.actual",
        actual.size,
    )
    reference = reference.crop(
        (
            reference_box[0],
            reference_box[1],
            reference_box[0] + reference_box[2],
            reference_box[1] + reference_box[3],
        )
    )
    actual = actual.crop(
        (
            actual_box[0],
            actual_box[1],
            actual_box[0] + actual_box[2],
            actual_box[1] + actual_box[3],
        )
    )

    preserve_aspect = bool(region.get("preserveAspect", True))
    vertical_align = str(region.get("verticalAlign", "top"))
    if vertical_align not in {"top", "center", "bottom"}:
        raise SystemExit(f"Invalid verticalAlign for region {name}: {vertical_align}")

    if preserve_aspect:
        scale = reference.width / actual.width
        scaled_height = max(1, round(actual.height * scale))
        scaled = actual.resize(
            (reference.width, scaled_height),
            Image.Resampling.LANCZOS,
        )
        aligned = Image.new("RGB", reference.size, background)
        if scaled_height <= reference.height:
            paste_y = 0 if vertical_align == "top" else (
                reference.height - scaled_height
                if vertical_align == "bottom"
                else (reference.height - scaled_height) // 2
            )
            aligned.paste(scaled, (0, paste_y))
        else:
            crop_y = 0 if vertical_align == "top" else (
                scaled_height - reference.height
                if vertical_align == "bottom"
                else (scaled_height - reference.height) // 2
            )
            aligned.paste(
                scaled.crop((0, crop_y, reference.width, crop_y + reference.height)),
                (0, 0),
            )
        actual = aligned

    if actual.size != reference.size:
        actual = actual.resize(reference.size, Image.Resampling.LANCZOS)

    try:
        threshold = int(region.get("threshold", 16))
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"Region {name}: threshold must be an integer.") from exc
    if not 0 <= threshold <= 255:
        raise SystemExit(f"Region {name}: threshold must be between 0 and 255.")
    grid_value = str(region.get("grid", f"{default_grid[0]}x{default_grid[1]}"))
    cols, rows = parse_grid(grid_value)
    difference = ImageChops.difference(reference, actual)
    channels = difference.split()
    maximum = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
    mismatch_mask = maximum.point(lambda value: 255 if value > threshold else 0)
    width, height = reference.size
    total = width * height
    diff_pixels = list(difference.getdata())
    mismatch_count = mismatch_mask.histogram()[255]
    mean_error = sum(sum(pixel) for pixel in diff_pixels) / (total * 3)
    mismatch_percent = mismatch_count / total * 100

    cells = []
    for row in range(rows):
        y0 = round(row * height / rows)
        y1 = round((row + 1) * height / rows)
        for col in range(cols):
            x0 = round(col * width / cols)
            x1 = round((col + 1) * width / cols)
            cell_mask = mismatch_mask.crop((x0, y0, x1, y1))
            cell_diff = difference.crop((x0, y0, x1, y1))
            count = max(1, (x1 - x0) * (y1 - y0))
            cells.append({
                "row": row,
                "column": col,
                "box": [x0, y0, x1, y1],
                "mismatchPercent": round(
                    cell_mask.histogram()[255] / count * 100,
                    3,
                ),
                "meanChannelError": round(
                    sum(sum(pixel) for pixel in cell_diff.getdata()) / (count * 3),
                    3,
                ),
            })

    dimmed = ImageEnhance.Brightness(actual).enhance(0.35)
    heat_color = Image.new("RGB", reference.size, (255, 48, 72))
    diff_image = Image.composite(heat_color, dimmed, mismatch_mask)
    worst_cells = sorted(
        cells,
        key=lambda item: (item["mismatchPercent"], item["meanChannelError"]),
        reverse=True,
    )[:8]
    worst_cell_mismatch = worst_cells[0]["mismatchPercent"] if worst_cells else 0.0
    return {
        "name": name,
        "safeName": safe_name,
        "referenceCrop": list(reference_box),
        "actualCrop": list(actual_box),
        "preserveAspect": preserve_aspect,
        "verticalAlign": vertical_align,
        "threshold": threshold,
        "grid": {"columns": cols, "rows": rows},
        "global": {
            "meanChannelError": round(mean_error, 3),
            "mismatchPercent": round(mismatch_percent, 3),
            "worstCellMismatchPercent": round(worst_cell_mismatch, 3),
            "mismatchedPixels": mismatch_count,
            "totalPixels": total,
        },
        "gate": make_gate(
            name,
            mismatch_percent,
            worst_cell_mismatch,
            mean_error,
            region.get("failOver", default_fail_over),
            region.get("maxWorstCellMismatch", default_max_worst_cell),
            region.get("maxMeanChannelError", default_max_mean_error),
        ),
        "worstCell": worst_cells[0] if worst_cells else None,
        "worstCells": worst_cells,
        "_reference": reference,
        "_actual": actual,
        "_diff": diff_image,
    }


def compare_regions(args: argparse.Namespace) -> int:
    config = load_region_config(args.region_config)
    regions = config.get("regions")
    if not isinstance(regions, list) or not regions:
        raise SystemExit("Region config must contain a non-empty regions array.")
    reference_path = resolve_companion_path(
        config.get("reference"),
        args.reference,
        args.region_config.resolve().parent,
    )
    actual_path = resolve_companion_path(
        config.get("actual"),
        args.actual,
        args.region_config.resolve().parent,
    )
    for path in (reference_path, actual_path):
        if not path.is_file():
            raise SystemExit(f"Image not found: {path}")
    args.out.mkdir(parents=True, exist_ok=True)
    results = []
    for region in regions:
        result = region_compare(
            region,
            reference_path,
            actual_path,
            args.background,
            args.grid,
            args.fail_over,
            args.max_worst_cell_mismatch,
            args.max_mean_channel_error,
        )
        region_dir = args.out / str(result["safeName"])
        region_dir.mkdir(parents=True, exist_ok=True)
        result["_reference"].save(region_dir / "reference-crop.png")
        result["_actual"].save(region_dir / "actual-aligned.png")
        result["_diff"].save(region_dir / "diff.png")
        public_result = {
            key: value for key, value in result.items() if not key.startswith("_")
        }
        public_result["diffImage"] = str((region_dir / "diff.png").resolve())
        (region_dir / "metrics.json").write_text(
            json.dumps(public_result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        results.append(public_result)
    summary = {
        "reference": str(reference_path.resolve()),
        "actual": str(actual_path.resolve()),
        "regions": results,
    }
    (args.out / "regions-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    gates = [
        {
            "name": region["name"],
            "mismatchPercent": region["global"]["mismatchPercent"],
            **region["gate"],
        }
        for region in results
    ]
    counts = {
        "pass": sum(gate["status"] == "pass" for gate in gates),
        "fail": sum(gate["status"] == "fail" for gate in gates),
        "notConfigured": sum(gate["status"] == "not-configured" for gate in gates),
    }
    machine_status = (
        "fail"
        if counts["fail"]
        else "partial"
        if counts["notConfigured"]
        else "pass"
    )
    qa_summary = {
        "schemaVersion": 1,
        "mode": "regions",
        "automatedOnly": True,
        "manualReviewRequired": True,
        "visualStatus": "review-required",
        "machineStatus": machine_status,
        "reference": str(reference_path.resolve()),
        "actual": str(actual_path.resolve()),
        "regionCount": len(results),
        "statusCounts": counts,
        "gates": gates,
    }
    qa_path = args.out / "qa-summary.json"
    qa_path.write_text(
        json.dumps(qa_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 2 if machine_status == "fail" else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare reference and ArkUI screenshots and emit a diff heatmap."
    )
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--actual", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument(
        "--grid",
        default="8x16",
        type=parse_grid,
        help="Grid used to localize differences, for example 8x16.",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=16,
        help="Per-pixel maximum-channel error considered a mismatch (0-255).",
    )
    parser.add_argument(
        "--background",
        type=parse_background,
        default=(0, 0, 0),
        help="Hex background used to flatten transparency.",
    )
    parser.add_argument(
        "--resize-actual",
        action="store_true",
        help="Resize the actual screenshot to the reference dimensions.",
    )
    parser.add_argument(
        "--preserve-aspect",
        action="store_true",
        help="With --resize-actual, fit width proportionally and align the result.",
    )
    parser.add_argument(
        "--vertical-align",
        choices=("top", "center", "bottom"),
        default="top",
        help="Alignment when --preserve-aspect leaves extra or excess height.",
    )
    parser.add_argument(
        "--reference-crop",
        type=parse_crop,
        help="Crop the reference before comparison as X,Y,WIDTH,HEIGHT.",
    )
    parser.add_argument(
        "--actual-crop",
        type=parse_crop,
        help="Crop the actual screenshot before comparison as X,Y,WIDTH,HEIGHT.",
    )
    parser.add_argument(
        "--fail-over",
        type=float,
        default=None,
        help=(
            "Optional mismatch percentage gate. A matching pass returns exit 0; "
            "a failure returns exit code 2. Region failOver overrides it."
        ),
    )
    parser.add_argument(
        "--max-worst-cell-mismatch",
        type=float,
        default=None,
        help="Maximum mismatch percentage allowed in any single grid cell (0-100).",
    )
    parser.add_argument(
        "--max-mean-channel-error",
        type=float,
        default=None,
        help="Maximum mean channel error allowed per region (0-255).",
    )
    parser.add_argument(
        "--region-config",
        type=Path,
        help="JSON file describing independently aligned comparison regions.",
    )
    args = parser.parse_args()

    for path in (args.reference, args.actual):
        if not path.is_file():
            raise SystemExit(f"Image not found: {path}")
    if not 0 <= args.threshold <= 255:
        raise SystemExit("--threshold must be between 0 and 255.")
    if args.fail_over is not None and not 0 <= args.fail_over <= 100:
        raise SystemExit("--fail-over must be between 0 and 100.")
    if args.max_worst_cell_mismatch is not None and not 0 <= args.max_worst_cell_mismatch <= 100:
        raise SystemExit("--max-worst-cell-mismatch must be between 0 and 100.")
    if args.max_mean_channel_error is not None and not 0 <= args.max_mean_channel_error <= 255:
        raise SystemExit("--max-mean-channel-error must be between 0 and 255.")
    if args.region_config:
        if not args.region_config.is_file():
            raise SystemExit(f"Region config not found: {args.region_config}")
        return compare_regions(args)

    reference_full = flatten(Image.open(args.reference), args.background)
    actual_full = flatten(Image.open(args.actual), args.background)
    original_reference_size = reference_full.size
    original_actual_size = actual_full.size

    reference = (
        reference_full.crop(
            (
                args.reference_crop[0],
                args.reference_crop[1],
                args.reference_crop[0] + args.reference_crop[2],
                args.reference_crop[1] + args.reference_crop[3],
            )
        )
        if args.reference_crop
        else reference_full
    )
    actual = (
        actual_full.crop(
            (
                args.actual_crop[0],
                args.actual_crop[1],
                args.actual_crop[0] + args.actual_crop[2],
                args.actual_crop[1] + args.actual_crop[3],
            )
        )
        if args.actual_crop
        else actual_full
    )
    args.out.mkdir(parents=True, exist_ok=True)
    if args.reference_crop:
        reference.save(args.out / "reference-crop.png")
    if args.actual_crop:
        actual.save(args.out / "actual-crop.png")

    reference_size = reference.size

    if actual.size != reference.size:
        if not args.resize_actual:
            raise SystemExit(
                "Screenshot dimensions differ: "
                f"reference={reference.size}, actual={actual.size}. "
                "Capture at the same viewport or pass --resize-actual."
            )
        if args.preserve_aspect:
            scale = reference.width / actual.width
            scaled_height = max(1, round(actual.height * scale))
            scaled = actual.resize(
                (reference.width, scaled_height),
                Image.Resampling.LANCZOS,
            )
            aligned = Image.new("RGB", reference.size, args.background)
            if scaled_height <= reference.height:
                if args.vertical_align == "top":
                    paste_y = 0
                elif args.vertical_align == "bottom":
                    paste_y = reference.height - scaled_height
                else:
                    paste_y = (reference.height - scaled_height) // 2
                aligned.paste(scaled, (0, paste_y))
            else:
                if args.vertical_align == "top":
                    crop_y = 0
                elif args.vertical_align == "bottom":
                    crop_y = scaled_height - reference.height
                else:
                    crop_y = (scaled_height - reference.height) // 2
                aligned.paste(
                    scaled.crop((0, crop_y, reference.width, crop_y + reference.height)),
                    (0, 0),
                )
            actual = aligned
            actual.save(args.out / "actual-aligned.png")
        else:
            actual = actual.resize(reference.size, Image.Resampling.LANCZOS)

    difference = ImageChops.difference(reference, actual)
    channels = difference.split()
    maximum = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
    mismatch_mask = maximum.point(lambda value: 255 if value > args.threshold else 0)

    width, height = reference.size
    diff_pixels = list(difference.getdata())
    total = width * height
    absolute_error = sum(sum(pixel) for pixel in diff_pixels)
    mean_channel_error = absolute_error / (total * 3)
    mismatch_count = mismatch_mask.histogram()[255]
    mismatch_percent = mismatch_count / total * 100

    cols, rows = args.grid
    cell_width = width / cols
    cell_height = height / rows
    cells = []
    for row in range(rows):
        y0 = round(row * cell_height)
        y1 = round((row + 1) * cell_height)
        for col in range(cols):
            x0 = round(col * cell_width)
            x1 = round((col + 1) * cell_width)
            cell_mask = mismatch_mask.crop((x0, y0, x1, y1))
            cell_diff = difference.crop((x0, y0, x1, y1))
            count = (x1 - x0) * (y1 - y0)
            mismatch = cell_mask.histogram()[255]
            error_sum = sum(sum(pixel) for pixel in cell_diff.getdata())
            cells.append(
                {
                    "row": row,
                    "column": col,
                    "box": [x0, y0, x1, y1],
                    "mismatchPercent": round(mismatch / count * 100, 3),
                    "meanChannelError": round(error_sum / (count * 3), 3),
                }
            )

    worst_cells = sorted(
        cells,
        key=lambda item: (item["mismatchPercent"], item["meanChannelError"]),
        reverse=True,
    )[:12]
    worst_cell_mismatch = worst_cells[0]["mismatchPercent"] if worst_cells else 0.0

    dimmed = ImageEnhance.Brightness(actual).enhance(0.35)
    heatmap = Image.new("RGB", reference.size, (255, 48, 72))
    diff_image = Image.composite(heatmap, dimmed, mismatch_mask)
    diff_path = args.out / "diff.png"
    diff_image.save(diff_path)

    gate = make_gate(
        "global",
        mismatch_percent,
        worst_cell_mismatch,
        mean_channel_error,
        args.fail_over,
        args.max_worst_cell_mismatch,
        args.max_mean_channel_error,
    )
    metrics = {
        "reference": str(args.reference.resolve()),
        "actual": str(args.actual.resolve()),
        "dimensions": {
            "referenceOriginal": list(original_reference_size),
            "reference": list(reference_size),
            "actualOriginal": list(original_actual_size),
            "comparedActual": list(actual.size),
            "resized": original_actual_size != reference_size,
            "scaleMode": (
                "preserve-aspect-fit-width"
                if args.resize_actual and args.preserve_aspect
                else "stretch"
                if args.resize_actual
                else "none"
            ),
            "verticalAlign": args.vertical_align if args.preserve_aspect else None,
        },
        "crops": {
            "reference": list(args.reference_crop) if args.reference_crop else None,
            "actual": list(args.actual_crop) if args.actual_crop else None,
        },
        "threshold": args.threshold,
        "grid": {"columns": cols, "rows": rows},
        "global": {
            "meanChannelError": round(mean_channel_error, 3),
            "mismatchPercent": round(mismatch_percent, 3),
            "worstCellMismatchPercent": round(worst_cell_mismatch, 3),
            "mismatchedPixels": mismatch_count,
            "totalPixels": total,
        },
        "gate": gate,
        "worstCell": worst_cells[0] if worst_cells else None,
        "worstCells": worst_cells,
        "diffImage": str(diff_path.resolve()),
    }
    metrics_path = args.out / "metrics.json"
    metrics_path.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    machine_status = (
        "fail" if gate["status"] == "fail"
        else "partial" if gate["status"] == "not-configured"
        else "pass"
    )
    qa_summary = {
        "schemaVersion": 1,
        "mode": "single",
        "automatedOnly": True,
        "manualReviewRequired": True,
        "visualStatus": "review-required",
        "machineStatus": machine_status,
        "reference": metrics["reference"],
        "actual": metrics["actual"],
        "gates": [{"name": "global", **gate}],
    }
    qa_path = args.out / "qa-summary.json"
    qa_path.write_text(
        json.dumps(qa_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 2 if machine_status == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
