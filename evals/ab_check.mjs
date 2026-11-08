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
 * settings and banks as JSON, plus OUT/grade/slides.txt. Needs Node 22+ (or 20 with --experimental-websocket),
 * Python with pypdf, and Chrome. */
import {spawnSync} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const {findChrome, launch} = await import(pathToFileURL(path.join(HERE, '../tests/browser/cdp.mjs')).href);
const OUT = path.resolve(process.argv[2] || '');
if (!fs.existsSync(path.join(OUT, 'meta.json'))) { console.error('usage: node evals/ab_check.mjs OUT (made by ab.py run)'); process.exit(1); }
const meta = JSON.parse(fs.readFileSync(path.join(OUT, 'meta.json'), 'utf8'));
const GRADE = path.join(OUT, 'grade');
fs.mkdirSync(GRADE, {recursive: true});

/* the slides as text, for the graders */
const slides = spawnSync('python3', ['-c', `
import sys, pypdf
for f in sys.argv[1:]:
    r = pypdf.PdfReader(f)
    for i, p in enumerate(r.pages, 1):
        print(f"=== {f.split('/')[-1]} p.{i}"); print((p.extract_text() or '').strip())
`, ...fs.readdirSync(path.join(HERE, meta.case, 'files/slides')).sort().map(f => path.join(HERE, meta.case, 'files/slides', f))], {encoding: 'utf8'});
fs.writeFileSync(path.join(GRADE, 'slides.txt'), slides.stdout);

function find(dir, name, skip = /\/\.claude\//) {
  const hits = [];
  for (const e of fs.readdirSync(dir, {withFileTypes: true})) {
    const p = path.join(dir, e.name);
    if (skip.test(p + '/')) continue;
    if (e.isDirectory()) hits.push(...find(p, name, skip));
    else if (e.name === name) hits.push(p);
  }
  return hits;
}

const browser = await launch(findChrome(), {blockUrls: ['https://fonts.googleapis.com/*', 'https://fonts.gstatic.com/*', 'https://cdnjs.cloudflare.com/*']});
const results = {};
const runs = fs.readdirSync(OUT, {withFileTypes: true}).filter(e => e.isDirectory() && /^[A-Za-z]+-\d+$/.test(e.name)).map(e => e.name).sort();
for (const run of runs) {
  const dir = path.join(OUT, run), r = results[run] = {};
  const pages = find(dir, 'review.html');
  const pagePath = pages.find(p => p.includes('/econ150-review/')) || pages[0];
  r.folder = fs.existsSync(path.join(dir, 'econ150-review'));
  if (!pagePath) { r.page = null; continue; }
  r.page = path.relative(dir, pagePath);
  const course = path.dirname(pagePath);
  const secDir = path.join(course, 'sections');
  r.section_files = fs.existsSync(secDir) ? fs.readdirSync(secDir).sort() : [];
  const b = spawnSync('python3', [path.join(dir, '.claude/skills/study-guide/scripts/build.py'), course, '--check'], {encoding: 'utf8'});
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
    for (const name of ['practice', 'mock', 'short']) fs.mkdirSync(path.join(GRADE, run), {recursive: true});
    fs.writeFileSync(path.join(GRADE, run, 'course.json'), JSON.stringify(data.config, null, 1));
    for (const name of ['practice', 'mock', 'short']) fs.writeFileSync(path.join(GRADE, run, name + '.json'), JSON.stringify(data[name], null, 1));
  }
  /* a practice answer survives a reload */
  if (data) {
    const key = data.config.storageKey;
    await page.eval(() => localStorage.clear());
    await page.reload();
    await new Promise(res => setTimeout(res, 200));
    const clicked = await page.eval(() => { const o = document.querySelector('#bank-practice .q .opt'); if (!o) return null; o.click(); return o.closest('.q').id; });
    await new Promise(res => setTimeout(res, 200));
    await page.reload();
    await new Promise(res => setTimeout(res, 300));
    r.answer_survives_reload = !!clicked && await page.eval((id, k) => {
      const st = JSON.parse(localStorage.getItem(k + ':practice') || 'null');
      return !!(st && Object.keys(st.ans || {}).length && document.getElementById(id)?.querySelector('.why'));
    }, clicked, key);
  }
  /* figures: rendered text boxes */
  r.figures = await page.eval(() => [...document.querySelectorAll('main .dia svg')].map(svg => {
    const s = svg.getBoundingClientRect(), problems = [];
    const boxes = [...svg.querySelectorAll('text')].filter(t => t.textContent.trim()).map(t => ({s: t.textContent, r: t.getBoundingClientRect()}));
    boxes.forEach((a, i) => {
      if (a.r.left < s.left - 1 || a.r.right > s.right + 1 || a.r.top < s.top - 1 || a.r.bottom > s.bottom + 1) problems.push(`"${a.s}" leaves the figure`);
      boxes.slice(i + 1).forEach(b => {
        if (a.r.left < b.r.right - 1 && b.r.left < a.r.right - 1 && a.r.top < b.r.bottom - 2 && b.r.top < a.r.bottom - 2) problems.push(`"${a.s}" x "${b.s}"`);
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
