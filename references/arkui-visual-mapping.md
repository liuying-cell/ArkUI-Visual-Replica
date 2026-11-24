# ArkUI Visual Mapping

Read the target project's existing components and tokens before applying this
guide. Existing project conventions win unless they prevent visual fidelity.

## Contents

- [Layout Intent](#layout-intent)
- [Units and Tokens](#units-and-tokens)
- [CSS Mapping](#css-mapping)
- [Typography](#typography)
- [Effects](#effects)
- [Animation](#animation)
- [Positioning During Calibration](#positioning-during-calibration)

## Layout Intent

Use the following size intents rather than per-element coordinates:

| Intent | Use |
|---|---|
| `fill` | Page widths, full-width separators, regions that consume free space |
| `hug` | Text, chips, icon controls, and content-sized rows |
| `fixed` | Stable platform details, small icons, borders, and non-scaling marks |
| `aspectRatio` | Circular planets, avatars, charts, and illustrated regions |
| `weighted` | Competing children in a row or column |
| `bounded` | Panels that grow but require min/max limits |

Prefer:

- `Column`, `Row`, `Stack`, `Flex`, `Grid`, `List`, and `Scroll` for structure;
- `RelativeContainer` for anchored relationships;
- `layoutWeight` and percentage sizing for available-space distribution;
- `aspectRatio` and `constraintSize` for proportional decorations;
- `align`, `justifyContent`, `margin`, `padding`, and `gap` for relationships.

Use absolute placement only when the source composition is intrinsically
overlapping and a normal layout tree cannot express it.

## Units and Tokens

- Use ArkUI `vp` values for layout and `fp` for text when supported by the
  target API.
- Convert source dimensions at the declared reference viewport; do not paste
  CSS pixels indiscriminately.
- Read the actual viewport width from `onAreaChange`. Keep phone content
  full-width, center a bounded content column on tablet and wide layouts, and
  derive one shared scale from that content width.
- Adapt
  [ResponsiveVisualScale.ets](../assets/arkts/ResponsiveVisualScale.ets) when
  the target project has no equivalent. Clamp the scale, then apply it to
  fixed illustration details and typography. Do not multiply flexible width
  intents by the same scale.
- Let vertical flow and line wrapping determine page height. Do not stretch
  vertical gaps to force a different device aspect ratio.
- Centralize colors, typography, spacing, radii, and repeated effect values.
- Convert browser-only color syntax such as `oklch()` to concrete HarmonyOS-safe
  color resources before code generation.
- Distinguish transparent overlays from solid colors and preserve alpha.

## CSS Mapping

| Source | ArkUI direction |
|---|---|
| Block flow | `Column` |
| Inline/flex row | `Row` with weights and alignment |
| Absolute overlap | `Stack` or `RelativeContainer` |
| CSS grid | `Grid` or nested proportional rows |
| Internal page scroll | `Scroll` or `List` |
| Fixed tab/bar | Layout sibling anchored at the intended edge |
| Aspect-ratio box | `aspectRatio` with width/height intent |
| Gradient background | ArkUI gradient modifier or custom Canvas layer |
| Border and shadow | ArkUI border/shadow modifiers using centralized tokens |
| Simple SVG icon | Preserve SVG as media or `Path`/`Shape` when integration permits |
| Complex SVG/Chart | Evaluate `Shape` first, then Canvas |
| Canvas/WebGL | ArkUI `Canvas` redraw with normalized drawing coordinates |
| Blur/filter/mask | Use verified ArkUI effect APIs; use a custom layer when unsupported |

Do not assume a CSS property has an equivalent. Check the installed SDK and
documentation when the result affects fidelity or compilation.

## Typography

Reproduce the font family only when the matching file is available. Preserve
role, size, weight, line height, letter spacing, alignment, and truncation.
Do not use truncation merely to avoid fixing the layout. If the source font
cannot be loaded, report the substitution and its visual impact.

## Effects

Split complex design effects into layers:

1. background gradient and noise;
2. glow and blur;
3. geometric paths or orbit lines;
4. stars and particles;
5. foreground content.

Use native effects for layers that map cleanly. Use Canvas for the layers that
need deterministic custom drawing. Draw in normalized coordinates and handle
component resize so that a custom layer does not become a fixed bitmap of one
screen size.

## Animation

Preserve autonomous entry and ambient animation:

- entrance motion and one-shot staged sequences;
- looping opacity, scale, rotation, shimmer, glow, and particle motion;
- source reduced-motion behavior when practical.

Omit interaction-triggered transitions such as button presses, tab changes, and
sheet opening. Use the animation API supported by the installed SDK; verify
rather than guessing exact method names.

Use [visual-motion.md](visual-motion.md) for a deterministic static-capture
mode. A frozen timer alone is not enough for declarative effects: set explicit
frozen opacity, scale, rotation, or Canvas state.

## Positioning During Calibration

A small absolute correction may be used after native layout is substantially
correct. Prefer adjusting alignment, padding, gap, width intent, line height,
or container bounds. Do not turn the entire component tree into a coordinate
canvas to chase a one-frame screenshot.
