#!/usr/bin/env node
'use strict';

const childProcess = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

function parseArgs(argv) {
  const args = { requireSigning: false };
  for (let index = 0; index < argv.length; index += 1) {
    const flag = argv[index];
    if (flag === '--help' || flag === '-h') {
      console.log(`Usage:
  node harmony_preflight.js --project <dir> [options]

Options:
  --project <dir>         HarmonyOS project root
  --device <serial>       Target device or emulator serial
  --hdc <file>            hdc executable
  --emulator <name>       Expected emulator instance name
  --bundle-name <id>      Bundle expected on the device
  --require-signing       Treat missing signingConfigs as a blocker

This command is read-only: it does not start, stop, install, or launch anything.
`);
      process.exit(0);
    }
    if (flag === '--require-signing') {
      args.requireSigning = true;
      continue;
    }
    const value = argv[++index];
    if (value === undefined) throw new Error(`Missing value for ${flag}`);
    if (flag === '--project') args.project = value;
    if (flag === '--device') args.device = value;
    if (flag === '--hdc') args.hdc = value;
    if (flag === '--emulator') args.emulator = value;
    if (flag === '--bundle-name') args.bundle = value;
  }
  if (!args.project) throw new Error('--project is required.');
  args.project = path.resolve(args.project);
  return args;
}

function run(command, args, cwd, timeoutMs = 15000) {
  const useShell =
    process.platform === 'win32' &&
    !path.isAbsolute(command) &&
    !command.toLowerCase().endsWith('.exe');
  return childProcess.spawnSync(command, args, {
    cwd,
    shell: useShell,
    encoding: 'utf8',
    timeout: timeoutMs,
    maxBuffer: 16 * 1024 * 1024,
  });
}

function addCheck(checks, name, status, detail) {
  checks.push({ name, status, detail });
}

function outputOf(result) {
  return `${result.stdout || ''}\n${result.stderr || ''}`.trim();
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const checks = [];
  const blockers = [];
  const warnings = [];

  if (!fs.existsSync(args.project)) {
    throw new Error(`Project does not exist: ${args.project}`);
  }
  addCheck(checks, 'project', 'pass', args.project);

  const requiredFiles = [
    'build-profile.json5',
    'oh-package.json5',
    'entry/src/main/module.json5',
  ];
  for (const relative of requiredFiles) {
    const file = path.join(args.project, relative);
    if (fs.existsSync(file)) {
      addCheck(checks, `config:${relative}`, 'pass', file);
    } else {
      blockers.push(`Missing project config: ${relative}`);
      addCheck(checks, `config:${relative}`, 'error', 'missing');
    }
  }

  const devecocli = run('devecocli', ['--version'], args.project);
  if (devecocli.status === 0) {
    addCheck(checks, 'devecocli', 'pass', outputOf(devecocli));
  } else {
    const detail = devecocli.error
      ? `${devecocli.error.code || 'ERROR'}: ${devecocli.error.message}`
      : outputOf(devecocli);
    blockers.push('devecocli is unavailable.');
    addCheck(checks, 'devecocli', 'error', String(detail).trim());
  }

  const deveco = run('deveco', ['--version'], args.project);
  if (deveco.status === 0) {
    addCheck(checks, 'deveco', 'pass', outputOf(deveco));
  } else {
    warnings.push('deveco CLI version could not be read.');
    addCheck(checks, 'deveco', 'warning', outputOf(deveco));
  }

  const buildProfilePath = path.join(args.project, 'build-profile.json5');
  if (fs.existsSync(buildProfilePath)) {
    const profile = fs.readFileSync(buildProfilePath, 'utf8');
    const signingEmpty = /"signingConfigs"\s*:\s*\[\s*\]/.test(profile);
    if (signingEmpty) {
      const message = 'build-profile.json5 has an empty signingConfigs array.';
      if (args.requireSigning) blockers.push(message);
      else warnings.push(message);
      addCheck(
        checks,
        'signing',
        args.requireSigning ? 'error' : 'warning',
        message,
      );
    } else {
      addCheck(checks, 'signing', 'pass', 'signingConfigs is not empty');
    }
  }

  if (args.emulator) {
    const emulator = run('devecocli', ['emulator', 'list'], args.project);
    const output = outputOf(emulator);
    if (emulator.status === 0 && output.includes(args.emulator)) {
      addCheck(checks, 'emulator', 'pass', args.emulator);
    } else {
      warnings.push(`Expected emulator was not found: ${args.emulator}`);
      addCheck(checks, 'emulator', 'warning', output.trim());
    }
  }

  if (args.device) {
    const hdc = args.hdc || 'hdc';
    const targets = run(hdc, ['list', 'targets'], args.project);
    const targetOutput = outputOf(targets);
    const lines = targetOutput
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line && !line.includes('[Empty]'));
    if (lines.includes(args.device)) {
      addCheck(checks, 'device', 'pass', args.device);
      if (lines.length > 1) {
        warnings.push(
          `Multiple targets are connected; always pass --device ${args.device}.`,
        );
      }
      warnings.push(
        'Device was already present at preflight time. Do not stop it unless this task owns it.',
      );

      const windows = run(
        'devecocli',
        ['ui', 'window', 'list', '--device', args.device],
        args.project,
        20000,
      );
      const windowOutput = outputOf(windows);
      if (
        windows.error &&
        String(windows.error.code).includes('ETIMEDOUT')
      ) {
        warnings.push(
          'UI window list timed out; another session may own the device. Do not stop it without confirmation.',
        );
        addCheck(checks, 'ui-window', 'warning', 'timed out');
      } else if (windows.status === 0 && !/No windows found/i.test(windowOutput)) {
        addCheck(checks, 'ui-window', 'pass', 'UI window service returned windows');
      } else {
        warnings.push(
          'UI window list was empty; screen may be off, locked, or UI automation may be unavailable.',
        );
        addCheck(checks, 'ui-window', 'warning', windowOutput.trim());
      }

      if (args.bundle) {
        const packageDump = run(
          hdc,
          ['-t', args.device, 'shell', 'bm', 'dump', '-n', args.bundle],
          args.project,
          20000,
        );
        const packageOutput = outputOf(packageDump);
        if (packageDump.status === 0 && packageOutput.includes(args.bundle)) {
          addCheck(checks, 'bundle', 'pass', `${args.bundle} is installed`);
        } else {
          addCheck(checks, 'bundle', 'warning', `${args.bundle} is not installed`);
          warnings.push(`Bundle is not installed yet: ${args.bundle}`);
        }
      }
    } else {
      blockers.push(`Target device is not connected: ${args.device}`);
      addCheck(checks, 'device', 'error', targetOutput);
    }
  }

  const report = {
    schemaVersion: 1,
    project: args.project,
    device: args.device || null,
    status: blockers.length ? 'error' : warnings.length ? 'warning' : 'pass',
    readOnly: true,
    checks,
    blockers,
    warnings,
  };
  console.log(JSON.stringify(report, null, 2));
  process.exit(blockers.length ? 1 : 0);
}

try {
  main();
} catch (error) {
  console.error(`harmony_preflight: ${error.message}`);
  process.exit(1);
}
