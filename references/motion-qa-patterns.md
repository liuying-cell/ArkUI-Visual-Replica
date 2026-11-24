# Motion QA Patterns

Use only the sections that match the requested behavior. Start from the core [motion QA](motion-qa.md) evidence and timing rules.

## Contents

- [Animated Mask Boundary Checks](#animated-mask-boundary-checks)
- [Pausable Loop Checks](#pausable-loop-checks)
- [Clipped Loading Shimmer Checks](#clipped-loading-shimmer-checks)
- [Seekable Trail Checks](#seekable-trail-checks)
- [Behavior-Specific Checks](#behavior-specific-checks)
  - [Scroll-Linked Header](#scroll-linked-header)
  - [Swipe Tabs](#swipe-tabs)
  - [Keyframe Burst](#keyframe-burst)
  - [Navigation Shared Geometry](#navigation-shared-geometry)
  - [Interruptible List](#interruptible-list)
  - [Gesture Card Stack](#gesture-card-stack)
  - [Planar 3D Tilt and Flip](#planar-3d-tilt-and-flip)
  - [Volumetric Solid Checks](#volumetric-solid-checks)

## Animated Mask Boundary Checks

Map both captures to the same content-local coordinates and compare intermediate frames at the contracted phases or visible crossings. For a circular reveal, measure from the specified center along several directions and use rays that reach the mask edge before hitting the content boundary. Check which layer is visible just inside and outside the expected edge, allowing for the agreed spatial tolerance and antialiasing. At the endpoints, check the specified coverage, including corners for a full reveal. If the animation supports reversal, inspect frames on both sides of the handoff to verify that the mask continues from the current boundary.

## Pausable Loop Checks

1. Pause at a visible phase away from the seam. Compare lossless crops of the moving region over a hold longer than one nominal cycle. Include an intermediate frame or a continuous recording to rule out a full rotation returning to the same position.
2. Compare the held pose with the first distinguishable movement after resume. Measure along the contracted direction across the seam when applicable. Record the first animation callback and the first visible movement separately, using the held pose as their shared phase reference. State the sampling method and tolerance for each measured result.
3. Exit separately while paused and while playing. Verify teardown and check the first visible pose after re-entry against the contracted initial phase and playback state. Corroborate the visual result with lifecycle events when available.

## Clipped Loading Shimmer Checks

1. Compare a motion frame near each clip edge against the unlit base in content-local coordinates. Check for leakage outside every rounded mask and record any tolerance for antialiasing or capture compression.
2. Capture adjacent samples on both sides of a real wrap. Confirm both show the same unlit base. Use the same placeholder and visible phase landmark, such as the band peak crossing its center, to measure the period on both platforms. Exclude peaks cut off by completion or exit and report the sampling interval and period delta. Capture cadence and application render FPS require separate evidence.
3. Complete loading while the band is visible. Compare the last loading frame and first loaded frame for slot alignment and a visible handoff. Observe the loaded state for at least one former cycle to check stability. Exit during a fresh sweep and verify cleanup and the contracted first frame on re-entry. When available, corroborate the visual evidence with lifecycle events.

## Seekable Trail Checks

For a trail defined by current progress, capture a settled intermediate frame, seek backward, then seek to the exact same progress and capture again in the same runtime. Compare the full canvas region to check marker position, tail extent and fade, and pixels left behind by the previous position. Use pixel equality for stable captures from the same runtime, or a documented tolerance when the capture pipeline varies.

## Behavior-Specific Checks

### Scroll-Linked Header

- Scroll upward and downward through multiple frames; confirm the header progress responds in both directions.
- Confirm the platform callback's offset units and semantics before mapping it to absolute progress.
- Take screenshots at rest and after scrolling; the condensed masthead, progress trace, and hero transform must all reflect the same progress.
- Verify overlays stay above the scrolling content after the list redraws.
- Resize or rotate the viewport and confirm the progress range still clamps correctly.

**Gesture sensitivity.** When tuning scroll travel, repeat the same input before and after the change from the same initial progress and viewport. Record the input type, swipe coordinates in device pixels and speed or duration. For browser wheel input, record the wheel delta. After scrolling settles, record the scroll position and progress change. If the contract specifies how many swipes should reach the end, verify that count from 0%.

**Reverse reconstruction.** Capture the stage at an exact intermediate progress, advance far enough to change the stage, reverse past the first point, then return to the same exact progress. For example, use `0.42 → 0.72 → 0.18 → 0.42` and compare the two 0.42 stage crops within the same runtime. Check the actual offset or full-precision progress because the visible percentage may be rounded. Use pixel equality for stable captures or record a tolerance if capture varies. If a test-only scroll controller sets the exact positions, record that method and verify touch input on the delivery build.

### Swipe Tabs

- Tap every segment; the content and indicator must land on the same index.
- Swipe left and right; `onChange` must update the custom indicator without a one-frame lag.
- Attempt a swipe at both ends; edge resistance must not move the track beyond the intended bound.
- Tap a tab while the swipe animation is still settling.
- Resize the segmented control and confirm the measured indicator width remains correct.

### Keyframe Burst

- Trigger the burst once and check the button compression, overshoot, rings, particles, and counter.
- Trigger twice faster than the first animation completes; counters must both register and the effect must restart cleanly.
- Disable motion, then trigger; the count must still change while animated decorations stay inactive.
- Confirm temporary particles and rings are cleared after completion and on page leave.
- On the target device, verify whether native `Particle` is visible. If not, record the fallback and do not claim visual parity.

### Navigation Shared Geometry

- Open the destination and confirm the source hero and destination hero keep one visual identity; there must not be two visible copies at rest.
- Close with the explicit destination control and with the system Back key where the platform supports it.
- Trigger open again immediately after pop; the shared id must not be stale or detached from the current node.
- Compare home, middle, and detail frames at high rate. If the emulator window recorder shows a single blank/compositor frame, repeat the test and inspect HDC endpoint snapshots before treating it as an app frame.
- Confirm the root page and destination both have a dark/opaque surface so a route swap cannot expose an unrelated system background.

### Interruptible List

- Initial rows: last row, count footer, and toolbar are all visible without clipping.
- Add and remove repeatedly faster than 340 ms; the final count and row order match the latest action.
- Rapid mode should finish with a stable list and no timers mutating after the scene is hidden.
- Inspect insertion order: the new row should enter from a clear offset/opacity state while existing rows reflow without a hard jump.

### Gesture Card Stack

- Perform a short release and verify it springs back to the same card.
- Perform a swipe or high-velocity release beyond the threshold and verify exactly one card advances.
- Guard against duplicate release callbacks; one swipe must not skip two cards.
- Inspect the card while dragging: translate/scale/2D rotation follow the pointer and the card does not jump on release.
- Reset while a fly-out animation is pending; the timer must not later overwrite the reset state.

### Planar 3D Tilt and Flip

- Compare reference and target at matched yaw and pitch. Measure the two projected side edges along their lengths and compare left/right ratios with a tolerance from the motion contract. Check that the intended near edge is longer and that reversing yaw with pitch held at zero swaps the longer edge. Retain a mid-drag capture as evidence of the projection.
- Record the side change on a yaw-only flip. Check the front, the narrow silhouette near edge-on, the first visible back, and the stable landing. Only one face should be visible at a time, and the back text should read in its original direction. Use a short recording when quick stills miss the switch.
- Release just below and just above the contracted drag threshold. Verify return to the current side and a single flip to the opposite side. Reverse from the back and check the settled pose again. Read the face and the state marker so a correct status cannot conceal stale artwork.

### Volumetric Solid Checks

- At a three-quarter pose, confirm that at least two side faces and one top or bottom face are visible with connected shared edges and perspective foreshortening. A single bright rectangle is not volumetric evidence.
- Confirm that visible faces do not share one flat tint. Record the peak face and compare at least two neighboring face luminances from the same frame.
- During autonomous rotation, capture a sequence that shows the light angle and peak face changing. Use it to prove that shading follows pose and normals, not a static texture.
- Pause the animation and compare two stage crops separated by several hundred milliseconds. Expected difference: zero, excluding system chrome.
- Test a movement below the contracted gesture dead zone. Convert the physical tap/drag distance to `vp` before judging it. The pose and stage pixels should remain unchanged and inertia must not start.
- Perform a real drag, then wait for inertia to finish. Capture immediately after settling, wait another second, and compare the animation region again. Expected difference: zero until the ambient timeline resumes.
- Check explicit pause, temporary drag pause, and resume ownership separately. A user who paused the scene must not have it resume merely because a drag ended.
- Keep HDC stills for endpoint, ordering, and coarse pose evidence. Do not infer sustained FPS from a 1–2 FPS HDC sequence. Use a validated high-rate recording or device counters for performance claims.
- Re-run the scene after switching tabs or routes and confirm that no previous animator continues updating the hidden or new scene.
