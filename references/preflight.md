# HarmonyOS Preflight

Set `$skillRoot` to the skill folder, then run the preflight helper before build, install, launch, or device screenshot
operations when a device or emulator is involved.

```powershell
$skillRoot = "C:\path\to\arkui-visual-replica"
node "$skillRoot\scripts\harmony_preflight.js" `
  --project "D:\path\HarmonyProject" `
  --device "127.0.0.1:5555" `
  --hdc "D:\path\sdk\toolchains\hdc.exe" `
  --emulator "Emulator Instance Name" `
  --bundle-name "com.example.app"
```

The command is read-only. It does not start, stop, install, or launch anything.
It checks:

- required project configuration files;
- `devecocli` and DevEco CLI availability;
- signing configuration;
- the expected emulator instance;
- the explicitly selected device;
- whether the HarmonyOS UI window service responds;
- whether the bundle is already installed.

Use an explicit `--device` whenever more than one target is connected. A
preoccupied emulator belongs to another session unless this task started it.
Do not stop or restart an unknown emulator because an operation hangs. Prefer a
different target or wait for the owning session to release it.

Missing signing is a warning by default because preview or unsigned debugging
workflows may still be valid. Add `--require-signing` when the requested handoff
requires an installable signed build.

If the UI window check times out, treat it as an availability warning. First
confirm device ownership and target selection; do not reinterpret a shared
device problem as an ArkUI page defect.

HDC connectivity and a completed boot flag can coexist with an unresponsive UI
service. If a normal restart of a task-owned emulator reloads the same state,
check the current emulator CLI help for a data-preserving cold boot. Wait for
the original process to exit before starting it again, and verify the selected
target, bundle, and UI response before resuming capture.
