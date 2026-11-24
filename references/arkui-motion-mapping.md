# ArkUI Motion Mapping

Choose by behavior, not by API resemblance. Read the matching entry in [motion patterns](arkui-motion-patterns.md) only when the scene uses that behavior.

## Contents

- [Decision Table](#decision-table)
- [Core Translation Rules](#core-translation-rules)
- [Explicit Animation Pattern](#explicit-animation-pattern)
- [Interruptible Multi-element Timeline](#interruptible-multi-element-timeline)
- [Transition Pattern](#transition-pattern)
- [Gesture Pattern](#gesture-pattern)
- [Shared Element Pattern](#shared-element-pattern)
- [Curve Guidance](#curve-guidance)
- [Performance Rules](#performance-rules)

## Decision Table

| HTML behavior | Preferred ArkUI model | Avoid |
|---|---|---|
| CSS transition triggered by state | `animation` on animatable properties or explicit `animateTo` | Rebuilding the whole page per frame |
| Imperative multi-property state change | `this.getUIContext().animateTo(param, () => state = next)` | Independent timers per property |
| Multi-stage one-off timeline | `keyframeAnimateTo` | Chained fixed delays without cancellation |
| Reversible staggered timeline | `UIContext.createAnimator` feeding one observed progress value with per-element phase windows | Independent delayed tracks with competing finish callbacks |
| Insert/remove or `if` branch reveal | `transition(TransitionEffect...)` | Manual timer-driven removal when transition suffices |
| Shared card/image expansion | `geometryTransition(id)` inside `animateTo` | Fading between two unrelated copies |
| Navigation-level shared element | Navigation custom/shared transition | Replacing navigation with one page of hidden overlays |
| Drag with release physics | PanGesture + direct state update + `curves.springMotion` | CSS-like keyframe playback from the start |
| CSS perspective with card tilt or flip | [Planar 3D tilt and flip](arkui-motion-patterns.md#planar-3d-tilt-and-flip) | Using width or scale alone to represent perspective |
| CSS 3D volume, cube, or closed convex solid with per-face light | One Canvas model transform with projected vertices, backface culling, depth sorting, and normal lighting | Independently transformed face nodes when hierarchy depth ordering is unverified |
| Scroll progress | Scroll/List callbacks, progress state, transform/opacity | Sampling scroll position from a timer |
| Loop, pulse, ambient drift | Property animation with `iterations: -1` or a lifecycle-safe clock | Unbounded `setInterval` without cleanup |
| Loading shimmer with clipped placeholders | [Shared phase and local clipping](arkui-motion-patterns.md#clipped-loading-shimmer) | A sweep overlay that crosses the gaps between placeholders |
| Particle field, path trail, complex mask | Canvas or drawing | Hundreds of declarative nodes |
| CSS blur, backdrop filter, mix blend | Native blur/effect where supported, otherwise a labeled fallback | Claiming exact fidelity without device evidence |

## Core Translation Rules

1. **Preserve behavior before numbers.** Match trigger, order, interruption, and gesture response first. Calibrate duration and curve second.
2. **Use unified logical units.** Convert CSS pixels only after recording the reference viewport and target logical width. Do not multiply every value by one global scale by default.
3. **Prefer compositor-friendly properties.** Animate `translate`, `scale`, `rotate`, and `opacity` before `width`, `height`, `left`, `top`, or `margin`.
4. **Use spring semantics where the reference is physical.** Import `curves` from `@kit.ArkUI`; use `curves.springMotion(response, dampingFraction)` for interruptible, inherit-velocity motion. Do not add a fixed duration that the curve ignores.
5. **Make stale animation impossible.** Before a new imperative animation, ensure state is the current value. Rapid triggers should start from the rendered state, not the previous logical target.
6. **Keep state machines visible.** Use explicit states such as `closed`, `dragging`, `opening`, `open`, `closing` when a tap and gesture can race.
7. **Do not reset geometry on close.** For shared elements, set the transition id, animate the branch swap, then clear the id only after completion.

## Explicit Animation Pattern

```ts
import { curves } from '@kit.ArkUI';

@State expanded: boolean = false;

private toggle(): void {
  this.getUIContext().animateTo({
    duration: 420,
    curve: curves.cubicBezierCurve(0.2, 0.8, 0.2, 1)
  }, () => {
    this.expanded = !this.expanded;
  });
}
```

Attach visual properties to state and keep the `transition` or `geometryTransition` inside the animated state change.

## Interruptible Multi-element Timeline

Use one `UIContext.createAnimator` when several tracks must reverse or seek as a unit. Let `onFrame` update one component-local observed progress in `[0,1]`. Map it into clamped local windows and piecewise curves for each stable node. Drive transforms and opacity on the nodes so layout stays fixed. Keep a one-off sequence on `keyframeAnimateTo` when its contract only needs forward playback.

Keep the requested endpoint separate from the last applied progress. Capture that progress before cancellation, invalidate the old run ID, then cancel its animator. Start the new run at the captured progress and scale its duration by the remaining distance to preserve the absolute timeline rate. Check the run ID in frame and completion callbacks. Only the active run may commit an endpoint. Invalidate the run when its component disappears. Reduced motion can cancel and commit the active endpoint directly. A timeline reversal preserves position and flips direction. Use a physical model if the contract requires velocity continuity.

In the API 18 lab, a nested `@Builder` that received computed progress values by value stayed visually frozen while status text and progress logs advanced. The working version passes only fixed track metadata into the builder and reads observed progress from the animatable modifier expressions. A child component with a reactive `@Prop` is another way to connect the state. Review intermediate pixels after changing a binding boundary.

See [InterruptibleTimeline.ets](../assets/arkts/InterruptibleTimeline.ets) for the validated component and [its motion contract](../assets/motion-contract.batch-04.json) for phase values.

## Transition Pattern

```ts
if (this.showPanel) {
  Panel()
    .transition(
      TransitionEffect.OPACITY
        .combine(TransitionEffect.translate({ y: 40 }))
        .animation({ duration: 360, curve: curves.springMotion(0.5, 0.86) })
    )
}
```

Use asymmetric transitions when enter and exit timing differ. Verify that the first and last frames do not flash.

## Gesture Pattern

```ts
PanGesture({ fingers: 1, direction: PanDirection.Vertical })
  .onActionStart(() => {
    this.sheetOffsetAtStart = this.sheetOffset;
    this.cancelSettlingFromCurrentFrame();
  })
  .onActionUpdate((event: GestureEvent) => {
    this.sheetOffset = clamp(
      this.sheetOffsetAtStart + event.offsetY,
      this.openOffset,
      this.closedOffset
    );
  })
  .onActionEnd((event: GestureEvent) => {
    this.settleUsingThresholdAndVelocity(event.velocityY);
  })
```

Keep the direct-manipulation property update outside `animateTo`. Start animation only after release or when switching to an automatic state.

## Shared Element Pattern

```ts
private navigateObject(): void {
  this.geometryId = 'meridian-orb';
  this.getUIContext().animateTo({
    duration: 520,
    curve: curves.cubicBezierCurve(0.2, 0.8, 0.2, 1),
    onFinish: () => {
      this.geometryId = '';
    }
  }, () => {
    this.expanded = !this.expanded;
  });
}
```

Bind the same `.geometryTransition(this.geometryId)` to the in/out components. Pair it with `TransitionEffect.OPACITY` when content around the shared object must crossfade.

## Curve Guidance

- Short feedback or reversible UI: damped spring with no overshoot or slight overshoot.
- Page or large-surface movement: spring or a controlled cubic bezier; avoid excessive bounce for large objects.
- Stagger: delay by element order, not by chained completion callbacks.
- Loading/ambient loops: linear or breathing curves, with lifecycle cleanup and reduced-motion fallback.
- Scroll-linked motion: derive from progress and make it monotonic with scroll direction.

## Performance Rules

- Keep animation state local when only one component changes.
- Avoid constructing objects, parsing strings, or allocating arrays inside per-frame callbacks.
- Limit simultaneous blurred, shadowed, masked, or clipped layers.
- Stop ambient clocks in `aboutToDisappear`; restore timers after returning to foreground when required.
- Use Canvas for dense particles or custom paths and measure on the target device.
- A static screenshot cannot prove frame rate. Use screen recording, frame inspection, device traces, or explicit unverified reporting.
