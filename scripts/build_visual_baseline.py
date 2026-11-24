#!/usr/bin/env python3
"""Record the design/device coordinate relationship before coding."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover - dependency failure path
    raise SystemExit("Pillow is required: python -m pip install Pillow") from exc


def parse_pair(value: str) -> tuple[int, int]:
    try:
        left, right = value.lower().split("x", 1)
        width, height = int(left), int(right)
    except (ValueError, AttributeError) as exc:
        raise argparse.ArgumentTypeError("Expected WIDTHxHEIGHT.") from exc
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("Dimensions must be positive.")
    return width, height


def parse_crop(value: str) -> tuple[int, int, int, int]:
    try:
        x, y, width, height = (int(item) for item in value.split(","))
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError("Expected X,Y,WIDTH,HEIGHT.") from exc
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("Crop dimensions must be positive.")
    return x, y, width, height


def clipped_crop(
    size: tuple[int, int], crop: tuple[int, int, int, int] | None
) -> tuple[int, int, int, int]:
    if crop is None:
        return 0, 0, size[0], size[1]
    x, y, width, height = crop
    if x < 0 or y < 0 or x + width > size[0] or y + height > size[1]:
        raise ValueError(f"Crop {crop} exceeds image size {size}.")
    return x, y, width, height


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a visual coordinate baseline before ArkUI coding."
    )
    parser.add_argument("--reference-image", required=True, type=Path)
    parser.add_argument("--target-pixels", required=True, type=parse_pair)
    parser.add_argument("--design-width", required=True, type=float)
    parser.add_argument("--logical-width", type=float)
    parser.add_argument("--reference-crop", type=parse_crop)
    parser.add_argument("--target-crop", type=parse_crop)
    parser.add_argument("--safe-top-px", type=int, default=0)
    parser.add_argument("--safe-bottom-px", type=int, default=0)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    if not args.reference_image.is_file():
        raise SystemExit(f"Reference image not found: {args.reference_image}")
    if args.design_width <= 0:
        raise SystemExit("--design-width must be positive.")
    if args.logical_width is not None and args.logical_width <= 0:
        raise SystemExit("--logical-width must be positive.")

    reference_size = Image.open(args.reference_image).size
    target_size = args.target_pixels
    target_crop = args.target_crop
    if target_crop is None:
        target_crop = (
            0,
            args.safe_top_px,
            target_size[0],
            target_size[1] - args.safe_top_px - args.safe_bottom_px,
        )

    reference_box = clipped_crop(reference_size, args.reference_crop)
    target_box = clipped_crop(target_size, target_crop)
    reference_content = (reference_box[2], reference_box[3])
    target_content = (target_box[2], target_box[3])
    x_ratio = target_content[0] / reference_content[0]
    y_ratio = target_content[1] / reference_content[1]
    warnings: list[str] = []
    if abs(x_ratio - y_ratio) / max(x_ratio, y_ratio) > 0.01:
        warnings.append(
            "Reference and target content aspect ratios differ by more than 1%; "
            "compare separately cropped content, not a stretched full screenshot."
        )

    baseline = {
        "schemaVersion": 1,
        "reference": {
            "image": str(args.reference_image.resolve()),
            "imageSize": list(reference_size),
            "contentCrop": list(reference_box),
            "contentSize": list(reference_content),
            "contentAspectRatio": round(reference_content[0] / reference_content[1], 6),
        },
        "target": {
            "physicalSize": list(target_size),
            "logicalWidthVp": args.logical_width,
            "pixelDensity": (
                round(target_size[0] / args.logical_width, 6)
                if args.logical_width
                else None
            ),
            "safeTopPx": args.safe_top_px,
            "safeBottomPx": args.safe_bottom_px,
            "contentCrop": list(target_box),
            "contentSize": list(target_content),
            "contentAspectRatio": round(target_content[0] / target_content[1], 6),
        },
        "conversion": {
            "designWidth": args.design_width,
            "designToLogicalScale": (
                round(args.logical_width / args.design_width, 6)
                if args.logical_width
                else None
            ),
            "referenceContentToTargetX": round(x_ratio, 6),
            "referenceContentToTargetY": round(y_ratio, 6),
            "targetContentToReferenceX": round(1 / x_ratio, 6),
            "targetContentToReferenceY": round(1 / y_ratio, 6),
        },
        "warnings": warnings,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(baseline, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(baseline, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
