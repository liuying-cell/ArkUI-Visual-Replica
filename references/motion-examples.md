# Motion Examples

Open the examples that match the requested behavior. Historical reports preserve the coverage and limitations of their original runs. Use [motion QA](motion-qa.md) for acceptance rules and current capture commands.

| Behavior | Reference and native example | Contract or QA |
|---|---|---|
| Staggered entrance, spring sheet, shared-element geometry | [HTML](../assets/html-motion-lab/index.html) · `intro` lab | [Contract](../assets/motion-contract.example.json) |
| Scroll-linked progress, swipe tabs, retriggerable burst | [HTML](../assets/html-motion-lab-02/index.html) · `scroll-and-burst` lab | [Contract](../assets/motion-contract.batch-02.json) · [Burst QA config](../assets/motion-qa.reaction-burst.json) |
| Navigation shared geometry, interruptible list, gesture card stack | [HTML](../assets/html-motion-lab-03/index.html) · `navigation-and-gestures` lab | [Contract](../assets/motion-contract.batch-03.json) |
| Reversible multi-element timeline | [HTML](../assets/html-motion-lab-04/index.html) · [ArkUI component](../assets/arkts/InterruptibleTimeline.ets) | [Contract](../assets/motion-contract.batch-04.json) · [Scene QA config](../assets/motion-qa.interruptible-timeline.json) |
| Text reveal with per-glyph timing | [HTML](../assets/text-reveal/index.html) · [Glyph measurement](../assets/text-reveal/measure_glyphs.py) | [Scene QA config](../assets/text-reveal/qa-config.json) |
| Deterministic ambient motion | [ArkUI helper](../assets/arkts/VisualMotion.ets) | [Visual motion guide](visual-motion.md) |
| Clipped loading shimmer and pausable loops | [Shimmer mapping](arkui-motion-patterns.md#clipped-loading-shimmer) | [Shimmer QA](motion-qa-patterns.md#clipped-loading-shimmer-checks) · [Loop QA](motion-qa-patterns.md#pausable-loop-checks) |
| Lit solid, planar tilt, and flip | [Volumetric mapping](arkui-motion-patterns.md#volumetric-3d-and-per-face-lighting) | [Solid QA](motion-qa-patterns.md#volumetric-solid-checks) · [Planar QA](motion-qa-patterns.md#planar-3d-tilt-and-flip) |
| Dense particles | [Particle contract guidance](motion-contract-fields.md#particles) | [Performance sampling](motion-measurement.md#performance) |

## Contents

- [Create a lab project](#create-a-lab-project)
- [Interruptible timeline](#interruptible-timeline)
- [Text reveal example](#text-reveal-example)
- [Example Acceptance Reports](#example-acceptance-reports)
  - [Gesture and Spring Sheet](#gesture-and-spring-sheet)
  - [Scroll Progress, Swipe Tabs, and Reaction Burst](#scroll-progress-swipe-tabs-and-reaction-burst)
  - [Shared Geometry, Interruptible List, and Card Stack](#shared-geometry-interruptible-list-and-card-stack)
  - [Lit Solid Cube](#lit-solid-cube)

## Create a lab project

Run [the lab helper](../scripts/materialize_motion_lab.py) from the skill root and choose a new project directory. The available labs are `intro`, `scroll-and-burst`, and `navigation-and-gestures`.

```powershell
python scripts/materialize_motion_lab.py scroll-and-burst "D:/path/to/work/scroll-lab"
```

The helper copies the [shared project](../assets/harmonyos-motion-lab) and applies the selected scene's files. Open the generated directory in DevEco Studio. If Hvigor reports `00306003`, recreate the lab under an actual ASCII path. A substituted drive letter may still resolve to the original path.

## Interruptible timeline

Use [the timeline scene config](../assets/motion-qa.interruptible-timeline.json) for the primary timing capture. Open the existing Motion Lab app and select `04 Timeline`. The config checks for `timeline-play` and `timeline-status=START`. The coordinates are from one Mate 90 Pro layout. Recheck the control bounds and capture crop on a different layout. For a settled reverse, make a copy of the config in the same folder with expected `timeline-status` text `END`, and run it in quick mode from `END`.

For rapid input, use the existing emulator recorder's `--trigger-shell` for three taps, or drive those taps on-device. Start the second and third taps while the outgoing runs are still moving. Confirm from app logs that both interrupted transitions started at an interior progress, their first callbacks stayed near the handoff values, and only the last run committed an endpoint. Inspect the recording around each reversal because state logs can look correct while a node stays frozen. Verify reduced motion separately by enabling it during playback and confirming an immediate settle, then tapping once more with motion still reduced.

Use a per-track position crossing when aggregate frame energy selects different events on the two platforms. For this sample, analyze 10% and 90% of each marker's measured travel and align the two traces at the lime marker's 10% crossing. This compares stagger and travel once motion is visible. Preserve the original trigger-relative result and its tolerance alongside this supplemental measurement. A multi-tap shell command's return occurs after the last tap, so use video-relative stages and the app's event timestamps for interruption review.

## Text reveal example

The [text reveal example](../assets/text-reveal/qa-config.json) contains separate regions for the two capture modes plus a `glyphTiming` block. In Motion Lab, select `05 Text` and confirm `待播放`. Switch away and return to reset the scene before another live run. Recheck the device coordinates if the viewport changes.

```powershell
python scripts/run_motion_qa.py assets/text-reveal/qa-config.json --serial 127.0.0.1:5555 --mode timing --output D:/codex-work/qa/text-reveal
python assets/text-reveal/measure_glyphs.py assets/text-reveal/qa-config.json "D:/codex-work/qa/text-reveal/run-example/report.json"
```

Use the actual report path printed by the timing run. The example measures each glyph's half-brightness crossing using the green-blue contrast in its slot, normalized to that slot's settled frame. It reports crossing order, per-glyph offsets from the first glyph, and the largest cross-platform difference. Adjust the frame dimensions, slot positions, and text when using a different reference layout. Check replay and immediate reveal separately in the recording. The glyph analyzer is specific to this lime-text sample and runs independently of the shared QA runner.

## Example Acceptance Reports

### Gesture and Spring Sheet

```text
Scene: gesture/spring sheet
Reference: index.html?scene=sheet, 390x844 CSS px
Target: HarmonyOS NEXT API 18, Mate 90 Pro emulator
Contract: valid
Static: ArkTS pass, lint pass
Build: pass
Runtime: launch pass
Interaction: tap open pass; drag close pass; rapid interruption not yet recorded
Temporal: endpoint screenshots pass; intermediate frames not captured
Performance: not measured
Remaining differences: scrim timing needs frame comparison
```

### Scroll Progress, Swipe Tabs, and Reaction Burst

```text
Scene: scroll-linked header
Reference: html-motion-lab-02, 390x844
Target: HarmonyOS NEXT API 18, Mate 90 Pro emulator
Static: pass
Build: pass
Runtime: pass
Overlay: visible after scroll
Interaction: upward and downward progress exercised
Temporal: endpoint screenshots; continuous scrolling not frame-measured
Performance: not measured

Scene: swipe tabs
Indicator sync after tap: pass
Indicator sync after swipe: pass
Edge resistance: implemented; not separately photographed
Rapid tap while settling: not yet recorded

Scene: reaction burst
Single trigger: pass
Rapid retrigger count: pass
Native Particle visibility: not observed in current emulator
Declarative particle fallback: visible
Temporal frames: captured with HDC at early and mid states
```

### Shared Geometry, Interruptible List, and Card Stack

~~~text
Scene: navigation shared geometry
Reference: html-motion-lab-03, 390x844
Target: HarmonyOS NEXT API 18, Mate 90 Pro emulator
Static: ArkTS pass; lint pass
Build: pass
Runtime: pass
Open: pass
Close: pass
Shared identity: endpoint pass; intermediate window capture showed a short compositor gap on one run
Timing: browser and target capture produced named anchors; cross-source Navigation start differs materially

Scene: interruptible list
Initial viewport: footer and 4-row set fit
Add/remove: pass
Rapid mode: pass; final state stable
Timing: first visible change is earlier than the browser reference; peak remains within the 75 ms comparison threshold

Scene: gesture card stack
Short release: not separately recorded
Swipe release: pass; exactly one card advanced after duplicate-end guard
Reset: pass
Timing: HDC stills show start, card swap, and settled state; sparse capture is ordering evidence only
~~~

### Lit Solid Cube

~~~text
Scene: lit solid cube
Reference: HTML 390x844, front/top/back deterministic phases
Target: HarmonyOS NEXT API 18, Mate 90 Pro emulator
Static: ArkTS pass; lint pass
Build: pass
Runtime: pass
Geometry: 3 faces visible at three-quarter poses; shared edges connected
Lighting: peak face changes with light orbit; neighboring faces differ
Pause: stage pixel diff 0 while paused
Micro touch: below 8 vp dead zone; stage pixel diff 0
Drag: pose changes; stage pixels stable after inertia
Temporal: HDC snapshots show light and peak-face order
Performance: not measured; sparse capture is not FPS evidence
~~~
