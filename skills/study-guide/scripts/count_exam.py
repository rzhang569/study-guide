#!/usr/bin/env python3
"""Measure a sample exam PDF without reading its questions.

    python3 count_exam.py sample_exam.pdf

Prints the page count, the question numbers found (and any gaps), how many A–E option lines there are,
and headings that announce question ranges ("Questions 1–4", "Q11-14"), which reveal scenario groups.
No question or option text is printed, so a student can keep the sample unseen for a timed run while
the mock exam is still calibrated to its size and structure. Needs pypdf (pip install pypdf).
"""
import re
import sys

try:
    from pypdf import PdfReader
except ImportError:
    sys.exit("count_exam.py needs pypdf: pip install pypdf")

if len(sys.argv) != 2:
    sys.exit(__doc__)
RANGE = re.compile(r"\b(Questions?|Q)\s*(\d{1,3})\s*(?:[–—-]|to|through)\s*(\d{1,3})\b", re.I)
r = PdfReader(sys.argv[1])
qnums, opt_lines, heads, tf_lines = [], 0, [], 0
for pi, p in enumerate(r.pages):
    t = p.extract_text() or ""
    for line in t.split("\n"):
        s = line.strip()
        m = re.match(r"^(?:Q(?:uestion)?\s*)?(\d{1,3})[.):]\s", s)
        if m:
            qnums.append((int(m.group(1)), pi + 1))
        if re.match(r"^\(?[A-Ea-e][.)]\s", s):
            opt_lines += 1
        if re.search(r"\b(True|False)\b.*\b(True|False)\b", s) and len(s) < 40:
            tf_lines += 1
        # print only the matched range, never the rest of the line: a stem can follow on the same line
        for rm in RANGE.finditer(s):
            heads.append((pi + 1, "Questions %s–%s" % (rm.group(2), rm.group(3))))
nums = [n for n, _ in qnums]
top = max(nums) if nums else 0
print("pages", len(r.pages))
print("question-number lines", len(nums), "distinct", len(set(nums)), "max", top or None)
print("missing in 1..max", [i for i in range(1, top + 1) if i not in set(nums)])
print("first page of each question", {n: pg for n, pg in sorted(set(qnums))})
print("option lines (A-E)", opt_lines, "· True/False answer lines", tf_lines)
print("question ranges announced (scenario groups):")
for h in heads:
    print("  p%d: %s" % h)
