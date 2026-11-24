#!/usr/bin/env node
'use strict';

const childProcess = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

function parseArgs(argv) {
  const args = { mode: 'full', visualStatic: false };
  for (let index = 0; index < argv.length; index += 1) {
    const flag = argv[index];
    if (flag === '--help' || flag === '-h') {
      console.log(`Usage:
  node capture_arkui_runtime.js --project <dir> --device <serial> --out <dir>

Options:
  --project <dir>     HarmonyOS project root
  --device <serial>   Device or emulator serial
  --out <dir>         Output directory
  --mode <mode>       Layout mode: full or simplified (default: full)
  --visual-static     Cold-start with freezeMotion=true, then restore normal launch
  --hdc <file>        hdc executable used for visual-static launch
  --bundle-name <id>  Application bundle name
  --ability-name <n>  Ability name
`);
      process.exit(0);
    }
    if (flag === '--visual-static') {
      args.visualStatic = true;
      continue;
    }
    const value = argv[++index];
    if (value === undefined) throw new Error(`Missing value for ${flag}`);
    if (flag === '--project') args.project = value;
    if (flag === '--device') args.device = value;
    if (flag === '--out') args.out = value;
    if (flag === '--mode') args.mode = value;
    if (flag === '--hdc') args.hdc = value;
    if (flag === '--bundle-name') args.bundle = value;
    if (flag === '--ability-name') args.ability = value;
  }
  if (!args.project || !args.device || !args.out) {
    throw new Error('--project, --device, and --out are required.');
  }
  if (args.visualStatic && (!args.hdc || !args.bundle || !args.ability)) {
    throw new Error(
      '--visual-static requires --hdc, --bundle-name, and --ability-name.',
    );
  }
  args.project = path.resolve(args.project);
  args.out = path.resolve(args.out);
  return args;
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function runHdc(args, cwd) {
  const useShell =
    process.platform === 'win32' &&
    !path.isAbsolute(args.hdc) &&
    !args.hdc.toLowerCase().endsWith('.exe');
  const result = childProcess.spawnSync(args.hdc, args.args, {
    cwd,
    shell: useShell,
    encoding: 'utf8',
    timeout: 20000,
    maxBuffer: 16 * 1024 * 1024,
  });
  if (result.error) throw result.error;
  if (result.status !== 0 || /^error:/im.test(result.stdout)) {
    throw new Error(
      `hdc ${args.args.join(' ')} failed with ${result.status}\n${result.stderr || result.stdout}`,
    );
  }
  return result.stdout;
}

async function restartApp(args, freezeMotion) {
  const prefix = ['-t', args.device, 'shell'];
  runHdc({
    hdc: args.hdc,
    args: [...prefix, 'aa', 'force-stop', args.bundle],
  }, args.project);
  await delay(300);
  const startArgs = [
    ...prefix,
    'aa', 'start',
    '-a', args.ability,
    '-b', args.bundle,
  ];
  if (freezeMotion) {
    startArgs.push('--pb', 'freezeMotion', 'true');
  }
  runHdc({ hdc: args.hdc, args: startArgs }, args.project);
  await delay(1500);
}

function runDeveco(args, cwd) {
  const result = childProcess.spawnSync('devecocli', args, {
    cwd,
    shell: process.platform === 'win32',
    encoding: 'utf8',
    maxBuffer: 64 * 1024 * 1024,
    timeout: 30000,
  });
  if (result.error) {
    throw new Error(`devecocli ${args.slice(0, 2).join(' ')}: ${result.error.message}`);
  }
  if (result.status !== 0) {
    throw new Error(
      `devecocli ${args.join(' ')} failed with ${result.status}\n${result.stderr || result.stdout}`,
    );
  }
  return result.stdout;
}

function extractJson(output) {
  const start = output.indexOf('[');
  const end = output.lastIndexOf(']');
  if (start < 0 || end < start) {
    throw new Error('Could not find a JSON layout payload in devecocli output.');
  }
  return JSON.parse(output.slice(start, end + 1));
}

function summarize(nodes) {
  const textNodes = [];
  const containers = [];
  const counts = {};

  function walk(node) {
    counts[node.type] = (counts[node.type] || 0) + 1;
    const bounds = Array.isArray(node.bounds) ? node.bounds : null;
    if (node.text && textNodes.length < 2000) {
      textNodes.push({
        text: node.text,
        type: node.type || null,
        id: node.id || null,
        bounds,
      });
    }
    if (
      bounds &&
      ['Stack', 'Column', 'Row', 'List', 'Scroll', 'ListItem'].includes(node.type) &&
      bounds[2] - bounds[0] > 80 &&
      bounds[3] - bounds[1] > 40 &&
      containers.length < 600
    ) {
      containers.push({
        type: node.type,
        id: node.id || null,
        bounds,
      });
    }
    for (const child of node.children || []) walk(child);
  }

  for (const node of nodes) walk(node);
  return { textNodes, containers, typeCounts: counts };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  fs.mkdirSync(args.out, { recursive: true });
  const screenshotPath = path.join(args.out, 'arkui.png');
  const layoutPath = path.join(args.out, 'layout.json');
  const summaryPath = path.join(args.out, 'runtime.json');

  let captureFailed = false;
  try {
    if (args.visualStatic) {
      await restartApp(args, true);
    }
    runDeveco([
      'ui', 'screenshot',
      '--device', args.device,
      '--path', screenshotPath,
    ], args.project);
    const layoutOutput = runDeveco([
      'ui', 'layout',
      '--device', args.device,
      '--format', 'json',
      '--mode', args.mode,
    ], args.project);
    const layout = extractJson(layoutOutput);
    const summary = summarize(layout);
    const rootBounds = layout[0]?.bounds || null;

    fs.writeFileSync(layoutPath, JSON.stringify(layout, null, 2));
    fs.writeFileSync(summaryPath, JSON.stringify({
      schemaVersion: 1,
      capturedAt: new Date().toISOString(),
      project: args.project,
      device: args.device,
      visualStatic: args.visualStatic,
      screenshot: screenshotPath,
      layout: layoutPath,
      rootBounds,
      ...summary,
    }, null, 2));

    console.log(JSON.stringify({
      screenshot: screenshotPath,
      layout: layoutPath,
      summary: summaryPath,
      visualStatic: args.visualStatic,
      rootBounds,
      textNodes: summary.textNodes.length,
      containers: summary.containers.length,
    }, null, 2));
  } catch (error) {
    captureFailed = true;
    throw error;
  } finally {
    if (args.visualStatic) {
      try {
        await restartApp(args, false);
      } catch (error) {
        if (!captureFailed) throw error;
        console.error(`Could not restore normal launch: ${error.message}`);
      }
    }
  }
}

main().catch((error) => {
  console.error(`capture_arkui_runtime: ${error.message}`);
  process.exit(1);
});
