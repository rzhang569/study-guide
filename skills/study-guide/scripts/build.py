#!/usr/bin/env python3
"""Check a course folder and build its review page as one self-contained HTML file.

    python3 build.py COURSE_DIR              # check, then write COURSE_DIR/review.html
    python3 build.py COURSE_DIR --check      # check only
    python3 build.py --init COURSE_DIR       # start a new course folder from the bundled example

A course folder holds:
    course.json      config: title, lang, storageKey, lectures, mock exam layout
    sections/*.html  page content in file-name order (<header> hero, <section class="part" id=...> per lecture)
    practice.json    practice bank {groups, items}
    mock.json        mock exam pool {groups, items}; never shares questions with practice.json
    short.json       optional step-by-step short answers {groups, items}
    extra.css / extra.js   optional page-specific styles and widgets

Errors stop the build. Warnings are the question-bank audits from references/question-bank.md.
Standard library only.
"""
import argparse
import difflib
import html
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
EXAMPLE = HERE.parent / "examples" / "demo"

UI = {
    "zh": {"toc": "目录", "hero": "考试信息", "practice": "练习和考试", "html_lang": "zh-CN"},
    "en": {"toc": "Contents", "hero": "Exam info", "practice": "Practice and exams", "html_lang": "en"},
}
TYPES = {"single", "tf", "multi", "fill", "card"}
CATS = {"single", "tf", "multi", "fill"}
LETTERS = "ABCDEFGH"
DEFAULT_SECTIONS = [{"cat": "tf", "n": 10}, {"cat": "single", "n": 10}, {"cat": "multi", "n": 5}, {"cat": "fill", "n": 5}]  # same as engine.js
FONTS = ("https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600"
         "&family=Noto+Sans+SC:wght@400;500;700&family=Noto+Serif+SC:wght@600;700"
         "&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;0,8..60,700;1,8..60,400&display=swap")
MATHJAX = """<script>
window.MathJax = {
  startup: { typeset: false, pageReady: function () { return MathJax.startup.defaultPageReady().then(function () { if (window.__renderTex) window.__renderTex(); }); } },
  svg: { fontCache: "local" },
  options: { enableMenu: false }
};
</script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/3.2.2/es5/tex-svg-full.min.js" defer></script>"""
MARKERS = """<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>
<marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="ah"/></marker>
<marker id="ahw" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="ahw"/></marker>
</defs></svg>"""


class Report:
    def __init__(self):
        self.errors, self.warnings = [], []

    def err(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)


def text_of(h):
    return html.unescape(re.sub(r"<[^>]+>", "", str(h or ""))).strip()


def load_json(path, rep, required=False):
    if not path.exists():
        if required:
            rep.err(f"{path.name} is missing")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        rep.err(f"{path.name}: invalid JSON at line {e.lineno} col {e.colno}: {e.msg}")
        return None


def read_sections(course):
    files = sorted((course / "sections").glob("*.html"))
    return [(f.name, f.read_text(encoding="utf-8")) for f in files]


def toc_entries(body, ui):
    """Top-level <header id> and <section id> blocks become contents entries.
    data-toc sets the label, data-n the marker; data-toc-skip leaves a block out."""
    out, n = [], 0
    for m in re.finditer(r"<(header|section)\b([^>]*)>", body):
        tag, attrs = m.group(1), m.group(2)
        idm = re.search(r'\bid="([^"]+)"', attrs)
        if not idm or "data-toc-skip" in attrs:
            continue
        sid = idm.group(1)
        label = re.search(r'\bdata-toc="([^"]*)"', attrs)
        mark = re.search(r'\bdata-n="([^"]*)"', attrs)
        if label:
            label = label.group(1)
        elif sid == "practice":
            label = ui["practice"]
        elif tag == "header":
            label = ui["hero"]
        else:
            h2 = re.search(r"<h2\b[^>]*>(.*?)</h2>", body[m.end():], re.S)
            label = html.escape(text_of(h2.group(1))) if h2 else sid
        if mark:
            mark = mark.group(1)
        elif tag == "header":
            mark = "0"
        elif sid == "practice":
            mark = "?"
        else:
            n += 1
            mark = str(n)
        out.append((sid, mark, label))
    return out


def check_bank(name, bank, rep, ids, lectures, sec_ids):
    if bank is None:
        return []
    groups = bank.get("groups", [])
    items = bank.get("items", [])
    gmap = {}
    for g in groups:
        gid = g.get("id")
        if not gid:
            rep.err(f"{name}: a group has no id")
            continue
        if gid in gmap:
            rep.err(f"{name}: duplicate group id {gid!r}")
        gmap[gid] = g
        if lectures and g.get("lec") and g["lec"] not in lectures:
            rep.err(f"{name}: group {gid!r} has lec {g['lec']!r}, which is not in course.json lectures")
        if g.get("sec") and sec_ids is not None and g["sec"] not in sec_ids:
            rep.warn(f"{name}: group {gid!r} points at section {g['sec']!r}, but no <section id=\"{g['sec']}\"> exists, so its practice box will not show")
    for q in items:
        qid = q.get("id")
        where = f"{name} item {qid!r}"
        if not qid:
            rep.err(f"{name}: an item has no id (stem: {text_of(q.get('stem'))[:50]!r})")
            continue
        if qid in ids:
            rep.err(f"{where}: id already used in {ids[qid]} (ids must be unique across all banks)")
        ids[qid] = name
        if q.get("g") not in gmap:
            rep.err(f"{where}: group {q.get('g')!r} is not defined")
        t = q.get("type", "single")
        if t not in TYPES:
            rep.err(f"{where}: unknown type {t!r}")
            continue
        if not q.get("stem"):
            rep.err(f"{where}: empty stem")
        if t == "card":
            if name == "mock":
                rep.warn(f"{where}: flashcards are skipped in the mock exam")
            if not q.get("answer"):
                rep.err(f"{where}: card needs 'answer'")
            continue
        if t == "fill":
            acc = q.get("accept")
            if not isinstance(acc, list) or not acc:
                rep.err(f"{where}: fill-in needs a non-empty 'accept' list")
            continue
        opts = q.get("opts")
        if t == "tf" and opts is None:
            opts = [{}, {}]
        if not isinstance(opts, list) or len(opts) < 2:
            rep.err(f"{where}: needs at least 2 options")
            continue
        if len(opts) > 8:
            rep.err(f"{where}: at most 8 options")
        if t == "tf" and len(opts) != 2:
            rep.err(f"{where}: true/false needs exactly 2 options")
        n = len(opts)
        ans = q.get("ans")
        if t == "multi":
            if not isinstance(ans, list) or not ans or len(set(ans)) != len(ans) or any(not isinstance(a, int) or not 0 <= a < n for a in ans):
                rep.err(f"{where}: multi 'ans' must be a list of distinct option indexes 0..{n - 1}")
        elif not isinstance(ans, int) or isinstance(ans, bool) or not 0 <= ans < n:
            rep.err(f"{where}: 'ans' must be an option index 0..{n - 1}")
        if q.get("show") is not None and (t != "single" or str(q["show"]).upper() not in LETTERS[:n] or len(str(q["show"])) != 1):
            rep.err(f"{where}: 'show' must be one letter A..{LETTERS[n - 1]} on a single-choice question")
        for o in opts:
            if isinstance(o, dict) and t != "tf" and not o.get("t"):
                rep.err(f"{where}: an option has no text 't'")
    return items


def check_short(short, rep, ids, lectures, sec_ids, practice_groups):
    if short is None:
        return
    gmap = {g.get("id"): g for g in short.get("groups", [])}
    for g in gmap.values():
        if g.get("sec") and sec_ids is not None and g["sec"] not in sec_ids:
            rep.warn(f"short group {g.get('id')!r} points at missing section {g['sec']!r}")
        if g.get("g") and g["g"] not in practice_groups:
            rep.err(f"short group {g.get('id')!r} links practice group {g['g']!r}, which does not exist")
        if lectures and g.get("lec") and g["lec"] not in lectures:
            rep.err(f"short group {g.get('id')!r} has lec {g['lec']!r}, which is not in course.json lectures")
    for s in short.get("items", []):
        sid = s.get("id")
        where = f"short item {sid!r}"
        if not sid:
            rep.err("short: an item has no id")
            continue
        if sid in ids:
            rep.err(f"{where}: id already used in {ids[sid]}")
        ids[sid] = "short"
        if s.get("k") not in gmap:
            rep.err(f"{where}: group {s.get('k')!r} is not defined")
        steps = s.get("steps") or []
        if not steps:
            rep.err(f"{where}: needs steps")
        for i, p in enumerate(steps, 1):
            if not p.get("ask") or not p.get("sol"):
                rep.err(f"{where} step {i}: needs 'ask' and 'sol'")
            if p.get("opts") is not None:
                if not isinstance(p.get("ans"), int) or not 0 <= p["ans"] < len(p["opts"]):
                    rep.err(f"{where} step {i}: 'ans' must index into 'opts'")
            elif p.get("accept") is not None and (not isinstance(p["accept"], list) or not p["accept"]):
                rep.err(f"{where} step {i}: 'accept' must be a non-empty list")


def audit(name, items, rep):
    """Patterns students learn to exploit instead of learning the material."""
    choice = [q for q in items if q.get("type", "single") in ("single", "multi", "tf")]
    no_why = [q["id"] for q in choice if any(not (isinstance(o, dict) and o.get("why")) for o in (q.get("opts") or [{}, {}]))]
    if no_why:
        rep.warn(f"{name}: {len(no_why)} choice questions lack a 'why' on every option (e.g. {', '.join(no_why[:5])})")
    singles = [q for q in items if q.get("type", "single") == "single" and isinstance(q.get("ans"), int) and isinstance(q.get("opts"), list)]
    if len(singles) >= 6:
        def ln(o):
            return len(text_of(o.get("t") if isinstance(o, dict) else o))
        longest = 0
        for q in singles:
            lens = [ln(o) for o in q["opts"]]
            a = q["ans"]
            if a < len(lens) and lens[a] == max(lens) and lens.count(max(lens)) == 1:
                longest += 1
        share = longest / len(singles)
        if share > 0.3:
            rep.warn(f"{name}: the correct option is the single longest one in {longest}/{len(singles)} single-choice questions ({share:.0%}); keep it under about 30%")
    multis = [q for q in items if q.get("type") == "multi" and isinstance(q.get("ans"), list)]
    if len(multis) >= 4:
        counts = sorted({len(q["ans"]) for q in multis})
        if len(counts) == 1:
            rep.warn(f"{name}: every multi-select question has exactly {counts[0]} correct answers; mix 1 to 4")
    tfs = [q for q in items if q.get("type") == "tf" and isinstance(q.get("ans"), int)]
    if len(tfs) >= 6:
        true_share = sum(1 for q in tfs if q["ans"] == 0) / len(tfs)
        if not 0.3 <= true_share <= 0.7:
            rep.warn(f"{name}: {true_share:.0%} of true/false answers are True; keep it between 30% and 70%")


def _utf16_units(s):
    for ch in s:
        c = ord(ch)
        if c > 0xFFFF:
            c -= 0x10000
            yield 0xD800 + (c >> 10)
            yield 0xDC00 + (c & 0x3FF)
        else:
            yield c


def seeded_order(seed, n):
    """The engine's display order for n options (engine.js seeded/seededOrder), so the build can see
    which letter each correct answer is shown as. order[position] = stored option index."""
    M = 0xFFFFFFFF
    h = 2166136261
    for unit in _utf16_units(seed):
        h = ((h ^ unit) * 16777619) & M

    def rnd():
        nonlocal h
        h = (h + 0x6D2B79F5) & M
        x = ((h ^ (h >> 15)) * (h | 1)) & M
        x = (x ^ ((x + (((x ^ (x >> 7)) * (x | 61)) & M)) & M)) & M
        return ((x ^ (x >> 14)) & M) / 4294967296

    idx = list(range(n))
    for i in range(n - 1, 0, -1):
        j = int(rnd() * (i + 1))
        idx[i], idx[j] = idx[j], idx[i]
    return idx


def display_order(q, key):
    """engine.js displayOrder for a single-choice question: seeded shuffle, then "show" moves the answer."""
    order = seeded_order(f"{key}:{q['id']}", len(q["opts"]))
    show = str(q.get("show") or "").upper()
    if show and show in LETTERS[:len(order)]:
        order = [i for i in order if i != q["ans"]]
        order.insert(LETTERS.index(show), q["ans"])
    return order


def letter_audit(name, items, key, rep):
    """Warn when the correct answer is shown as the same letter too often. The engine shuffles options per
    question, so a small bank can still come out lopsided (e.g. 8 of 15 answers shown as D)."""
    singles = [q for q in items if q.get("type", "single") == "single" and isinstance(q.get("opts"), list)
               and len(q["opts"]) >= 3 and not q.get("fixed") and isinstance(q.get("ans"), int) and 0 <= q["ans"] < len(q["opts"])]
    if len(singles) < 8:
        return
    letters = LETTERS
    shown, counts = {}, {}
    for q in singles:
        pos = display_order(q, key).index(q["ans"])
        shown[q["id"]] = pos
        counts[pos] = counts.get(pos, 0) + 1
    top_pos = max(counts, key=counts.get)
    top, n = counts[top_pos], len(singles)
    if top / n <= 0.4:
        return
    width = max(len(q["opts"]) for q in singles)
    dist = ", ".join(f"{letters[p]} {counts.get(p, 0)}" for p in range(width))
    need = top - int(0.35 * n)
    tips = []
    for q in singles:
        if shown[q["id"]] != top_pos or q.get("show") or len(tips) >= min(need, 6):
            continue
        target = min((p for p in range(len(q["opts"])) if p != top_pos), key=lambda p: counts.get(p, 0))
        counts[target] = counts.get(target, 0) + 1
        tips.append(f'{q["id"]}: "show": "{letters[target]}"')
    rep.warn(f"{name}: the correct answer is shown as {letters[top_pos]} in {top}/{n} single-choice questions "
             f"(shown letters: {dist}). Add a \"show\" letter to move the answer on screen; it never changes stored "
             f"options, so saved answers stay valid: " + "; ".join(tips))


def stem_tokens(h):
    """A stem as words and math symbols, with every number replaced by #, to catch questions that only swap
    the numbers or a word or two. Symbols stay: "P(A ∪ B)" and "P(A ∩ B)" are different tokens."""
    t = re.sub(r"\d+(?:[.,]\d+)?", "#", text_of(h).lower())
    return re.findall(r"[^\W\d_]+|#|[^\s\w#]", t)


def check(course):
    rep = Report()
    cfg = load_json(course / "course.json", rep, required=True) or {}
    practice = load_json(course / "practice.json", rep, required=True)
    mock = load_json(course / "mock.json", rep)
    short = load_json(course / "short.json", rep)
    sections = read_sections(course)
    if not sections:
        rep.err("sections/ has no .html files")
    body = "\n".join(s for _, s in sections)
    sec_ids = set(re.findall(r'<section\b[^>]*\bid="([^"]+)"', body))
    lang = cfg.get("lang", "zh")
    if lang not in UI:
        rep.err(f"course.json: lang must be one of {sorted(UI)}")
    for k in ("title", "storageKey"):
        if not cfg.get(k):
            rep.err(f"course.json: '{k}' is required")
    if cfg.get("storageKey") and not re.fullmatch(r"[A-Za-z0-9_.-]+", cfg["storageKey"]):
        rep.err("course.json: storageKey may only use letters, digits, '.', '_' and '-'")
    lectures = cfg.get("lectures") or []
    ids = {}
    p_items = check_bank("practice", practice, rep, ids, lectures, sec_ids)
    m_items = check_bank("mock", mock, rep, ids, lectures, sec_ids)
    check_short(short, rep, ids, lectures, sec_ids, {g.get("id") for g in (practice or {}).get("groups", [])})
    audit("practice", p_items, rep)
    audit("mock", m_items, rep)

    key = cfg.get("storageKey") or "study-guide"
    letter_audit("practice", p_items, key, rep)
    letter_audit("mock", m_items, key, rep)

    # a mock question that is a practice question with new numbers or a few words changed measures memory
    p_toks = [(q.get("id"), stem_tokens(q.get("stem"))) for q in p_items]
    near = []
    for q in m_items:
        a = stem_tokens(q.get("stem"))
        for pid, b in p_toks:
            if a == b or (min(len(a), len(b)) >= 6 and difflib.SequenceMatcher(None, a, b).ratio() >= 0.9):
                near.append(f"{q.get('id')} ~ {pid}")
                break
    if near:
        rep.warn(f"mock: {len(near)} question(s) look like practice questions with only numbers or a word or two changed "
                 f"({', '.join(near[:6])}); if so, write a new scenario so the mock measures understanding, not memory")

    mcfg = cfg.get("mock") or {}
    if m_items:
        gl = {g.get("id"): g.get("lec") for g in mock.get("groups", [])}
        for sec in mcfg.get("sections") or DEFAULT_SECTIONS:
            cat, n = sec.get("cat"), sec.get("n", 0)
            if cat not in CATS:
                rep.err(f"course.json: mock section cat {cat!r} must be one of {sorted(CATS)}")
                continue

            def cat_of(q):
                t = q.get("type", "single")
                opts = q.get("opts") or []
                if t == "single" and len(opts) == 2 and all(isinstance(o, (str, dict)) for o in opts):
                    labels = [o.get("t") if isinstance(o, dict) else o for o in opts]
                    if labels == (cfg.get("tfLabels") or ["True", "False"]):
                        return "tf"
                return t
            pool = [q for q in m_items if cat_of(q) == cat]
            if len(pool) < n:
                rep.warn(f"mock: section {cat!r} wants {n} questions but the pool has {len(pool)}")
            elif n and len(pool) < 2 * n:
                rep.warn(f"mock: section {cat!r} draws {n} from a pool of {len(pool)}; about 2x lets repeat papers differ")
            weights = mcfg.get("weights")
            if weights:
                missing = sorted({gl.get(q.get("g")) for q in pool} - set(weights))
                if missing:
                    rep.warn(f"mock: weights give no share to {missing}; their {cat!r} questions will never be drawn")
    return rep, cfg, practice, mock, short, sections


def build(course, out):
    rep, cfg, practice, mock, short, sections = check(course)
    for w in rep.warnings:
        print("warning:", w)
    for e in rep.errors:
        print("error:", e)
    if rep.errors:
        print(f"{len(rep.errors)} error(s); nothing written.")
        return 1
    if out is None:
        print(f"check passed with {len(rep.warnings)} warning(s).")
        return 0
    ui = UI[cfg.get("lang", "zh")]
    body = "\n".join(s for _, s in sections)
    if not re.search(r'<section\b[^>]*\bid="practice"', body):
        body += '\n<section class="part" id="practice"></section>\n'
    toc = toc_entries(body, ui)
    toc_html = "".join(f'<li><a href="#{sid}"><span class="n">{html.escape(mark)}</span>{label}</a></li>' for sid, mark, label in toc)
    data = {"config": cfg, "practice": practice or {}, "mock": mock or {}, "short": short or {}}
    data_js = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    uses_tex = "data-tex" in body or "data-tex" in data_js
    css = (ASSETS / "page.css").read_text(encoding="utf-8")
    extra_css = course / "extra.css"
    if extra_css.exists():
        css += "\n" + extra_css.read_text(encoding="utf-8")
    extra_js = course / "extra.js"
    footer = f"<footer>{cfg['footer']}</footer>\n" if cfg.get("footer") else ""
    page = "\n".join([
        "<!doctype html>",
        f'<html lang="{ui["html_lang"]}">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{html.escape(cfg['title'])}</title>",
        '<link rel="preconnect" href="https://fonts.googleapis.com">',
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
        f'<link rel="stylesheet" href="{FONTS}">',
        f"<style>\n{css}\n</style>",
        MATHJAX if uses_tex else "",
        "</head>",
        "<body>",
        MARKERS,
        '<div class="wrap">',
        f'<nav class="toc" aria-label="{ui["toc"]}">\n  <p>{ui["toc"]}</p>\n  <ol>{toc_html}</ol>\n</nav>',
        "<main>",
        body,
        footer + "</main>",
        '<aside class="rail" hidden></aside>',
        "</div>",
        f"<script>window.STUDY_DATA = {data_js};</script>",
        "<script>\n" + (ASSETS / "engine.js").read_text(encoding="utf-8") + "\n</script>",
        ("<script>\n" + extra_js.read_text(encoding="utf-8") + "\n</script>") if extra_js.exists() else "",
        "</body>",
        "</html>",
        "",
    ])
    out.write_text(page, encoding="utf-8")
    counts = f"{len((practice or {}).get('items', []))} practice, {len((mock or {}).get('items', []))} mock, {len((short or {}).get('items', []))} short answer"
    print(f"wrote {out} ({len(page.encode('utf-8')) // 1024} KB; {counts}; {len(rep.warnings)} warning(s))")
    return 0


def init(course):
    if course.exists() and any(course.iterdir()):
        print(f"{course} is not empty; pick a new folder.")
        return 1
    shutil.copytree(EXAMPLE, course, dirs_exist_ok=True, ignore=shutil.ignore_patterns("review.html"))
    print(f"copied the example course into {course}; replace its content, then run build.py {course}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("course", type=Path, help="course folder")
    ap.add_argument("--check", action="store_true", help="validate only, write nothing")
    ap.add_argument("--init", action="store_true", help="create the course folder from the bundled example")
    ap.add_argument("-o", "--out", type=Path, help="output file (default: COURSE/review.html)")
    a = ap.parse_args()
    if a.init:
        return init(a.course)
    if not a.course.is_dir():
        print(f"{a.course} is not a folder")
        return 1
    return build(a.course, None if a.check else (a.out or a.course / "review.html"))


if __name__ == "__main__":
    sys.exit(main())
