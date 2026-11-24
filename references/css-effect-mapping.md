# CSS Effect Mapping

Use this reference when the source relies on blur, masks, blend modes, noise,
multi-layer shadows, pseudo-elements, filters, or other compound visual effects.

## Decision Order

Choose the first option that preserves the intended visual:

1. **Verified native ArkUI equivalent.** Use native effects only when the result
   has been checked against the reference, not merely because an API exists.
2. **Independent pre-rendered decoration layer.** Pre-render only the decorative
   layer when browser filter chains, pseudo-elements, or multi-layer shadows
   have no stable native equivalent.
3. **Canvas or Shape layer.** Use custom drawing when the decoration must react
   to resize, motion phase, or runtime state.
4. **Report the limitation.** State the visual gap and the smallest viable
   fallback when none of the above can preserve fidelity.

Never flatten text, ordinary layout, or controls into a pre-rendered asset.

## Pre-Rendered Decoration Rules

- Keep text, lyrics, controls, cards, and ordinary backgrounds native.
- Render at the target physical scale, normally 2x for a 2x tablet.
- Preserve transparency and inspect the alpha edges.
- Match the source layer size, crop, opacity, blur, saturation, transform, and
  stacking order before placing it in ArkUI.
- Record the source effect values and output asset dimensions in the task notes.
- Compare the decoration inside its own local region as well as in the full page.
- Do not paste a cropped reference screenshot that contains text or controls.

## Common Cases

| Source effect | Preferred approach | Avoid |
|---|---|---|
| CSS pseudo-element with `background-image` + blur | Pre-render the pseudo-element as an alpha PNG | One `Image.blur()` with guessed size and opacity |
| Multiple box-shadows on one element | Native shadow only after local visual check; otherwise pre-render the shadow/decor layer | Collapsing every layer into one shadow |
| Backdrop blur over complex content | Use native backdrop blur when verified; otherwise simplify and report | Pretending a translucent color is equivalent |
| Mask-image fades over text | Use native opacity/geometry when possible; otherwise build a local mask layer | Masking the entire page image |
| Noise or grain overlay | Use a deterministic local texture asset | Adding random runtime pixels that drift between captures |
| Mix-blend-mode | Test native blend support; otherwise flatten only the decorative layers | Flattening the whole page |
| Complex SVG | Preserve SVG or use Shape/Canvas when integration allows | Converting text and layout to Canvas |
| CSS filter chain | Reproduce the chain in the pre-render source and verify locally | Mapping each filter to a different guessed ArkUI property |

## Verification

- Gate the decorative region separately with aggregate and worst-cell limits.
- Inspect the decoration boundary, color distribution, opacity, and layering.
- Check that the asset does not introduce a visible rectangular or oval edge.
- Compare a static frame and, when applicable, a motion frame.
- Treat a compound-effect mismatch as a fidelity issue, not as a reason to lower
  the evidence level or relax the threshold.