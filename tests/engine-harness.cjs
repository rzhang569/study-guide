/* No browser emulator or npm dependencies. Missing document roots keep layout dormant;
 * individual cards still create nodes and use their actual click/input listeners.
 * The only source instrumentation exposes closure bindings before the real boot(). */
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ROOT = path.resolve(__dirname, '..');
const ENGINE = path.join(ROOT, 'skills/study-guide/assets/engine.js');
const source = fs.readFileSync(ENGINE, 'utf8');
const clone = value => JSON.parse(JSON.stringify(value));
const decode = value => value.replace(/&(#x[\da-f]+|#\d+|amp|lt|gt|quot|apos|nbsp|ldquo|rdquo|lsquo|rsquo);/gi,
  (_, entity) => entity[0] === '#' ? String.fromCodePoint(parseInt(entity.slice(entity[1] === 'x' ? 2 : 1), entity[1] === 'x' ? 16 : 10)) :
    ({amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ', ldquo: '“', rdquo: '”', lsquo: '‘', rsquo: '’'})[entity.toLowerCase()]);
class Element {
  constructor(tag = 'div') {
    this.tagName = tag; this.children = []; this.attrs = {}; this.dataset = {};
    this.events = {}; this.className = ''; this._html = ''; this.value = ''; this.hidden = false;
    this.classList = {
      add: (...names) => { this.className = [...new Set([...this.className.split(/\s+/).filter(Boolean), ...names])].join(' '); },
      remove: (...names) => { this.className = this.className.split(/\s+/).filter(n => !names.includes(n)).join(' '); },
      contains: name => this.className.split(/\s+/).includes(name)
    };
  }
  set innerHTML(value) { this._html = String(value); this.children = []; }
  get innerHTML() { return this._html; }
  get textContent() { return decode(this._html.replace(/<[^>]*>/g, '')) + this.children.map(x => x.textContent).join(''); }
  set textContent(value) { this.innerHTML = value; }
  get childNodes() { return this.children; }
  get firstChild() { return this.children[0]; }
  appendChild(child) { child.parentElement = this; this.children.push(child); return child; }
  insertBefore(child, ref) { child.parentElement = this; this.children.splice(this.children.indexOf(ref), 0, child); }
  replaceWith(child) {
    if (this.parentElement) { const p = this.parentElement; p.children[p.children.indexOf(this)] = child; child.parentElement = p; }
  }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return this.attrs[k] ?? null; }
  addEventListener(k, fn) { (this.events[k] ||= []).push(fn); }
  emit(k, values = {}) {
    if (this.disabled) return;
    let stopped = false;
    const event = {clientX: 0, clientY: 0, preventDefault() {}, stopImmediatePropagation() { stopped = true; }, ...values};
    for (const fn of this.events[k] || []) { fn(event); if (stopped) break; }
  }
  click() { this.emit('click'); }
  querySelectorAll(selector) {
    const matches = e => selector.startsWith('.') ? e.classList.contains(selector.slice(1)) : e.tagName === selector;
    const found = [];
    function visit(e) { for (const child of e.children) { if (matches(child)) found.push(child); visit(child); } }
    visit(this); return found;
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
  focus() {} select() {} scrollIntoView() {}
}
function fixture() {
  const opts = [{t: 'one', why: 'First.'}, {t: 'two', why: 'Second.'}, {t: 'three', why: 'Third.'}];
  const groups = [{id: 'g', lec: 'L1', sec: 'l1', title: 'Test values'}];
  return {config: {title: 'Fictional test', storageKey: 'test', lang: 'en', lectures: ['L1', 'L2'],
    mock: {sections: [{cat: 'single', n: 1}, {cat: 'multi', n: 1}, {cat: 'fill', n: 1}], minutes: [1, 0]}},
    practice: {groups, items: [
      {id: 'p1', g: 'g', stem: '<b>Choose</b> x<sup>2</sup> &amp; y<sub>1</sub>', opts, ans: 0, show: 'B'},
      {id: 'p2', g: 'g', type: 'multi', stem: 'Select', opts, ans: [0, 2]},
      {id: 'p3', g: 'g', type: 'fill', stem: 'Value', accept: ['0.5'], answer: '½'},
      {id: 'p4', g: 'g', type: 'card', stem: 'Recall', answer: 'one'},
      {id: 'p5', g: 'g', type: 'tf', stem: 'True?', ans: 1}]},
    mock: {groups, items: [
      {id: 'm1', g: 'g', stem: 'Pick', opts, ans: 0, show: 'C'},
      {id: 'm2', g: 'g', type: 'multi', stem: 'Select', opts, ans: [0, 2]},
      {id: 'm3', g: 'g', type: 'fill', stem: 'Value', accept: ['0.5'], answer: '½'},
      {id: 'm4', g: 'g', type: 'tf', stem: 'True?', ans: 0}]},
    short: {groups: [{id: 's', g: 'g', kind: 'Values'}], items: [{id: 's1', k: 's', stem: 'Steps', steps: [
      {ask: 'Value?', pts: 2, accept: ['0.5'], sol: '½'},
      {ask: 'Pick?', pts: 3, opts: ['one', 'two'], ans: 0, sol: 'one'},
      {ask: 'Explain?', pts: 1, sol: 'Reason'}]}]}};
}
function load({data = fixture(), storage = new Map(), failStorage = false, code = source, instrument = true} = {}) {
  let now = Date.parse('2026-10-26T12:00:00Z'), next = 0;
  const timeouts = new Map(), intervals = [];
  class Clock extends Date { constructor(...args) { super(...(args.length ? args : [now])); } static now() { return now; } }
  const document = {createElement: tag => new Element(tag), getElementById: () => null,
    querySelector: () => null, querySelectorAll: () => [], body: new Element('body'), head: new Element('head')};
  const window = {STUDY_DATA: clone(data), addEventListener() {}, innerHeight: 800};
  const context = vm.createContext({window, document, Date: Clock,
    localStorage: {getItem(k) { if (failStorage) throw Error('blocked'); return storage.get(k) ?? null; },
      setItem(k, v) { if (failStorage) throw Error('full'); storage.set(k, v); }},
    setTimeout(fn, ms) { const id = ++next; timeouts.set(id, {fn, due: now + ms}); return id; },
    clearTimeout(id) { timeouts.delete(id); }, setInterval(fn) { intervals.push(fn); return intervals.length; },
    requestAnimationFrame(fn) { fn(); }});
  const bindings = ['BANKS', 'SA', 'LECS', 'STATE', 'norm', 'evalExpr', 'numsOf', 'approx', 'fillCheck', 'scoreOf',
    'firstScore', 'displayOrder', 'letterOf', 'seededOrder', 'saScore', 'stepOk', 'saStarted', 'setStep',
    'practiceCard', 'saCard', 'updateSABar', 'mockCard', 'drawPaper', 'newPaper', 'submitMock', 'answeredDraft',
    'clockState', 'mmss', 'save', 'bookEntries', 'mastered', 'exportPanel', 'plain', 'setOpen', 'openMap',
    'STR', 'mockBook', 'bookCard', 'updatePracticeBar'];
  const end = '  boot();\n})();';
  if (instrument) {
    if (!code.includes(end)) throw Error('engine boot marker changed; update test instrumentation');
    code = code.replace(end, `  window.__test = {${bindings.join(',')}};\n${end}`);
  }
  vm.runInContext(code, context, {filename: ENGINE, timeout: 2000});
  return {api: window.__test, window, document, storage, context,
    advance(ms) { now += ms; }, tick() { for (const fn of intervals) fn(); },
    flush(ms = 10000) {
      now += ms;
      const ready = [...timeouts].filter(([, task]) => task.due <= now);
      for (const [id, task] of ready) { timeouts.delete(id); task.fn(); }
    }};
}
module.exports = {load, fixture, clone, Element, ROOT, source};
