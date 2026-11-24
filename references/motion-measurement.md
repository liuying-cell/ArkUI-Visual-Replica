# Motion Timing and Performance

Use this guide for named timing checkpoints, high-rate recordings, or device performance claims. Use the [single-scene runner](motion-qa.md#single-scene-qa) for common quick and timing captures.

## Contents

- [Timing Toolchain](#timing-toolchain)
- [Performance](#performance)

## Timing Toolchain

Choose the time origin for each acceptance check before recording. For relative phase timing, align both traces on the same visible crossing, such as the first glyph reaching half brightness. For input-to-first-motion latency, mark the actual input event on each platform with a trace timestamp aligned to the recording or a visible marker emitted by the input callback. Keep a visible marker outside the motion analysis region and within the capture. Label a callback marker as callback-to-first-motion when input delivery time is outside the measurement. An HDC command-return timestamp supports a command-relative timing result. Record its uncertainty alongside the result.

For a marker following a curved path, normalize each capture to the same board coordinates. Pick visible crossings along a monotonic axis and align both runs on the first crossing. Use the surrounding frame timestamps to bound each crossing and compare its relative time, position, and tangent direction. Check replay and snap-to-end separately.

### 1. Capture the browser reference

~~~powershell
python scripts/capture_motion.py browser --url "file:///.../index.html?scene=burst" --output work/timing/browser-burst --width 390 --height 844 --pre-roll-ms 500 --duration-ms 1800 --trigger-js "window.motionLab.triggerBurst()"
~~~

The browser recorder uses CDP screencast and writes timestamped JPEGs plus capture.json. It commonly records 30-60 effective FPS in headless Edge.

### 2. Capture the HarmonyOS target

Prefer high-rate emulator-window recording on Windows:

~~~powershell
python scripts/capture_emulator_window.py --model "Mate 90 Pro" --serial 127.0.0.1:5557 --output work/timing/emulator-burst --fps 60 --pre-roll-ms 500 --duration-ms 2000 --trigger-click 640,1754
~~~

The trigger reference is the completion time of 'uitest uiInput click'. This is closer to the injected tap than the command start time. A video file and nominal FPS do not prove the capture is usable. Inspect the first, middle, and last decoded frames: the target app scene must be visible, stable, and free of overlapping IDE or desktop content. If desktop capture shows an overlapping window or a blank surface, reject that run and retry with a compositor capture targeting the emulator window handle (for example, Windows Graphics Capture). Recheck the crop on a frame from the accepted method. Keep HDC stills for device-side state evidence.

Use HDC snapshots when window capture is unavailable:

~~~powershell
python scripts/capture_motion.py harmony --serial 127.0.0.1:5557 --output work/timing/device-burst --pre-roll-ms 1000 --duration-ms 2200 --trigger-click 640,1754
python scripts/capture_motion.py harmony-sweep --serial 127.0.0.1:5557 --output work/timing/device-phase-sweep --trigger-click 640,1754 --phase 60 --phase 105 --phase 150 --phase 270 --phase 500 --phase 720
~~~

HDC snapshot throughput is roughly 1-2 FPS on the tested emulator. It is suitable for endpoint, ordering, and coarse phase evidence, not 60 FPS claims.

### 3. Analyze and compare

~~~powershell
python scripts/analyze_motion_trace.py analyze work/timing/browser-burst/capture.json
python scripts/analyze_motion_trace.py analyze work/timing/emulator-burst/capture.json
python scripts/analyze_motion_trace.py compare work/timing/browser-burst/analysis.json work/timing/emulator-burst/analysis.json --checkpoints firstMotionMs,peakMotionMs --tolerance-ms 75 --output work/timing/comparison.json
~~~

The analyzer reports first visible motion, peak frame-energy change, last activity, event clusters, capture coverage, ROI, per-frame metrics, and a contact sheet. Compare only anchors that the recording can actually resolve.

### 4. Read device counters as auxiliary evidence

~~~powershell
python scripts/probe_render_stats.py --serial 127.0.0.1:5557 --surface motionlab020 --trigger-click 640,1754 --wait-ms 1400 --output work/timing/render-stats.json
~~~

- 'hitchs' counters report recent windows over 16.67, 33, and 66 ms.
- 'fpsCount' reports system refresh-rate transitions, not application view FPS.
- An empty or all-zero app FPS series is 'unavailable', not proof of 60 FPS.

### Acceptance rules

- Report the capture method, effective capture FPS, anchor values, tolerance, and comparison result.
- Do not treat capture coverage as render performance.
- Do not claim sub-frame timing from HDC stills.
- For interrupted or gesture-driven motion, use a high-rate recording; phase sweeps only work when each trigger returns to the same settled state.

## Performance

- Record the device model, refresh-rate context, and app build mode.
- Limit large blur, shadow, mask, and offscreen layer changes.
- Check for layout animation in lists, text reflow, and repeated resource allocation.
- Confirm that ambient animations stop when the component disappears.
- Use device traces or frame presentation timestamps to verify presented frame rate. Report it as unavailable if those measurements cannot be obtained.
- For Canvas particle scenes, record the device, particle count, warm-up time, and sampling window. Measure Canvas submission time, animation callback intervals, and presented frame rate separately. Use the same sampling setup before and after a drawing optimization. Report long callback intervals with the threshold and count, and identify any unavailable metric.
