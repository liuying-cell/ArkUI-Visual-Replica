# Motion QA

Verify the behavior, including intermediate states and endpoints. Use [motion QA patterns](motion-qa-patterns.md) only for the matching mask, loop, trail, scroll, tab, navigation, list, card, or 3D behavior.

## Contents

- [Evidence Levels](#evidence-levels)
- [Reference Capture](#reference-capture)
- [ArkUI Endpoint Checks](#arkui-endpoint-checks)
- [Interaction Checks](#interaction-checks)
- [Temporal Checks](#temporal-checks)
- [First Runtime Check](#first-runtime-check)
- [Single-scene QA](#single-scene-qa)
- [Accessibility](#accessibility)
- [Handoff](#handoff)

## Evidence Levels

Report exactly which levels were completed:

1. **Contract valid**: JSON structure and required behavior are present.
2. **Static check**: ArkTS and lint checks pass.
3. **Build verified**: the target module packages successfully.
4. **Runtime verified**: the app launches on a named device or emulator.
5. **Interaction verified**: every primary trigger, threshold, reverse, and interruption path was exercised.
6. **Temporal verified**: intermediate frames, timing, and continuity were inspected through recording or frame capture.
7. **Performance verified**: frame behavior and expensive effects were measured on the target device.

Do not describe level 3 as runtime verification or level 4 as temporal verification.

## Reference Capture

- Use a real browser, not source reading alone.
- Fix the viewport to the contract dimensions and hide browser chrome.
- Replay each trigger at normal speed and at 0.25x-0.5x speed.
- Capture initial, early, middle, overshoot, settled, reverse, and interrupted frames.
- Exercise rapid repeated input before recording acceptance evidence.
- Treat the post-script DOM or animation state as evidence; do not trust stale HTML literals.

## ArkUI Endpoint Checks

- The first visible frame matches the intended state.
- The final frame has no one-pixel offset, stale shadow, clipped radius, or flicker.
- Backdrop/scrim visibility matches the open ratio.
- Text and icons remain crisp during scaling.
- Safe areas and the navigation bar do not cover controls.
- Orientation change preserves or explicitly resets the motion state.

## Interaction Checks

- Tap while opening.
- Tap while closing.
- Drag while settling.
- Release below and above each snap threshold.
- Release with upward and downward velocity.
- Rapidly alternate the trigger three to five times.
- Switch scenes or routes during motion.
- Send the app to background and restore it.
- Verify that no timer or animation restarts unexpectedly after return.

## Temporal Checks

- Stagger order is correct and does not collapse into one simultaneous animation.
- Spring overshoot is intentional and bounded.
- Interrupted animation starts from the current rendered value.
- Shared geometry maintains one visual identity; the old and new copies do not both remain visible.
- Scrim and content fades stay synchronized with geometry.
- There is no visible snap when a JavaScript reference uses inherited velocity and ArkUI uses a spring.

## First Runtime Check

For multi-element motion, build one representative track and run it on the target before connecting the remaining tracks. Capture its start, an intermediate frame, and its endpoint. Choose a short recording if HDC stills miss the middle. A changing progress log or state label can coexist with a frozen marker. Inspect the actual moving property, especially across an `@Builder` boundary. Then connect the rest of the tracks and exercise the contracted interruption paths.

## Single-scene QA

Run from the skill directory, or use absolute paths to the script and scene file. Start the target app and confirm the device serial and scene coordinates. The configured clicks in bundled examples match their recorded layout.

After a viewport or layout change, including adding or removing tabs, read the current UI tree and update the device-pixel coordinates for scene entry, reset, and trigger. Inspect the first captured frame and recheck the ROI in that capture's coordinate space. The `expectedNodes` check confirms the configured node IDs and any specified initial text. Controls and the animation region can still move between layouts.

```powershell
python scripts/run_motion_qa.py assets/motion-qa.reaction-burst.json --serial 127.0.0.1:5555 --mode quick --output D:/codex-work/qa/burst
python scripts/run_motion_qa.py assets/motion-qa.reaction-burst.json --serial 127.0.0.1:5555 --mode timing --output D:/codex-work/qa/burst
```

- `quick` captures timestamped HDC stills and produces a sample sheet for checking the observed states and sequence.
- `timing` records the emulator, analyzes the selected motion region, and compares named anchors at the configured tolerance. Each mode falls back to `target.roi` when its own field is absent. Set a mode's ROI to `null` to analyze its full frame.
- Anchor each analysis ROI to its actual capture frame. `reference.roi` uses the browser capture, `target.quickRoi` uses the HDC snapshot at its output size (360 × 720 by default in the runner), and `target.timingRoi` uses the video frame after `target.crop` if configured. Define `X,Y,W,H` in frame pixels or fractions of that frame’s width and height. When setting up a mode or changing its capture settings, inspect one frame from that mode and verify that the ROI fits inside it and covers the intended motion. The analysis JSON records the resolved region and frame dimensions.
- Set `reference.inputs` to all local dependencies used by the entry, including CSS, JavaScript, images and fonts. The baseline key includes reference file hashes, viewport, trigger, analysis settings, and the browser executable identity. Keep the same output directory for repeated runs. Use `--refresh-reference` for changes outside the declared local inputs.
- Set `target.triggerClick` or `target.triggerSwipe` in device pixels. Optional `target.resetClick` prepares a known starting state before recording. Set the device with `--serial` or `target.serial`. Run the changed scene before expanding to related scenes.
- Each run prints the path to `report.json` and includes elapsed time. Timing exit codes are 0 for pass, 1 for mismatch, and 2 for insufficient evidence or a tool error. Quick mode exits 0 when the sample sheet is ready for review. Inspect the sampled frames or recording for the intended state, motion continuity, and any overlapping windows.
- Timing reports include the input command interval when available. The current desktop recorder uses command return as its comparison origin. Interpret first-motion deltas in light of that interval. Capture coverage describes the recording cadence. Use device frame profiling to measure app FPS.
- Use `--target-capture <capture.json>` to reanalyze an earlier trace without connecting the device. An existing HDC capture works in quick mode. Timing mode requires an emulator recording with sufficient capture coverage.

### Live scene and initial-state check

Set `target.expectedNodes` to a list of `{ "id": "control-id" }` entries for stable scene nodes. Require exact visible UI-tree text for a state marker with `{ "id": "state-id", "text": "START" }`. The runner checks these entries after `resetClick` and before baseline capture or playback. A failure exits with code 2 and records the missing ID or unexpected text in `report.json`, retains any received layout, and attempts a diagnostic screenshot. Configs without `expectedNodes` and offline `--target-capture` runs use their existing flow.

See [scene setups](motion-examples.md#interruptible-timeline) for the timeline and text reveal fixtures. Use [timing and performance measurements](motion-measurement.md) when recording named anchors or profiling frames.

## Accessibility

- Provide a non-gesture control for every gesture-only action.
- Honor reduced-motion intent by shortening, replacing, or disabling nonessential motion.
- Do not flash rapidly or rely on color-only feedback.
- Keep touch targets reachable and independent of animation completion.
- Ensure content remains readable with animations disabled.

## Handoff

Use the [visual handoff](visual-qa.md#handoff) for the shared delivery details. Motion completion also requires a valid contract, launch on the named target, and execution of the applicable primary and interruption paths. Report the [motion evidence levels](#evidence-levels) actually completed, including any gaps.

List the contract path and exercised paths. For each timing comparison, identify the reference and target sampling methods, effective capture coverage, anchor deltas, tolerances, and whether the anchor passed, failed, or could not be resolved. State the unsupported effects and any timing or performance measurement gaps. See the [historical report examples](motion-examples.md#example-acceptance-reports) when a concrete format helps.
