# Visual Failure Patterns

Use this reference when the implementation is drifting, the comparison is
inconclusive, or a shortcut would replace native layout with a static image.

| Failure | Symptom | Correction |
|---|---|---|
| Whole-page WebView | Page appears exact but is not native ArkUI | Rebuild with ArkUI components; use WebView only if the user explicitly changes scope |
| Whole-page background image | Text, accessibility, resizing, and motion are no longer native | Keep text and layout as ArkUI content; limit image assets to genuinely static art |
| Per-element absolute map | Every coordinate is copied and small device changes break the page | Convert to fill/hug/fixed/ratio/weighted/bounded intents |
| Global stretch | One width ratio is applied to gaps, fonts, and every box | Use a bounded content scale and let vertical flow determine height |
| Fixed page height | Large screens create empty gaps or small screens clip content | Use min/max constraints, scroll, and content-driven height |
| Source markup as truth | Text or layout differs from the browser after scripts run | Use the captured screenshot and post-JavaScript manifest |
| Manifest without screenshot | Rectangles are accurate but visual state or clipping is wrong | Capture and inspect the image at the same viewport and motion state |
| System chrome mixed in | Status or navigation bars dominate the diff | Remove matching chrome with explicit crops before comparison |
| Crop selection error | A real difference disappears because it was outside every region | Verify crop bounds, coverage, and edge alignment before trusting metrics |
| Ignored clipped ancestor | Hidden scroll/overflow geometry is reconstructed as visible content | Recreate the clipping relationship from `visibleRect` and `clippedBy` |
| Wrong hidden state | The wrong tab, overlay, or empty state is reproduced | Select one explicit page/state with a selector or preparation script |
| Silent font substitution | Line breaks and hierarchy shift after using a host font | Bundle the source font when possible; otherwise report the substitution |
| Motion approximated by timer only | Static capture still drifts or declarative effects remain random | Set an explicit frozen opacity/scale/rotation/Canvas frame |
| Global diff as proof | One aggregate percentage is reported as success | Inspect region heatmaps and manually verify missing content, clipping, type, and effects |
| Average hides a severe local error | Region average passes while one grid cell is far over budget | Add a worst-cell gate and fail the region; inspect the local crop |
| Post-hoc threshold fitting | Limits are lowered after seeing the result | Define the risk budget before final measurement; record and re-review any change |
| Machine pass treated as visual acceptance | `qa-summary.json` pass is reported as L3/L4 without manual review | Keep `machineStatus` and `visualStatus` separate; accept visually only after inspection |
| Device-free visual claim | Static checks are described as device-level verification | Report only the achieved evidence level |
| Unknown-device takeover | A hung check leads to stopping a shared emulator | Select another explicit target or wait for the owning session |
| Blind numeric retries | Two rounds of tuning do not reduce the worst-region error | Reinspect source structure, crop selection, or the available ArkUI API |