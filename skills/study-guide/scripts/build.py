#!/usr/bin/env python3
"""Check a course folder and build its review page as one self-contained HTML file.

    python3 build.py COURSE_DIR              # check, then write COURSE_DIR/review.html
    python3 build.py COURSE_DIR --check      # check only
    python3 build.py COURSE_DIR --strict     # also fail (exit code 2) on warnings; works with --check
    python3 build.py --init COURSE_DIR       # start a new course folder from the bundled example

A course folder holds:
    course.json      config: title, lang, storageKey, lectures, mock exam layout
    sections/*.html  page content in file-name order (<header> hero, <section class="part" id=...> per lecture)
    practice.json    practice bank {groups, items}
    mock.json        mock exam pool {groups, items}; never shares questions with practice.json
    short.json       optional step-by-step short answers {groups, items}
    extra.css / extra.js   optional page-specific styles and widgets

Errors stop the build. Warnings are the question-bank audits from references/question-bank.md.
Exit codes: 0 success, 1 errors (nothing written), 2 warnings with --strict (the page is still written).
The page is UTF-8 with LF line endings on every OS, so a Windows build is byte-identical to a Linux one.
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
TF_LABELS = ["True", "False"]  # engine.js default for course.json tfLabels
DEFAULT_SECTIONS = [{"cat": "tf", "n": 10}, {"cat": "single", "n": 10}, {"cat": "multi", "n": 5}, {"cat": "fill", "n": 5}]  # same as engine.js
BANKS = ("practice", "mock", "short")
# an id attribute, but not data-id or aria-...-id
ID_ATTR = re.compile(r'(?<![\w-])id="([^"]+)"')
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


def read_text(path, rep, label):
    """A UTF-8 text file (a leading BOM is dropped), or None after a one-line error."""
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as e:
        rep.err(f"{label}: must be UTF-8 (byte {e.start} is not)")
    except OSError as e:
        rep.err(f"{label}: cannot read it ({e.strerror or e})")
    return None


def load_json(path, rep, required=False):
    """Returns (value, ok). A missing optional file is (None, True); a missing required or unreadable file
    is (None, False) after an error."""
    def reject_constant(value):
        raise ValueError(f"non-JSON numeric constant {value}")

    if not path.exists():
        if required:
            rep.err(f"{path.name} is missing")
        return None, not required
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        rep.err(f"{path.name}: must be UTF-8 JSON")
        return None, False
    except OSError as e:
        rep.err(f"{path.name}: cannot read it ({e.strerror or e})")
        return None, False
    try:
        return json.loads(raw, parse_constant=reject_constant), True
    except json.JSONDecodeError as e:
        rep.err(f"{path.name}: invalid JSON at line {e.lineno} col {e.colno}: {e.msg}")
    except ValueError as e:
        rep.err(f"{path.name}: invalid JSON: {e}")
    return None, False


def read_sections(course, rep):
    sections = []
    for f in sorted((course / "sections").glob("*.html")):
        text = read_text(f, rep, f"sections/{f.name}")
        if text is not None:
            sections.append((f.name, text))
    return sections


def strip_comments(body):
    return re.sub(r"<!--.*?-->", "", body, flags=re.S)


def section_ids(body):
    """Ids of every <section>, nested ones included (a practice box can sit in any of them)."""
    ids = (ID_ATTR.search(attrs) for attrs in re.findall(r"<section\b([^>]*)>", strip_comments(body)))
    return {m.group(1) for m in ids if m}


def top_blocks(body):
    """(tag, attrs, inner html) for each <header> or <section> not nested inside another one."""
    body = strip_comments(body)
    blocks, depth, start = [], 0, None
    for m in re.finditer(r"<(/?)(header|section)\b([^>]*)>", body):
        if m.group(1):
            depth = max(depth - 1, 0)
            if depth == 0 and start:
                blocks.append((start.group(2), start.group(3), body[start.end():m.start()]))
                start = None
        else:
            if depth == 0:
                start = m
            depth += 1
    if start:  # an unclosed block runs to the end, as in a browser
        blocks.append((start.group(2), start.group(3), body[start.end():]))
    return blocks


def toc_entries(body, ui):
    """Top-level <header id> and <section id> blocks become contents entries; nested sections do not.
    data-toc sets the label, data-n the marker; data-toc-skip leaves a block out."""
    def attr(attrs, name):
        m = re.search(r'(?<![\w-])' + name + r'="([^"]*)"', attrs)
        return m.group(1) if m else None

    out, n = [], 0
    for tag, attrs, inner in top_blocks(body):
        sid = attr(attrs, "id")
        if not sid or re.search(r"(?<![\w-])data-toc-skip(?![\w-])", attrs):
            continue
        label, mark = attr(attrs, "data-toc"), attr(attrs, "data-n")
        if not label:
            if sid == "practice":
                label = ui["practice"]
            elif tag == "header":
                label = ui["hero"]
            else:
                h2 = re.search(r"<h2\b[^>]*>(.*?)</h2>", inner, re.S)
                label = html.escape(text_of(h2.group(1))) if h2 else sid
        if not mark:
            if tag == "header":
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
    def check_item(q):
        qid = q.get("id")
        where = f"{name} item {qid!r}"
        if not qid:
            rep.err(f"{name}: an item has no id (stem: {text_of(q.get('stem'))[:50]!r})")
            return
        if qid in ids:
            rep.err(f"{where}: id already used in {ids[qid]} (ids must be unique across all banks)")
        ids[qid] = name
        if q.get("g") not in gmap:
            rep.err(f"{where}: group {q.get('g')!r} is not defined")
        elif name == "mock" and not (q.get("lec") or gmap[q["g"]].get("lec")):
            rep.err(f"{where}: needs a 'lec' on the item or its group {q['g']!r}; mock papers are drawn and scored by lecture")
        if lectures and q.get("lec") and q["lec"] not in lectures:
            rep.err(f"{where}: lec {q['lec']!r} is not in course.json lectures")
        t = q.get("type", "single")
        if t not in TYPES:
            rep.err(f"{where}: unknown type {t!r}")
            return
        if not isinstance(q.get("stem"), str):
            rep.err(f"{where}: stem must be text" if q.get("stem") else f"{where}: empty stem")
        elif not q["stem"].strip():
            rep.err(f"{where}: empty stem")
        if t == "card":
            if name == "mock":
                rep.warn(f"{where}: flashcards are skipped in the mock exam")
            if not q.get("answer"):
                rep.err(f"{where}: card needs 'answer'")
            return
        if t == "fill":
            acc = q.get("accept")
            if not isinstance(acc, list) or not acc:
                rep.err(f"{where}: fill-in needs a non-empty 'accept' list")
            return
        opts = q.get("opts")
        if t == "tf" and opts is None:
            opts = [{}, {}]
        if not isinstance(opts, list) or len(opts) < 2:
            rep.err(f"{where}: needs at least 2 options")
            return
        if len(opts) > 8:
            rep.err(f"{where}: at most 8 options")
        if t == "tf" and len(opts) != 2:
            rep.err(f"{where}: true/false needs exactly 2 options")
        n = len(opts)
        ans = q.get("ans")
        if t == "multi":
            if not isinstance(ans, list) or not ans or any(type(a) is not int or not 0 <= a < n for a in ans) or len(set(ans)) != len(ans):
                rep.err(f"{where}: multi 'ans' must be a list of distinct option indexes 0..{n - 1}")
        elif not isinstance(ans, int) or isinstance(ans, bool) or not 0 <= ans < n:
            rep.err(f"{where}: 'ans' must be an option index 0..{n - 1}")
        if q.get("show") is not None and (t != "single" or str(q["show"]).upper() not in LETTERS[:n] or len(str(q["show"])) != 1):
            rep.err(f"{where}: 'show' must be one letter A..{LETTERS[min(n, len(LETTERS)) - 1]} on a single-choice question")
        for o in opts:
            if isinstance(o, dict) and t != "tf" and not o.get("t"):
                rep.err(f"{where}: an option has no text 't'")

    # the audits and letter checks index into options and answers, so they only see items that passed these checks
    good = []
    for q in items:
        before = len(rep.errors)
        check_item(q)
        if len(rep.errors) == before:
            good.append(q)
    return good


def check_short(short, rep, ids, lectures, sec_ids, practice_groups):
    if short is None:
        return
    gmap = {}
    for g in short.get("groups", []):
        gid = g.get("id")
        if not gid:
            rep.err(f"short: a group has no id (kind {g.get('kind')!r}); items find their group by id through 'k'")
            continue
        if gid in gmap:
            rep.err(f"short: duplicate group id {gid!r}")
        gmap[gid] = g
    for g in gmap.values():
        if g.get("sec") and sec_ids is not None and g["sec"] not in sec_ids:
            rep.warn(f"short group {g.get('id')!r} points at missing section {g['sec']!r}")
        if g.get("g") and practice_groups is not None and g["g"] not in practice_groups:
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
        if not s.get("k"):
            rep.err(f"{where}: needs 'k', the id of its short-answer group")
        elif s["k"] not in gmap:
            rep.err(f"{where}: group {s['k']!r} is not defined")
        if not s.get("stem"):
            rep.err(f"{where}: empty stem")
        if lectures and s.get("lec") and s["lec"] not in lectures:
            rep.err(f"{where}: lec {s['lec']!r} is not in course.json lectures")
        steps = s.get("steps") or []
        if not steps:
            rep.err(f"{where}: needs steps")
        for i, p in enumerate(steps, 1):
            if not p.get("ask") or not p.get("sol"):
                rep.err(f"{where} step {i}: needs 'ask' and 'sol'")
            if p.get("opts") is not None:
                if type(p.get("ans")) is not int or not 0 <= p["ans"] < len(p["opts"]):
                    rep.err(f"{where} step {i}: 'ans' must index into 'opts'")
            elif p.get("accept") is not None and (not isinstance(p["accept"], list) or not p["accept"]):
                rep.err(f"{where} step {i}: 'accept' must be a non-empty list")


def cat_of(q, tf_labels=None):
    """The category the engine gives a question (engine.js prep): a single-choice question whose two options
    are exactly the true/false labels is shown, drawn and scored as true/false."""
    t = q.get("type", "single")
    opts = q.get("opts")
    if t == "single" and isinstance(opts, list) and len(opts) == 2:
        labels = [o.get("t") if isinstance(o, dict) else o for o in opts]
        if labels == list(tf_labels or TF_LABELS):
            return "tf"
    return t


def audit(name, items, rep, tf_labels=None):
    """Patterns students learn to exploit instead of learning the material."""
    choice = [q for q in items if q.get("type", "single") in ("single", "multi", "tf")]
    no_why = [q["id"] for q in choice if any(not (isinstance(o, dict) and o.get("why")) for o in (q.get("opts") or [{}, {}]))]
    if no_why:
        rep.warn(f"{name}: {len(no_why)} choice questions lack a 'why' on every option (e.g. {', '.join(no_why[:5])})")
    singles = [q for q in items if cat_of(q, tf_labels) == "single" and isinstance(q.get("ans"), int) and isinstance(q.get("opts"), list)]
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
    tfs = [q for q in items if cat_of(q, tf_labels) == "tf" and isinstance(q.get("ans"), int)]
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
    if tips:
        advice = ("Add a \"show\" letter to move the answer on screen; it never changes stored options, "
                  "so saved answers stay valid: " + "; ".join(tips))
    else:  # every answer shown at the top letter is there because of its own "show"
        pinned = [q["id"] for q in singles if shown[q["id"]] == top_pos]
        advice = (f"Their \"show\" letters put them there; change some of them to other letters "
                  f"({', '.join(pinned[:6])})")
    rep.warn(f"{name}: the correct answer is shown as {letters[top_pos]} in {top}/{n} single-choice questions "
             f"(shown letters: {dist}). {advice}")


def stem_tokens(h):
    """A stem as words and math symbols, with every number replaced by #, to catch questions that only swap
    the numbers or a word or two. Symbols stay: "P(A ∪ B)" and "P(A ∩ B)" are different tokens."""
    t = re.sub(r"\d+(?:[.,]\d+)?", "#", text_of(h).lower())
    return re.findall(r"[^\W\d_]+|#|[^\s\w#]", t)


def check_shapes(cfg, banks, rep):
    """Reject malformed JSON shapes before semantic checks index into them. Returns the names of the files
    ("course", "practice", …) whose shape is broken, so later checks skip just those files."""
    def fields(obj, names, kind, where):
        for key in names:
            if key in obj and not isinstance(obj[key], kind):
                rep.err(f"{where}: '{key}' must be {kind.__name__}")

    broken, before = set(), len(rep.errors)
    fields(cfg, ("title", "storageKey", "lang", "practiceIntro", "shortIntro", "footer"), str, "course.json")
    if "lectures" in cfg and (not isinstance(cfg["lectures"], list) or
                              any(not isinstance(x, str) for x in cfg["lectures"])):
        rep.err("course.json: lectures must be a list of strings")
    if "tfLabels" in cfg and (not isinstance(cfg["tfLabels"], list) or len(cfg["tfLabels"]) != 2 or
                              any(not isinstance(x, str) for x in cfg["tfLabels"])):
        rep.err("course.json: tfLabels must contain two strings")
    if "mock" in cfg:
        mc = cfg["mock"]
        if not isinstance(mc, dict):
            rep.err("course.json: mock must be an object")
        else:
            fields(mc, ("note",), str, "course.json mock")
            if "sections" in mc:
                sections = mc["sections"]
                if not isinstance(sections, list) or any(not isinstance(x, dict) for x in sections):
                    rep.err("course.json: mock.sections must be a list of objects")
                elif not sections:
                    rep.err("course.json: mock.sections is empty, so a mock paper would have no questions; delete the key "
                            "to use the default layout (10 tf, 10 single, 5 multi, 5 fill)")
                else:
                    for sec in sections:
                        if not isinstance(sec.get("cat"), str) or sec["cat"] not in CATS:
                            rep.err(f"course.json: mock section cat {sec.get('cat')!r} must be one of {sorted(CATS)}")
                        if type(sec.get("n")) is not int or sec["n"] < 0:
                            rep.err("course.json: mock section n must be a non-negative integer")
                        fields(sec, ("title", "desc", "short"), str, "course.json mock section")
                    counts = [sec.get("n") for sec in sections]
                    if all(type(n) is int and n >= 0 for n in counts) and not sum(counts):
                        rep.err("course.json: every mock section has n: 0, so a mock paper would have no questions; "
                                "at least one section's n must be greater than 0 (n: 0 only skips one question type)")
            def minutes(x):
                return type(x) in (int, float) and 0 <= x < float("inf")
            if "minutes" in mc:
                values = mc["minutes"]
                if not isinstance(values, list) or not values or any(
                    not minutes(x.get("m") if isinstance(x, dict) else x) for x in values):
                    rep.err("course.json: mock.minutes must be a non-empty list of non-negative limits (numbers or objects with m)")
                elif any(isinstance(x, dict) and "note" in x and not isinstance(x["note"], str) for x in values):
                    rep.err("course.json: mock.minutes note must be a string")
            if "defaultMinutes" in mc and not minutes(mc["defaultMinutes"]):
                rep.err("course.json: mock.defaultMinutes must be a non-negative number")
            if "weights" in mc and (not isinstance(mc["weights"], dict) or any(
                not minutes(x) for x in mc["weights"].values())):
                rep.err("course.json: mock.weights must map lecture labels to non-negative numbers")
    if len(rep.errors) > before:
        broken.add("course")
    for name, bank in banks.items():
        if bank is None:
            continue
        before = len(rep.errors)
        for field in ("groups", "items"):
            rows = bank.get(field, [])
            if not isinstance(rows, list) or any(not isinstance(x, dict) for x in rows):
                rep.err(f"{name}.json: {field} must be a list of objects")
                continue
            for row in rows:
                where = f"{name} {field} {row.get('id')!r}"
                fields(row, ("id", "g", "k", "lec", "sec", "type", "stem", "answer", "title", "desc", "kind", "note", "opt", "why", "src"), str, where)
                if "fixed" in row and type(row["fixed"]) is not bool:
                    rep.err(f"{where}: fixed must be a boolean")
                if "opts" in row and isinstance(row["opts"], list):
                    if any(not isinstance(x, (dict, str)) for x in row["opts"]):
                        rep.err(f"{where}: each option must be text or an object")
                    for opt in row["opts"]:
                        if isinstance(opt, dict):
                            fields(opt, ("t", "why"), str, where + " option")
                if name == "short" and field == "items":
                    steps = row.get("steps", [])
                    if not isinstance(steps, list) or any(not isinstance(x, dict) for x in steps):
                        rep.err(f"{where}: steps must be a list of objects")
                        continue
                    for step in steps:
                        fields(step, ("ask", "sol"), str, where + " step")
                        if "pts" in step and (type(step["pts"]) not in (int, float) or not 0 < step["pts"] < float("inf")):
                            rep.err(f"{where}: step pts must be a positive number")
                        if "opts" in step and (not isinstance(step["opts"], list) or len(step["opts"]) < 2 or any(not isinstance(x, str) for x in step["opts"])):
                            rep.err(f"{where}: step opts must contain at least two text options")
        if len(rep.errors) > before:
            broken.add(name)
    return broken


def check(course):
    """Every file that parses and has the right shape is checked, so one broken file does not hide errors in
    the others; checks that need a broken file are skipped. Returns (report, config, practice, mock, short,
    sections, extras)."""
    rep = Report()
    loaded = {}
    for name in ("course",) + BANKS:
        path = course / f"{name}.json"
        value, ok = load_json(path, rep, required=name in ("course", "practice"))
        # a missing optional bank is fine; a present JSON null or scalar is not an object
        if ok and path.exists() and not isinstance(value, dict):
            rep.err(f"{name}.json must be an object")
            ok = False
        loaded[name] = value if ok else None
    cfg = loaded["course"] if loaded["course"] is not None else {}
    banks = {name: loaded[name] for name in BANKS}
    broken = check_shapes(cfg, banks, rep)
    cfg_ok = loaded["course"] is not None and "course" not in broken
    if not cfg_ok:
        cfg = {}
    banks = {name: None if name in broken else bank for name, bank in banks.items()}
    practice, mock, short = banks["practice"], banks["mock"], banks["short"]
    has_sections = any((course / "sections").glob("*.html"))
    sections = read_sections(course, rep)
    extras = {}
    for name in ("extra.css", "extra.js"):
        if (course / name).exists():
            extras[name] = read_text(course / name, rep, name)
    if not has_sections:
        rep.err("sections/ has no .html files")
    sec_ids = section_ids("\n".join(s for _, s in sections))

    tf_labels, key = TF_LABELS, None
    if cfg_ok:
        if cfg.get("lang", "zh") not in UI:
            rep.err(f"course.json: lang must be one of {sorted(UI)}")
        for k in ("title", "storageKey"):
            if not cfg.get(k):
                rep.err(f"course.json: '{k}' is required")
        if cfg.get("storageKey") and not re.fullmatch(r"[A-Za-z0-9_.-]+", cfg["storageKey"]):
            rep.err("course.json: storageKey may only use letters, digits, '.', '_' and '-'")
        tf_labels = cfg.get("tfLabels") or TF_LABELS
        key = cfg.get("storageKey") or "study-guide"
    lectures = cfg.get("lectures") or []
    ids = {}
    p_items = check_bank("practice", practice, rep, ids, lectures, sec_ids)
    m_items = check_bank("mock", mock, rep, ids, lectures, sec_ids)
    p_groups = {g.get("id") for g in practice.get("groups", [])} if practice is not None else None
    check_short(short, rep, ids, lectures, sec_ids, p_groups)
    audit("practice", p_items, rep, tf_labels)
    audit("mock", m_items, rep, tf_labels)
    if key:  # the shown letters depend on storageKey
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

    if cfg_ok and m_items:
        mcfg = cfg.get("mock") or {}
        gl = {g.get("id"): g.get("lec") for g in mock.get("groups", [])}
        layout = mcfg["sections"] if "sections" in mcfg else DEFAULT_SECTIONS
        for sec in [s for s in layout if s["n"] > 0]:  # the engine drops n: 0 sections
            cat, n = sec["cat"], sec["n"]
            pool = [q for q in m_items if cat_of(q, tf_labels) == cat]
            if len(pool) < n:
                rep.warn(f"mock: section {cat!r} wants {n} questions but the pool has {len(pool)}")
            elif len(pool) < 2 * n:
                rep.warn(f"mock: section {cat!r} draws {n} from a pool of {len(pool)}; about 2x lets repeat papers differ")
            weights = mcfg.get("weights")
            if weights:
                # items with no lecture at all are already an error above
                missing = sorted({q.get("lec") or gl.get(q.get("g")) for q in pool} - set(weights) - {None, ""}, key=str)
                if missing:
                    rep.warn(f"mock: weights give no share to {missing}; their {cat!r} questions will never be drawn")
    return rep, cfg, practice, mock, short, sections, extras


def build(course, out, strict=False):
    """Check, then write the page to out (None: check only). Returns the exit code: 0, 1 on errors, or 2 when
    strict and there are warnings."""
    rep, cfg, practice, mock, short, sections, extras = check(course)
    for w in rep.warnings:
        print("warning:", w)
    for e in rep.errors:
        print("error:", e)
    if rep.errors:
        print(f"{len(rep.errors)} error(s); nothing written.")
        return 1

    def done():
        if strict and rep.warnings:
            print(f"--strict: {len(rep.warnings)} warning(s), so the exit code is 2.")
            return 2
        return 0

    if out is None:
        print(f"check passed with {len(rep.warnings)} warning(s).")
        return done()
    ui = UI[cfg.get("lang", "zh")]
    body = "\n".join(s for _, s in sections)
    if "practice" not in section_ids(body):
        body += '\n<section class="part" id="practice"></section>\n'
    toc = toc_entries(body, ui)
    toc_html = "".join(f'<li><a href="#{sid}"><span class="n">{html.escape(mark)}</span>{label}</a></li>' for sid, mark, label in toc)
    data = {"config": cfg, "practice": practice or {}, "mock": mock or {}, "short": short or {}}
    # \u003c for every "<" keeps "</script>" and "<!--" in a string from closing or confusing the script tag
    data_js = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    uses_tex = "data-tex" in body or "data-tex" in data_js
    css = (ASSETS / "page.css").read_text(encoding="utf-8")
    if "extra.css" in extras:
        css += "\n" + extras["extra.css"]
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
        ("<script>\n" + extras["extra.js"] + "\n</script>") if "extra.js" in extras else "",
        "</body>",
        "</html>",
        "",
    ])
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        # newline="\n": no CRLF on Windows (Path.write_text only takes newline= from Python 3.10)
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write(page)
    except OSError as e:
        print(f"error: cannot write {out}: {e.strerror or e}")
        return 1
    counts = f"{len((practice or {}).get('items', []))} practice, {len((mock or {}).get('items', []))} mock, {len((short or {}).get('items', []))} short answer"
    print(f"wrote {out} ({len(page.encode('utf-8')) // 1024} KB; {counts}; {len(rep.warnings)} warning(s))")
    return done()


def init(course):
    if course.exists() and not course.is_dir():
        print(f"{course} is not a folder")
        return 1
    if course.exists() and any(course.iterdir()):
        print(f"{course} is not empty; pick a new folder.")
        return 1
    shutil.copytree(EXAMPLE, course, dirs_exist_ok=True, ignore=shutil.ignore_patterns("review.html"))
    print(f"copied the example course into {course}; replace its content, then run build.py {course}")
    return 0


def utf8_stdio():
    """A Windows console or pipe can default to a code page (cp1252, cp437) that cannot print a Chinese stem;
    print UTF-8 instead of crashing with UnicodeEncodeError."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")


def main():
    utf8_stdio()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("course", type=Path, help="course folder")
    ap.add_argument("--check", action="store_true", help="validate only, write nothing")
    ap.add_argument("--strict", action="store_true",
                    help="exit with code 2 when there are warnings (errors are still 1); works with --check")
    ap.add_argument("--init", action="store_true", help="create the course folder from the bundled example")
    ap.add_argument("-o", "--out", type=Path, help="output file (default: COURSE/review.html)")
    a = ap.parse_args()
    if a.init:
        return init(a.course)
    if not a.course.is_dir():
        print(f"{a.course} is not a folder")
        return 1
    return build(a.course, None if a.check else (a.out or a.course / "review.html"), strict=a.strict)


if __name__ == "__main__":
    sys.exit(main())
