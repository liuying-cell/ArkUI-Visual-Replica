# ArkUI Motion Patterns

Choose only the behavior sections needed by the selected scene. Pair each with [mapping rules](arkui-motion-mapping.md) and the matching [behavior QA](motion-qa-patterns.md).

## Contents

- [Verified Implementation Shapes](#verified-implementation-shapes)
- [Clipped Loading Shimmer](#clipped-loading-shimmer)
- [Scroll-Linked Motion](#scroll-linked-motion)
- [Swipe Tabs and Custom Indicator](#swipe-tabs-and-custom-indicator)
- [Keyframe and Burst Motion](#keyframe-and-burst-motion)
- [Navigation Shared Geometry](#navigation-shared-geometry)
- [Interruptible List Layout](#interruptible-list-layout)
- [Gesture Card Stack](#gesture-card-stack)
- [Planar 3D Tilt and Flip](#planar-3d-tilt-and-flip)
- [Volumetric 3D and Per-face Lighting](#volumetric-3d-and-per-face-lighting)
- [Ambient Timeline with Drag Takeover](#ambient-timeline-with-drag-takeover)

## Verified Implementation Shapes

Use these as tested starting points, not as a substitute for target verification.

| Behavior | Verified ArkUI shape |
|---|---|
| Scroll header | `List.onDidScroll` delta accumulation plus an explicit `zIndex` overlay |
| Swipe tabs | `Swiper` + `onChange` + measured custom indicator |
| Reaction burst | `keyframeAnimateTo` + delayed ring `animateTo` + shared-progress particles |
| Navigation shared geometry | `NavDestination` + `geometryTransition` + `animateTo` + `pushPath(..., false)` |
| Interruptible list | keyed `ForEach` + explicit `animateTo` + staggered `TransitionEffect` |
| Card stack | `PanGesture` + velocity threshold + spring return + guarded release |

## Clipped Loading Shimmer

- Clip each rounded placeholder independently. Move a gradient layer inside a fixed-size wrapper that matches the placeholder so percentage translation is relative to the placeholder width. Verify the native clip and transform reference on the target.
- For a synchronized linear sweep, a component-local `UIContext.createAnimator` can drive one normalized phase across all gradient translations. Start from the contracted phase. On load completion or scene teardown, clear the active animator reference before canceling it and ignore callbacks from older runs.
- Keep the placeholders and loaded content in the same layout slots. Commit the loaded state and stop the loop in the same UI action. If the scene provides a static reduced-motion variant, retain the same slots and base fill.

## Scroll-Linked Motion

- Use `onDidScroll` for `List`, `Grid`, `WaterFlow`, and `Scroll` state updates.
- Treat `onDidScroll`'s `scrollOffset` as the current-frame delta, not the total position. Accumulate it into clamped progress when the effect needs absolute progress:
  `progress = clamp(progress + delta / range, 0, 1)`.
- Bind only derived scalars and transform/opacity properties in the callback. Do not allocate large objects or write logs inside the high-frequency handler.
- Give overlay headers and progress traces an explicit `zIndex` or place them after the scrolling child. A scroll container drawn later can cover a nominal overlay.
- Use `onWillScroll` only when the motion must inspect or modify a frame before it is committed.

## Swipe Tabs and Custom Indicator

- Use native `Swiper` for the content drag and snapping. Do not rebuild horizontal pan physics unless the reference requires behavior Swiper cannot express.
- Keep the custom indicator index in sync through `Swiper.onChange`; tap controls should call `SwiperController.changeIndex(index, true)` rather than changing only local state.
- Measure the segmented-control inner width with `onAreaChange`, then translate the indicator by `index * segmentWidth`.
- Use `Swiper.duration` and its curve for page movement and a matching animated transform for the indicator.
- Do not name the state field `tabIndex`; it conflicts with an inherited ArkUI component property. Prefer `selectedTab`.

## Keyframe and Burst Motion

- Use `keyframeAnimateTo` for one-off segmented button feedback such as `1 → 0.82 → 1.12 → 1`.
- Reset counters immediately on tap even when motion is disabled. Motion is feedback, not the source of truth for state.
- Reset prior ring or particle state before a retrigger, then start a new animation. Clear lifecycle timers in `aboutToDisappear`.
- Button labels do not expose all `Text` attributes. For letter spacing or custom typography, build `Button() { Text(...) }` instead of `Button('label')`.
- `@Builder` bodies may contain UI declarations only. Declare local constants or computed vectors in fields or helper methods, not directly inside the builder.
- Avoid state-variable assignments directly inside a `for` loop in a page component; move the assignment into a helper method to satisfy ArkUI performance linting.
- Use a shared scalar progress for simple declarative particle bursts. Per-index animation arrays are easy to drift and are not automatically a reliable per-particle timeline.
- The native `Particle` component can be appropriate for dense or continuous systems. In the recorded reaction-burst emulator run, the configured `Particle` sample was not visible; keep a declarative fallback and verify `Particle` on the actual target device before treating it as the only implementation.

## Navigation Shared Geometry

- Use 'Navigation(pathStack)' with a registered 'navDestination' builder for page-level route scenes. Prefer a native 'NavDestination' over hidden overlay pages when route state and system back behavior matter.
- Disable the default page transition when the motion is explicitly composed: push or pop inside 'animateTo' and pass 'false' for the animated argument. In API 14+, also declare 'NavDestination.systemTransition(NavigationSystemTransitionType.NONE)' so the result is not dependent on the default transition.
- Bind the same 'geometryTransition(id)' to the source and destination nodes. Keep one identity: do not create a second orb/card copy that remains visible after the route switch.
- The route and shared node need a shared animated boundary. The sample uses 520 ms and a controlled cubic bezier; pop uses the same family of timing and the current geometry.
- Use an explicit labelled close control on the destination. The UI layout dump can return the root page even while the destination is visible; use the actual destination window or exact button bounds when automating UI tests.
- A high-rate window capture may expose a compositor/blank frame around a Navigation surface swap. Do not call that proof of an app defect; inspect HDC endpoint snapshots and repeat the capture before changing the animation.

## Interruptible List Layout

- Keep row identity stable and reassign a new array inside 'animateTo'. This lets ArkUI animate layout positions while the latest state wins.
- Apply 'transition(TransitionEffect...)' to each row for insertion/removal, and put the per-index stagger in the transition's animation delay.
- Rapid add/remove should not queue independent timers that mutate stale rows. Recompute the next array from the current state on every action and clear any repeating helper timer on disappearance.
- Keep the list viewport tall enough for the initial row set; extra rows can scroll. A fixed row height plus a known gap avoids the last row being clipped under the footer.
- Test repeated operations faster than one animation duration. The final state should be the one implied by the last action, not the last timer that happened to finish.

## Gesture Card Stack

- Use 'PanGesture' on the top card and write offsets, rotation, and scale directly during 'onActionUpdate'. Do not wrap direct manipulation in 'animateTo'.
- On release, use displacement plus 'event.velocityX' to choose fly-out versus spring-back. 'curves.springMotion(response, dampingFraction)' is appropriate for the return path; a short controlled bezier is appropriate for the fly-out.
- Guard 'onActionEnd' with an active-gesture boolean. Some automation paths can deliver a duplicate end callback; without a guard one swipe advances two cards.
- Keep the back cards declarative and static; only the top card needs per-frame state. This avoids animating a whole stack during every pointer move.
- The card stack sample uses a 2D approximation with rotation, scale, and translation. For a perspective card, use the mapping below.

## Planar 3D Tilt and Flip

Check the installed SDK declarations for the rotation signature. `rotate(RotateOptions)` has an axis vector (`x`, `y`, `z`) and `angle`, with `perspective` in physical pixels since API 10. The separate `RotateAngleOptions` signature uses per-axis angles. It and `transform3D()` are API 20. Verify the projected edges on the target before choosing a mapping.

For a single flat card targeting API 18, the lab verified `matrix4.init()` with `.transform()` on the Mate 90 Pro emulator. Use a `z = 0` plane, a centered pivot, and the same perspective distance relative to the card size on both platforms. The example applies `Perspective × rotateY(yaw) × rotateX(pitch)` with the rightmost rotation applied first. Pass radians and convert the logical camera distance to physical pixels with `this.getUIContext().vp2px(distanceVp)`. Keep the pitch magnitude below 90° for this face-selection rule, and choose a distance that keeps all corners in front of the camera.

```ts
import { matrix4 } from '@kit.ArkUI';

function cardProjection(yaw: number, pitch: number, distancePx: number): matrix4.Matrix4Transit {
  const cosYaw = Math.cos(yaw);
  const sinYaw = Math.sin(yaw);
  const cosPitch = Math.cos(pitch);
  const sinPitch = Math.sin(pitch);
  const faceDirection = cosYaw < 0 ? -1 : 1;
  // Column-major matrix. The x and y terms in w give the flat plane depth-dependent scale.
  return matrix4.init([
    Math.max(0.0002, Math.abs(cosYaw)), 0, 0, sinYaw * faceDirection / distancePx,
    sinYaw * sinPitch, cosPitch, 0, -cosYaw * sinPitch / distancePx,
    0, 0, 1, 0,
    0, 0, 0, 1
  ]);
}
```

Apply the transform to the card inside a fixed gesture surface. The small positive horizontal term keeps the matrix invertible at edge-on. Derive the visible artwork and projection from the same observed yaw. Switching artwork when `cos(yaw)` changes sign also reverses the card's local X direction in the projection so the back text stays readable. Bind the face's text, color, and projection to live state in the builder or through a reactive prop. Keep the release threshold separate from the face switch. Verify both with the [card geometry checklist](motion-qa-patterns.md#planar-3d-tilt-and-flip).

## Volumetric 3D and Per-face Lighting

Use one Canvas rendering surface when the reference object has real volume, multiple faces can occlude one another, and lighting varies per face. A `matrix4` transform remains appropriate for one flat plane. On API 18, do not assume a hierarchy of independently transformed face nodes will provide CSS `preserve-3d` depth ordering or stable shared edges.

Verified API 18 pipeline on Mate 90 Pro:

1. Define unit vertices plus indexed faces with outward normals.
2. Apply the exact same rotation order to both vertices and normals. In the verified sample the order was `Rz * Rx * Ry`.
3. Perspective-project every vertex:

   `scale = cameraDistance / max(epsilon, cameraDistance - z)`

   `screen = center + xy * scale`

   Keep vertex units, canvas units, and camera distance in the same coordinate system.
4. Cull a face when its transformed normal has `z <= epsilon`.
5. Sort visible faces by average transformed `z`, far to near, then fill them as screen-space polygons.
6. Shade each face from its transformed normal and one normalized light direction. Use the same diffuse/specular result for fill color, edge brightness, highlights, and face-label opacity.
7. Draw the visible light source and contact shadow from the same phase and coordinate space. Do not leave a debug ray that crosses in front of the solid unless the reference contains it.

Keep geometry, camera distance, and lighting in one place so a pose change cannot update the mesh without updating its normals.

```ts
interface Vec3 { x: number; y: number; z: number; }
interface ProjectedPoint { x: number; y: number; z: number; }

function projectVertex(point: Vec3, centerX: number, centerY: number, cameraDistance: number): ProjectedPoint {
  const scale = cameraDistance / Math.max(1, cameraDistance - point.z);
  return { x: centerX + point.x * scale, y: centerY + point.y * scale, z: point.z };
}
```

For a closed convex solid, culling plus depth sorting is usually enough. If faces intersect, self-intersect, or need transparency, move to a dedicated 3D renderer or split polygons rather than adding ad-hoc z-index values.

## Ambient Timeline with Drag Takeover

When an autonomous rotation also accepts direct manipulation:

- Drive the ambient pose with one lifecycle-safe timeline, such as `AnimatorResult` with `iterations: -1`, and one observed phase.
- Use the gesture activation distance as the dead zone. Give `PanGesture({ distance })` the contracted value so a tap or tiny jitter does not start rotation.
- Keep user pause separate from temporary interaction pause. Pause the ambient timeline on drag start, but remember whether it should resume after inertia.
- Convert pointer velocity into the same units as the rotation state. The verified sample treated yaw/pitch velocity as degrees per second, capped yaw at 84 and pitch at 48, then integrated with `velocity * dtMs / 1000`. Treat these limits as calibrated examples, not universal values.
- Decay velocity with elapsed seconds. Do not multiply a per-second velocity by a raw millisecond frame delta.
- After inertia finishes, resume the ambient timeline only when the user had not explicitly paused it.
- Cancel ambient, inertia, and settling animators in `aboutToDisappear`; guard callbacks with the active animator identity.
- Regression-check a below-dead-zone nudge (the pose and stage pixels should stay unchanged) and a real drag (the pose should change, then become pixel-stable after inertia completes).
