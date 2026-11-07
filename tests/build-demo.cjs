/* Builds the demo course with scripts/build.py for the Node tests; the built page is not checked in.
 * Python is $PYTHON when set (a path or command name), else the first of python3 / python / py -3 that runs
 * (python first on Windows, where python3 is often only the Microsoft Store stub). */
const {spawnSync} = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..');
const DEMO = path.join(ROOT, 'skills/study-guide/examples/demo');
const BUILD = path.join(ROOT, 'skills/study-guide/scripts/build.py');

let python;
/* [command, ...args] for a working Python, or null */
function findPython() {
  if (python !== undefined) return python;
  const candidates = process.env.PYTHON ? [[process.env.PYTHON]]
    : process.platform === 'win32' ? [['python'], ['py', '-3'], ['python3']] : [['python3'], ['python']];
  python = candidates.find(([cmd, ...args]) => spawnSync(cmd, [...args, '--version']).status === 0) || null;
  return python;
}

/* build the demo into dir and return the page's path; with lang, a copy of the course with that lang */
function buildDemo(dir, lang) {
  const py = findPython();
  if (!py) throw new Error('Python not found (set PYTHON)');
  let course = DEMO;
  if (lang) {
    course = path.join(dir, `course-${lang}`);
    fs.cpSync(DEMO, course, {recursive: true, filter: f => path.basename(f) !== 'review.html'});
    const cfgFile = path.join(course, 'course.json'), cfg = JSON.parse(fs.readFileSync(cfgFile, 'utf8'));
    cfg.lang = lang; fs.writeFileSync(cfgFile, JSON.stringify(cfg, null, 2));
  }
  const out = path.join(dir, lang ? `review-${lang}.html` : 'review.html');
  const [cmd, ...args] = py;
  const r = spawnSync(cmd, [...args, BUILD, course, '-o', out], {encoding: 'utf8'});
  if (r.status !== 0) throw new Error(`build.py failed${lang ? ' for ' + lang : ''}:\n${r.stdout}\n${r.stderr}${r.error || ''}`);
  return out;
}

module.exports = {DEMO, findPython, buildDemo};
