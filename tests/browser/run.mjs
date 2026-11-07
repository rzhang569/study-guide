#!/usr/bin/env node
/* Real-browser tests for the review page engine (engine.js + page.css) in headless Chrome.
 *
 *   node tests/browser/run.mjs
 *
 * Zero dependencies: Node >= 20, Python, and Chrome, Chromium or Edge. Node 22+ has a global WebSocket; on Node 20
 * this script re-runs itself with --experimental-websocket, so the same command works. Chrome is found via CHROME_PATH, then
 * the usual macOS/Linux/Windows locations (Chrome first, then Edge), then the PATH; Python is PYTHON, then python3,
 * python or py -3. Without a browser or Python it prints SKIP and exits 0.
 * Pages are built from a temporary copy of examples/demo with scripts/build.py (once in English, once in Chinese),
 * opened over file:// with a fresh Chrome profile, and the font/MathJax CDNs are blocked so the run is offline.
 * Not picked up by `node --test` on purpose: the unit tests stay browser-free. */
import {spawnSync} from 'node:child_process';
import fs from 'node:fs';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';

const skip = why => {
  /* CI sets REQUIRE_BROWSER=1 so a missing browser fails the job instead of passing silently */
  if (process.env.REQUIRE_BROWSER) { console.log(`FAIL: browser tests not run: ${why}`); process.exit(1); }
  console.log(`SKIP: browser tests not run: ${why}`); process.exit(0);
};

if (typeof WebSocket === 'undefined') {
  if (process.execArgv.includes('--experimental-websocket') || +process.versions.node.split('.')[0] < 20)
    skip(`Node ${process.version} has no WebSocket (use Node 20 or newer)`);
  const r = spawnSync(process.execPath, ['--experimental-websocket', ...process.execArgv, fileURLToPath(import.meta.url), ...process.argv.slice(2)], {stdio: 'inherit'});
  process.exit(r.status ?? 1);
}
const {findChrome, launch} = await import('./cdp.mjs');
const chrome = findChrome();
if (!chrome) skip('Chrome, Chromium or Edge not found (set CHROME_PATH)');
const {findPython, buildDemo} = (await import('../build-demo.cjs')).default;
if (!findPython()) skip('Python not found (set PYTHON; needed to build the pages)');
console.log(`# browser: ${chrome}\n# python: ${findPython().join(' ')}`);

const {test, before, after, afterEach} = await import('node:test');
const assert = (await import('node:assert/strict')).default;
const KEY = 'demo-prob101-mt1';

/* fallback when localStorage does not work on file://: a static server on 127.0.0.1 with an ephemeral port */
function serve(dir) {
  const server = http.createServer((req, res) => {
    const file = path.join(dir, path.basename(decodeURIComponent(new URL(req.url, 'http://x').pathname)));
    fs.readFile(file, (err, body) => { res.writeHead(err ? 404 : 200, {'content-type': 'text/html; charset=utf-8'}); res.end(err ? '' : body); });
  });
  return new Promise(resolve => server.listen(0, '127.0.0.1', () => resolve({server, base: `http://127.0.0.1:${server.address().port}/`})));
}

let browser, page, tmp, server, url = {};
before(async () => {
  tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'sg-browser-'));
  const files = {en: buildDemo(tmp, 'en'), zh: buildDemo(tmp, 'zh')};
  browser = await launch(chrome, {blockUrls: ['https://fonts.googleapis.com/*', 'https://fonts.gstatic.com/*', 'https://cdnjs.cloudflare.com/*']});
  page = await browser.newPage();
  for (const lang of ['en', 'zh']) url[lang] = pathToFileURL(files[lang]).href;
  await page.goto(url.en);
  const storageOk = await page.eval(() => { try { localStorage.setItem('probe', '1'); return localStorage.getItem('probe') === '1'; } catch (e) { return false; } });
  if (!storageOk) {
    const s = await serve(tmp); server = s.server;
    for (const lang of ['en', 'zh']) url[lang] = s.base + path.basename(files[lang]);
    console.log('# localStorage does not work on file:// here; serving over ' + s.base);
  }
});
after(async () => {
  if (browser) await browser.close();
  if (server) server.close();
  if (tmp) fs.rmSync(tmp, {recursive: true, force: true, maxRetries: 5});
});
afterEach(() => { if (page) { const errors = page.errors.splice(0); assert.deepEqual(errors, [], 'console errors or uncaught exceptions'); } });

/* open a build with empty storage */
async function fresh(lang) {
  await page.goto(url[lang]);
  await page.eval(() => localStorage.clear());
  await page.reload();
  await page.waitFor(() => document.querySelectorAll('#bank-practice .q').length > 0);
}
const stored = key => page.eval(k => JSON.parse(localStorage.getItem(k) || 'null'), `${KEY}:${key}`);
const optionsOf = sel => page.eval(s => [...document.querySelectorAll(s + ' .opt')].map(o =>
  [o.querySelector('.bub').textContent, o.querySelector('.otext').firstChild.textContent, o.className]), sel);

test('en page loads with no console errors; the practice center, section boxes and [hidden] work', async () => {
  await fresh('en');
  const info = await page.eval(() => ({
    tabs: [...document.querySelectorAll('[data-tab]')].map(b => b.textContent),
    cards: document.querySelectorAll('#bank-practice .q').length,
    boxes: [...document.querySelectorAll('.secprac .sp-title')].map(e => e.textContent),
    bar: document.querySelector('#bar-practice .score').textContent,
    mockHidden: getComputedStyle(document.getElementById('wrap-mock')).display,
  }));
  assert.deepEqual(info.tabs, ['Practice', 'Short answer', 'Mock exam', 'Mistakes']);
  assert.equal(info.cards, 24);
  assert.deepEqual(info.boxes, Array(3).fill('Practice for this section'));
  assert.match(info.bar, /^Answered 0 \/ 23/);
  assert.equal(info.mockHidden, 'none');
  // display:flex rules must not beat the hidden attribute
  const shown = await page.eval(() => ['pnav', 'flagbar'].map(cls => {
    const d = document.createElement('div'); d.className = cls; d.hidden = true; document.body.appendChild(d);
    const v = getComputedStyle(d).display; d.remove(); return v;
  }));
  assert.deepEqual(shown, ['none', 'none']);
});

test('a practice answer (clicked by its visible text) shows feedback and survives a reload', async () => {
  await fresh('en');
  await page.click('[id="q-p-p1-1"] .otext', '1/11');
  await page.waitFor(() => document.querySelector('[id="q-p-p1-1"] .why'));
  const why = await page.text('[id="q-p-p1-1"] .why'), opts = await optionsOf('[id="q-p-p1-1"]');
  assert.match(why, /^First pick was C; the answer is B\./);
  assert.deepEqual(opts.map(o => o.slice(0, 2)), [['A', '1/12'], ['B', '1/6'], ['C', '1/11'], ['D', '7/36']]);
  assert.deepEqual((await stored('practice')).ans['p1-1'], {first: 1, tried: [1]});   // original index of 1/11
  await page.reload();
  await page.waitFor(() => document.querySelector('[id="q-p-p1-1"] .why'));
  assert.equal(await page.text('[id="q-p-p1-1"] .why'), why);
  assert.deepEqual(await optionsOf('[id="q-p-p1-1"]'), opts);
  assert.match(opts[2][2], /\bwrong\b/); assert.match(opts[1][2], /\bright\b/);
  assert.match(await page.text('#sp-l1 .sp-meta'), /8 questions · 1 done · first-try accuracy 0%/);
});

test('short-answer redo after a miss never restores first-try credit (choice and self-marked steps)', async () => {
  await fresh('en');
  await page.click('[data-tab="sa"]');
  const card = '[id="sa-p-sa-a1"]', self = '[id="sa-p-sa-b2"]';
  await page.click(card + ' .otext', 'The test is broken');
  await page.click(card + ' button', 'Redo this step', {exact: true});
  await page.click(card + ' .otext', 'False positives from the large healthy group');
  assert.equal(await page.text(card + ' .qmeta .qscore'), 'First try 0 / 10 (after fixes 1)');
  for (const label of ['Done, show answer', 'I missed it', 'Redo this step', 'Done, show answer', 'I got it'])
    await page.click(self + ' button', label, {exact: true});
  assert.equal(await page.text(self + ' .qmeta .qscore'), 'First try 0 / 2 (after fixes 1)');
  const sa = (await stored('practice')).sa;
  assert.deepEqual(sa['sa-a1'][3], {tries: 1, tried: [1, 0], v: 0, ok: true, shown: true});
  await page.reload();
  await page.waitFor(s => document.querySelector(s + ' .qscore'), card);
  assert.equal(await page.text(card + ' .qmeta .qscore'), 'First try 0 / 10 (after fixes 1)');
  assert.equal(await page.text(self + ' .qmeta .qscore'), 'First try 0 / 2 (after fixes 1)');
});

test('a full mock paper is handed in, the score report has the per-lecture table, the notebook keeps the mistakes', async () => {
  await fresh('en');
  await page.click('[data-tab="mock"]');
  const cards = await page.waitFor(() => {
    const qs = [...document.querySelectorAll('#bank-mock .q')];
    return qs.length && qs.map(c => [c.id, !!c.querySelector('input')]);
  });
  assert.equal(cards.length, 11);
  await page.click(`[id="${cards[0][0]}"] .flagbtn`);
  for (const [id, isFill] of cards) {
    if (isFill) await page.type(`[id="${id}"] input`, '0');    // every demo fill answer is nonzero
    else await page.click(`[id="${id}"] .opt`);
  }
  await page.click('#bar-mock button', 'Hand in', {exact: true});
  await page.waitFor(() => document.querySelector('#sum-mock .summary'));
  const report = await page.eval(() => ({
    title: document.querySelector('#sum-mock h3').textContent,
    rows: [...document.querySelectorAll('#sum-mock .summary table.gtable tr')].slice(1).map(r => r.cells[0].textContent),
    bar: document.querySelector('#bar-mock .score').textContent,
  }));
  assert.equal(report.title, 'Score report');
  assert.deepEqual(report.rows, ['L1', 'L2', 'L3']);
  assert.match(report.bar, /^Handed in · score/);
  await page.click('[data-tab="book"]');
  await page.waitFor(() => document.querySelector('#bank-book .q'));
  const book = await page.text('#bank-book');
  assert.match(book, /Wrong on mock paper 1; you answered “0”/);
  assert.match(book, /Flagged on mock paper 1/);
  assert.match(await page.text('[data-tab="book"]'), /^Mistakes \(\d+\)$/);
  const mock = await stored('mock');
  assert.equal(mock.book.v, 1); assert.equal(mock.book.papers, 1);
  await page.reload();
  await page.waitFor(() => document.querySelector('#bank-book .q'));   // the remembered tab reopens the notebook
  assert.equal(await page.text('#bank-book'), book);
});

test('the zh build renders Chinese UI strings', async () => {
  await fresh('zh');
  const info = await page.eval(() => ({
    lang: document.documentElement.lang,
    tabs: [...document.querySelectorAll('[data-tab]')].map(b => b.textContent),
    box: document.querySelector('.secprac .sp-title').textContent,
    bar: document.querySelector('#bar-practice .score').textContent,
  }));
  assert.equal(info.lang, 'zh-CN');
  assert.deepEqual(info.tabs, ['练习题', '简答分步', '模拟考试', '错题本']);
  assert.equal(info.box, '本节练习');
  assert.match(info.bar, /^已答 0 \/ 23/);
  await page.click('[id="q-p-p1-1"] .otext', '1/11');
  assert.match(await page.waitFor(() => document.querySelector('[id="q-p-p1-1"] .why')?.textContent), /^第一次选了 C，正确答案是 B。/);
});
