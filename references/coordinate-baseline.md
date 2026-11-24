# Coordinate Baseline

Establish these values before writing ArkUI layout code. They prevent the
common failure where a 440px design is compared directly with a 1280px device
screenshot or the system bars are included in one image but not the other.

## Coordinate Layers

Record each layer explicitly:

1. **Source design pixels**: the width and height used by the HTML or image.
2. **ArkUI logical pixels (`vp`)**: the device content width reported by the
   runtime layout tree or an equivalent system query.
3. **Physical screenshot pixels (`px`)**: the PNG dimensions returned by the
   device screenshot.
4. **Content crop**: the region excluding status/navigation bars or prototype
   shell chrome that does not exist in the other image.
5. **Safe-area insets**: top and bottom system avoidance regions in the same
   units as the layer being used.

## Build the Baseline

Set `$skillRoot` to the skill folder before running bundled scripts.

```powershell
$skillRoot = "C:\path\to\arkui-visual-replica"
python "$skillRoot\scripts\build_visual_baseline.py" `
  --reference-image "D:\path\reference.png" `
  --reference-crop "0,44,440,908" `
  --target-pixels "1280x2832" `
  --target-crop "0,137,1280,2695" `
  --design-width 440 `
  --logical-width 366 `
  --safe-top-px 137 `
  --out "D:\path\work\coordinate-baseline.json"
```

Use the output before coding:

- `designToLogicalScale` converts design values into `vp`.
- `referenceContentToTargetX/Y` map source content to device pixels.
- A content aspect-ratio mismatch above 1% is a warning: compare crops, not a
  stretched full screenshot.

## Runtime Confirmation

After launch, record the ArkUI layout tree:

```powershell
node "$skillRoot\scripts\capture_arkui_runtime.js" `
  --project "D:\path\HarmonyProject" `
  --device "127.0.0.1:5555" `
  --out "D:\path\work\runtime-pass"
```

Reconcile the planned baseline with actual root bounds, text bounds, and major
container bounds before changing typography or spacing.

## Common Errors

- Using screenshot width as the ArkUI logical width.
- Assuming a 3x device density without checking the target.
- Comparing system status/navigation bars that one image simulates and the
  other renders natively.
- Stretching a 1280x2832 screenshot to 440x952 and treating the resulting
  distortion as component error.
- Reading runtime text from the original HTML while a script later replaces it.
