# Image Visual Analysis

Use this reference when the source is a screenshot, design image, or exported
mockup.

## Establish the Page Boundary

Inspect the whole image first, then zoom into the target. Distinguish the
actual application page from browser chrome, a device frame, presentation
background, annotations, and neighboring screenshots.

If the image contains several pages or unlabeled states, choose the region the
user named. If the intended region remains ambiguous, ask rather than combining
unrelated screens.

Use the source image's visible page rectangle as evidence. Do not assume that
its pixel dimensions equal ArkUI `vp`. If the user supplied a target device or
reference viewport, use that for implementation and verification.

## Derive the Visual Model

Build the model in this order:

1. page regions and reading order;
2. component grouping and repeated patterns;
3. background, surface, text, semantic, and accent color roles;
4. typography hierarchy, weights, alignment, and line spacing;
5. spacing scale, card radii, borders, shadows, and icon sizes;
6. size intent: fill, hug, fixed, ratio, weighted, min/max;
7. decorative layers and autonomous motion evidence.

Sample colors from clean areas, not antialiased text edges or glows. Treat
gradients and shadows as ranges rather than one flat color.

## Handle Missing Evidence

A single image cannot reveal:

- off-screen content or scroll behavior;
- hidden, selected, empty, and error states;
- hit targets or interaction behavior;
- exact animation timing;
- exact font files;
- widths outside the captured device.

Record assumptions that affect visual implementation. Do not fabricate unseen
details merely to complete a component. If motion is visible but timing cannot
be inferred reliably, implement a restrained loop that matches the perceived
effect and report the uncertainty.

## Complex Effects

For star fields, nebula clouds, rings, masks, refraction, noise, and
multi-layer glow:

- separate the effect from the content tree;
- determine whether ArkUI effects suffice;
- propose a Canvas or Shape layer when needed;
- keep fixed background art as an image only when it is genuinely static and
  the user accepts the asset approach.

Never flatten the entire page into one image. Text and ordinary layout regions
must remain real ArkUI content.
