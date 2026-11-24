# Region-Anchored Comparison

Use region comparison when the source frame and the ArkUI device do not share
the same aspect ratio, especially when a vertically expanding content region
would make a whole-page stretch misleading.

## Contents

- [Region Model](#region-model)
- [Config](#config)
- [Run](#run)
- [Outputs and Gates](#outputs-and-gates)

## Region Model

Split the page into regions with different vertical behavior:

- **top-anchored**: status bar, header, title, and any region whose top edge
  should match the source.
- **fill/body**: scrollable or content-driven regions that may become taller or
  shorter than the reference.
- **bottom-anchored**: tab bars, bottom controls, and fixed overlays whose
  bottom edge should match.

Give every region its own crop in the original reference image and the original
ArkUI screenshot. Crops use `[x, y, width, height]` pixels before any resizing.

## Config

Create a JSON config next to the screenshots. `reference` and `actual` may be
relative to the config file; if omitted, the command-line image paths are used.

```json
{
  "reference": "reference.png",
  "actual": "arkui.png",
  "regions": [
    {
      "name": "top",
      "referenceCrop": [0, 0, 390, 120],
      "actualCrop": [0, 96, 1170, 360],
      "verticalAlign": "top",
      "grid": "8x4",
      "failOver": 5
    },
    {
      "name": "body",
      "referenceCrop": [0, 120, 390, 500],
      "actualCrop": [0, 456, 1170, 1560],
      "verticalAlign": "center",
      "grid": "8x12",
      "failOver": 7,
      "maxWorstCellMismatch": 30,
      "maxMeanChannelError": 8
    },
    {
      "name": "bottom",
      "referenceCrop": [0, 620, 390, 80],
      "actualCrop": [0, 2340, 1170, 240],
      "verticalAlign": "bottom",
      "grid": "8x3",
      "failOver": 4
    }
  ]
}
```

`preserveAspect` defaults to `true`: width is matched first and the remaining
height is padded or cropped according to `verticalAlign`. Set it to `false`
only when stretching is intentional. `threshold` and `grid` may be overridden
per region. `failOver`, `maxWorstCellMismatch`, and
`maxMeanChannelError` are optional per-region gates; matching command-line
values are the fallbacks when a region omits them.

Verify crop coverage before trusting metrics. Define thresholds from the visual
risk budget before measuring the final result. A low average around a bad crop,
or a gate chosen to fit the current result, can hide a real failure.

## Run

Resolve the script against the skill folder:

```powershell
$skillRoot = "C:\path\to\arkui-visual-replica"
python "$skillRoot\scripts\compare_screenshots.py" `
  --reference "D:\path\reference.png" `
  --actual "D:\path\arkui.png" `
  --region-config "D:\path\regions.json" `
  --out "D:\path\diff" `
  --fail-over 8 `
  --max-worst-cell-mismatch 30 `
  --max-mean-channel-error 8
```

## Outputs and Gates

The helper writes:

- `<out>/<safeName>/reference-crop.png`;
- `<out>/<safeName>/actual-aligned.png`;
- `<out>/<safeName>/diff.png`;
- `<out>/<safeName>/metrics.json`;
- `<out>/regions-summary.json`;
- `<out>/qa-summary.json`.

Each region result includes `global.worstCellMismatchPercent`, `worstCell`, and
a `gate` object containing the effective limits, criterion-level checks, and
`status` (`pass`, `fail`, or `not-configured`).
`qa-summary.json` aggregates the machine result:

- `pass`: every evaluated gate passed;
- `fail`: at least one aggregate, worst-cell, or mean-error gate failed;
- `partial`: at least one region had no gate, while no gate failed.

`qa-summary.json` also sets `visualStatus: review-required`. The comparison tool
never grants visual acceptance. Inspect every region heatmap and the runtime
layout, then record the explicit manual visual status before reporting L3 or L4. Do not compare a
content-driven middle region as though it had fixed height.