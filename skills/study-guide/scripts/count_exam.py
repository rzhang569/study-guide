#!/usr/bin/env python3
"""Measure a sample exam PDF without reading its questions.

    python3 count_exam.py sample_exam.pdf

Prints only structure, never question, option or scenario text:
  - page count, question numbers (and gaps), the first page of each question
  - how many lettered options (A–E) each question has
  - point values: per question when a question line carries a marker like "(8 points)",
    and point figures stated in the cover instructions
  - from the cover instructions (text before the first question or scenario): time limit, calculator
    and notes rules, part headings
  - question ranges that share a scenario ("Questions 5–8 refer to …")
  - questions that refer back to earlier material ("Using the … above", "your answers to Questions 1–2"), by number
This lets a student keep the sample unseen for a timed run while the mock exam is still calibrated
to its size and structure. Needs pypdf (pip install pypdf).
"""
import re
import sys

QLINE = re.compile(r"^(?:Q(?:uestion)?\s*)?(\d{1,3})[.):]\s")
OPT = re.compile(r"^\(?([A-Ea-e])[.)]\s")
RANGE = re.compile(r"\b(?:Questions?|Q)\s*(\d{1,3})\s*(?:[–—-]|to|through|and)\s*(\d{1,3})\b", re.I)
# a scenario announcement starts the line; the same range in the middle of a question is only a reference
HEADER_START = re.compile(r"^\W{0,3}(?:questions?\b|q\s*\d|for\s+questions?\b|use\s+(?:this|the\s+following)\b|"
                          r"the\s+following\b|refer\s+to\b|based\s+on\b|scenario\b)", re.I)
PART = re.compile(r"^(Part|Section)\s+([A-Z0-9IVX]{1,4})\b", re.I)
# per-question points only from an explicit marker, so numbers inside a question are never reported
QPOINTS = re.compile(r"[(\[]\s*(\d{1,3})\s*(?:points?|pts?\.?|marks?)\s*[)\]]", re.I)
POINTS = re.compile(r"\b(\d{1,3})\s*(?:points?|pts?|marks?)\b", re.I)
MINUTES = re.compile(r"\b(\d{1,3})\s*(?:minutes?|mins?|hours?|hrs?)\b", re.I)
# a cover number counts only on an instruction line, not in a story ("ran for 17 minutes", "scored 9 points")
TIME_CUE = re.compile(r"\b(?:time|limit|duration|you\s+(?:will\s+)?have|allowed|lasts?|exam|test|quiz|midterm|final)\b", re.I)
POINTS_CUE = re.compile(r"\b(?:each|total|worth|part|section|questions?|exam|out\s+of)\b", re.I)
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
BACKREF = re.compile(r"\b(?:using\s+the|use\s+the|refer(?:s|ring)?\s+(?:back\s+)?to|from\s+(?:the\s+)?(?:scenario|question|part|previous)|"
                     r"(?:same|previous|above)\s+(?:scenario|data|equations?|table|figure|market|example|question)|"
                     r"(?:in|from|to)\s+questions?\s+\d|above)\b", re.I)


def analyze(pages):
    """pages: the extracted text of each page. Returns structure only, no question text."""
    questions, order = {}, []
    cover = {"time": [], "points": [], "rules": {}, "show_work": False}
    parts, pending_parts, ranges = [], [], []
    current, in_cover = None, True
    for pi, text in enumerate(pages):
        lines = [x.strip() for x in (text or "").split("\n")]
        # a page with no question line is a cover or instructions page; its "Part A: ..." lines describe, not head
        cover_page = not any(QLINE.match(x) for x in lines)
        for s in lines:
            if not s:
                continue
            qm = QLINE.match(s)
            if qm:
                n = int(qm.group(1))
                in_cover, current = False, n
                if n not in questions:
                    questions[n] = {"page": pi + 1, "opts": 0, "points": None, "backref": False}
                    order.append(n)
                parts += [(p, label, n) for p, label in pending_parts]
                pending_parts = []
                q = questions[n]
                pt = QPOINTS.search(s)
                if pt and q["points"] is None:
                    q["points"] = int(pt.group(1))
                if BACKREF.search(s) or RANGE.search(s):
                    q["backref"] = True
                continue
            pm = PART.match(s)
            if pm and not cover_page:
                pending_parts.append((pi + 1, f"{pm.group(1).title()} {pm.group(2)}"))
                continue
            rm = RANGE.search(s)
            if rm and HEADER_START.match(s):
                ranges.append((pi + 1, int(rm.group(1)), int(rm.group(2))))
                current, in_cover = None, False   # what follows is shared scenario text, not cover or question
                continue
            if in_cover:
                if TIME_CUE.search(s):
                    cover["time"] += [m.group(0) for m in MINUTES.finditer(s)]
                if POINTS_CUE.search(s):
                    cover["points"] += [m.group(0) for m in POINTS.finditer(s)]
                for key, neg, pos, no_label, yes_label in RULES:
                    if neg.search(s):
                        cover["rules"][key] = no_label
                    elif pos.search(s) and key not in cover["rules"]:
                        cover["rules"][key] = yes_label
                cover["show_work"] = cover["show_work"] or bool(SHOW_WORK.search(s))
                continue
            if current is None:
                continue
            if OPT.match(s):
                questions[current]["opts"] += 1
            elif BACKREF.search(s) or RANGE.search(s):
                questions[current]["backref"] = True
    # questions inside an announced range naturally refer to their own scenario; report only the ones outside
    back = [n for n in sorted(questions) if questions[n]["backref"] and not any(a <= n <= b for _, a, b in ranges)]
    return {"pages": len(pages), "questions": questions, "order": order, "cover": cover,
            "parts": parts, "ranges": ranges, "backrefs": back}


def report(res):
    qs = res["questions"]
    top = max(qs) if qs else 0
    rules = list(res["cover"]["rules"].values()) + (["show your work"] if res["cover"]["show_work"] else [])
    pts = {n: qs[n]["points"] for n in sorted(qs) if qs[n]["points"] is not None}
    out = [
        f"pages {res['pages']}",
        f"questions found {len(qs)} · numbered 1 to {top or None}",
        f"missing in 1..max {[i for i in range(1, top + 1) if i not in qs]}",
        f"first page of each question {({n: qs[n]['page'] for n in sorted(qs)})}",
        f"options per question (0 = no lettered options, e.g. short answer): {({n: qs[n]['opts'] for n in sorted(qs)})}",
        f"points marked on question lines: {pts or 'none found'}",
        "cover instructions (before the first question or scenario):",
        "  time: " + (", ".join(dict.fromkeys(res["cover"]["time"])) or "not found"),
        "  point figures: " + (", ".join(res["cover"]["points"]) or "not found"),
        "  rules: " + (", ".join(rules) or "none recognised"),
    ]
    if res["parts"]:
        out.append("part / section headings: " + ", ".join(f"{label} (p{p}, starts at Q{n})" for p, label, n in res["parts"]))
    out.append("question ranges announced (shared scenarios): " + (", ".join(f"Q{a}–{b} (p{p})" for p, a, b in res["ranges"]) or "none"))
    out.append(f"questions that refer back to earlier material (check which scenario they reuse): {res['backrefs'] or 'none'}")
    return "\n".join(out)


def main(argv):
    if len(argv) != 2:
        sys.exit(__doc__)
    try:
        from pypdf import PdfReader
    except ImportError:
        sys.exit("count_exam.py needs pypdf: pip install pypdf")
    pages = [p.extract_text() or "" for p in PdfReader(argv[1]).pages]
    print(report(analyze(pages)))


if __name__ == "__main__":
    main(sys.argv)
