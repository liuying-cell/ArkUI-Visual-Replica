#!/usr/bin/env node
'use strict';

const childProcess = require('node:child_process');
const fs = require('node:fs');
const net = require('node:net');
const os = require('node:os');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

const DEFAULTS = {
  width: 375,
  height: 811,
  scale: 1,
  waitMs: 1200,
  settleMs: 250,
  maxDepth: 14,
  maxNodes: 3000,
  grid: '8x16',
};

function usage() {
  console.log(`Usage:
  node capture_html_reference.js --html <file> --out <dir> [options]

Required:
  --html <file>          Local HTML source
  --out <dir>            Output directory

Target selection:
  --page <value>         Activate and capture [data-page="value"]
  --selector <css>       Capture the first matching element
  --prep-js <file>       Run page-context JavaScript before capture
  --query <string>       Query string for the local page before its scripts run
  --hide-selector <css>  Hide matching prototype-only elements; repeatable
  --visible-only         Exclude hidden/off-screen subtrees from the manifest
  --viewport-only        Exclude nodes outside the current viewport
  --preserve-svg         Keep zero-size SVG structural nodes

Viewport and timing:
  --width <px>           Reference width (default ${DEFAULTS.width})
  --height <px>          Reference height (default ${DEFAULTS.height})
  --scale <number>       Device scale factor (default ${DEFAULTS.scale})
  --wait-ms <ms>         Initial load/readiness wait (default ${DEFAULTS.waitMs})
  --settle-ms <ms>       Post-prepare settle wait (default ${DEFAULTS.settleMs})
  --freeze-motion        Pause CSS animations and transitions for a stable frame

Extraction:
  --max-depth <n>        Computed-tree depth limit (default ${DEFAULTS.maxDepth})
  --max-nodes <n>        Computed-tree node limit (default ${DEFAULTS.maxNodes})

Browser:
  --browser <file>       Edge/Chrome executable

Environment:
  ARKUI_CAPTURE_BROWSER  Optional browser executable override
`);
}

function parseArgs(argv) {
  const args = {
    ...DEFAULTS,
    freezeMotion: false,
    visibleOnly: false,
    viewportOnly: false,
    preserveSvg: false,
    hideSelectors: [],
  };
  const valueFlags = new Set([
    '--html', '--out', '--page', '--selector', '--prep-js', '--query', '--width',
    '--height', '--scale', '--wait-ms', '--settle-ms', '--max-depth',
    '--max-nodes', '--browser', '--grid', '--hide-selector',
  ]);

  for (let i = 0; i < argv.length; i += 1) {
    const flag = argv[i];
    if (flag === '--help' || flag === '-h') {
      usage();
      process.exit(0);
    }
    if (flag === '--freeze-motion') {
      args.freezeMotion = true;
      continue;
    }
    if (flag === '--visible-only') {
      args.visibleOnly = true;
      continue;
    }
    if (flag === '--viewport-only') {
      args.viewportOnly = true;
      continue;
    }
    if (flag === '--preserve-svg') {
      args.preserveSvg = true;
      continue;
    }
    if (!valueFlags.has(flag)) {
      throw new Error(`Unknown option: ${flag}`);
    }
    const value = argv[++i];
    if (value === undefined) {
      throw new Error(`Missing value for ${flag}`);
    }
    if (flag === '--html') args.html = value;
    if (flag === '--out') args.out = value;
    if (flag === '--page') args.page = value;
    if (flag === '--selector') args.selector = value;
    if (flag === '--prep-js') args.prepJs = value;
    if (flag === '--query') args.query = value;
    if (flag === '--hide-selector') args.hideSelectors.push(value);
    if (flag === '--width') args.width = Number(value);
    if (flag === '--height') args.height = Number(value);
    if (flag === '--scale') args.scale = Number(value);
    if (flag === '--wait-ms') args.waitMs = Number(value);
    if (flag === '--settle-ms') args.settleMs = Number(value);
    if (flag === '--max-depth') args.maxDepth = Number(value);
    if (flag === '--max-nodes') args.maxNodes = Number(value);
    if (flag === '--browser') args.browser = value;
    if (flag === '--grid') args.grid = value;
  }

  if (!args.html || !args.out) {
    throw new Error('Both --html and --out are required.');
  }
  for (const key of ['width', 'height', 'scale', 'waitMs', 'settleMs', 'maxDepth', 'maxNodes']) {
    if (!Number.isFinite(args[key]) || args[key] <= 0) {
      throw new Error(`Invalid positive number for ${key}.`);
    }
  }

  args.html = path.resolve(args.html);
  args.out = path.resolve(args.out);
  if (!fs.existsSync(args.html)) {
    throw new Error(`HTML file does not exist: ${args.html}`);
  }
  if (args.prepJs) {
    args.prepJs = path.resolve(args.prepJs);
    if (!fs.existsSync(args.prepJs)) {
      throw new Error(`Prep JavaScript file does not exist: ${args.prepJs}`);
    }
  }
  return args;
}

function findBrowser(explicit) {
  const candidates = [
    explicit,
    process.env.ARKUI_CAPTURE_BROWSER,
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
    '/usr/bin/google-chrome',
    '/usr/bin/google-chrome-stable',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
    '/usr/bin/microsoft-edge',
  ].filter(Boolean);

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) return candidate;
  }
  throw new Error(
    'No Chromium browser found. Pass --browser or set ARKUI_CAPTURE_BROWSER.',
  );
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function freePort() {
  const server = net.createServer();
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  const address = server.address();
  const port = address.port;
  await new Promise((resolve) => server.close(resolve));
  return port;
}

async function waitForJson(url, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  let lastError = null;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok) return await response.json();
      lastError = new Error(`HTTP ${response.status}`);
    } catch (error) {
      lastError = error;
    }
    await delay(150);
  }
  throw new Error(`Browser debugging endpoint did not become ready: ${lastError}`);
}

class CdpClient {
  constructor(wsUrl) {
    this.wsUrl = wsUrl;
    this.socket = null;
    this.nextId = 1;
    this.pending = new Map();
  }

  async connect() {
    this.socket = new WebSocket(this.wsUrl);
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('CDP WebSocket open timeout')), 10000);
      this.socket.addEventListener('open', () => {
        clearTimeout(timer);
        resolve();
      }, { once: true });
      this.socket.addEventListener('error', () => {
        clearTimeout(timer);
        reject(new Error('CDP WebSocket connection failed'));
      }, { once: true });
    });

    this.socket.addEventListener('message', (event) => {
      const message = JSON.parse(String(event.data));
      if (!message.id || !this.pending.has(message.id)) return;
      const pending = this.pending.get(message.id);
      this.pending.delete(message.id);
      if (message.error) {
        pending.reject(new Error(`${pending.method}: ${message.error.message}`));
      } else {
        pending.resolve(message.result);
      }
    });
  }

  send(method, params = {}) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      throw new Error('CDP socket is not open.');
    }
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject, method });
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }

  close() {
    if (this.socket && this.socket.readyState <= WebSocket.OPEN) {
      this.socket.close();
    }
  }
}

function safeRemoveTemp(dir, tempRoot) {
  const resolved = path.resolve(dir);
  const root = path.resolve(tempRoot);
  const relative = path.relative(root, resolved);
  if (!relative || relative.startsWith('..') || path.isAbsolute(relative)) {
    throw new Error(`Refusing to remove unsafe temporary path: ${resolved}`);
  }
  fs.rmSync(resolved, { recursive: true, force: true });
}

function evaluationExpression(args) {
  const extraction = `
    (() => {
      const cfg = ${JSON.stringify({
        page: args.page || null,
        selector: args.selector || null,
        visibleOnly: args.visibleOnly,
        viewportOnly: args.viewportOnly,
        preserveSvg: args.preserveSvg,
        maxDepth: args.maxDepth,
        maxNodes: args.maxNodes,
      })};
      const styleProps = [
        'display', 'position', 'left', 'top', 'right', 'bottom',
        'width', 'height', 'min-width', 'min-height', 'max-width', 'max-height',
        'box-sizing', 'overflow-x', 'overflow-y', 'z-index', 'opacity',
        'transform', 'transform-origin', 'filter', 'backdrop-filter',
        'mix-blend-mode', 'isolation',
        'flex-direction', 'flex-wrap', 'justify-content', 'align-items',
        'align-content', 'align-self', 'flex-grow', 'flex-shrink', 'flex-basis',
        'gap', 'row-gap', 'column-gap',
        'grid-template-columns', 'grid-template-rows', 'grid-auto-flow',
        'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
        'margin-top', 'margin-right', 'margin-bottom', 'margin-left',
        'border-top-width', 'border-right-width', 'border-bottom-width', 'border-left-width',
        'border-top-style', 'border-right-style', 'border-bottom-style', 'border-left-style',
        'border-top-color', 'border-right-color', 'border-bottom-color', 'border-left-color',
        'border-top-left-radius', 'border-top-right-radius',
        'border-bottom-right-radius', 'border-bottom-left-radius',
        'color', 'background-color', 'background-image', 'background-size',
        'background-position', 'background-repeat', 'box-shadow', 'outline',
        'font-family', 'font-size', 'font-style', 'font-weight', 'font-stretch',
        'line-height', 'letter-spacing', 'word-spacing', 'text-align',
        'text-decoration', 'text-transform', 'white-space', 'word-break',
        'text-overflow', 'vertical-align', 'list-style-type',
        'animation-name', 'animation-duration', 'animation-delay',
        'animation-iteration-count', 'animation-direction',
        'animation-fill-mode', 'animation-timing-function',
        'transition-property', 'transition-duration', 'transition-delay',
        'transition-timing-function',
        'aspect-ratio'
      ];

      const colorCanvas = document.createElement('canvas');
      colorCanvas.width = 1;
      colorCanvas.height = 1;
      const colorContext = colorCanvas.getContext('2d', { willReadFrequently: true });
      function canonicalColor(value) {
        if (!value || value === 'none' || value === 'transparent') return value || '';
        try {
          colorContext.clearRect(0, 0, 1, 1);
          colorContext.fillStyle = '#010203';
          colorContext.fillStyle = value;
          colorContext.fillRect(0, 0, 1, 1);
          const pixels = colorContext.getImageData(0, 0, 1, 1).data;
          return 'rgba(' + pixels[0] + ',' + pixels[1] + ',' + pixels[2] + ',' +
            (pixels[3] / 255).toFixed(4) + ')';
        } catch (_) {
          return value;
        }
      }
      const colorKeys = new Set([
        'color', 'background-color', 'border-top-color', 'border-right-color',
        'border-bottom-color', 'border-left-color', 'outline-color',
        'text-decoration-color', 'caret-color', 'fill', 'stroke'
      ]);

      function customProperties(style) {
        const result = {};
        for (let i = 0; i < style.length; i += 1) {
          const name = style[i];
          if (!name.startsWith('--')) continue;
          const value = style.getPropertyValue(name).trim();
          result[name] = window.CSS && CSS.supports('color', value)
            ? canonicalColor(value)
            : value;
        }
        return result;
      }

      function round(value) {
        return Math.round(Number(value) * 100) / 100;
      }

      function rectOf(el) {
        const rect = el.getBoundingClientRect();
        return {
          x: round(rect.x),
          y: round(rect.y),
          width: round(rect.width),
          height: round(rect.height),
          top: round(rect.top),
          right: round(rect.right),
          bottom: round(rect.bottom),
          left: round(rect.left),
        };
      }

      function clippingState(el, rect) {
        let left = rect.left;
        let top = rect.top;
        let right = rect.right;
        let bottom = rect.bottom;
        const clippedBy = [];
        let ancestor = el.parentElement;
        while (ancestor && ancestor !== document.documentElement) {
          const style = getComputedStyle(ancestor);
          const overflow = style.overflowX + ' ' + style.overflowY;
          if (/(hidden|clip|auto|scroll)/.test(overflow)) {
            const box = ancestor.getBoundingClientRect();
            const before = [left, top, right, bottom];
            left = Math.max(left, box.left);
            top = Math.max(top, box.top);
            right = Math.min(right, box.right);
            bottom = Math.min(bottom, box.bottom);
            if (
              left !== before[0] ||
              top !== before[1] ||
              right !== before[2] ||
              bottom !== before[3]
            ) {
              clippedBy.push({
                tag: ancestor.tagName.toLowerCase(),
                id: ancestor.id || null,
                class: typeof ancestor.className === 'string' ? ancestor.className : '',
              });
            }
          }
          ancestor = ancestor.parentElement;
        }
        const visibleWidth = Math.max(0, right - left);
        const visibleHeight = Math.max(0, bottom - top);
        const viewportRight = Math.min(right, window.innerWidth);
        const viewportBottom = Math.min(bottom, window.innerHeight);
        const hasArea = right > left && bottom > top;
        const inViewport = hasArea
          ? viewportRight > Math.max(0, left) && viewportBottom > Math.max(0, top)
          : left >= 0 && top >= 0 &&
            left < window.innerWidth && top < window.innerHeight;
        return {
          inViewport,
          visibleRect: {
            x: round(left),
            y: round(top),
            width: round(visibleWidth),
            height: round(visibleHeight),
          },
          clippedBy,
        };
      }

      function directText(el) {
        let text = '';
        for (const node of el.childNodes) {
          if (node.nodeType === Node.TEXT_NODE) text += node.nodeValue || '';
        }
        text = text.replace(/\\s+/g, ' ').trim();
        return text.length > 500 ? text.slice(0, 500) + '…' : text;
      }

      function pseudoData(el, pseudo) {
        const style = getComputedStyle(el, pseudo);
        if (!style || style.content === 'none' || style.content === 'normal') return null;
        const result = {};
        for (const prop of styleProps) {
          const value = style.getPropertyValue(prop);
          if (value) result[prop] = colorKeys.has(prop) ? canonicalColor(value) : value;
        }
        result.content = style.content;
        return result;
      }

      let selected = null;
      let pageElement = null;
      let activatedPage = null;
      if (cfg.page) {
        const candidates = Array.from(document.querySelectorAll('[data-page]'));
        pageElement = candidates.find((el) => el.getAttribute('data-page') === cfg.page) || null;
        if (pageElement) {
          activatedPage = cfg.page;
          for (const candidate of candidates) {
            candidate.classList.toggle('active', candidate === pageElement);
          }
          pageElement.style.visibility = 'visible';
          pageElement.style.opacity = '1';
        }
      }
      if (cfg.selector) {
        selected = document.querySelector(cfg.selector);
      } else if (pageElement) {
        selected = pageElement;
      } else {
        selected = document.querySelector('.screen.active') ||
          document.querySelector('[data-page].active') ||
          document.querySelector('#app') ||
          document.body;
      }
      if (!selected) throw new Error('Target element was not found.');

      const rootStyle = getComputedStyle(document.documentElement);
      const targetStyle = getComputedStyle(selected);
      const targetRect = rectOf(selected);
      const stats = { nodes: 0, truncated: false, maxDepthReached: false };
      const fontFamilies = new Set();
      const assetUrls = new Set();
      let truncated = false;

      function walk(el, depth, pathPart) {
        if (stats.nodes >= cfg.maxNodes) {
          truncated = true;
          stats.truncated = true;
          return null;
        }
        const computed = getComputedStyle(el);
        const elementRect = el.getBoundingClientRect();
        const isSvgNode =
          el.namespaceURI === 'http://www.w3.org/2000/svg' ||
          Boolean(el.closest && el.closest('svg'));
        const zeroSize = elementRect.width <= 0 || elementRect.height <= 0;
        const clipState = clippingState(el, elementRect);
        if (
          cfg.visibleOnly &&
          depth > 0 &&
          (
            computed.display === 'none' ||
            computed.visibility === 'hidden' ||
            Number.parseFloat(computed.opacity || '1') <= 0.001 ||
            (zeroSize && !(cfg.preserveSvg && isSvgNode)) ||
            el.getAttribute('aria-hidden') === 'true'
          )
        ) {
          return null;
        }
        if (cfg.viewportOnly && depth > 0 && !clipState.inViewport) {
          return null;
        }
        stats.nodes += 1;
        const style = {};
        for (const prop of styleProps) {
          const value = computed.getPropertyValue(prop);
          if (!value) continue;
          style[prop] = colorKeys.has(prop) ? canonicalColor(value) : value;
        }
        const direct = directText(el);
        const attrs = {};
        for (const name of ['id', 'role', 'aria-label', 'alt', 'title', 'src', 'href', 'viewBox']) {
          if (el.hasAttribute && el.hasAttribute(name)) attrs[name] = el.getAttribute(name);
        }
        if (style['font-family']) fontFamilies.add(style['font-family']);
        for (const key of ['background-image', 'content']) {
          const raw = style[key] || '';
          const regex = /url\\((['"]?)(.*?)\\1\\)/g;
          let match;
          while ((match = regex.exec(raw))) assetUrls.add(match[2]);
        }

        let asset = null;
        if (['IMG', 'SVG', 'CANVAS', 'VIDEO'].includes(el.tagName)) {
          asset = {
            tag: el.tagName.toLowerCase(),
            width: el.width || null,
            height: el.height || null,
            src: el.currentSrc || el.getAttribute('src') || null,
          };
        }

        const node = {
          path: pathPart,
          tag: el.tagName.toLowerCase(),
          id: el.id || null,
          class: typeof el.className === 'string' ? el.className : el.getAttribute('class') || '',
          attrs,
          rect: rectOf(el),
          inViewport: clipState.inViewport,
          visibleRect: clipState.visibleRect,
          clippedBy: clipState.clippedBy,
          style,
          text: direct || null,
          asset,
          pseudo: {
            before: pseudoData(el, '::before'),
            after: pseudoData(el, '::after'),
          },
          children: [],
        };

        if (depth >= cfg.maxDepth) {
          if (el.children.length) {
            stats.maxDepthReached = true;
            truncated = true;
          }
          return node;
        }
        let childIndex = 0;
        for (const child of el.children) {
          if (child.tagName === 'SCRIPT' || child.tagName === 'STYLE' || child.tagName === 'LINK') {
            continue;
          }
          childIndex += 1;
          const childNode = walk(child, depth + 1, pathPart + '/' + childIndex);
          if (childNode) node.children.push(childNode);
        }
        return node;
      }

      const tree = walk(selected, 0, '0');
      return {
        target: {
          page: activatedPage,
          selector: cfg.selector,
          tag: selected.tagName.toLowerCase(),
          id: selected.id || null,
          class: typeof selected.className === 'string' ? selected.className : '',
          rect: targetRect,
          customProperties: customProperties(targetStyle),
        },
        document: {
          title: document.title,
          url: location.href,
          scrollX: round(window.scrollX),
          scrollY: round(window.scrollY),
          bodyBackground: canonicalColor(getComputedStyle(document.body).backgroundColor),
          viewport: {
            innerWidth: window.innerWidth,
            innerHeight: window.innerHeight,
            devicePixelRatio: window.devicePixelRatio,
          },
          rootCustomProperties: customProperties(rootStyle),
        },
        fonts: {
          families: Array.from(fontFamilies).sort(),
          status: document.fonts ? document.fonts.status : 'unavailable',
        },
        assets: Array.from(assetUrls).sort(),
        stats,
        tree,
      };
    })()
  `;
  return extraction;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const browser = findBrowser(args.browser);
  const port = await freePort();
  const tempRoot = path.resolve(os.tmpdir());
  const profileDir = fs.mkdtempSync(path.join(tempRoot, 'arkui-visual-capture-'));
  const browserArgs = [
    '--headless=new',
    '--disable-gpu',
    '--hide-scrollbars',
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-extensions',
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profileDir}`,
    'about:blank',
  ];

  const browserProcess = childProcess.spawn(browser, browserArgs, {
    stdio: ['ignore', 'ignore', 'pipe'],
    windowsHide: true,
  });
  let stderr = '';
  browserProcess.stderr.on('data', (chunk) => {
    stderr += chunk.toString();
    if (stderr.length > 12000) stderr = stderr.slice(-12000);
  });

  let client = null;
  try {
    await waitForJson(`http://127.0.0.1:${port}/json/version`, 15000);
    let targets = await fetch(`http://127.0.0.1:${port}/json/list`).then((r) => r.json());
    let pageTarget = targets.find((target) => target.type === 'page');
    if (!pageTarget) {
      const response = await fetch(
        `http://127.0.0.1:${port}/json/new?${encodeURIComponent('about:blank')}`,
        { method: 'PUT' },
      );
      pageTarget = await response.json();
    }
    if (!pageTarget || !pageTarget.webSocketDebuggerUrl) {
      throw new Error('Could not find a CDP page target.');
    }

    client = new CdpClient(pageTarget.webSocketDebuggerUrl);
    await client.connect();
    await client.send('Page.enable');
    await client.send('Runtime.enable');
    await client.send('Emulation.setDeviceMetricsOverride', {
      width: args.width,
      height: args.height,
      deviceScaleFactor: args.scale,
      mobile: false,
      screenWidth: args.width,
      screenHeight: args.height,
    });
    const sourceUrl = pathToFileURL(args.html);
    if (args.query !== undefined) sourceUrl.search = args.query;
    await client.send('Page.navigate', { url: sourceUrl.href });
    await delay(args.waitMs);

    await client.send('Runtime.evaluate', {
      expression: `new Promise(async (resolve) => {
        if (document.fonts && document.fonts.ready) await document.fonts.ready;
        await Promise.all(Array.from(document.images).map((img) => {
          if (img.complete) return Promise.resolve();
          return new Promise((done) => {
            img.addEventListener('load', done, { once: true });
            img.addEventListener('error', done, { once: true });
          });
        }));
        requestAnimationFrame(() => requestAnimationFrame(() => resolve(true)));
      })`,
      awaitPromise: true,
      returnByValue: true,
    });

    if (args.prepJs) {
      const prepSource = fs.readFileSync(args.prepJs, 'utf8');
      const prepared = await client.send('Runtime.evaluate', {
        expression: `(async () => { ${prepSource}\n })()`,
        awaitPromise: true,
        returnByValue: true,
      });
      if (prepared.exceptionDetails) {
        throw new Error(prepared.exceptionDetails.exception?.description ||
          prepared.exceptionDetails.text || 'Capture preparation failed.');
      }
    }

    if (args.hideSelectors.length > 0) {
      const hiddenCss = args.hideSelectors
        .map((selector) => `${selector}{display:none!important;}`)
        .join('\n');
      await client.send('Runtime.evaluate', {
        expression: `(() => {
          const id = '__arkui_visual_replica_hidden__';
          document.getElementById(id)?.remove();
          const style = document.createElement('style');
          style.id = id;
          style.textContent = ${JSON.stringify(hiddenCss)};
          document.head.appendChild(style);
          return true;
        })()`,
        returnByValue: true,
      });
    }

    if (args.freezeMotion) {
      await client.send('Runtime.evaluate', {
        expression: `(() => {
          const id = '__arkui_visual_replica_freeze__';
          if (!document.getElementById(id)) {
            const style = document.createElement('style');
            style.id = id;
            style.textContent = '*,*::before,*::after{animation-play-state:paused!important;' +
              'transition-duration:0s!important;transition-delay:0s!important;' +
              'caret-color:transparent!important;}';
            document.head.appendChild(style);
          }
          return true;
        })()`,
        returnByValue: true,
      });
    }
    await delay(args.settleMs);

    const extracted = await client.send('Runtime.evaluate', {
      expression: evaluationExpression(args),
      returnByValue: true,
      awaitPromise: true,
    });
    if (extracted.exceptionDetails) {
      throw new Error(
        extracted.exceptionDetails.exception?.description ||
        extracted.exceptionDetails.text ||
        'Page evaluation failed.',
      );
    }
    const manifest = extracted.result.value;
    if (!manifest || manifest.target.rect.width <= 0 || manifest.target.rect.height <= 0) {
      throw new Error('Target element has no visible capture area.');
    }

    const rect = manifest.target.rect;
    if (rect.width > 20000 || rect.height > 20000) {
      throw new Error(`Refusing unusually large capture: ${rect.width}x${rect.height}`);
    }

    const screenshot = await client.send('Page.captureScreenshot', {
      format: 'png',
      fromSurface: true,
      captureBeyondViewport: true,
      clip: {
        x: Math.max(0, rect.x + manifest.document.scrollX),
        y: Math.max(0, rect.y + manifest.document.scrollY),
        width: rect.width,
        height: rect.height,
        scale: 1,
      },
    });

    fs.mkdirSync(args.out, { recursive: true });
    const pngPath = path.join(args.out, 'reference.png');
    const jsonPath = path.join(args.out, 'reference.json');
    fs.writeFileSync(pngPath, Buffer.from(screenshot.data, 'base64'));
    fs.writeFileSync(jsonPath, JSON.stringify({
      schemaVersion: 1,
      capturedAt: new Date().toISOString(),
      source: args.html,
      sourceUrl: sourceUrl.href,
      viewport: {
        width: args.width,
        height: args.height,
        scale: args.scale,
      },
      motionFrozen: args.freezeMotion,
      visibleOnly: args.visibleOnly,
      viewportOnly: args.viewportOnly,
      preserveSvg: args.preserveSvg,
      hiddenSelectors: args.hideSelectors,
      browser,
      ...manifest,
    }, null, 2));

    console.log(JSON.stringify({
      screenshot: pngPath,
      manifest: jsonPath,
      target: manifest.target,
      nodes: manifest.stats.nodes,
      truncated: manifest.stats.truncated,
    }, null, 2));
  } catch (error) {
    if (stderr) process.stderr.write(stderr);
    throw error;
  } finally {
    if (client) client.close();
    browserProcess.kill();
    await delay(250);
    safeRemoveTemp(profileDir, tempRoot);
  }
}

main().catch((error) => {
  console.error(`capture_html_reference: ${error.message}`);
  process.exit(1);
});
