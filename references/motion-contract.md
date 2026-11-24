# Motion Contract

Record the core behavior first. Open [conditional contract fields](motion-contract-fields.md) only when the scene uses progress, paths, masks, interruption, loops, particles, or timing validation.

## Contents

- [Required Fields](#required-fields)
- [Rules](#rules)
- [Scene Triggers](#scene-triggers)
- [Acceptance Language](#acceptance-language)
- [Allowed Scene IDs](#allowed-scene-ids)

## Required Fields

```json
{
  "schemaVersion": 1,
  "id": "spring-sheet",
  "source": {
    "type": "html",
    "path": "../index.html",
    "scene": "sheet",
    "viewport": { "width": 390, "height": 844, "unit": "css-px" }
  },
  "target": {
    "platform": "HarmonyOS NEXT",
    "apiLevel": 18,
    "unit": "vp"
  },
  "scenes": [
    {
      "id": "sheet",
      "trigger": { "type": "tap-or-pan" },
      "durationMs": null,
      "spring": { "response": 0.45, "dampingFraction": 0.82 },
      "properties": ["translateY", "scrim.opacity"],
      "gesture": {
        "follow": "sheet.translateY += pan.offsetY",
        "openThreshold": 0.35,
        "closeThreshold": 0.65,
        "velocityHandoff": true
      },
      "interruption": "Stop the spring on pointer down; continue from the current offset and inherited velocity.",
      "accessibility": "Provide an open/close button and honor reduced-motion preferences.",
      "performance": "Use transform only; avoid blur and layout animation during drag."
    }
  ]
}
```

## Rules

- Use one scene object per independently triggered motion behavior.
- Keep source viewport separate from target logical dimensions. Do not silently treat CSS pixels as `vp`.
- Use `durationMs: null` for pure spring motion whose duration is determined by the curve and distance.
- Describe threshold values as normalized ratios when the exact pixel value is device-sensitive.
- State interruption behavior explicitly. An empty or generic value such as "smooth" is not a contract.
- List only properties that visibly change. Mark browser-only effects in `fallback` or `notes`.
- Record reduced-motion behavior and performance constraints before implementation.

## Scene Triggers

Use stable trigger names such as:

- `scene-enter`
- `tap`
- `tap-or-pan`
- `scroll-progress`
- `state-change`
- `route-enter`
- `route-exit`
- `long-press`
- `drag-release`

## Acceptance Language

Write acceptance criteria as observable behavior:

- The sheet follows the pointer without lag and continues from its current position when dragging starts during settling.
- The shared object keeps one visual identity while its frame and corner radius interpolate.
- A rapid second tap reverses from the current frame without a one-frame reset.
- The final state settles at the selected snap point and remains stable.

Validate the JSON shape with:

```powershell
python scripts/validate_motion_contract.py assets/motion-contract.example.json
```
## Allowed Scene IDs

Use lowercase hyphen-case and unique IDs. Examples from bundled contracts include:

- `timeline-stagger`
- `gesture-spring-sheet`
- `shared-orb`
- `scroll-linked-header`
- `swipe-tabs`
- `reaction-burst`
