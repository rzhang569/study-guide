#!/usr/bin/env node
/* Checks that a refactor changed nothing a student can see: builds the demo with an older version of the skill
 * (a git ref, default main) and with the working tree, then drives both pages through the same scripted tour in
 * headless Chrome and compares, at every checkpoint, each element's tag, attributes, own text and full computed
 * style (pseudo-elements included).
 *
 *   node tests/browser/compare.mjs [ref] [--quick]
 *
 * Both pages use the current demo data, a seeded Math.random and a frozen clock, and each has its own localStorage.
 * The tour runs in English and Chinese at several window widths and in print media (--quick: 1280 px only).
 * Exits 1 on the first checkpoint that differs and prints the elements and style properties that changed.
 * Needs git, tar, Python and Chrome; it is a tool for refactors, not part of the test suites. */
import {spawnSync} from 'node:child_process';
import fs from 'node:fs';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

if (typeof WebSocket === 'undefined') {
  const r = spawnSync(process.execPath, ['--experimental-websocket', fileURLToPath(import.meta.url), ...process.argv.slice(2)], {stdio: 'inherit'});
  process.exit(r.status ?? 1);
}
const {findChrome, launch} = await import('./cdp.mjs');
const {buildDemo} = (await import('../build-demo.cjs')).default;
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const args = process.argv.slice(2), quick = args.includes('--quick');
const ref = args.find(a => !a.startsWith('--')) || 'main';
const chrome = findChrome();
if (!chrome) { console.log('Chrome, Chromium or Edge not found (set CHROME_PATH)'); process.exit(1); }

/* the older skill folder, from git */
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'sg-compare-'));
const base = path.join(tmp, 'base');
fs.mkdirSync(base);
const archive = spawnSync('git', ['-C', ROOT, 'archive', '--format=tar', ref, 'skills/study-guide'], {maxBuffer: 1 << 28});
if (archive.status !== 0) { console.log(`git archive ${ref} failed: ${archive.stderr}`); process.exit(1); }
spawnSync('tar', ['-x', '-C', base], {input: archive.stdout});
const pages = {};
for (const lang of ['en', 'zh']) {
  pages[lang] = {
    a: path.basename(buildDemo(tmp, lang, {build: path.join(base, 'skills/study-guide/scripts/build.py'), name: `a-${lang}.html`})),
    b: path.basename(buildDemo(tmp, lang, {name: `b-${lang}.html`})),
  };
}
const server = http.createServer((req, res) => {
  fs.readFile(path.join(tmp, path.basename(new URL(req.url, 'http://x').pathname)), (err, body) => {
    res.writeHead(err ? 404 : 200, {'content-type': 'text/html; charset=utf-8'}); res.end(err ? '' : body);
  });
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const origin = `http://127.0.0.1:${server.address().port}/`;

/* same random numbers and the same "now" in both pages; __advance(ms) moves the clock */
const DETERMINISM = `(() => {
  let s = 20261107;
  Math.random = () => { s = s + 0x6D2B79F5 | 0; let t = Math.imul(s ^ s >>> 15, 1 | s);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
  const R = Date, T = R.UTC(2026, 10, 7, 15, 0, 0); let off = 0;
  class D extends R { constructor(...a) { super(...(a.length ? a : [T + off])); } static now() { return T + off; } }
  window.Date = D; window.__advance = ms => { off += ms; };
})();`;

/* runs in the page: one row per element under <body>, [depth, tag, attributes, own text, style hash];
   detail: row numbers to return full computed styles for */
function snapshot(detail) {
  const hash = s => { let h = 0x811c9dc5; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return (h >>> 0).toString(36); };
  const styleOf = (el, pe) => { const cs = getComputedStyle(el, pe), o = {}; for (let i = 0; i < cs.length; i++) o[cs[i]] = cs.getPropertyValue(cs[i]); return o; };
  const rows = [], full = {};
  const walk = (el, depth) => {
    const st = {'': styleOf(el)};
    for (const pe of ['::before', '::after']) { const c = getComputedStyle(el, pe).content; if (c && c !== 'none' && c !== 'normal') st[pe] = styleOf(el, pe); }
    const own = /^(SCRIPT|STYLE)$/.test(el.tagName) ? '' : [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.data).join('').replace(/\s+/g, ' ').trim();
    let attrs = [...el.attributes].map(a => a.name + '=' + a.value).sort().join(' ');
    if (attrs.length > 300) attrs = '#' + hash(attrs);
    if (detail.includes(rows.length)) full[rows.length] = st;
    rows.push([depth, el.tagName.toLowerCase(), attrs, own.length > 200 ? '#' + hash(own) : own, hash(JSON.stringify(st))]);
    for (const c of el.children) walk(c, depth + 1);
  };
  walk(document.body, 0);
  return {rows, full, scroll: [scrollX, scrollY]};
}

/* runs in the page: answer the first `max` cards under root the same way every time (rerenders replace cards,
   so each step looks the card up again by id) */
function work(root, max, rounds) {
  const ids = [...document.querySelectorAll(root + ' .q')].slice(0, max).map(c => c.id);
  const vis = e => e && e.checkVisibility();
  ids.forEach((id, k) => {
    for (let r = 0; r < rounds; r++) {
      const card = () => document.getElementById(id);
      if (!card()) return;
      const opts = [...card().querySelectorAll('.opt')].filter(vis).filter(o => !/\b(right|wrong|picked|sel|on)\b/.test(o.className));
      const input = [...card().querySelectorAll('input:not([type=checkbox])')].find(i => vis(i) && !i.value && !i.disabled);
      const button = [...card().querySelectorAll('button')].find(b => vis(b) && !b.disabled && !b.classList.contains('flagbtn'));
      if (opts.length) opts[(k + r) % opts.length].click();
      else if (input) {
        input.value = ['0.5', '1/6', 'abc'][(k + r) % 3];
        input.dispatchEvent(new Event('input', {bubbles: true}));
        input.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', bubbles: true}));
      } else if (button) button.click();
      else return;
    }
  });
  return ids.length;
}

const browser = await launch(chrome, {blockUrls: ['https://fonts.googleapis.com/*', 'https://fonts.gstatic.com/*', 'https://cdnjs.cloudflare.com/*']});
const both = {a: await browser.newPage({isolated: true}), b: await browser.newPage({isolated: true})};
for (const p of Object.values(both)) await p.send('Page.addScriptToEvaluateOnNewDocument', {source: DETERMINISM});
const run = (fn, ...a) => Promise.all([both.a.eval(fn, ...a), both.b.eval(fn, ...a)]);
/* wait until smooth scrolling has stopped: the same scroll position for 5 frames in a row (at most 3 s) */
const settle = () => run(() => new Promise(r => {
  let last = '', same = 0, frames = 0;
  const tick = () => { const now = scrollX + ',' + scrollY; same = now === last ? same + 1 : 0; last = now;
    if (same >= 5 || ++frames > 180) setTimeout(r, 30); else requestAnimationFrame(tick); };
  requestAnimationFrame(tick);
}));

let checkpoints = 0;
async function check(label) {
  await settle();
  const [a, b] = await run(snapshot, []);
  checkpoints++;
  const errors = [...both.a.errors.splice(0).map(e => 'old: ' + e), ...both.b.errors.splice(0).map(e => 'new: ' + e)];
  const where = i => {   // tag.class path of row i
    const out = []; let d = a.rows[i][0] + 1;
    for (let j = i; j >= 0 && d > 0; j--) if (a.rows[j][0] < d) { d = a.rows[j][0]; const cls = /(?:^| )class=([^ ]+(?: [^ =]+(?= |$))*)/.exec(a.rows[j][2]); out.unshift(a.rows[j][1] + (cls ? '.' + cls[1].split(' ').join('.') : '')); }
    return out.join(' > ');
  };
  const diffs = [];
  for (let i = 0; i < Math.max(a.rows.length, b.rows.length) && diffs.length < 8; i++) {
    const x = a.rows[i], y = b.rows[i];
    if (!x || !y || x.slice(0, 4).join('\u0001') !== y.slice(0, 4).join('\u0001')) {
      diffs.push(`  element ${i} differs (${x ? where(i) : 'missing in old'}):\n    old ${JSON.stringify(x?.slice(0, 4))}\n    new ${JSON.stringify(y?.slice(0, 4))}`);
      break;   // the trees no longer line up
    }
    if (x[4] !== y[4]) diffs.push(i);
  }
  const styled = diffs.filter(d => typeof d === 'number');
  if (styled.length) {
    const [fa, fb] = await run(snapshot, styled);
    for (const i of styled) {
      const props = [];
      for (const pe of new Set([...Object.keys(fa.full[i]), ...Object.keys(fb.full[i])]))
        for (const k of new Set([...Object.keys(fa.full[i][pe] || {}), ...Object.keys(fb.full[i][pe] || {})]))
          if (fa.full[i][pe]?.[k] !== fb.full[i][pe]?.[k]) props.push(`${pe}${k}: ${fa.full[i][pe]?.[k]} → ${fb.full[i][pe]?.[k]}`);
      diffs[diffs.indexOf(i)] = `  style of element ${i} (${where(i)}):\n    ` + props.slice(0, 8).join('\n    ');
    }
  }
  if (String(a.scroll) !== String(b.scroll)) diffs.push(`  scroll position: old ${a.scroll}, new ${b.scroll}`);
  if (errors.length) diffs.push('  page errors:\n    ' + errors.join('\n    '));
  if (diffs.length) {
    console.log(`DIFFERENT at "${label}" (${a.rows.length} vs ${b.rows.length} elements):\n${diffs.join('\n')}`);
    await browser.close(); server.close(); fs.rmSync(tmp, {recursive: true, force: true});
    process.exit(1);
  }
}

async function tour(lang, tag) {
  for (const k of ['a', 'b']) {
    await both[k].goto(origin + pages[lang][k]);
    await both[k].eval(() => localStorage.clear());
    await both[k].reload();
  }
  await run(() => new Promise(r => { const t = () => document.querySelector('#bank-practice .q') ? r() : setTimeout(t, 20); t(); }));
  const tab = name => run(n => document.querySelector(`[data-tab="${n}"]`).click(), name);
  await check(`${tag} load`);
  await run(work, '#bank-practice', 12, 3);
  await check(`${tag} practice answered`);
  await run(() => document.querySelector('.secprac .sp-toggle')?.click());
  await check(`${tag} section box open`);
  await run(work, '.secprac', 4, 2);
  await check(`${tag} section box answered`);
  await tab('sa');
  await check(`${tag} short-answer tab`);
  await run(work, '#bank-sa', 3, 8);
  await check(`${tag} short answers worked`);
  await tab('mock');
  await check(`${tag} mock tab`);
  await run(() => { const b = [...document.querySelectorAll('#bar-mock button')].find(x => !x.disabled && /start|开始/i.test(x.textContent)); b?.click(); });
  await run(() => window.__advance(7 * 60 * 1000));
  await run(() => document.querySelector('#bank-mock .q .flagbtn')?.click());
  await run(work, '#bank-mock', 6, 1);
  await check(`${tag} mock half answered`);
  await run(() => document.querySelector('.pnav button')?.click());
  await check(`${tag} paper navigator`);
  await run(work, '#bank-mock', 99, 1);
  await run(() => [...document.querySelectorAll('#bar-mock button')].find(b => !b.disabled && /hand in|交卷/i.test(b.textContent))?.click());
  await run(() => [...document.querySelectorAll('#bar-mock button')].find(b => !b.disabled && /hand in|交卷/i.test(b.textContent))?.click());
  await check(`${tag} mock handed in`);
  await tab('book');
  await check(`${tag} notebook`);
  await run(() => document.querySelectorAll('#bank-book .seg button, #wrap-book .seg button')[1]?.click());
  await check(`${tag} notebook filter`);
  await run(work, '#bank-book', 3, 2);
  await check(`${tag} notebook redo`);
  await run(() => [...document.querySelectorAll('button')].find(b => /export|导出/i.test(b.textContent) && b.checkVisibility())?.click());
  await check(`${tag} export panel`);
  for (const k of ['a', 'b']) await both[k].reload();
  await run(() => new Promise(r => { const t = () => document.querySelector('#bank-practice .q') ? r() : setTimeout(t, 20); t(); }));
  await check(`${tag} after reload`);
}

const viewports = quick ? [[1280, 900]] : [[1280, 900], [375, 812], [800, 1000], [1600, 1000], [2300, 1300], [2600, 1400]];
for (const [w, h] of viewports) {
  for (const p of Object.values(both)) await p.send('Emulation.setDeviceMetricsOverride', {width: w, height: h, deviceScaleFactor: 1, mobile: w < 600});
  for (const lang of (w === 1280 ? ['en', 'zh'] : ['en'])) await tour(lang, `${lang} ${w}px`);
}
for (const p of Object.values(both)) await p.send('Emulation.setEmulatedMedia', {media: 'print'});
await tour('en', 'en print');
console.log(`same: ${checkpoints} checkpoints match between ${ref} and the working tree`);
await browser.close(); server.close(); fs.rmSync(tmp, {recursive: true, force: true});
