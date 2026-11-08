#!/usr/bin/env node
/* Browser and file checks for the runs made by evals/ab.py, plus the material its graders read.
 *
 *   node evals/ab_check.mjs OUT
 *
 * For every run folder OUT/<name>/ it opens the built page in headless Chrome (font and MathJax CDNs blocked, as
 * offline) and records: script errors, sideways scrolling at 375 px, whether a practice answer survives a reload,
 * every figure's overlapping or clipped text (measured from the rendered page), slide citations, practice options
 * without an explanation, the mock layout, and the run's own final build warnings. Results go to OUT/checks.json.
 * It also writes OUT/grade/<name>/: notes.md (the notes' text in reading order), figures/figN.png and the page's
 * settings and banks as JSON. (`ab.py grade` adds the slides' text.) Needs Node 20 or newer, Python (PYTHON, else
 * python3 / python / py -3) and Chrome. */
import {spawnSync} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';

/* Node 20 has WebSocket only behind a flag: run again with it */
if (typeof WebSocket === 'undefined') {
  if (process.execArgv.includes('--experimental-websocket') || +process.versions.node.split('.')[0] < 20) {
    console.error(`Node ${process.version} has no WebSocket; use Node 20 or newer`); process.exit(1);
  }
  const r = spawnSync(process.execPath, ['--experimental-websocket', ...process.execArgv, fileURLToPath(import.meta.url), ...process.argv.slice(2)], {stdio: 'inherit'});
  process.exit(r.status ?? 1);
}
const HERE = path.dirname(fileURLToPath(import.meta.url));
const {findChrome, launch} = await import(pathToFileURL(path.join(HERE, '../tests/browser/cdp.mjs')).href);
const {findPython} = (await import(pathToFileURL(path.join(HERE, '../tests/build-demo.cjs')).href)).default;
const OUT = path.resolve(process.argv[2] || '');
if (!fs.existsSync(path.join(OUT, 'meta.json'))) { console.error('usage: node evals/ab_check.mjs OUT (made by ab.py run)'); process.exit(1); }
const python = findPython();
if (!python) { console.error('Python not found (set PYTHON)'); process.exit(1); }
const chrome = findChrome();
if (!chrome) { console.error('Chrome, Chromium or Edge not found (set CHROME_PATH)'); process.exit(1); }
const GRADE = path.join(OUT, 'grade');
fs.mkdirSync(GRADE, {recursive: true});
const slash = p => p.split(path.sep).join('/');

function find(dir, name) {
  const hits = [];
  for (const e of fs.readdirSync(dir, {withFileTypes: true})) {
    const p = path.join(dir, e.name);
    if (e.name === '.claude' || e.name === 'node_modules') continue;
    if (e.isDirectory()) hits.push(...find(p, name));
    else if (e.name === name) hits.push(p);
  }
  return hits;
}

const browser = await launch(chrome, {blockUrls: ['https://fonts.googleapis.com/*', 'https://fonts.gstatic.com/*', 'https://cdnjs.cloudflare.com/*']});
const results = {};
const runs = fs.readdirSync(OUT, {withFileTypes: true}).filter(e => e.isDirectory() && /^[A-Za-z]+-\d+$/.test(e.name)).map(e => e.name).sort();
for (const run of runs) {
  const dir = path.join(OUT, run), r = results[run] = {};
  const pages = find(dir, 'review.html');
  const pagePath = pages.find(p => slash(p).includes('/econ150-review/')) || pages[0];
  r.folder = fs.existsSync(path.join(dir, 'econ150-review'));
  if (!pagePath) { r.page = null; continue; }
  r.page = slash(path.relative(dir, pagePath));
  const course = path.dirname(pagePath);
  const secDir = path.join(course, 'sections');
  r.section_files = fs.existsSync(secDir) ? fs.readdirSync(secDir).sort() : [];
  const [py, ...pyArgs] = python;
  const b = spawnSync(py, [...pyArgs, path.join(dir, '.claude/skills/study-guide/scripts/build.py'), course, '--check'],
    {encoding: 'utf8', env: {...process.env, PYTHONIOENCODING: 'utf-8'}});
  r.final_build = {exit: b.status, warnings: (b.stdout.match(/^warning: .*/gm) || []), errors: (b.stdout.match(/^error: .*/gm) || [])};

  const page = await browser.newPage({isolated: true});
  const url = pathToFileURL(pagePath).href;
  await page.send('Emulation.setDeviceMetricsOverride', {width: 1280, height: 900, deviceScaleFactor: 1, mobile: false});
  await page.goto(url);
  await new Promise(res => setTimeout(res, 300));
  r.errors_on_load = page.errors.splice(0);
  const data = await page.eval(() => window.STUDY_DATA || null);
  r.has_engine = !!data;
  if (data) {
    const items = (data.practice.items || []);
    const choice = items.filter(q => ['single', 'multi', 'tf', undefined].includes(q.type));
    r.practice = {items: items.length, choice: choice.length,
      options_without_why: choice.reduce((n, q) => n + (q.type === 'tf' ? (q.opts || [{}, {}]) : (q.opts || [])).filter(o => !(o && String(o.why || '').trim())).length, 0)};
    r.mock = {items: (data.mock.items || []).length, sections: data.config.mock?.sections || 'default',
      minutes: data.config.mock?.minutes || null, short_items: (data.short.items || []).length};
    fs.mkdirSync(path.join(GRADE, run), {recursive: true});
    fs.writeFileSync(path.join(GRADE, run, 'course.json'), JSON.stringify(data.config, null, 1));
    for (const name of ['practice', 'mock', 'short']) fs.writeFileSync(path.join(GRADE, run, name + '.json'), JSON.stringify(data[name], null, 1));
  }
  /* a practice answer survives a reload: answer the bank's first question the way its type needs (click a choice;
     pick and submit a multi-select; type and submit a fill-in; reveal a flashcard), then compare its saved record and
     its card before and after the reload */
  if (data && (data.practice.items || []).length) {
    const key = data.config.storageKey, q = data.practice.items[0];
    await page.eval(() => localStorage.clear());
    await page.reload();
    await new Promise(res => setTimeout(res, 200));
    const done = await page.eval(q => {
      const card = () => document.getElementById('q-p-' + q.id);  // the engine redraws the card after each step
      if (!card()) return 'its card is not on the page';
      const click = sel => { const e = card().querySelector(sel); if (!e) return false; e.click(); return true; };
      if (q.type === 'card') return click('.reveal') || 'no reveal button';
      if (q.type === 'fill') {
        const inp = card().querySelector('input');
        if (!inp) return 'no answer box';
        inp.value = String((q.accept || [])[0] ?? '');
        return click('.fillrow .btn') || 'no submit button';
      }
      if (!click('.opt')) return 'no options';
      if (q.type === 'multi') return click('.qfoot .btn') || 'no submit button';
      return true;
    }, q);
    await new Promise(res => setTimeout(res, 200));
    const snap = id => page.eval((id, k) => {
      const st = JSON.parse(localStorage.getItem(k + ':practice') || 'null'), card = document.getElementById('q-p-' + id);
      return {saved: st && st.ans ? st.ans[id] ?? null : null,
        card: card ? [card.className, [...card.querySelectorAll('.opt')].map(o => o.className).join('|'),
          card.querySelector('.why:not([hidden])')?.textContent || '', card.querySelector('input')?.value ?? ''] : null};
    }, id, key);
    const before = await snap(q.id);
    await page.reload();
    await new Promise(res => setTimeout(res, 300));
    const after = await snap(q.id);
    r.reload_check = {question: q.id, type: q.type || 'single', answered: done === true ? 'yes' : done};
    r.answer_survives_reload = done === true && before.saved !== null && JSON.stringify(before) === JSON.stringify(after);
  }
  /* figures: rendered text boxes */
  r.figures = await page.eval(() => [...document.querySelectorAll('main .dia svg')].map(svg => {
    const s = svg.getBoundingClientRect(), problems = [];
    const boxes = [...svg.querySelectorAll('text')].filter(t => t.textContent.trim()).map(t => ({s: t.textContent, r: t.getBoundingClientRect()}));
    boxes.forEach((a, i) => {
      if (a.r.left < s.left - 1 || a.r.right > s.right + 1 || a.r.top < s.top - 1 || a.r.bottom > s.bottom + 1) problems.push(`"${a.s}" leaves the figure`);
      boxes.slice(i + 1).forEach(b => {
        /* glyph boxes include line spacing, so two stacked lines touch; count an overlap only when it covers more
           than a third of the shorter label's height */
        const w = Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left);
        const h = Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top);
        if (w > 2 && h > Math.min(a.r.height, b.r.height) / 3) problems.push(`"${a.s}" x "${b.s}"`);
      });
    });
    return {section: svg.closest('section')?.id || '', texts: boxes.length, text_problems: problems,
      caption: svg.closest('figure')?.querySelector('figcaption')?.textContent.trim() || ''};
  }));
  /* screenshots of each figure */
  const gdir = path.join(GRADE, run, 'figures');
  fs.mkdirSync(gdir, {recursive: true});
  const n = await page.eval(() => document.querySelectorAll('main .dia svg').length);
  for (let i = 0; i < n; i++) {
    const rect = await page.eval(k => { const f = document.querySelectorAll('main .dia svg')[k].closest('figure') || document.querySelectorAll('main .dia svg')[k];
      f.scrollIntoView({block: 'start'}); const b = f.getBoundingClientRect(); return {x: b.left, y: b.top + window.scrollY, w: b.width, h: b.height}; }, i);
    const shot = await page.send('Page.captureScreenshot', {format: 'png', clip: {x: rect.x, y: rect.y, width: rect.w, height: rect.h, scale: 1}, captureBeyondViewport: true});
    fs.writeFileSync(path.join(gdir, `fig${i + 1}.png`), Buffer.from(shot.data, 'base64'));
  }
  /* the notes as text: figures become [Figure N] + caption, formulas their TeX; the practice center is left out */
  const notes = await page.eval(() => {
    const main = document.querySelector('main');
    main.querySelectorAll('#practice, .secprac, footer').forEach(e => e.remove());
    main.querySelectorAll('.dia').forEach((d, i) => { const p = document.createElement('p'); p.textContent = `[Figure ${i + 1}]`; d.replaceWith(p); });
    main.querySelectorAll('figcaption').forEach(c => { c.textContent = 'Caption: ' + c.textContent; });
    main.querySelectorAll('[data-tex]').forEach(m => { m.textContent = (m.classList.contains('tex-d') ? '$$' : '$') + m.dataset.tex + (m.classList.contains('tex-d') ? '$$' : '$'); });
    main.querySelectorAll('details').forEach(d => { d.open = true; });
    return main.innerText;
  });
  fs.writeFileSync(path.join(GRADE, run, 'notes.md'), notes);
  r.citations = (notes.match(/\bL\s?\d+\s*(?:p\.?|pp\.?|slide)\s*\d+/gi) || []).length;
  r.notes_chars = notes.length;
  /* 375 px wide */
  await page.send('Emulation.setDeviceMetricsOverride', {width: 375, height: 812, deviceScaleFactor: 2, mobile: true});
  await page.goto(url);
  await new Promise(res => setTimeout(res, 300));
  r.sideways_at_375 = await page.eval(() => Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - window.innerWidth);
  r.errors_later = page.errors.splice(0);
  r.figures_by_section = r.figures.reduce((m, f) => (m[f.section] = (m[f.section] || 0) + 1, m), {});
  r.figure_text_problems = r.figures.reduce((n, f) => n + f.text_problems.length, 0);
  console.log(`${run}: ${r.page}, sections ${r.section_files.join(' ')}, figures ${JSON.stringify(r.figures_by_section)}, text problems ${r.figure_text_problems}, citations ${r.citations}, sideways ${r.sideways_at_375}, reload ${r.answer_survives_reload}, errors ${r.errors_on_load.length + r.errors_later.length}, final warnings ${r.final_build.warnings.length}`);
}
await browser.close();
fs.writeFileSync(path.join(OUT, 'checks.json'), JSON.stringify(results, null, 1));
