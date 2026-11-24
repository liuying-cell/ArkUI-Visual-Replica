# Local HTML Capture

Use this reference when the source is a local `.html` file.

## Contents

- [Dependencies](#dependencies)
- [1. Inventory Before Rendering](#1-inventory-before-rendering)
- [2. Capture a Stable Reference](#2-capture-a-stable-reference)
- [3. Motion](#3-motion)
- [4. Assets and Fonts](#4-assets-and-fonts)
- [5. Multi-Page and Hidden States](#5-multi-page-and-hidden-states)

## Dependencies

The HTML capture helper requires:

- Node.js 22 or newer with the global `WebSocket` API (verified with Node 24);
- a Chromium-based Edge or Chrome browser.

It uses the browser's DevTools protocol directly and does not require npm
packages or Playwright. Pass `--browser` or set
`ARKUI_CAPTURE_BROWSER` when automatic browser discovery does not find the
expected executable.

The screenshot comparison helper requires Python Pillow.

## 1. Inventory Before Rendering

Inspect the HTML source for:

- screen containers such as `.screen`, `[data-page]`, or route sections;
- overlays, sheets, and dialogs;
- reference viewport and device-frame styling;
- local fonts, images, SVG symbols, Canvas, and external dependencies;
- autonomous animation declarations and reduced-motion behavior.

Replicate one clearly selected page. A source that visually presents eight
screens should normally produce eight separate tasks, not one interactive app.

## 2. Capture a Stable Reference

Run the bundled capture helper from this skill directory. Set `$skillRoot` to that directory; do not assume the current project directory contains `scripts/`.

```powershell
$skillRoot = "C:\path\to\arkui-visual-replica"
node "$skillRoot\scripts\capture_html_reference.js" `
  --html "D:\path\page.html" `
  --out "D:\path\work\arkui-reference" `
  --page "profile" `
  --selector ".phone" `
  --hide-selector ".demo-dock" `
  --visible-only `
  --width 375 `
  --height 811 `
  --wait-ms 1200 `
  --freeze-motion
```

`--page` matches an element by the `data-page` attribute and activates that
screen using the page's existing `active` class when present. `--selector`
controls what is captured, so a page and a containing device frame can be
selected together. `--hide-selector` is repeatable and removes prototype-only
controls such as demo panels before screenshot capture. Prefer a direct
selector when the source uses another convention:

`--visible-only` excludes hidden, zero-size, transparent, and `aria-hidden`
subtrees. Use it when selecting a full device frame that contains inactive
pages or closed overlays; otherwise hidden screens dominate the manifest.
`--viewport-only` also removes nodes clipped entirely outside the current
viewport. `--preserve-svg` retains zero-size SVG structural nodes when they
explain paths, masks, or `viewBox` geometry.

```powershell
$skillRoot = "C:\path\to\arkui-visual-replica"
node "$skillRoot\scripts\capture_html_reference.js" `
  --html "D:\path\page.html" `
  --selector ".screen.active" `
  --out "D:\path\work\arkui-reference" `
  --width 375 `
  --height 811
```

Use `--prep-js` with a small JavaScript file when an overlay or visual state
must be made visible before capture. The prep script runs in page context and
must not alter unrelated content. When the page exposes a preview query, pass
it with `--query` (for example `--query "stay=1"`). This applies it before the
page scripts run and records the resolved URL in `reference.json`. A query
that holds the current route leaves the original HTML and JavaScript intact.

The helper writes:

- `reference.png`: the captured target page;
- `reference.json`: viewport, target bounds, design variables, visual asset
  references, and a depth-limited computed-style tree.

Inspect the PNG with the image viewer. The JSON is evidence, not an instruction
to reproduce every literal number.

Every manifest node includes `inViewport` and `visibleRect`. `clippedBy`
identifies scroll or overflow ancestors that actually changed the visible
rectangle. Use this information to reproduce clipping relationships; do not
flatten a clipped screenshot into a coordinate-only drawing.

The manifest is collected after scripts run and after fonts/images settle.
When source HTML and rendered content disagree, use the manifest text and
rectangles. Do not copy stale literals from the original markup.

## 3. Motion

Capture two kinds of evidence:

- Use `--freeze-motion` for geometry and pixel comparison. It pauses animation
  at the frame reached after the load wait. For cross-runtime comparison at a
  named phase, select the intended animations in `--prep-js`, call
  `animation.pause()` and set `animation.currentTime` explicitly. Match that
  phase on ArkUI and recapture once with a different load wait to check drift.
  A CSS freeze does not stop JS timers or automatic navigation.
- Capture without that flag when the exact initial animated appearance matters.

Read animation names, duration, delay, iteration, direction, and easing from
the computed tree and CSS. Preserve looping environmental motion even though
user-triggered transitions are out of scope.

## 4. Assets and Fonts

Copy only assets actually used by the selected page into the HarmonyOS media
resources. Preserve aspect ratio and alpha. For fonts:

- use local font files supplied with the source;
- confirm the project can register and load them;
- report missing fonts instead of depending on a host machine font.

Remote URLs are dependencies, not captured assets. If the selected page needs
a remote asset and the task does not authorize downloading it, report the
dependency.

## 5. Multi-Page and Hidden States

For hidden screens, the capture helper can activate a matching `data-page`
element. For more complex hidden states, write a narrow `--prep-js` that makes
only the requested region visible at its intended size.

Do not implement the interaction that normally reveals that state. The final
ArkUI page should show the chosen visual state directly.
