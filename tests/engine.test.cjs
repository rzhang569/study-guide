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

/* ---------- batch 1: golden orders, languages, notebook store, regression tests ---------- */
const DEMO = path.join(ROOT, 'skills/study-guide/examples/demo');
function demoData() {
  return Object.fromEntries([['config', 'course'], ['practice', 'practice'], ['mock', 'mock'], ['short', 'short']]
    .map(([key, file]) => [key, JSON.parse(fs.readFileSync(path.join(DEMO, file + '.json'), 'utf8'))]));
}
const byText = (card, text) => card.querySelectorAll('.opt').find(o => o.innerHTML.includes('<span class="otext">' + text));
const bubble = opt => opt.innerHTML.match(/<span class="bub[^"]*">(\w)<\/span>/)[1];
const whyText = card => card.querySelectorAll('.why').map(x => x.textContent).join(' | ');
const inStep = (card, i) => card.querySelectorAll('.sastep')[i];
const bookView = h => clone(h.api.bookEntries().map(e => [e.q.id, e.notes]));
const bookIds = (h, keep = () => true) => clone(h.api.bookEntries().filter(keep).map(e => e.q.id));

// Changing the shuffle would relabel the letters students saw (and the letters in reports); stored indexes
// would stay right. These values pin the current algorithm; build.py's Python port gives the same ones.
test('golden shuffle orders: seededOrder, fixture and demo display orders are pinned', () => {
  const h = load();
  assert.deepEqual(clone(h.api.seededOrder('test:x', 8)), [1, 7, 6, 5, 4, 0, 3, 2]);
  assert.deepEqual(clone(h.api.seededOrder('test:x', 4)), [2, 0, 3, 1]);
  assert.deepEqual(clone(h.api.displayOrder(h.api.BANKS.practice.imap.p1)), [2, 0, 1]);
  const d = load({data: demoData()}), p = d.api.BANKS.practice.imap['p1-1'];
  assert.deepEqual(clone(d.api.displayOrder(p)), [3, 0, 1, 2]);           // show: "B" puts the answer (1/6) at B
  assert.deepEqual(['A', 'B', 'C', 'D'].map((_, pos) => p.opts[d.api.displayOrder(p)[pos]].t), ['1/12', '1/6', '1/11', '7/36']);
  assert.deepEqual(clone(d.api.displayOrder(d.api.BANKS.mock.imap['m1-1'])), [0, 1]);   // first mock item: tf, never shuffled
  assert.deepEqual(clone(d.api.displayOrder(d.api.BANKS.mock.imap['m1-4'])), [0, 3, 1, 2]); // first shuffled mock item
  assert.deepEqual(clone(d.api.seededOrder('demo-prob101-mt1:sa-a1:3', 4)), [3, 1, 0, 2]); // short-answer choice step
});

test('clicking an option by its visible text stores the original index and restores the same feedback after reload', () => {
  const data = demoData(), h = load({data}), p = h.api.BANKS.practice.imap['p1-1'];
  const pick = byText(h.api.practiceCard(p, 1), '1/11');
  assert.equal(bubble(pick), 'C');
  pick.click();
  assert.deepEqual(clone(h.api.STATE.practice.ans['p1-1']), {first: 1, tried: [1]});
  assert.deepEqual(JSON.parse(h.storage.get('demo-prob101-mt1:practice')).ans['p1-1'], {first: 1, tried: [1]});
  const before = h.api.practiceCard(p, 1);
  assert.match(whyText(before), /First pick was C; the answer is B\./);
  const again = load({data, storage: h.storage}), card = again.api.practiceCard(again.api.BANKS.practice.imap['p1-1'], 1);
  assert.ok(byText(card, '1/11').classList.contains('wrong'));
  assert.ok(byText(card, '1/6').classList.contains('right'));
  assert.equal(bubble(byText(card, '1/11')), 'C');
  assert.equal(whyText(card), whyText(before));
  const missed = again.window.StudyGuide.report().practice.missed[0];
  assert.equal(missed.firstAnswer, 'C (1/11)'); assert.equal(missed.correct, 'B (1/6)');
});

test('zh boot renders Chinese strings and an unknown lang falls back to zh', () => {
  const data = fixture(); data.config.lang = 'zh';
  const h = load({data}), p = h.api.BANKS.practice.imap.p1;
  assert.equal(h.window.StudyGuide.t('tabPractice'), '练习题');
  option(h.api.practiceCard(p, 1), h, p, 1).click();
  assert.match(whyText(h.api.practiceCard(p, 1)), /第一次选了 [AC]，正确答案是 B。/);
  assert.equal(h.window.StudyGuide.report().practice.missed.length, 1);
  data.config.lang = 'fr';
  const f = load({data});
  assert.equal(f.window.StudyGuide.t('tabMock'), '模拟考试');
  assert.equal(f.window.StudyGuide.t('secMeta', {n: 3, d: 1}), '3 道题 · 已做 1');
});

test('zh and en string tables have the same keys and the same {placeholders}', () => {
  const {zh, en} = load().api.STR, holes = s => [...String(s).matchAll(/\{(\w+)\}/g)].map(m => m[1]).sort();
  assert.deepEqual(Object.keys(en).sort(), Object.keys(zh).sort());
  for (const key of Object.keys(zh)) {
    const a = zh[key], b = en[key];
    assert.equal(typeof a, typeof b, key);
    if (Array.isArray(a)) assert.equal(a.length, b.length, key);
    else if (typeof a === 'object') {
      assert.deepEqual(Object.keys(b).sort(), Object.keys(a).sort(), key);
      for (const k of Object.keys(a)) assert.deepEqual(holes(b[k]), holes(a[k]), key + '.' + k);
    } else assert.deepEqual(holes(b), holes(a), key);
  }
});

test('bug 1: redoing a wrong short-answer choice step never restores first-try credit', () => {
  const h = load(), s = h.api.SA[0], order = h.api.seededOrder('test:s1:1', 2);
  const opt = (card, j) => inStep(card, 1).querySelectorAll('.opt')[order.indexOf(j)];
  opt(h.api.saCard(s, 1, 'p'), 1).click();
  assert.deepEqual(clone(h.api.saScore(s)), {s: 0, f: 0, m: 6});
  button(inStep(h.api.saCard(s, 1, 'p'), 1), 'Redo this step').click();
  assert.deepEqual(clone(h.api.STATE.practice.sa.s1[1]), {tries: 1, tried: [1]});
  const reopened = h.api.saCard(s, 1, 'p');
  assert.ok(opt(reopened, 1).classList.contains('wrong'));      // the earlier miss stays visible
  assert.ok(!opt(reopened, 0).classList.contains('right'));     // the answer is not revealed yet
  opt(reopened, 0).click();
  assert.deepEqual(clone(h.api.STATE.practice.sa.s1[1]), {tries: 1, tried: [1, 0], v: 0, ok: true, shown: true});
  assert.deepEqual(clone(h.api.saScore(s)), {s: 0, f: 3, m: 6});
  assert.match(whyText(inStep(h.api.saCard(s, 1, 'p'), 1)), /fixed after 1 wrong tries/);
  assert.deepEqual(clone(load({storage: h.storage}).api.saScore(s)), {s: 0, f: 3, m: 6});
});

test('bug 1: redoing self-marked and done-on-paper steps keeps the miss counted', () => {
  const h = load(), s = h.api.SA[0], step = i => inStep(h.api.saCard(s, 1, 'p'), i);
  button(step(2), 'Done, show answer').click();
  button(step(2), 'I missed it').click();
  button(step(2), 'Redo this step').click();
  assert.deepEqual(clone(h.api.STATE.practice.sa.s1[2]), {tries: 1});
  button(step(2), 'Done, show answer').click();
  button(step(2), 'I got it').click();
  assert.deepEqual(clone(h.api.saScore(s)), {s: 0, f: 1, m: 6});
  button(step(0), 'Done on paper, show answer').click();
  button(step(0), 'I missed it').click();
  button(step(0), 'Redo this step').click();
  // reopened on paper: no "Not right" message or red input, and it is still marked by hand
  assert.equal(step(0).querySelector('input').className, '');
  assert.equal(button(step(0), 'Show answer'), undefined);
  button(step(0), 'Done on paper, show answer').click();
  button(step(0), 'I got it').click();
  assert.deepEqual(clone(h.api.saScore(s)), {s: 0, f: 3, m: 6});
  assert.deepEqual(clone(h.window.StudyGuide.report().shortAnswer[0].missedSteps), [1, 2, 3]);
});

test('bug 2: report missedSteps agrees with saScore for an override after one try', () => {
  const h = load(), s = h.api.SA[0], step = () => inStep(h.api.saCard(s, 1, 'p'), 0);
  const first = step(); first.querySelector('input').value = '0.9'; button(first, 'Check').click();
  button(step(), 'Show answer').click();
  button(step(), 'My answer is right, count it').click();
  assert.deepEqual(clone(h.api.STATE.practice.sa.s1[0]), {v: '0.9', tries: 1, ok: true, shown: true, fix: true});
  assert.equal(h.api.saScore(s).s, 2);
  const row = h.window.StudyGuide.report().shortAnswer[0];
  assert.equal(row.firstScore, 2);
  assert.deepEqual(clone(row.missedSteps), [2, 3]);
  // the same rule for every step: a step is missed exactly when it earns no first-try points
  const pts = s.steps.reduce((a, p, i) => a + (row.missedSteps.includes(i + 1) ? 0 : p.pts), 0);
  assert.equal(pts, row.firstScore);
});

test('bug 3: a mock fill typed and then cleared is blank, not an answer for the notebook', () => {
  for (const cleared of ['', '   ']) {
    const h = load(), st = h.api.STATE.mock;
    st.paper = ['m1', 'm2', 'm3', 'm4']; st.draft = {m1: 1, m4: 0}; st.flags = {m3: 1};
    const input = h.api.mockCard(h.api.BANKS.mock.imap.m3, 3).querySelector('input');
    input.value = '0.7'; input.emit('input'); input.value = cleared; input.emit('input'); h.flush(400);
    assert.equal(h.api.answeredDraft(st.draft.m3), false);
    h.api.submitMock(false);
    assert.ok(st.result.wrong.includes('m3'));
    assert.equal('m3' in st.result.picks, false);
    assert.deepEqual(bookIds(h), ['m1']);
    const last = h.window.StudyGuide.report().mock.last;
    assert.equal(last.wrong.find(x => x.id === 'm3').answered, null);
  }
});

test('bug 4: Clear practice record clears notebook redos of practice questions, not short answers or mock redos', () => {
  const h = load(), ps = h.api.STATE.practice, p = h.api.BANKS.practice.imap.p1;
  ps.ans.p1 = {first: 1, tried: [1]}; ps.redo = {p1: {first: 0, tried: [0]}, m1: {first: 0, tried: [0]}};
  h.api.setStep(h.api.SA[0], 0, {v: '0.5', ok: true, shown: true});
  assert.equal(h.api.mastered(p), true);
  const bar = new Element(), score = new Element('p'), acts = new Element(), sum = new Element();
  score.className = 'score'; acts.className = 'acts'; bar.appendChild(score); bar.appendChild(acts);
  h.document.getElementById = id => ({'bar-practice': bar, 'sum-practice': sum})[id] || null;
  h.api.updatePracticeBar();
  const clear = () => button(acts, 'Clear practice record') || button(acts, 'Clear everything? Click again');
  clear().click(); clear().click();
  assert.deepEqual(clone(ps.ans), {});
  assert.deepEqual(clone(Object.keys(ps.redo)), ['m1']);
  assert.equal(ps.sa.s1[0].ok, true);
  option(h.api.practiceCard(p, 1), h, p, 1).click();          // missed again after clearing
  assert.equal(h.api.mastered(p), false);
  assert.deepEqual(bookIds(h, e => !h.api.mastered(e.q)), ['p1']);
  // the per-question reset clears the notebook redo too
  option(h.api.practiceCard(p, 1, 'b'), h, p, 0).click();
  assert.equal(h.api.mastered(p), true);
  const undo = button(h.api.practiceCard(p, 1), 'Misclick: reset this question'); undo.click(); undo.click();
  assert.equal(ps.redo.p1, undefined);
});

test('bug 5: thousands separators count as one number; malformed decimals are unreadable', () => {
  const h = load();
  for (const [ref, value] of [['1000', '1,000'], ['1000000', '1,000,000'], ['1234.5', '1,234.5'], ['-2500', '-2,500'],
      ['1,000', '1000'], ['0.5', '1/2']]) assert.equal(fill(h, ref, value), true, `${value} for ${ref}`);
  assert.equal(fill(h, '1000', '1,00'), false);                // not a thousands pattern: still a list of two
  assert.equal(fill(h, '(1,0)', '1,000'), true);               // vector answers keep list semantics
  assert.equal(fill(h, '(3,100)', '3,100'), true);
  assert.equal(h.api.evalExpr('2.5.3'), null);
  assert.equal(fill(h, '0.75', '2.5.3'), null);
  assert.equal(fill(h, '2.5', '2.5.3'), null);
  assert.equal(h.api.evalExpr('2.5'), 2.5); assert.equal(h.api.evalExpr('3.'), 3); assert.equal(h.api.evalExpr('.5'), 0.5);
});

const RIGHT = {m1: 0, m2: [0, 2], m3: '0.5', m4: 0};
function hand(h, draft = RIGHT, flags = {}) {
  const st = h.api.STATE.mock;
  st.paper = ['m1', 'm2', 'm3', 'm4']; st.draft = clone(draft); st.flags = clone(flags); st.submitted = false;
  h.advance(1000); h.api.submitMock(false);
}
test('notebook keeps mock mistakes past the 20-paper history, with paper numbers that never shift', () => {
  const h = load(), letter = h.api.letterOf(h.api.BANKS.mock.imap.m1, 1);
  hand(h, {...RIGHT, m1: 1});
  for (let i = 2; i <= 21; i++) hand(h);
  hand(h, {...RIGHT, m2: [0]}, {m4: 1});
  for (let i = 23; i <= 30; i++) hand(h);
  const st = h.api.STATE.mock;
  assert.equal(st.history.length, 20);
  assert.equal(st.book.papers, 30);
  assert.equal(st.history.some(x => x.wrong.includes('m1')), false);   // paper 1 left the history long ago
  assert.deepEqual(bookView(h), [
    ['m1', [`Wrong on mock paper 1; you answered ${letter} (two)`]],
    ['m2', [`Wrong on mock paper 22; you answered ${h.api.letterOf(h.api.BANKS.mock.imap.m2, 0)}`]],
    ['m4', ['Flagged on mock paper 22, answered correctly']]]);
  const reloaded = load({storage: h.storage});
  assert.deepEqual(bookView(reloaded), bookView(h));
  assert.equal(reloaded.window.StudyGuide.report().mock.papers, 20);
});

test('an old save (no notebook store) migrates its history entries; loading alone leaves the state unchanged', () => {
  const h0 = load(), m1 = h0.api.BANKS.mock.imap.m1, m2 = h0.api.BANKS.mock.imap.m2;
  const units = {L1: {s: 1, m: 4}};
  const paper = (day, extra) => ({at: `2026-10-0${day}T12:00:00.000Z`, s: 1, m: 4, units, used: null, limit: null, auto: false, ...extra});
  // exactly what the previous engine stored: history entries are its submitMock results
  const oldMock = {v: 1, paper: ['m1', 'm2', 'm3', 'm4'], draft: {m1: 1, m2: [0], m3: '', m4: 0}, flags: {m4: 1},
    seen: {m1: 1, m2: 1, m3: 1, m4: 1}, pcount: 2, submitted: true,
    history: [
      paper(1, {wrong: ['m2'], flags: []}),                                            // oldest format: no picks
      paper(2, {wrong: ['m1', 'm3'], flags: ['m1', 'm4'], picks: {m1: 2, m4: 0}}),     // m3 blank
      paper(3, {wrong: ['m1', 'm2', 'm3'], flags: ['m4'], picks: {m1: 1, m2: [0], m3: '', m4: 0}})], // m3 typed+cleared
    timer: {limit: 1, startedAt: ''}, updatedAt: '2026-10-03T12:00:00.000Z'};
  oldMock.result = oldMock.history[2];
  const storage = new Map([['test:mock', JSON.stringify(oldMock)]]), h = load({storage});
  assert.deepEqual(clone(h.api.STATE.mock), oldMock);
  const L = i => h.api.letterOf(m1, i), names = ['one', 'two', 'three'];
  const expected = [
    ['m2', ['Wrong on mock paper 1', `Wrong on mock paper 3; you answered ${h.api.letterOf(m2, 0)}`]],
    ['m1', [`Wrong on mock paper 2; you answered ${L(2)} (${names[2]})`, 'Flagged on mock paper 2',
            `Wrong on mock paper 3; you answered ${L(1)} (${names[1]})`]],
    ['m4', ['Flagged on mock paper 2, answered correctly', 'Flagged on mock paper 3, answered correctly']]];
  assert.deepEqual(bookView(h), expected);
  // the first hand-in writes the store; later papers push the old history out without losing these entries
  for (let i = 0; i < 20; i++) hand(h);
  const st = h.api.STATE.mock, saved = JSON.parse(storage.get('test:mock'));
  assert.equal(st.book.v, 1); assert.equal(st.book.papers, 23); assert.deepEqual(saved.book, clone(st.book));
  assert.equal(st.history[0].at > oldMock.history[2].at, true);
  assert.deepEqual(bookView(h), expected);
  assert.deepEqual(clone(st.book.items.m1[0]), {paper: 2, wrong: true, flagged: true, pick: 2});
});

test('a student can remove a mock mistake; a new miss after mastery brings it back to the todo list', () => {
  const h = load(), q = h.api.BANKS.mock.imap.m1;
  hand(h, {...RIGHT, m1: 1});
  option(h.api.bookCard(q, 1), h, q, 0).click();                 // redo in the notebook, right
  assert.equal(h.api.mastered(q), true);
  hand(h, {...RIGHT, m1: 2});                                     // wrong again on paper 2
  assert.equal(h.api.mastered(q), false);
  assert.equal(h.api.bookEntries()[0].notes.length, 2);
  const card = h.api.bookCard(q, 1), remove = button(card, 'Remove from notebook');
  remove.click(); assert.ok(h.api.STATE.mock.book.items.m1);     // asks once first
  remove.click();
  assert.equal(h.api.STATE.mock.book.items.m1, undefined);
  assert.equal(h.api.bookEntries().length, 0);
  assert.equal(JSON.parse(h.storage.get('test:mock')).book.items.m1, undefined);
  assert.equal(button(h.api.bookCard(h.api.BANKS.practice.imap.p1, 1), 'Remove from notebook'), undefined);
});

test('mock items without a lecture do not crash drawing, cards, hand-in, notebook or report', () => {
  const data = fixture(); data.mock.groups.push({id: 'nolec'});
  data.mock.items.push({id: 'm9', g: 'nolec', stem: 'No lecture', opts: data.mock.items[0].opts, ans: 0});
  const h = load({data}), st = h.api.STATE.mock;
  assert.equal(clone(h.api.drawPaper()).includes('m9'), false);
  st.paper = ['m9', 'm1']; st.draft = {m9: 1, m1: 0};
  h.api.mockCard(h.api.BANKS.mock.imap.m9, 1);
  h.api.submitMock(false);
  assert.deepEqual(clone(st.result.units), {L1: {s: 1, m: 1}});
  assert.deepEqual(bookIds(h), ['m9']);
  assert.equal(h.window.StudyGuide.report().mock.last.wrong[0].id, 'm9');
});
