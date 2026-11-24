# Visual QA

Verification must match the reference viewport, visual state, and requested
evidence level.

## Contents

- [Evidence Levels](#evidence-levels)
- [Automated Checks](#automated-checks)
- [Machine QA Summary](#machine-qa-summary)
- [Manual Inspection](#manual-inspection)
- [Correction Order](#correction-order)
- [Acceptance](#acceptance)
- [Handoff](#handoff)

## Evidence Levels

Report the highest level that was fully completed:

| Level | Evidence |
|---|---|
| L0 | ArkTS/lint or equivalent source validation passed |
| L1 | The target module built successfully |
| L2 | The app launched and runtime layout evidence was captured on the explicit target |
| L3 | Reference and runtime screenshots were compared with region crops and manually inspected |
| L4 | L3 plus deterministic static frames and normal-motion frames were verified |

Levels are not interchangeable. A successful build remains L1 even if a device
was merely detected. A screenshot without manual review remains machine
evidence, not complete visual acceptance.

## Automated Checks

Resolve scripts against the skill folder, not the user's project directory:

```powershell
$skillRoot = "C:\path\to\arkui-visual-replica"
node "$skillRoot\scripts\capture_html_reference.js" --help
python "$skillRoot\scripts\compare_screenshots.py" --help
```

Run these checks in order when the environment supports them:

1. Run ArkTS and project lint checks.
2. Run the read-only [preflight](preflight.md) helper before device operations.
3. Build the target module.
4. Launch and capture the ArkUI screenshot and runtime layout tree with
   `capture_arkui_runtime.js` on an explicit device.
5. Reconcile major text and container bounds with the coordinate baseline.
6. Compare corresponding content regions with `compare_screenshots.py`.
7. Inspect the crops, heatmap, runtime tree, and source at the same state.

Use the project's visual-static flag for deterministic comparison:

```powershell
node "$skillRoot\scripts\capture_arkui_runtime.js" `
  --project "D:\path\HarmonyProject" `
  --device "127.0.0.1:5555" `
  --out "D:\path\work\runtime-static" `
  --visual-static `
  --hdc "D:\path\sdk\toolchains\hdc.exe" `
  --bundle-name "com.example.app" `
  --ability-name "EntryAbility"
```

Adapt [VisualMotion.ets](../assets/arkts/VisualMotion.ets) for a normal launch
and a frozen page frame; see [visual-motion.md](visual-motion.md).

## Machine QA Summary

Run a whole-image comparison first:

```powershell
python "$skillRoot\scripts\compare_screenshots.py" `
  --reference "D:\path\reference.png" `
  --reference-crop "0,44,440,908" `
  --actual "D:\path\arkui.png" `
  --actual-crop "0,137,1280,2695" `
  --out "D:\path\work\visual-diff" `
  --resize-actual `
  --preserve-aspect `
  --vertical-align top `
  --grid 8x16 `
  --fail-over 8 `
  --max-worst-cell-mismatch 30 `
  --max-mean-channel-error 8
```

It writes `diff.png`, cropped inputs, `metrics.json`, and
`qa-summary.json`. When the source and target aspects differ because body
height is content-driven, use [region-comparison.md](region-comparison.md)
instead of stretching the page.

`qa-summary.json` reports two separate states:

- `machineStatus: pass` when every evaluated aggregate, worst-cell, and mean
  error threshold passed;
- `machineStatus: fail` when any gate failed;
- `machineStatus: partial` when one or more checks have no configured gate;
- `visualStatus: review-required` is always set by the comparison script and
  must be replaced by an explicit manual acceptance decision before L3/L4.

Available gates are:

- `--fail-over`: region mismatch percentage;
- `--max-worst-cell-mismatch`: maximum mismatch percentage in any grid cell;
- `--max-mean-channel-error`: maximum mean channel error in the region.

A region config may set `failOver`, `maxWorstCellMismatch`, and
`maxMeanChannelError` per region. Define thresholds from the task's visual risk
before screen measurement. Changing them after seeing a result requires a
recorded reason and re-review of previous cases. Never lower a threshold merely
to obtain a pass.

## Manual Inspection

After the machine pass, inspect:

- missing, duplicated, or incorrectly clipped content;
- reading order and container hierarchy;
- text wrapping, line height, alignment, and truncation;
- gradients, borders, radii, shadows, opacity, and icon geometry;
- scroll and overflow relationships;
- page state, system chrome crops, and asset substitutions;
- autonomous motion without a static or phase mismatch.

## Correction Order

Fix visible problems in this order:

1. missing or clipped content;
2. container hierarchy and major region geometry;
3. typography and wrapping;
4. spacing and alignment;
5. colors, opacity, borders, radii, and shadows;
6. icons and asset scaling;
7. decorative effects and motion.

Run no more than two same-layer retries without new evidence. If two correction
rounds do not reduce the worst-region error, inspect the source structure, crop
selection, or available ArkUI API instead of continuing to tune numbers.

## Acceptance

Perfect pixel equality may be impossible because of font rasterization, device
scaling, animation phase, and unsupported browser effects. The result is
acceptable when:

- no material content is missing or clipped;
- major regions and alignment relationships match;
- typography and surface hierarchy read the same;
- custom effects preserve the intended visual rather than merely approximate a
  color;
- `machineStatus` is `pass`;
- manual inspection sets `visualStatus` to `accepted`;
- residual differences are localized, understood, and reported.

An aggregate pass with a failing worst-cell gate is a visual failure. Report the
failed gate and fix the affected region; do not average it away.

## Handoff

Visual completion requires a compilable native ArkUI artifact, a recorded coordinate baseline, and the post-JavaScript capture when HTML was the source. Apply the requested evidence level. L3/L4 require a runtime screenshot comparison and manual review.

Report the source and selected surface, reference viewport, destination project/module/component, changed files, checks run, and highest visual evidence level reached. Include the coordinate baseline and comparison artifacts used. Give `qa-summary.json` machine status and manual visual status separately. Describe observed differences, any custom-layer decision still needed, and behavior omitted by scope.
