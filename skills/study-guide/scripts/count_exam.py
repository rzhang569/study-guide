#!/usr/bin/env python3
"""Measure a sample exam PDF without reading its questions.

    python3 count_exam.py sample_exam.pdf

Prints only structure, never question, option or scenario text:
  - page count, question numbers (and gaps), the first page of each question
  - how many lettered options (A–H) each question has, and lettered sub-parts (a), (b), …
  - point values: per question when a question line carries a marker like "(8 points)",
    and point figures stated in the cover instructions
  - from the cover instructions (text before the first question or scenario): time limit, calculator
    and notes rules; part headings ("Part A", "Section II") and where numbering starts again
  - question ranges that share a scenario ("Questions 5–8 refer to …")
  - questions that refer back to earlier material ("Using the … above", "your answers to Questions 1–2"), by number
Everything printed is fixed wording, numbers and normalised labels. What cannot be measured is reported as
unknown. This lets a student keep the sample unseen for a timed run while the mock exam is still calibrated
to its size and structure. Needs pypdf (python3 -m pip install pypdf).
"""
import logging
import re
import sys
import warnings
from pathlib import Path

QLINE = re.compile(r"^(?:Q(?:uestion)?\s*)?(\d{1,3})[.):]\s")
# options are "A." "A)" "(A)" in capitals, or "a." in lower case; "(a)" and "a)" are sub-parts of a question
OPT = re.compile(r"^(?:\(([A-H])\)|([A-H])[.)]|([a-h])\.)(?=\s)")
OPT_MORE = {True: re.compile(r"(?<=\s)\(?([A-H])[.)](?=\s|$)"), False: re.compile(r"(?<=\s)([a-h])\.(?=\s|$)")}
SUBPART = re.compile(r"^\(?([a-h])\)(?=\s|$)")
RANGE = re.compile(r"\b(?:Questions?|Q)\s*(\d{1,3})\s*(?:[–—-]|to|through|and)\s*(\d{1,3})\b", re.I)
# a scenario announcement starts the line; the same range in the middle of a question is only a reference
HEADER_START = re.compile(r"^\W{0,3}(?:questions?\b|q\s*\d|for\s+questions?\b|use\s+(?:this|the\s+following)\b|"
                          r"the\s+following\b|refer\s+to\b|based\s+on\b|scenario\b)", re.I)
# the label must be a capital letter, a number or a roman numeral, so "Part of the cost …" is never a heading
PART = re.compile(r"^(?i:(part|section))\s+([IVX]{1,5}|[A-Z]|\d{1,2})(?!\.\d)(?=\s*$|\s*[:.)(\-–—]|\s+[A-Z0-9(])")
# per-question points only from an explicit marker, so numbers inside a question are never reported
QPOINTS = re.compile(r"[(\[]\s*(\d{1,3})\s*(?:points?|pts?\.?|marks?)\s*[)\]]", re.I)
POINTS = re.compile(r"(?<![\d.])(\d{1,3})\s*(points?|pts?|marks?)\b", re.I)
MINUTES = re.compile(r"(?<![\d.])(\d{1,3}(?:\.\d)?)\s*(minutes?|mins?|hours?|hrs?)\b", re.I)
# a cover number counts only on an instruction line, not in a story ("ran for 17 minutes", "scored 9 points")
TIME_CUE = re.compile(r"\b(?:time|limit|duration|you\s+(?:will\s+)?have|allowed|lasts?|exam|test|quiz|midterm|final)\b", re.I)
POINTS_CUE = re.compile(r"\b(?:each|total|worth|part|section|questions?|exam|out\s+of)\b", re.I)
# wording that marks a numbered line as an exam instruction rather than a question (see instruction_lines)
INSTRUCTION_CUE = re.compile(
    r"\b(?:name|net\s*id|student\s+id|id\s+number|minutes?|mins?|hours?|calculators?|notes?|note\s*sheets?|"
    r"cheat\s*sheets?|crib\s*sheets?|phones?|devices?|electronics?|laptops?|pages?|booklet|scantron|bubble|"
    r"answer\s+sheet|pencil|pen|honou?r|integrity|cheating|closed[-\s]book|open[-\s]book|turn\s+(?:off|in|over)|"
    r"show\s+(?:all\s+)?(?:your\s+)?work|exam|midterm|quiz|instructions?|allowed|permitted|until\s+told)\b", re.I)
# rules are checked negation first: "No calculators allowed" must not also read as "calculators allowed"
RULES = [
    ("calculator",
     re.compile(r"\bno\s+calculators?\b|\bcalculators?\s+(?:are\s+|is\s+)?not\s+(?:allowed|permitted)\b|\bwithout\s+(?:a\s+)?calculators?\b", re.I),
     re.compile(r"\bcalculators?\s+(?:are\s+|is\s+)?(?:allowed|permitted)\b|\bmay\s+use\s+(?:a\s+)?calculators?\b", re.I),
     "no calculator", "calculator allowed"),
    ("notes",
     re.compile(r"\bno\s+(?:notes|note\s*sheets?|cheat\s*sheets?|crib\s*sheets?)\b|\b(?:notes|note\s*sheets?|cheat\s*sheets?)\s+(?:are\s+|is\s+)?not\s+(?:allowed|permitted)\b|\bclosed[-\s](?:book|notes)\b", re.I),
     re.compile(r"\b(?:notes|note\s*sheets?|cheat\s*sheets?|crib\s*sheets?)\s+(?:are\s+|is\s+)?(?:allowed|permitted)\b|\bopen[-\s](?:book|notes?)\b|\bmay\s+(?:bring|use)\b.{0,30}\b(?:notes|sheet)\b", re.I),
     "no notes or note sheet", "notes or a note sheet allowed"),
]
SHOW_WORK = re.compile(r"\bshow\s+(?:all\s+)?(?:your\s+)?work\b", re.I)
# a bare "above" is ordinary prose ("lies above the line"); "the above" and "above question" point back
BACKREF = re.compile(r"\b(?:using\s+the|use\s+the|refer(?:s|ring)?\s+(?:back\s+)?to|from\s+(?:the\s+)?(?:scenario|question|part|previous)|"
                     r"(?:same|previous|preceding|earlier|above)\s+(?:scenario|data|equations?|table|figure|graph|market|example|questions?|problems?)|"
                     r"the\s+above|(?:in|from|to|of|for)\s+(?:questions?|Q)\s*\d)\b", re.I)
NO_TEXT = ("no text layer found (a scanned or image-only PDF), so nothing can be measured. Do not open the PDF yourself; "
           "ask the student for the cover-page facts: number of questions, points and time limit.")


def option_letters(s):
    """The option letters on a line that starts with one: "A. 1 B. 2 C. 3 D. 4" gives "ABCD". Later markers
    count only in sequence, so a stray "B." inside an option's text is not another option."""
    m = OPT.match(s)
    if not m:
        return ""
    letters = next(g for g in m.groups() if g)
    for more in OPT_MORE[letters.isupper()].finditer(s, m.end()):
        if more.group(1) == chr(ord(letters[-1]) + 1):
            letters += more.group(1)
    return letters.upper()


def instruction_lines(lines):
    """Indexes of numbered cover instructions ("1. Write your name", "2. You have 75 minutes").

    Numbered lines at the start are instructions, not questions, when both hold:
      1. numbering starts again at 1 before anything proves a question has begun (an option line after a
         numbered line, a per-question point marker, or a scenario header), so they carry no options or points;
      2. more than half of them use instruction wording (name, minutes, calculator, notes, pages, phones …).
    A short-answer Part A whose numbering restarts in Part B fails rule 2 and stays as questions."""
    run = []
    for i, (_, s) in enumerate(lines):
        qm = QLINE.match(s)
        if qm:
            if int(qm.group(1)) == 1 and run:
                cued = sum(1 for j in run if INSTRUCTION_CUE.search(lines[j][1]))
                return set(run) if 2 * cued > len(run) else set()
            if QPOINTS.search(s):
                return set()
            run.append(i)
        elif (run and option_letters(s)) or (RANGE.search(s) and HEADER_START.match(s)):
            return set()
    return set()


def figure(m, one, many):
    """A matched cover figure in fixed wording: "50 minutes", "1 hour", "8 points"."""
    return f"{m.group(1)} {one if m.group(1) == '1' else many}"


def fold_inner_list(questions, runs, n, odd):
    """Numbering that started again at 1 with no part heading and now continues the earlier numbering (5, 1, 2,
    3, 6) was a numbered list inside a question: give those lines back to the question before them."""
    earlier = [q for q in questions if q["run"] == len(runs) - 2]
    if n != earlier[-1]["n"] + 1:
        return
    inner = [q for q in questions if q["run"] == len(runs) - 1]
    for q in inner:
        earlier[-1]["letters"] |= q["letters"]
        earlier[-1]["subparts"] |= q["subparts"]
        earlier[-1]["backref"] = earlier[-1]["backref"] or q["backref"]
        odd.append(q["page"])
    del questions[-len(inner):]
    runs.pop()


def analyze(pages):
    """pages: the extracted text of each page. Returns structure only, no question text.
    questions: one dict per question in page order; "run" counts how often numbering started again at 1."""
    lines = [(pi + 1, s) for pi, text in enumerate(pages) for s in (x.strip() for x in (text or "").split("\n")) if s]
    instr = instruction_lines(lines)
    # a page with no question line is a cover or instructions page; its "Part A: ..." lines describe, not head
    question_pages = {p for i, (p, s) in enumerate(lines) if i not in instr and QLINE.match(s)}
    questions, runs, parts, pending, ranges, odd = [], [], [], [], [], []
    cover = {"time": [], "points": [], "rules": {}, "show_work": False}
    current, in_cover = None, True
    for i, (page, s) in enumerate(lines):
        qm = None if i in instr else QLINE.match(s)
        if qm:
            n = int(qm.group(1))
            if len(runs) > 1 and runs[-1] is None and n > questions[-1]["n"] + 1:
                fold_inner_list(questions, runs, n, odd)
            if not questions or n == 1:  # the first question, or numbering starts again (a new part)
                runs.append(pending[-1][1] if pending else None)
            elif n <= questions[-1]["n"]:
                odd.append(page)  # e.g. a numbered list inside a question: keep it with that question
                qm = None
        if qm:
            in_cover = False
            current = {"run": len(runs) - 1, "n": n, "page": page, "letters": set(), "subparts": set(),
                       "points": None, "backref": False}
            questions.append(current)
            parts += [(p, label, current["run"], n) for p, label in pending]
            pending = []
            pt = QPOINTS.search(s)
            if pt:
                current["points"] = int(pt.group(1))
            rest = s[qm.end():]
            if BACKREF.search(rest) or RANGE.search(rest):
                current["backref"] = True
            continue
        pm = PART.match(s)
        if pm and page in question_pages:
            pending.append((page, f"{pm.group(1).title()} {pm.group(2)}"))
            continue
        rm = RANGE.search(s)
        if rm and HEADER_START.match(s):
            ranges.append({"page": page, "a": int(rm.group(1)), "b": int(rm.group(2)), "after": len(questions)})
            current, in_cover = None, False   # what follows is shared scenario text, not cover or question
            continue
        if in_cover:
            if TIME_CUE.search(s):
                cover["time"] += [figure(m, *(("hour", "hours") if m.group(2)[0] in "hH" else ("minute", "minutes")))
                                  for m in MINUTES.finditer(s)]
            if POINTS_CUE.search(s):
                cover["points"] += [figure(m, *(("mark", "marks") if m.group(2)[0] in "mM" else ("point", "points")))
                                    for m in POINTS.finditer(s)]
            for key, neg, pos, no_label, yes_label in RULES:
                if neg.search(s):
                    cover["rules"][key] = no_label
                elif pos.search(s) and key not in cover["rules"]:
                    cover["rules"][key] = yes_label
            cover["show_work"] = cover["show_work"] or bool(SHOW_WORK.search(s))
            continue
        if current is None:
            continue
        letters = option_letters(s)
        sub = SUBPART.match(s)
        if letters:
            current["letters"].update(letters)
        elif sub:
            current["subparts"].add(sub.group(1))
        elif BACKREF.search(s) or RANGE.search(s):
            current["backref"] = True
    for q in questions:
        q["opts"] = len(q.pop("letters"))
        q["subparts"] = len(q["subparts"])
    # a range belongs to the numbering of the first question after it
    for r in ranges:
        r["run"] = questions[r["after"]]["run"] if r["after"] < len(questions) else max(len(runs) - 1, 0)
    # questions inside an announced range naturally refer to their own scenario; report only the ones outside
    back = [(q["run"], q["n"]) for q in questions if q["backref"] and not any(
        r["run"] == q["run"] and r["a"] <= q["n"] <= r["b"] for r in ranges)]
    return {"pages": len(pages), "blank": [i + 1 for i, t in enumerate(pages) if not (t or "").strip()],
            "questions": questions, "runs": runs, "cover": cover, "parts": parts,
            "ranges": [(r["page"], r["a"], r["b"]) for r in ranges], "range_runs": [r["run"] for r in ranges],
            "backrefs": back, "odd": odd}


def refs(keys, runs):
    """[(run, n), …] as "Q1–4, Q6", or "Part A Q1–12, Part B Q1–2" when numbering starts again."""
    keys, out, i, last_run = sorted(set(keys)), [], 0, None
    while i < len(keys):
        run, a = keys[i]
        b = a
        while i + 1 < len(keys) and keys[i + 1] == (run, b + 1):
            i, b = i + 1, b + 1
        out.append((run_prefix(runs, run) if run != last_run else "") + f"Q{a}" + (f"–{b}" if b > a else ""))
        last_run, i = run, i + 1
    return ", ".join(out)


def run_name(runs, run):
    return runs[run] or f"set {run + 1}"


def run_prefix(runs, run):
    return f"{run_name(runs, run)} " if len(runs) > 1 else ""


def pages_text(pages):
    """[2, 3, 4, 7] as "p2–4, p7"."""
    return refs([(0, p) for p in pages], [None]).replace("Q", "p")


def grouped(qs, runs, field, name):
    """Questions grouped by a value, in order of first appearance: "4 options: Q1–12, Q15; …"."""
    by = {}
    for q in qs:
        by.setdefault(q[field], []).append((q["run"], q["n"]))
    return "; ".join(f"{name(v)}: {refs(keys, runs)}" for v, keys in by.items())


def report(res):
    qs, runs, cover = res["questions"], res["runs"], res["cover"]
    out = [f"pages {res['pages']}"]
    if res["blank"]:
        out.append(f"no text layer on {pages_text(res['blank'])}: anything on those pages is unknown")
    if not qs:
        out.append("questions found 0: no numbered question lines, so the question count, options and points are unknown")
    else:
        out.append(f"questions found {len(qs)}: {refs([(q['run'], q['n']) for q in qs], runs)}")
        missing = [(r, n) for r in range(len(runs)) for n in range(1, max(q["n"] for q in qs if q["run"] == r) + 1)
                   if not any(q["run"] == r and q["n"] == n for q in qs)]
        if missing:
            out.append(f"missing numbers: {refs(missing, runs)}")
        if len(runs) > 1:
            starts = [next(q["page"] for q in qs if q["run"] == r) for r in range(len(runs))]
            out.append("numbering starts again at 1: " + ", ".join(
                f"{run_name(runs, r)} (p{starts[r]}" + ("" if runs[r] else ", no part heading found, so whether it is a new part is unknown") + ")"
                for r in range(1, len(runs))))
        if res["odd"]:
            out.append(f"numbered lines out of sequence, counted with the question before them: {pages_text(res['odd'])}")
        out.append("first page of each question: " + grouped(qs, runs, "page", lambda p: f"p{p}"))
        out.append("options per question: " + grouped(
            qs, runs, "opts", lambda k: f"{k} option{'s' * (k > 1)}" if k else "no lettered options (e.g. short answer)"))
        with_sub = [q for q in qs if q["subparts"]]
        if with_sub:
            out.append("lettered sub-parts (a), (b), …: " + grouped(with_sub, runs, "subparts", lambda k: f"{k} sub-part{'s' * (k > 1)}"))
        marked = [q for q in qs if q["points"] is not None]
        out.append("points marked on question lines: " + (grouped(
            marked, runs, "points", lambda k: f"{k} point" if k == 1 else f"{k} points") if marked else "none found"))
    rules = list(cover["rules"].values()) + (["show your work"] if cover["show_work"] else [])
    out += [
        "cover instructions (before the first question or scenario):",
        "  time: " + (", ".join(dict.fromkeys(cover["time"])) or "unknown (no time limit found)"),
        "  point figures: " + (", ".join(cover["points"]) or "not found"),
        "  rules: " + (", ".join(rules) or "none recognised"),
    ]
    if res["parts"]:
        out.append("part / section headings: " + ", ".join(f"{label} (p{p}, starts at Q{n})" for p, label, _, n in res["parts"]))
    out.append("question ranges announced (shared scenarios): " + (", ".join(
        f"{run_prefix(runs, run)}Q{a}–{b} (p{p})" for (p, a, b), run in zip(res["ranges"], res["range_runs"])) or "none"))
    out.append("questions that refer back to earlier material (check which scenario they reuse): "
               + (refs(res["backrefs"], runs) or "none"))
    return "\n".join(out)


def measure(pages):
    """(report text, exit code). A PDF without any text cannot be measured."""
    if not any((p or "").strip() for p in pages):
        return f"pages {len(pages)}\n{NO_TEXT}", 1
    return report(analyze(pages)), 0


def main(argv):
    if len(argv) != 2:
        print("usage: python3 count_exam.py sample_exam.pdf", file=sys.stderr)
        return 2
    path = Path(argv[1])
    if not path.is_file():
        print(f"count_exam.py: no such file: {path}", file=sys.stderr)
        return 1
    try:
        from pypdf import PdfReader
    except ImportError:
        print("count_exam.py needs pypdf: run python3 -m pip install pypdf, then run this again. "
              "Do not read the PDF any other way.", file=sys.stderr)
        return 1
    # pypdf logs and warns with raw bytes from damaged files (a bad header, a broken object), which can be question
    # text, so nothing it says may reach the terminal; our own messages below name only the error type
    logging.getLogger("pypdf").setLevel(logging.CRITICAL + 1)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pages = [p.extract_text() or "" for p in PdfReader(str(path)).pages]
    except Exception as e:  # damaged or encrypted file; the error type says enough without quoting the file
        print(f"count_exam.py: could not read {path.name} as a PDF ({type(e).__name__})", file=sys.stderr)
        return 1
    text, code = measure(pages)
    print(text)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
