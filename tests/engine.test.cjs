const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {load, fixture, clone, Element, ROOT, source} = require('./engine-harness.cjs');
const q = (type, extra = {}) => ({type, ...extra});
const fill = (h, ref, value) => h.api.fillCheck({accept: [ref]}, value);
function option(card, h, question, original) { return card.querySelectorAll('.opt')[h.api.displayOrder(question).indexOf(original)]; }
function button(card, label) { return card.querySelectorAll('button').find(x => x.textContent === label); }

// Every case uses a fresh realm, state, fake clock, and memory store.
test('unmodified engine boots and publishes its supported API with minimal DOM stubs', () => {
  const h = load({instrument: false});
  assert.deepEqual(Object.keys(h.window.StudyGuide).sort(), ['el', 'renderTex', 'report', 't']);
  assert.equal(h.window.StudyGuide.report().kind, 'study-guide-report');
});
for (const [name, ref, value] of [
  ['decimal', '0.5', '.500'], ['fraction', '0.5', '1/2'], ['percent', '0.5', '50%'],
  ['negative exponent', '0.5', '2^-1'], ['superscript negative', '0.25', '2⁻²'],
  ['superscript digits', '1024', '2¹⁰'], ['superscript precedence', '-4', '-2²'],
  ['scientific', '0.00025', '2.5e-4'], ['unicode multiplication', '6', '2 × 3'],
  ['unicode division', '0.5', '1÷2'], ['unicode minus', '-0.5', '−1/2'],
  ['sqrt', '2', '√4'], ['natural log', '1', 'ln(e)'], ['log is natural', '1', 'log(e)'],
  ['exp', '1', 'exp(0)'], ['implicit multiply', '6', '2(1+2)'],
  ['right associative powers', '512', '2^3^2'], ['pi', '6.283185307', '2pi'],
  ['equals suffix', '5.42', 'v3 = 5.42'], ['approx suffix', '0.5', 'p ≈ 1/2'],
  ['fullwidth brackets', '0.5', '（1/2）'], ['text normalization', 'Bayes rule', '“BAYES RULE”。'],
  ['straight quotes', 'same text', " ' Same Text ' "],
  ['vector', '(1,-0.5)', '[1, -1/2]'], ['vector spaces', '(1,-0.5)', '1 -0.5'],
  ['vector Chinese separators', '(1,-0.5)', '(1，−0.5)'],
]) test(`value checker accepts ${name}`, () => assert.equal(fill(load(), ref, value), true));

for (const [name, value, expected] of [
  ['wrong value', '0.8', false], ['blank', ' ', null], ['unreadable', 'banana', null],
  ['divide zero', '1/0', null], ['NaN', 'sqrt(-1)', null], ['infinite', 'exp(10000)', null],
  ['incomplete', '1+', null], ['code', 'process.exit()', null], ['units unsupported', '0.5 kg', null],
  ['currency unsupported', '$0.5', null], ['quoted numeric spelling', '“0.5”', true],
]) test(`value checker handles ${name}`, () => assert.equal(fill(load(), '0.5', value), expected));

test('text variants require an authored accept entry; vector length and order matter', () => {
  const h = load();
  assert.equal(fill(h, 'Bayes', 'Bayesian'), false);
  assert.equal(h.api.fillCheck({accept: ['Bayes', 'Bayesian']}, 'Bayesian'), true);
  assert.equal(fill(h, '(1,-0.5)', '1'), false);
  assert.equal(fill(h, '(1,-0.5)', '(-0.5,1)'), false);
  assert.equal(fill(h, '(1,-0.5)', '(1, banana)'), null);
});

test('rounding tolerance boundaries: zero, regular, small, and very small references', () => {
  const h = load();
  for (const [a, inside, outside] of [[0, 0.00049, 0.00051], [1, 1.0159, 1.0161],
      [0.02, 0.02059, 0.02061], [0.001, 0.001099, 0.001101]]) {
    assert.equal(h.api.approx(inside, a), true);
    assert.equal(h.api.approx(outside, a), false);
    assert.equal(h.api.approx(-inside, -a), true);
  }
});

test('all numeric references are accepted by value, including a later alternate reference', () => {
  const h = load();
  assert.equal(h.api.fillCheck({accept: ['0.5', '2/3']}, '4/6'), true);
});

test('single/tf scoring is strict and multi scoring follows the documented partial-credit formula', () => {
  const h = load();
  for (const type of ['single', 'tf']) {
    for (const [answer, score] of [[0, 1], [1, 0], [null, 0], ['0', 0]])
      assert.equal(h.api.scoreOf(q(type, {ans: 0}), answer), score);
  }
  const multi = q('multi', {ans: [0, 2]});
  for (const [sel, score] of [[[], 0], [[0], 0.5], [[0, 2], 1], [[0, 1], 0], [[0, 1, 2], 1/3], [[1], 0]])
    assert.equal(h.api.scoreOf(multi, sel), score);
  assert.equal(h.api.scoreOf(q('fill', {accept: ['0.5']}), '1/2'), 1);
  assert.equal(h.api.scoreOf(q('fill', {accept: ['0.5']}), 'wrong'), 0);
  assert.equal(h.api.scoreOf(q('card'), 0), 0);
});

test('display order is stable across realms, handles Unicode ids, and stores original indexes', () => {
  const h = load(), again = load();
  for (const id of ['p1', 'p2', 'p5']) {
    const a = h.api.BANKS.practice.imap[id], b = again.api.BANKS.practice.imap[id];
    assert.deepEqual(clone(h.api.displayOrder(a)), clone(again.api.displayOrder(b)));
    assert.deepEqual(clone(h.api.displayOrder(a)).sort(), Array.from(a.opts, (_, i) => i));
  }
  const p = h.api.BANKS.practice.imap.p1;
  assert.equal(h.api.letterOf(p, p.ans), 'B');
  assert.deepEqual(clone(h.api.displayOrder(h.api.BANKS.practice.imap.p5)), [0, 1]);
  const fixed = {...p, id: 'fixed', fixed: true};
  assert.deepEqual(clone(h.api.displayOrder(fixed)), [0, 1, 2]);
  for (const seed of ['test:ascii', 'test:中文', 'test:😀']) {
    assert.deepEqual(clone(h.api.seededOrder(seed, 8)), clone(again.api.seededOrder(seed, 8)));
  }
});

test('single-choice click persists first try; later clicks and notebook redos do not alter it', () => {
  const h = load(), p = h.api.BANKS.practice.imap.p1;
  let card = h.api.practiceCard(p, 1);
  option(card, h, p, 1).click();
  card = h.api.practiceCard(p, 1);
  option(card, h, p, 0).click();
  assert.deepEqual(clone(h.api.STATE.practice.ans.p1), {first: 1, tried: [1, 0]});
  const redo = h.api.practiceCard(p, 1, 'b');
  option(redo, h, p, 0).click();
  assert.equal(h.api.mastered(p), true);
  assert.equal(h.api.firstScore(p, h.api.STATE.practice.ans.p1), 0);
  assert.equal(h.window.StudyGuide.report().practice.missed[0].redoneRight, true);
  assert.equal(JSON.parse(h.storage.get('test:practice')).ans.p1.first, 1);
});

test('fill input does not record unreadable values; fixes preserve first try and Enter submits', () => {
  const h = load(), p = h.api.BANKS.practice.imap.p3;
  function answer(value, enter = false) {
    const card = h.api.practiceCard(p, 1), input = card.querySelector('input'); input.value = value;
    if (enter) input.emit('keydown', {key: 'Enter'}); else button(card, 'Submit').click();
  }
  answer('banana'); assert.equal(h.api.STATE.practice.ans.p3, undefined);
  answer('0.9'); answer('1/2', true);
  assert.deepEqual(clone(h.api.STATE.practice.ans.p3), {first: '0.9', last: '1/2'});
  assert.equal(h.api.firstScore(p, h.api.STATE.practice.ans.p3), 0);
});

test('multi-select drafts survive reload and only submission establishes first score', () => {
  const h = load(), p = h.api.BANKS.practice.imap.p2;
  option(h.api.practiceCard(p, 1), h, p, 0).click();
  assert.equal(h.api.firstScore(p, h.api.STATE.practice.ans.p2), null);
  const restored = load({storage: h.storage}), rp = restored.api.BANKS.practice.imap.p2;
  button(restored.api.practiceCard(rp, 1), 'Submit').click();
  assert.equal(restored.api.firstScore(rp, restored.api.STATE.practice.ans.p2), 0.5);
  button(restored.api.practiceCard(rp, 1), 'Try again').click();
  for (const index of [0, 2]) option(restored.api.practiceCard(rp, 1), restored, rp, index).click();
  button(restored.api.practiceCard(rp, 1), 'Submit').click();
  assert.deepEqual(clone(restored.api.STATE.practice.ans.p2.first), [0]);
  assert.equal(restored.api.scoreOf(rp, restored.api.STATE.practice.ans.p2.sel), 1);
});

test('flashcards remain unscored and absent from missed-question reports', () => {
  const h = load(), p = h.api.BANKS.practice.imap.p4;
  button(h.api.practiceCard(p, 1), 'Show answer').click();
  assert.deepEqual(clone(h.api.STATE.practice.ans.p4), {seen: true});
  const report = h.window.StudyGuide.report();
  assert.equal(report.practice.byLecture.L1.total, 4);
  assert.equal(report.practice.byLecture.L1.answered, 0);
  assert.equal(report.practice.missed.length, 0);
});

test('short-answer typed checks preserve first-try vs fixed points and ignore unreadable attempts', () => {
  const h = load(), s = h.api.SA[0];
  function answer(value) {
    const card = h.api.saCard(s, 1, 'p'); card.querySelector('input').value = value;
    button(card, 'Check').click();
  }
  answer('unreadable'); assert.equal(h.api.STATE.practice.sa.s1, undefined);
  answer('0.9'); assert.equal(h.api.STATE.practice.sa.s1[0].tries, 1);
  answer('1/2');
  h.api.setStep(s, 1, {v: 0, ok: true, shown: true});
  h.api.setStep(s, 2, {self: true, shown: true, ok: true});
  assert.deepEqual(clone(h.api.saScore(s)), {s: 4, f: 6, m: 6});
  assert.deepEqual(clone(h.window.StudyGuide.report().shortAnswer[0].missedSteps), [1]);
});

test('short-answer first choice is retained when later options are inspected', () => {
  const h = load(), s = h.api.SA[0], order = h.api.seededOrder('test:s1:1', 2);
  h.api.saCard(s, 1, 'p').querySelectorAll('.opt')[order.indexOf(1)].click();
  h.api.saCard(s, 1, 'p').querySelectorAll('.opt')[order.indexOf(0)].click();
  assert.deepEqual(clone(h.api.STATE.practice.sa.s1[1]), {v: 1, ok: false, shown: true, tried: [1, 0]});
  assert.equal(h.api.saScore(s).s, 0);
});

test('short-answer self checks, overrides, and old typed records use current checker', () => {
  const h = load(), s = h.api.SA[0], p = s.steps[0];
  assert.equal(h.api.stepOk(p, {v: '1/2', ok: false, shown: true}), true);
  assert.equal(h.api.stepOk(p, {v: 'wrong', ok: true, shown: false}), null);
  h.api.setStep(s, 0, {v: 'custom', tries: 1, fix: true, shown: true});
  assert.equal(h.api.saScore(s).s, 2);
  h.api.setStep(s, 0, {tries: 2});
  assert.equal(h.api.saScore(s).s, 0);
  assert.equal(h.api.saScore(s).f, 2);
  assert.equal(h.api.stepOk(p, {self: true, ok: true, shown: true}), true);
});

function exam(h) {
  const st = h.api.STATE.mock;
  st.paper = ['m1', 'm2', 'm3', 'm4'];
  st.draft = {m1: 1, m2: [0], m3: '1/2', m4: 0};
  st.flags = {m1: 1, m4: 1};
  return st;
}
test('mock submission totals partial credit, lecture units, blanks, flags, and original picks', () => {
  const h = load(), st = exam(h);
  st.timer.startedAt = new Date(Date.parse('2026-10-26T12:00:00Z') - 20000).toISOString();
  h.api.submitMock(false);
  assert.equal(st.submitted, true);
  assert.equal(st.result.s, 2.5); assert.equal(st.result.m, 4);
  assert.deepEqual(clone(st.result.units), {L1: {s: 2.5, m: 4}});
  assert.deepEqual(clone(st.result.wrong), ['m1', 'm2']);
  assert.deepEqual(clone(st.result.flags), ['m1', 'm4']);
  assert.deepEqual(clone(st.result.picks), {m1: 1, m2: [0], m4: 0});
  assert.equal(st.result.used, 20); assert.equal(st.result.auto, false);
  const last = h.window.StudyGuide.report().mock.last;
  assert.equal(last.wrong[0].flagged, true);
  assert.deepEqual(clone(last.flaggedButRight), ['m4']);
  assert.equal(h.api.mockCard(h.api.BANKS.mock.imap.m1, 1).querySelectorAll('.opt').some(x => x.events.click?.length > 1), false);
});

test('mock drafts and flags persist without scoring before hand-in', () => {
  const h = load(), st = exam(h), p = h.api.BANKS.mock.imap.m1;
  option(h.api.mockCard(p, 1), h, p, 0).click();
  assert.equal(st.draft.m1, 0); assert.equal(st.history.length, 0);
  const fillCard = h.api.mockCard(h.api.BANKS.mock.imap.m3, 3);
  fillCard.querySelector('input').value = '50%'; fillCard.querySelector('input').emit('input'); h.flush(400);
  const reloaded = load({storage: h.storage});
  assert.equal(reloaded.api.STATE.mock.draft.m3, '50%');
  assert.deepEqual(clone(reloaded.api.STATE.mock.flags), {m1: 1, m4: 1});
  assert.equal(reloaded.api.STATE.mock.submitted, false);
});

test('timer expiration automatically submits once at the boundary and caps used seconds', () => {
  const h = load(), st = exam(h);
  st.timer.startedAt = '2026-10-26T12:00:00Z'; st.timer.limit = 1;
  h.advance(59999); h.tick(); assert.equal(st.submitted, false);
  h.advance(1); h.tick(); assert.equal(st.submitted, true);
  assert.equal(st.result.auto, true); assert.equal(st.result.used, 60);
  h.advance(5000); h.tick(); assert.equal(st.history.length, 1);
});

test('timer resumes after reload, unlimited timer never submits, unstarted timer reports null', () => {
  const h = load(), st = exam(h);
  st.timer = {limit: 1, startedAt: '2026-10-26T11:59:00Z'}; h.api.save('mock');
  const restored = load({storage: h.storage}); restored.tick();
  assert.equal(restored.api.STATE.mock.result.auto, true);
  const unlimited = load(), us = exam(unlimited);
  us.timer = {limit: 0, startedAt: '2026-10-26T12:00:00Z'};
  unlimited.advance(3600000); unlimited.tick(); assert.equal(us.submitted, false);
  unlimited.api.submitMock(false); assert.equal(us.result.used, 3600); assert.equal(us.result.limit, 0);
  const idle = load(); exam(idle); assert.equal(idle.api.clockState(), null);
  idle.api.submitMock(false); assert.equal(idle.api.STATE.mock.result.used, null);
  assert.equal(idle.api.STATE.mock.result.limit, null);
  assert.equal(idle.api.mmss(-3), '0:00'); assert.equal(idle.api.mmss(125), '2:05');
});

test('blank questions score zero; notebook skips unanswered mock misses and preserves history cap', () => {
  const h = load(), st = exam(h); st.draft = {};
  h.api.submitMock(false); assert.equal(st.result.s, 0);
  assert.equal(h.api.bookEntries().length, 0);
  for (let i = 0; i < 22; i++) { st.submitted = false; h.advance(1000); h.api.submitMock(false); }
  assert.equal(st.history.length, 20);
  assert.equal(h.window.StudyGuide.report().mock.recent.length, 8);
});

test('paper drawing respects category order, counts, freshness, and finite pool capacity', () => {
  const data = fixture();
  data.mock.items.push({...clone(data.mock.items[0]), id: 'm5'});
  const h = load({data}), seen = {m1: 1};
  const paper = clone(h.api.drawPaper(seen));
  assert.equal(paper.length, 3); assert.equal(new Set(paper).size, 3);
  assert.deepEqual(paper.map(id => h.api.BANKS.mock.imap[id].cat), ['single', 'multi', 'fill']);
  assert.equal(paper[0], 'm5');
  const st = h.api.STATE.mock; st.paper = paper; st.draft = {m5: 0}; st.flags = {m5: 1}; st.timer.limit = 0;
  h.api.newPaper();
  assert.equal(st.pcount, 1); assert.equal(st.seen.m5, 0);
  assert.deepEqual(clone(st.draft), {}); assert.deepEqual(clone(st.flags), {});
  assert.equal(st.submitted, false); assert.equal(st.timer.limit, 0); assert.equal(st.timer.startedAt, '');
});

test('weighted draws redistribute capped quotas without drawing zero-weight lectures', () => {
  const data = fixture(); data.config.mock.sections = [{cat: 'single', n: 4}];
  data.config.mock.weights = {L1: 1, L2: 0};
  data.mock.groups.push({id: 'g2', lec: 'L2'});
  for (let i = 0; i < 5; i++) data.mock.items.push({...clone(data.mock.items[0]), id: `other${i}`, g: 'g2'});
  const h = load({data});
  assert.deepEqual(clone(h.api.drawPaper()), ['m1']);
});

test('pool-size and explicit positive weight proportions determine per-lecture quotas', () => {
  const data = fixture(); data.config.mock.sections = [{cat: 'single', n: 4}];
  data.mock.groups.push({id: 'g2', lec: 'L2'});
  for (let i = 0; i < 3; i++) data.mock.items.push({...clone(data.mock.items[0]), id: `more${i}`});
  for (let i = 0; i < 8; i++) data.mock.items.push({...clone(data.mock.items[0]), id: `other${i}`, g: 'g2'});
  const counts = h => clone(h.api.drawPaper()).reduce((a, id) => {
    const lec = h.api.BANKS.mock.imap[id].lec; a[lec] = (a[lec] || 0) + 1; return a;
  }, {});
  assert.deepEqual(counts(load({data})), {L1: 1, L2: 3});
  data.config.mock.weights = {L1: 1, L2: 1};
  assert.deepEqual(counts(load({data})), {L1: 2, L2: 2});
});

test('local persistence survives absent, malformed, incompatible and blocked storage', () => {
  for (const value of ['{bad', 'null', '{"v":9,"ans":{"p1":{"first":0}}}', '[]']) {
    const storage = new Map([['test:practice', value]]), h = load({storage});
    assert.equal(Object.keys(h.api.STATE.practice.ans).length, 0);
  }
  const h = load({failStorage: true}); h.api.save('practice'); h.api.save('mock');
  assert.equal(h.window.StudyGuide.report().practice.byLecture.L1.answered, 0);
});

test('removed IDs are ignored and appending questions retains original answer indexes', () => {
  const h = load(); h.api.STATE.practice.ans = {p1: {first: 1, tried: [1]}, removed: {first: 0}};
  h.api.STATE.mock.paper = ['m1', 'removed']; h.api.STATE.mock.draft = {m1: 1};
  h.api.save('practice'); h.api.save('mock');
  const data = fixture(); data.practice.items.push({...clone(data.practice.items[0]), id: 'new'});
  const restored = load({storage: h.storage, data});
  assert.equal(restored.api.STATE.practice.ans.p1.first, 1);
  assert.deepEqual(clone(restored.api.STATE.mock.paper), ['m1']);
  assert.equal(restored.window.StudyGuide.report().practice.missed.length, 1);
  assert.equal(restored.window.StudyGuide.report().practice.byLecture.L1.total, 5);
});

test('Export button textarea and download contain valid matching JSON with report and raw state', () => {
  const h = load();
  h.api.STATE.practice.ans.p1 = {first: 1, tried: [1, 0]};
  exam(h); h.api.submitMock(false);
  h.api.setStep(h.api.SA[0], 0, {v: '0.9', tries: 1, shown: true, ok: false});
  const host = new Element(); h.api.exportPanel(host);
  button(host, 'Export progress').click();
  const payload = JSON.parse(host.querySelector('textarea').value), download = host.querySelector('a');
  assert.deepEqual(JSON.parse(decodeURIComponent(download.href.split(',')[1])), payload);
  assert.equal(download.download, 'test-progress.json');
  assert.deepEqual(payload.state, clone(h.api.STATE));
  assert.equal(payload.report.kind, 'study-guide-report'); assert.equal(payload.report.v, 1);
  assert.equal(payload.report.key, 'test'); assert.equal(payload.report.course, 'Fictional test');
  assert.equal(payload.report.practice.missed[0].stem, 'Choose x^2 & y_1');
  assert.equal(payload.report.practice.missed[0].correct, 'B (one)');
  assert.match(payload.report.practice.missed[0].firstAnswer, /^[AC] \(two\)$/);
  assert.equal(payload.report.shortAnswer[0].max, 6);
  button(host, 'Export progress').click(); assert.equal(host.querySelector('.export-panel').hidden, true);
});

test('drills-from-progress legacy state roundtrips and export schema matches the eval contract', () => {
  const base = path.join(ROOT, 'evals/drills-from-progress/files');
  const previous = JSON.parse(fs.readFileSync(path.join(base, 'progress.json'), 'utf8'));
  const data = Object.fromEntries(['course', 'practice', 'mock', 'short'].map(name => [name === 'course' ? 'config' : name,
    JSON.parse(fs.readFileSync(path.join(base, 'prob101-review', name + '.json'), 'utf8'))]));
  const storage = new Map(Object.entries(previous.state).map(([key, value]) => [data.config.storageKey + ':' + key, JSON.stringify(value)]));
  const original = clone(previous.state), h = load({data, storage});
  assert.deepEqual(clone(h.api.STATE), original);
  const host = new Element(); h.api.exportPanel(host); button(host, 'Export progress').click();
  const exported = JSON.parse(host.querySelector('textarea').value);
  // Compare complete recursively inferred key/type shapes, not stale shuffled answer letters.
  function shape(value) {
    if (Array.isArray(value)) return value.length ? [shape(value[0])] : [];
    if (value === null) return null;
    if (typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map(k => [k, shape(value[k])]));
    return typeof value;
  }
  assert.deepEqual(shape(exported.report), shape(previous.report));
  assert.deepEqual(exported.state, original);
  assert.deepEqual(exported.report.practice.byLecture, previous.report.practice.byLecture);
  assert.deepEqual(exported.report.shortAnswer, previous.report.shortAnswer);
  assert.deepEqual(exported.report.mock, previous.report.mock);
  assert.equal(exported.report.practice.missed.length, 6);
  for (let i = 0; i < 6; i++) {
    const actual = exported.report.practice.missed[i], old = previous.report.practice.missed[i];
    for (const key of ['id', 'lec', 'group', 'type', 'stem', 'redoneRight']) assert.deepEqual(actual[key], old[key]);
  }
});

test('built demo embeds exactly the source data and its engine can boot with the same VM', () => {
  const demo = path.join(ROOT, 'skills/study-guide/examples/demo');
  const html = fs.readFileSync(path.join(demo, 'review.html'), 'utf8');
  const data = JSON.parse(html.match(/window.STUDY_DATA = (.*?);<\/script>/)[1]);
  for (const [key, file] of [['config', 'course'], ['practice', 'practice'], ['mock', 'mock'], ['short', 'short']])
    assert.deepEqual(data[key], JSON.parse(fs.readFileSync(path.join(demo, file + '.json'), 'utf8')));
  const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
  const code = scripts.find(s => s.includes('function fillCheck'));
  assert.ok(code); assert.equal(code.trim(), source.trim()); new vm.Script(code);
  const h = load({data, code, instrument: false});
  assert.equal(h.window.StudyGuide.report().practice.byLecture.L1.total, 7);
  assert.equal(h.window.StudyGuide.report().shortAnswer.length, 0);
});

test('numeric checking preserves grouping instead of accepting text-normalized expressions', () => {
  const h = load();
  assert.equal(fill(h, '(1+2)*3', '1+2*3'), false);
  assert.equal(fill(h, '0.5', '“1/2”'), true);
});

test('large capped weighted draws fill the available quota beyond fifty redistribution passes', () => {
  const data = fixture(); data.config.mock.sections = [{cat: 'single', n: 100}];
  data.config.mock.weights = {L1: 1000, L2: 1}; data.mock.groups.push({id: 'g2', lec: 'L2'});
  for (let i = 0; i < 100; i++) data.mock.items.push({...clone(data.mock.items[0]), id: `other${i}`, g: 'g2'});
  const h = load({data}), paper = clone(h.api.drawPaper());
  assert.equal(paper.length, 100); assert.equal(new Set(paper).size, 100);
});

test('per-lecture progress rounds the summed partial scores once, not each addition', () => {
  const data = fixture(), template = data.practice.items[1]; template.ans = [0, 1, 2];
  data.practice.items = [0, 1, 2].map(i => ({...clone(template), id: `partial${i}`}));
  const h = load({data});
  for (let i = 0; i < 3; i++) h.api.STATE.practice.ans[`partial${i}`] = {first: [0], sel: [0], submitted: true};
  assert.equal(h.window.StudyGuide.report().practice.byLecture.L1.firstScore, 1);
});

test('unit-bearing text requires an explicit spelling and is never silently converted', () => {
  const h = load();
  assert.equal(fill(h, '5 kg', '5KG'), true);
  assert.equal(fill(h, '5 kg', '5000 g'), false);
  assert.equal(fill(h, '5', '5000 g'), null);
});

test('true/false defaults and localized labels are filled without shuffling', () => {
  const data = fixture(); data.config.tfLabels = ['是', '否'];
  data.practice.items[0].opts = ['是', '否']; data.practice.items[0].ans = 1;
  const h = load({data});
  for (const id of ['p1', 'p5']) {
    const item = h.api.BANKS.practice.imap[id];
    assert.equal(item.type, 'tf');
    assert.deepEqual(clone(item.opts.map(x => x.t)), ['是', '否']);
    assert.deepEqual(clone(h.api.displayOrder(item)), [0, 1]);
  }
});

test('group inheritance and explicit item overrides select the report lecture and section', () => {
  const data = fixture(); data.practice.items[0].lec = 'L2'; data.practice.items[0].sec = 'l2';
  const h = load({data});
  assert.equal(h.api.BANKS.practice.imap.p1.lec, 'L2');
  assert.equal(h.api.BANKS.practice.imap.p1.sec, 'l2');
  assert.equal(h.api.SA[0].lec, 'L1'); assert.equal(h.api.SA[0].sec, 'l1');
  h.api.STATE.practice.ans.p1 = {first: 0}; h.api.STATE.practice.scope = 'L1';
  assert.equal(h.window.StudyGuide.report().practice.byLecture.L2.answered, 1);
});

test('question undo requires confirmation and permits a new first try after clearing', () => {
  const h = load(), p = h.api.BANKS.practice.imap.p1;
  option(h.api.practiceCard(p, 1), h, p, 1).click();
  const card = h.api.practiceCard(p, 1), reset = button(card, 'Misclick: reset this question');
  reset.click(); assert.equal(h.api.STATE.practice.ans.p1.first, 1);
  reset.click(); assert.equal(h.api.STATE.practice.ans.p1, undefined);
  option(h.api.practiceCard(p, 1), h, p, 0).click();
  assert.equal(h.api.STATE.practice.ans.p1.first, 0);
});

test('oldest seen questions follow never-seen questions when a category fills its quota', () => {
  const data = fixture(); data.config.mock.sections = [{cat: 'single', n: 2}];
  for (let i = 0; i < 3; i++) data.mock.items.push({...clone(data.mock.items[0]), id: `more${i}`});
  const h = load({data}), seen = {m1: 7, more0: 2, more1: 5};
  assert.deepEqual(clone(h.api.drawPaper(seen)).sort(), ['more0', 'more2']);
  data.config.mock.weights = {L1: 0};
  assert.deepEqual(clone(load({data}).api.drawPaper()), []);
  data.mock.items = [];
  assert.deepEqual(clone(load({data}).api.drawPaper()), []);
});

test('mock reports aggregate history and retain identifiable removed questions', () => {
  const h = load(), st = exam(h); h.api.submitMock(false);
  st.submitted = false; st.draft.m1 = 0; h.api.submitMock(false);
  let report = h.window.StudyGuide.report();
  assert.deepEqual(clone(report.mock.byLecture), {L1: {s: 6, m: 8}});
  assert.deepEqual(clone(report.mock.recent), [63, 88]);
  st.history[1].wrong.push('removed');
  report = h.window.StudyGuide.report();
  assert.deepEqual(clone(report.mock.last.wrong.at(-1)), {id: 'removed'});
});

test('open section state and complete practice/short/redo records survive reload', () => {
  const h = load();
  h.api.STATE.practice.ans = {p2: {first: [0], sel: [0, 2], submitted: true}, p3: {first: '0.9', last: '1/2'}, p4: {seen: true}};
  h.api.STATE.practice.redo = {p3: {first: '1/2', last: '1/2'}};
  h.api.STATE.practice.sa.s1 = {0: {v: '1/2', shown: true, ok: true, tries: 1, self: false, fix: false, tried: []}};
  h.api.save('practice'); h.api.setOpen('l1', true);
  const restored = load({storage: h.storage});
  assert.deepEqual(clone(restored.api.STATE.practice), clone(h.api.STATE.practice));
  assert.deepEqual(clone(restored.api.openMap()), {l1: 1});
  restored.api.setOpen('l1', false); assert.deepEqual(clone(restored.api.openMap()), {});
});

test('ambiguous display directives preserve fixed and two-option order', () => {
  const h = load(), base = h.api.BANKS.practice.imap.p1;
  for (const item of [{...base, id: 'two', opts: base.opts.slice(0, 2), show: 'B'},
                       {...base, id: 'fixed-show', fixed: true, show: 'C'}]) {
    assert.equal(h.api.displayOrder(item).indexOf(item.ans), 0);
  }
});


test('an explicit empty mock layout disables engine draws (documented build mismatch)', () => {
  const data = fixture(); data.config.mock.sections = [];
  assert.deepEqual(clone(load({data}).api.drawPaper()), []);
});

test('optional short questions are excluded from aggregate points but retain their own progress', () => {
  const data = fixture(); data.short.items.push({...clone(data.short.items[0]), id: 'optional', opt: 'Extra derivation'});
  const h = load({data});
  for (const s of h.api.SA) h.api.setStep(s, 0, {v: '0.5', ok: true, shown: true});
  const bar = new Element(), score = new Element('p'); score.className = 'score'; bar.appendChild(score);
  h.document.getElementById = id => id === 'bar-sa' ? bar : null;
  h.api.updateSABar();
  assert.match(score.textContent, /Started 2 \/ 2/);
  assert.match(score.textContent, /first-try score 2 \/ 6/);
  assert.equal(h.window.StudyGuide.report().shortAnswer.length, 2);
});

test('the configured first time choice and explicit defaultMinutes initialize fresh timers', () => {
  const data = fixture(); data.config.mock.minutes = [{m: 7, note: 'Suggested'}, 0];
  assert.equal(load({data}).api.STATE.mock.timer.limit, 7);
  data.config.mock.defaultMinutes = 0;
  assert.equal(load({data}).api.STATE.mock.timer.limit, 0);
});

test('storage namespaces isolate courses even when their question ids coincide', () => {
  const h = load(); h.api.STATE.practice.ans.p1 = {first: 0}; h.api.save('practice');
  const data = fixture(); data.config.storageKey = 'other-course';
  const other = load({data, storage: h.storage});
  assert.equal(other.api.STATE.practice.ans.p1, undefined);
  other.api.STATE.practice.ans.p1 = {first: 1}; other.api.save('practice');
  assert.equal(JSON.parse(h.storage.get('test:practice')).ans.p1.first, 0);
  assert.equal(JSON.parse(h.storage.get('other-course:practice')).ans.p1.first, 1);
});

test('omitted mock configuration draws the documented default 10/10/5/5 layout', () => {
  const data = fixture(); delete data.config.mock;
  const template = clone(data.mock.items[0]); data.mock.items = [];
  for (const [type, n] of [['tf', 12], ['single', 12], ['multi', 7], ['fill', 7]]) {
    for (let i = 0; i < n; i++) {
      const item = {...clone(template), id: `${type}${i}`, type};
      if (type === 'tf') { item.opts = [{}, {}]; delete item.show; }
      if (type === 'multi') item.ans = [0];
      if (type === 'fill') item.accept = ['0.5'];
      data.mock.items.push(item);
    }
  }
  const h = load({data}), paper = clone(h.api.drawPaper());
  assert.equal(paper.length, 30);
  assert.deepEqual(paper.map(id => h.api.BANKS.mock.imap[id].cat), [
    ...Array(10).fill('tf'), ...Array(10).fill('single'), ...Array(5).fill('multi'), ...Array(5).fill('fill')]);
  assert.equal(h.api.STATE.mock.timer.limit, 45);
});
