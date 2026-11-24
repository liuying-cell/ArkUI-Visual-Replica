# Deterministic Visual Motion

Autonomous visual motion is in scope, but screenshots and geometry checks need
a stable frame. Keep the normal animation and a deterministic test mode.

## Support Files

Copy [VisualMotion.ets](../assets/arkts/VisualMotion.ets) into the target
project's common utilities when the page needs timers or a static-capture flag.

Call `configureVisualTestFlags(want)` from `UIAbility.onCreate` and
`onNewWant`. The helper reads `freezeMotion=true` from launch parameters.

## Page Pattern

Use a short page-level watcher so a normal launch and a static launch share the
same component tree:

```ts
@StorageProp('visualTestFreezeMotion')
@Watch('syncVisualMotion')
private freezeMotion: boolean = false;

private readonly ambientClock: MotionClock = new MotionClock(900, () => {
  this.motionPhase = (this.motionPhase + 1) % 8;
  this.redrawCanvasLayer();
});

aboutToAppear(): void {
  this.syncVisualMotion();
}

aboutToDisappear(): void {
  this.ambientClock.stop();
}

private syncVisualMotion(): void {
  if (this.freezeMotion) {
    this.motionPhase = 2;
    this.redrawCanvasLayer();
  }
  this.ambientClock.setFrozen(this.freezeMotion);
}
```

Choose an explicit frame such as `motionPhase = 2`; do not freeze an arbitrary
timer value. Draw the frozen frame synchronously after the Canvas has an area.
For declarative looping animations, branch on `freezeMotion` and use fixed
opacity/scale/rotation values instead of only stopping a JavaScript timer.

Always stop timers in `aboutToDisappear`. Restore normal launch mode after a
static capture. Compare two static frames for zero drift, then compare normal
frames for the intended ambient motion. For guest screenshots, collect a short
on-device burst before transferring the files if host transfers miss visible
checkpoints. Timestamp the actual samples and exclude system launch overlays
from app-motion measurements. Use sparse captures for order and visible
change. Use higher-rate evidence for duration or frame-rate claims.
