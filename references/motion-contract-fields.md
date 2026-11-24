# Motion Contract Fields

Read only the sections that apply to the selected scene. The base schema and acceptance rules remain in [motion contract](motion-contract.md).

## Contents

- [Scene Detail Fields](#scene-detail-fields)
  - [Progress](#progress)
  - [Path Following](#path-following)
  - [Mask Reveal](#mask-reveal)
  - [Gesture Axis](#gesture-axis)
  - [Ambient Timeline and Drag Ownership](#ambient-timeline-and-drag-ownership)
  - [Keyframes](#keyframes)
  - [Particles](#particles)
- [Interruptible Timeline Fields](#interruptible-timeline-fields)
- [Pausable Loops](#pausable-loops)
- [Clipped Loading Shimmer](#clipped-loading-shimmer)
- [Timing Validation](#timing-validation)

## Scene Detail Fields

### Progress

Use `progress` for scroll- or range-driven motion:

```json
"progress": {
  "start": 0,
  "end": 180,
  "unit": "vp",
  "clamped": true
}
```

Record whether the source API reports an absolute position or a per-frame delta. The contract describes the intended semantic; the implementation must normalize the platform callback accordingly.

For scroll-linked scenes, record the effective travel from the motion's 0% anchor to its 100% anchor. Use CSS pixels for the HTML reference and `vp` for the ArkUI target. For a pinned stage, use the distance over which the stage advances from start to finish. If the distance depends on the viewport, record the formula and the reference viewport.

An optional `progress.travel` entry can store both distances. This example uses the `11 Scroll` tuning. Choose values per scene based on how much progress a typical swipe should advance.

```json
"travel": {
  "reference": { "distance": 350, "unit": "css-px" },
  "target": { "distance": 350, "unit": "vp" }
}
```

### Path Following

When a marker follows a path, record the geometry and coordinate units in `trajectory`. Specify how animation progress maps to the path. Linear progress in the Bézier parameter generally produces variable speed along the curve. Linear progress in arc length produces constant speed. Use the mapping observed in the reference and record any easing separately. State whether the marker keeps a fixed orientation or follows the path tangent.

For a distance-based trail that supports seeking, record its length and units, fade along the trail, and visibility at the start and end. Use one cumulative arc-length table to locate the marker and derive the trailing segment at the current progress. Render both from that progress during playback, pause, and seeking so an equal progress reconstructs the same trail.

### Mask Reveal

For an animated mask, record its shape, center or anchor, coordinate space and units, and the starting and ending boundaries. Specify how animation progress maps to the boundary. For a circle, distinguish linear radius from linear area, and define whether area means the full circle or the visible area inside the content bounds. State whether the content stays fixed or moves with the mask, and which regions should be visible at each endpoint.

### Gesture Axis

Add `gesture.axis` and edge behavior when horizontal or vertical constraints matter:

```json
"gesture": {
  "axis": "horizontal",
  "threshold": 0.2,
  "velocityHandoff": true,
  "edgeResistance": 0.28
}
```

### Ambient Timeline and Drag Ownership

Use this block when an object rotates or moves autonomously and the same object also accepts direct manipulation:

```json
"ambientTimeline": {
  "durationMs": 18000,
  "iterations": "infinite",
  "phase": "normalized-loop"
},
"interaction": {
  "activationDistanceVp": 8,
  "autoPauseOnDrag": true,
  "velocityUnit": "degrees-per-second",
  "maxAngularVelocity": { "yaw": 84, "pitch": 48 },
  "inertiaIntegration": "velocity * dtMs / 1000",
  "resumePolicy": "resume only if the user had not explicitly paused"
}
```

- Record the dead zone in logical units and use the same value as the gesture activation distance.
- A movement below the dead zone must not alter the pose or start inertia.
- State whether a user pause and a temporary drag pause are separate states. A resumed ambient timeline must not override an explicit pause.
- State velocity units and caps explicitly. Do not multiply degrees per second by a millisecond delta without converting to seconds.
- Require a post-release settled check: after inertia completes, the pose and animation region should remain stable until the next trigger or ambient resume.
- Cancel the ambient timeline and inertia in the component teardown path.
### Keyframes

Use `keyframes` when a property intentionally leaves and returns to a value:

```json
"keyframes": [
  { "at": 0.22, "scale": 0.82 },
  { "at": 0.56, "scale": 1.12 },
  { "at": 1, "scale": 1 }
]
```

Keep `durationMs` on the scene. The `at` values are normalized checkpoints, not ArkUI durations.

### Particles

Describe density and fallback cost:

```json
"particles": {
  "count": 12,
  "staggerMs": 16,
  "durationMs": 620,
  "fallback": "shared-progress declarative nodes; Canvas for larger counts"
}
```

Do not imply that browser particles and ArkUI `Particle` are visually identical without device verification.

For dense particle fields, record the seed and a deterministic freeze phase in the contract. Use the same seed and phase on the HTML and ArkUI sides to compare particle visibility at both the low and target densities. Capture playback at each density to verify that the particles actually move.

## Interruptible Timeline Fields

For shared-progress choreography, use `timeline` to record the range, per-element phase windows, keyframes within each local window, interpolation, and property values. Declare the settled `endpoints` for forward, reverse and re-trigger. Describe how cancellation selects the next start value and which run can commit the endpoint. State the velocity behavior explicitly when direction changes. See [the three-track example](../assets/motion-contract.batch-04.json).

## Pausable Loops

Record the playback period and seam, then define phase separately for pause, resume, and re-entry. When pause is a hold, preserve the last displayed phase and exclude the paused interval from playback time. Resume from that phase with the contracted direction and speed. On exit, specify how to dispose of the active run in either playback state. On re-entry, specify the initial phase and playback state, including whether any prior phase is restored.

## Clipped Loading Shimmer

For a sweep that wraps out of sight, record the following in the scene contract:

- **Band and path.** Give the band width and its start and end offsets as fractions of each placeholder's width. Record the duration, curve, shared or staggered phase, and each placeholder's clip shape.
- **Hidden interval.** Name the phases immediately before and after wrap where the entire band is outside the clip and the same base fill is visible. For a horizontal band of width `w` at left offset `x`, full exclusion requires `x + w <= 0` or `x >= 1`. Give both endpoints enough clearance to sample a hidden frame.
- **State and layout.** Record initial loading phase, what stops the loop, which layout slots stay fixed during content replacement, and the exit and re-entry behavior. Specify whether the next run starts at zero or resumes. Record the reduced-motion behavior and the evidence required for it.

## Timing Validation

Add optional 'timingValidation' to a scene when temporal parity matters. Keep it separate from the motion definition: it states how the implementation will be measured and accepted.

~~~json
"timingValidation": {
  "sampling": {
    "reference": "browser-screencast",
    "target": "emulator-window"
  },
  "checkpoints": [
    { "name": "first-visible-motion", "anchor": "firstMotionMs", "toleranceMs": 75 },
    { "name": "compression-peak", "anchor": "peakMotionMs", "toleranceMs": 75 }
  ],
  "evidence": {
    "comparison": "outputs/timing-comparison.json"
  }
}
~~~

Supported anchors are:

- 'firstMotionMs': the first visible frame change after the trigger.
- 'peakMotionMs': the largest visible frame-energy change.
- 'lastMotionMs': the end of the detected visible activity cluster.

For multi-track scenes, define track checkpoints before implementation. Name the element, visible property, crossing or keyframe, expected order, tolerance, and time origin. For example, select when each marker crosses 10% and 90% of its travel, align the two traces on the lead marker's 10% crossing, and record the relative deltas. Record relative phase timing from the same visible crossing in both traces. Give input-to-first-motion latency its own origin tied to the actual input event. A visible marker emitted by the callback measures callback-to-first-motion, while an HDC return timestamp is a command-relative origin. Label the origin used in the report. Add a handoff check around each reversal and verify the latest requested endpoint.

Rules:

- Name the sampling methods. Do not compare a 60 FPS reference against sparse stills and call the comparison exact.
- Set tolerance from capture uncertainty. A 50-75 ms tolerance is typical for cross-source high-rate capture; sparse HDC stills need a wider range or only ordering evidence.
- Keep 'evidence' paths relative to the delivery package, not one developer machine.
- A timing pass does not prove visual parity for properties that do not produce enough frame change to exceed the analysis threshold.

The analyzer creates 'analysis.json', 'analysis.md', and a contact sheet. The comparator records every anchor delta and whether it is within tolerance.
