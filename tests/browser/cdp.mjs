/* A tiny Chrome DevTools Protocol driver for the browser tests: find and launch Chrome, open a page, evaluate
 * code, click like a mouse and type like a keyboard. No npm packages. It needs a global WebSocket: Node >= 22,
 * or Node 20 with --experimental-websocket (run.mjs adds that flag by itself). */
import {spawn} from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const WIN = process.platform === 'win32';
/* Windows installs per machine (Program Files, Program Files (x86)) or per user (LOCALAPPDATA) */
const winPaths = file => [process.env.PROGRAMFILES || 'C:\\Program Files', process.env['PROGRAMFILES(X86)'], process.env.LOCALAPPDATA]
  .filter(Boolean).map(dir => path.join(dir, file));
const CANDIDATES = [
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Chromium.app/Contents/MacOS/Chromium',
  ...(WIN ? winPaths('Google\\Chrome\\Application\\chrome.exe') : []),
  // Edge is Chromium too, and every Windows machine has it
  '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
  ...(WIN ? winPaths('Microsoft\\Edge\\Application\\msedge.exe') : []),
];
const ON_PATH = WIN ? ['chrome.exe', 'msedge.exe'] : ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser'];

/* CHROME_PATH first, then the usual install locations (Chrome before Edge), then the PATH */
export function findChrome() {
  if (process.env.CHROME_PATH) return fs.existsSync(process.env.CHROME_PATH) ? process.env.CHROME_PATH : null;
  for (const file of CANDIDATES) if (fs.existsSync(file)) return file;
  for (const dir of (process.env.PATH || '').split(path.delimiter)) {
    for (const name of ON_PATH) { const file = path.join(dir, name); if (dir && fs.existsSync(file)) return file; }
  }
  return null;
}

function connect(url) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(url), pending = new Map(), listeners = new Set();
    let next = 0;
    ws.onerror = () => reject(new Error('could not open the DevTools websocket'));
    ws.onmessage = event => {
      const msg = JSON.parse(event.data);
      if (!msg.id) { for (const fn of listeners) fn(msg); return; }
      const call = pending.get(msg.id); if (!call) return;
      pending.delete(msg.id);
      if (msg.error) call.reject(new Error(`${call.method}: ${msg.error.message}`)); else call.resolve(msg.result);
    };
    ws.onopen = () => resolve({
      send(method, params = {}, sessionId) {
        const msg = {id: ++next, method, params, ...(sessionId ? {sessionId} : {})};
        return new Promise((ok, fail) => { pending.set(msg.id, {resolve: ok, reject: fail, method}); ws.send(JSON.stringify(msg)); });
      },
      on(fn) { listeners.add(fn); },
      close() { ws.close(); },
    });
  });
}

/* Fresh profile per run, headless=new, a fixed window size. blockUrls: URL patterns that never load
   (the tests block the font and MathJax CDNs so they run offline and fast). */
export async function launch(chromePath, {blockUrls = []} = {}) {
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'sg-chrome-'));
  const args = ['--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profile}`, '--no-first-run',
    '--no-default-browser-check', '--disable-extensions', '--disable-background-networking', '--disable-component-update',
    '--disable-sync', '--mute-audio', '--disable-gpu', '--window-size=1280,900', 'about:blank'];
  if (process.platform === 'linux' && process.getuid?.() === 0) args.push('--no-sandbox');
  const proc = spawn(chromePath, args, {stdio: ['ignore', 'ignore', 'pipe']});
  const exited = new Promise(resolve => proc.on('exit', resolve));
  const wsUrl = await new Promise((resolve, reject) => {
    let log = '';
    const timer = setTimeout(() => reject(new Error('Chrome did not start in 20 s:\n' + log.slice(-800))), 20000);
    proc.stderr.on('data', chunk => {
      log = (log + chunk).slice(-4000);
      const m = log.match(/DevTools listening on (ws:\/\/\S+)/);
      if (m) { clearTimeout(timer); resolve(m[1]); }
    });
    exited.then(code => { clearTimeout(timer); reject(new Error(`Chrome exited (${code}):\n${log.slice(-800)}`)); });
  });
  const conn = await connect(wsUrl);
  return {
    async newPage() {
      const {targetId} = await conn.send('Target.createTarget', {url: 'about:blank'});
      const {sessionId} = await conn.send('Target.attachToTarget', {targetId, flatten: true});
      const page = new Page((method, params) => conn.send(method, params, sessionId));
      conn.on(msg => { if (msg.sessionId === sessionId) page.handle(msg); });
      await Promise.all(['Page.enable', 'Runtime.enable', 'Log.enable', 'Network.enable'].map(m => page.send(m)));
      if (blockUrls.length) await page.send('Network.setBlockedURLs', {urls: blockUrls});
      return page;
    },
    async close() {
      await Promise.race([conn.send('Browser.close').catch(() => {}), new Promise(r => setTimeout(r, 2000))]);
      conn.close();
      if (proc.exitCode == null) proc.kill();
      await Promise.race([exited, new Promise(r => setTimeout(r, 3000))]);
      // Windows can keep profile files locked for a moment after Chrome exits; a leftover temp profile is not a failure
      try { fs.rmSync(profile, {recursive: true, force: true, maxRetries: 10, retryDelay: 200}); } catch {}
    },
  };
}

export class Page {
  constructor(send) { this.send = send; this.errors = []; this.loadWaiters = []; }
  handle({method, params}) {
    if (method === 'Page.loadEventFired') this.loadWaiters.splice(0).forEach(fn => fn());
    else if (method === 'Runtime.exceptionThrown') {
      const d = params.exceptionDetails; this.errors.push('exception: ' + (d.exception?.description || d.text));
    } else if (method === 'Runtime.consoleAPICalled' && (params.type === 'error' || params.type === 'assert')) {
      this.errors.push('console.error: ' + params.args.map(a => a.value ?? a.description).join(' '));
    } else if (method === 'Log.entryAdded' && params.entry.level === 'error' && params.entry.source !== 'network') {
      this.errors.push('log: ' + params.entry.text);  // blocked CDN requests are network entries, not page errors
    }
  }
  loaded() { return new Promise(resolve => this.loadWaiters.push(resolve)); }
  async goto(url) { const done = this.loaded(); await this.send('Page.navigate', {url}); await done; }
  async reload() { const done = this.loaded(); await this.send('Page.reload'); await done; }
  /* evaluate fn(...args) in the page and return its JSON value */
  async eval(fn, ...args) {
    const r = await this.send('Runtime.evaluate', {expression: `(${fn})(...${JSON.stringify(args)})`, awaitPromise: true, returnByValue: true});
    if (r.exceptionDetails) throw new Error('in page: ' + (r.exceptionDetails.exception?.description || r.exceptionDetails.text));
    return r.result.value;
  }
  async waitFor(fn, ...args) {
    const end = Date.now() + 5000;
    for (;;) {
      const value = await this.eval(fn, ...args);
      if (value) return value;
      if (Date.now() > end) throw new Error('timed out waiting for ' + String(fn).slice(0, 200) + ' ' + JSON.stringify(args));
      await new Promise(r => setTimeout(r, 40));
    }
  }
  /* a real mouse click in the middle of the first visible element that matches the selector and contains the
     text (or equals it, with exact), after checking that nothing covers it */
  async click(selector, text, {exact = false} = {}) {
    const at = await this.waitFor((sel, txt, ex) => {
      const norm = s => s.replace(/\s+/g, ' ').trim();
      const el = [...document.querySelectorAll(sel)].find(e => e.checkVisibility() &&
        (txt == null || (ex ? norm(e.textContent) === txt : norm(e.textContent).includes(txt))));
      if (!el) return null;
      el.scrollIntoView({block: 'center', behavior: 'instant'});
      const r = el.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2;
      const hit = document.elementFromPoint(x, y);
      if (!hit || !(hit === el || el.contains(hit))) throw new Error(`${sel} "${txt || ''}" is covered by ${hit && hit.outerHTML.slice(0, 120)}`);
      return {x, y};
    }, selector, text ?? null, exact);
    for (const type of ['mouseMoved', 'mousePressed', 'mouseReleased'])
      await this.send('Input.dispatchMouseEvent', {type, x: at.x, y: at.y, button: 'left', clickCount: type === 'mouseMoved' ? 0 : 1});
  }
  /* focus an input and type into it the way a keyboard would (fires input events) */
  async type(selector, text) {
    await this.click(selector);
    await this.send('Input.insertText', {text});
  }
  text(selector) { return this.eval(sel => { const e = document.querySelector(sel); return e ? e.textContent.replace(/\s+/g, ' ').trim() : null; }, selector); }
}
