"""Regression tests for skills/study-guide/scripts/count_exam.py. Run from the repo root:

    python3 -m unittest discover -s tests

Each case is fictional exam text fed straight to analyze(), so no PDF is needed. MARK words stand for
question content: they must never appear in the report. The strict spoiler test goes further: every word in
every report must come from the script's own fixed wording.
"""
import contextlib
import importlib.util
import io
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/study-guide/scripts/count_exam.py"
spec = importlib.util.spec_from_file_location("count_exam", SCRIPT)
ce = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ce)
EVAL_PDF = ROOT / "evals/measures-sample-exam-unseen/files/sample_midterm.pdf"
HAS_PYPDF = importlib.util.find_spec("pypdf") is not None

COVER = "Sample Midterm\nTime: 50 minutes.\nPart A: 4 multiple choice questions, 2 points each (8 points).\nPart B: 1 short answer, 10 points.\n"

# Every fixture is a list of page texts. Question text deliberately reuses report words ("questions",
# "options", "points", "scenario", "calculator allowed") and heading-like openings ("Part of", "Section This").
FIXTURES = {
    "scenario minutes": [COVER, "Questions 1–2 refer to this scenario. MARKA ran for 17 minutes every day.\n"
                                "1. MARKB what is it?\nA. x\nB. y\n2. MARKC why?\nA. x\nB. y"],
    "story before question one": ["A runner MARKA trained for 17 minutes and scored 9 points.\n1. MARKB how fast?\nA. x\nB. y"],
    "no cheat sheet": ["Exam rules\nNo cheat sheet allowed.\n1. MARKA?\nA. x\nB. y"],
    "no calculators allowed": ["Rules: No calculators allowed.\n1. MARKA?\nA. x\nB. y"],
    "note sheet allowed": ["One handwritten note sheet is allowed. Calculators are permitted.\n1. MARKA?\nA. x\nB. y"],
    "range cited in a question": [COVER, "1. MARKA?\nA. x\nB. y\n2. MARKB?\nA. x\nB. y\n"
                                         "3. Using your answers to Questions 1–2, compute MARKC."],
    "reference keeps options": [COVER, "4. MARKA, as in Questions 1–2 above,\nwhat is MARKB?\nA. x\nB. y\nC. z\nD. w"],
    "scenario and back reference": [COVER, "Questions 5–8 refer to this scenario. MARKS market.\n5. MARKA?\nA. x\n"
                                           "8. MARKB?\nA. x\n13. (8 points) Using the MARKS equations, find MARKC."],
    "points inside a question": ["5. If a MARKA score rises by 37 points, what happens?\nA. x\nB. y"],
    "options and scenario text": [COVER, "Questions 1–2 refer to this scenario. MARKS bakery.\n1. MARKA?\nA. MARKO1\nB. MARKO2\n"
                                         "2. MARKB?\nA. MARKO3\nB. MARKO4\n3. (10 points) From the scenario above, MARKC."],
    "numbered cover": ["Midterm\nInstructions\n1. Write your name on every page.\n2. You have 75 minutes.\n3. No calculators.\n",
                       "1. MARKA questions options points?\nA. MARKO1\nB. MARKO2\n2. MARKB?\nA. 1 B. 2 C. 3 D. 4\n"],
    "short answer part restarts": ["Time: 60 minutes\n",
                                   "Part A\n1. MARKA explain the scenario.\n2. MARKB describe the options.\n",
                                   "Part B\n1. MARKC?\nA. x\nB. y\nC. z\nD. w\nE. v\nF. u\nG. t\nH. s\n"
                                   "2. MARKD?\n(a) MARKE\n(b) MARKF\n(c) MARKG\n"],
    "heading-like question text": ["1. MARKA?\nA. x\nB. y\nPart of the cost is fixed.\nSection This is MARKB.\n"
                                   "PART OF THE MARKC\nSection 2.3 of the MARKD\nPart A of the figure\n"
                                   "2. Which point lies above the line?\nA. calculator allowed\n"
                                   "3. Using the above, find MARKE.\nPart B (16 points)\n4. MARKF?\nSECTION II: MARKG\n5. MARKH"],
    "restart without heading": ["1. MARKA\nA. x\n2. MARKB\nA. y\nShort answer\n1. MARKC\n2. MARKD\n"],
    "list inside a question": ["4. MARKA\nA. x\n5. MARKB which are true?\n1) MARKC\n2) MARKD\n3) MARKE\n"
                               "A. 1 only\nB. 2 only\nC. both\n6. MARKF\nA. x\n"],
    "blank pages": ["Time limit: 1.5 hours\n1. MARKA\nA. x\n", "", " "],
    "no question lines": ["MARKA MARKB questions options points minutes\nMARKC part section"],
}

# Every word a report may contain: the fixed wording in count_exam.py (checked below), nothing else.
# Normalised labels after "Part" / "Section" (A, 2, II) and numbers are allowed separately.
ALLOWED = set("""
pages no text layer on anything those is unknown questions found numbered question lines so the count options and
points missing numbers numbering starts again at part heading whether it a new out of sequence counted with before
them first page each per option lettered e g short answer sub parts marked point none cover instructions or scenario
time limit figures not rules recognised calculator allowed notes note sheet show your work section headings ranges
announced shared scenarios that refer back to earlier material check which they reuse minutes minute hours hour marks
mark set Q p scanned image only PDF can be measured Do open yourself ask student for facts number b are nothing
""".split())
LABEL = re.compile(r"\b(?:Part|Section) (?:[IVX]{1,5}|[A-Z]|\d{1,2})\b")


def run(*pages):
    res = ce.analyze(list(pages))
    return res, ce.report(res)


def fixture(name):
    return run(*FIXTURES[name])


def q(res, n, run=0):
    return next(x for x in res["questions"] if x["n"] == n and x["run"] == run)


def numbers(res):
    return [(x["run"], x["n"]) for x in res["questions"]]


def pdf_pages(path):
    from pypdf import PdfReader
    return [p.extract_text() or "" for p in PdfReader(path).pages]


class CoverInstructions(unittest.TestCase):
    def test_scenario_minutes_are_not_the_time_limit(self):
        res, out = fixture("scenario minutes")
        self.assertEqual(res["cover"]["time"], ["50 minutes"])
        self.assertNotIn("17", out)

    def test_story_before_question_one_without_a_header_is_ignored(self):
        res, _ = fixture("story before question one")
        self.assertEqual(res["cover"]["time"], [])
        self.assertEqual(res["cover"]["points"], [])

    def test_no_cheat_sheet_is_not_read_as_allowed(self):
        res, _ = fixture("no cheat sheet")
        self.assertEqual(res["cover"]["rules"]["notes"], "no notes or note sheet")

    def test_no_calculators_allowed_is_only_negative(self):
        res, out = fixture("no calculators allowed")
        self.assertEqual(res["cover"]["rules"]["calculator"], "no calculator")
        self.assertNotIn("calculator allowed", out)

    def test_note_sheet_allowed(self):
        res, _ = fixture("note sheet allowed")
        self.assertEqual(res["cover"]["rules"]["notes"], "notes or a note sheet allowed")
        self.assertEqual(res["cover"]["rules"]["calculator"], "calculator allowed")

    def test_numbered_cover_instructions_are_not_questions(self):
        res, out = fixture("numbered cover")
        self.assertEqual(numbers(res), [(0, 1), (0, 2)])
        self.assertEqual(q(res, 1)["page"], 2)
        self.assertEqual(res["cover"]["time"], ["75 minutes"])
        self.assertEqual(res["cover"]["rules"]["calculator"], "no calculator")
        self.assertIn("questions found 2: Q1–2\n", out)

    def test_numbered_short_answers_restarting_in_part_b_stay_questions(self):
        res, _ = fixture("short answer part restarts")
        self.assertEqual(numbers(res), [(0, 1), (0, 2), (1, 1), (1, 2)])
        self.assertEqual(res["runs"], ["Part A", "Part B"])

    def test_time_in_hours(self):
        res, _ = fixture("blank pages")
        self.assertEqual(res["cover"]["time"], ["1.5 hours"])
        res, _ = run("Exam time: 1 hour\n1. MARKA\nA. x")
        self.assertEqual(res["cover"]["time"], ["1 hour"])


class Questions(unittest.TestCase):
    def test_question_line_citing_a_range_is_still_counted(self):
        res, _ = fixture("range cited in a question")
        self.assertEqual(numbers(res), [(0, 1), (0, 2), (0, 3)])
        self.assertEqual(res["ranges"], [])
        self.assertEqual(res["backrefs"], [(0, 3)])

    def test_reference_inside_a_question_keeps_its_options(self):
        res, _ = fixture("reference keeps options")
        self.assertEqual(q(res, 4)["opts"], 4)
        self.assertEqual(res["ranges"], [])

    def test_scenario_header_and_back_reference(self):
        res, _ = fixture("scenario and back reference")
        self.assertEqual(res["ranges"], [(2, 5, 8)])
        self.assertEqual(res["backrefs"], [(0, 13)])
        self.assertEqual(q(res, 13)["points"], 8)

    def test_points_inside_a_question_are_not_reported(self):
        res, out = fixture("points inside a question")
        self.assertIsNone(q(res, 5)["points"])
        self.assertNotIn("37", out)

    def test_numbering_restarts_in_a_new_part(self):
        res, out = fixture("short answer part restarts")
        self.assertIn("questions found 4: Part A Q1–2, Part B Q1–2\n", out)
        self.assertIn("numbering starts again at 1: Part B (p3)\n", out)
        self.assertEqual(res["parts"], [(2, "Part A", 0, 1), (3, "Part B", 1, 1)])
        self.assertNotIn("missing", out)

    def test_restart_without_a_heading_is_reported_as_unknown(self):
        res, out = fixture("restart without heading")
        self.assertEqual(numbers(res), [(0, 1), (0, 2), (1, 1), (1, 2)])
        self.assertIn("set 2 (p1, no part heading found, so whether it is a new part is unknown)", out)

    def test_numbered_list_inside_a_question_is_not_a_question(self):
        res, out = fixture("list inside a question")
        self.assertEqual(numbers(res), [(0, 4), (0, 5), (0, 6)])
        self.assertEqual(q(res, 5)["opts"], 3)
        self.assertIn("numbered lines out of sequence, counted with the question before them: p1", out)

    def test_option_layouts(self):
        res, out = fixture("numbered cover")
        self.assertEqual(q(res, 2)["opts"], 4)  # "A. 1 B. 2 C. 3 D. 4" on one line
        res, out = fixture("short answer part restarts")
        self.assertEqual(q(res, 1, run=1)["opts"], 8)  # A–H
        self.assertEqual(q(res, 2, run=1)["opts"], 0)  # (a)(b)(c) are sub-parts
        self.assertEqual(q(res, 2, run=1)["subparts"], 3)
        self.assertIn("lettered sub-parts (a), (b), …: 3 sub-parts: Part B Q2", out)
        res, _ = run("1. MARKA\nA. 1 B. 2\nC. 3 D. 4\n2. MARKB\na. x\nb. y\nc. z\n3. MARKC\nA. Plan x C. later\nB. y")
        self.assertEqual([x["opts"] for x in res["questions"]], [4, 3, 2])

    def test_bare_above_is_not_a_back_reference(self):
        res, _ = fixture("heading-like question text")
        self.assertEqual(res["backrefs"], [(0, 3)])
        for phrase in ("the above", "the above question", "the previous question", "the result in Question 2",
                       "the same scenario"):
            with self.subTest(phrase=phrase):
                res, _ = run(f"1. MARKA\nA. x\n2. MARKB\nA. x\n3. Given {phrase}, find MARKC.")
                self.assertEqual(res["backrefs"], [(0, 3)])

    def test_part_headings_need_a_letter_number_or_roman_label(self):
        res, out = fixture("heading-like question text")
        self.assertEqual([(label, n) for _, label, _, n in res["parts"]], [("Part B", 4), ("Section II", 5)])
        self.assertIn("part / section headings: Part B (p1, starts at Q4), Section II (p1, starts at Q5)", out)

    def test_compact_per_question_output(self):
        _, out = run(*pdf_pages(EVAL_PDF)) if HAS_PYPDF and EVAL_PDF.exists() else fixture("numbered cover")
        self.assertNotRegex(out, r"[{}\[\]]")
        _, out = run("1. a\nA. x\nB. y\n2. b\nA. x\nB. y\n3. c\n4. d\nA. x\nB. y\n")
        self.assertIn("options per question: 2 options: Q1–2, Q4; no lettered options (e.g. short answer): Q3", out)
        self.assertIn("first page of each question: p1: Q1–4", out)

    def test_what_cannot_be_measured_is_unknown(self):
        res, out = fixture("no question lines")
        self.assertIn("questions found 0: no numbered question lines, so the question count, options and points are unknown", out)
        self.assertIn("time: unknown", out)
        _, out = fixture("blank pages")
        self.assertIn("no text layer on p2–3: anything on those pages is unknown", out)
        self.assertEqual(ce.measure(["", " \n"]), ("pages 2\n" + ce.NO_TEXT, 1))
        self.assertIn("Do not open the PDF yourself", ce.NO_TEXT)


class SpoilerFree(unittest.TestCase):
    """The report may contain only fixed wording, normalised labels and numbers."""

    def reports(self):
        for name, pages in FIXTURES.items():
            yield name, ce.measure(pages)[0]
        yield "no text", ce.measure(["", ""])[0]
        if HAS_PYPDF and EVAL_PDF.exists():
            yield "eval sample", ce.measure(pdf_pages(EVAL_PDF))[0]

    def test_allowlist_comes_from_the_script(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for word in ALLOWED:
            self.assertRegex(source, r"(?<![^\W\d_])" + re.escape(word) + r"(?![^\W\d_])", word)

    def test_reports_contain_only_template_words_labels_and_numbers(self):
        for name, out in self.reports():
            with self.subTest(fixture=name):
                words = re.findall(r"[^\W\d_]+", LABEL.sub(" ", out))
                self.assertEqual(sorted(set(words) - ALLOWED), [])
                self.assertNotIn("MARK", out)

    @unittest.skipUnless(HAS_PYPDF and EVAL_PDF.exists(), "needs pypdf and the eval sample")
    def test_econ_sample(self):
        res, out = run(*pdf_pages(EVAL_PDF))
        self.assertEqual(numbers(res), [(0, n) for n in range(1, 15)])
        self.assertEqual([x["opts"] for x in res["questions"]], [4] * 12 + [0, 0])
        self.assertEqual([(a, b) for _, a, b in res["ranges"]], [(5, 8)])
        self.assertEqual(res["backrefs"], [(0, 13)])
        self.assertEqual(res["cover"]["time"], ["50 minutes"])
        self.assertEqual(res["cover"]["rules"].get("calculator"), "no calculator")
        for word in ["marzipan", "thistlewood", "quokka", "zephyr", "saffron", "obsidian", "lantern", "pumice", "kelp", "walrus", "juniper", "gondola"]:
            self.assertNotIn(word, out.lower())


class CommandLine(unittest.TestCase):
    def cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True)

    def test_wrong_argument_count_and_missing_file(self):
        for args in ((), ("a.pdf", "b.pdf")):
            result = self.cli(*args)
            self.assertEqual(result.returncode, 2)
            self.assertIn("usage: python3 count_exam.py sample_exam.pdf", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
        result = self.cli(ROOT / "absent.pdf")
        self.assertEqual(result.returncode, 1)
        self.assertIn("no such file", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_missing_pypdf_says_how_to_install_and_not_to_read_the_pdf(self):
        err = io.StringIO()
        with mock.patch.dict(sys.modules, {"pypdf": None}), contextlib.redirect_stderr(err):
            self.assertEqual(ce.main(["count_exam.py", str(SCRIPT)]), 1)
        self.assertIn("python3 -m pip install pypdf", err.getvalue())
        self.assertIn("Do not read the PDF any other way", err.getvalue())

    @unittest.skipUnless(HAS_PYPDF, "needs pypdf")
    def test_image_only_and_damaged_pdfs(self):
        from pypdf import PdfWriter
        with tempfile.TemporaryDirectory() as tmp:
            blank = Path(tmp) / "scan.pdf"
            writer = PdfWriter()
            for _ in range(3):
                writer.add_blank_page(width=612, height=792)
            with open(blank, "wb") as f:
                writer.write(f)
            result = self.cli(blank)
            self.assertEqual(result.returncode, 1)
            self.assertIn("pages 3\nno text layer found", result.stdout)
            self.assertIn("ask the student for the cover-page facts", result.stdout)
            self.assertNotIn("questions found", result.stdout)
            broken = Path(tmp) / "broken.pdf"
            broken.write_bytes(b"not a pdf at all")
            result = self.cli(broken)
            self.assertEqual(result.returncode, 1)
            self.assertIn("could not read broken.pdf as a PDF", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    @unittest.skipUnless(HAS_PYPDF and EVAL_PDF.exists(), "needs pypdf and the eval sample")
    def test_damaged_pdfs_leak_nothing_on_stdout_or_stderr(self):
        # pypdf logs raw bytes from a bad header or a broken object; neither stream may carry them
        src = EVAL_PDF.read_bytes()
        planted = b" /MARKWORD (MARKLEAK zephyr) ]]] "
        obj = re.search(rb"\n\d+ 0 obj\s*<<", src).end()
        damaged = {
            "header.pdf": b"MARKHEAD zephyr\n" + src,
            "header-only.pdf": b"MARKHEAD zephyr\n",
            "object.pdf": src[:obj] + planted + src[obj:],
            "xref.pdf": re.sub(rb"startxref\s+\d+", b"startxref\n99999999", src),
        }
        error_line = re.compile(r"count_exam\.py: could not read [\w.-]+ as a PDF \(\w+\)")
        with tempfile.TemporaryDirectory() as tmp:
            for name, data in damaged.items():
                with self.subTest(file=name):
                    path = Path(tmp) / name
                    path.write_bytes(data)
                    result = self.cli(path)
                    for stream in (result.stdout, result.stderr):
                        self.assertNotIn("MARK", stream)
                        self.assertNotIn("zephyr", stream)
                    for line in filter(None, result.stderr.splitlines()):
                        self.assertRegex(line, error_line)
                    words = re.findall(r"[^\W\d_]+", LABEL.sub(" ", result.stdout))
                    self.assertEqual(sorted(set(words) - ALLOWED), [])


if __name__ == "__main__":
    unittest.main()
