"""Regression tests for skills/study-guide/scripts/count_exam.py. Run from the repo root:

    python3 -m unittest discover -s tests

Each case is fictional exam text fed straight to analyze(), so no PDF is needed. MARK words stand for
question content: they must never appear in the report.
"""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("count_exam", ROOT / "skills/study-guide/scripts/count_exam.py")
ce = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ce)

COVER = "Sample Midterm\nTime: 50 minutes.\nPart A: 4 multiple choice questions, 2 points each (8 points).\nPart B: 1 short answer, 10 points.\n"


def run(*pages):
    res = ce.analyze(list(pages))
    return res, ce.report(res)


class CoverInstructions(unittest.TestCase):
    def test_scenario_minutes_are_not_the_time_limit(self):
        res, out = run(COVER, "Questions 1–2 refer to this scenario. MARKA ran for 17 minutes every day.\n"
                              "1. MARKB what is it?\nA. x\nB. y\n2. MARKC why?\nA. x\nB. y")
        self.assertEqual(res["cover"]["time"], ["50 minutes"])
        self.assertNotIn("17", out)

    def test_story_before_question_one_without_a_header_is_ignored(self):
        res, _ = run("A runner MARKA trained for 17 minutes and scored 9 points.\n1. MARKB how fast?\nA. x\nB. y")
        self.assertEqual(res["cover"]["time"], [])
        self.assertEqual(res["cover"]["points"], [])

    def test_no_cheat_sheet_is_not_read_as_allowed(self):
        res, _ = run("Exam rules\nNo cheat sheet allowed.\n1. MARKA?\nA. x\nB. y")
        self.assertEqual(res["cover"]["rules"]["notes"], "no notes or note sheet")

    def test_no_calculators_allowed_is_only_negative(self):
        res, out = run("Rules: No calculators allowed.\n1. MARKA?\nA. x\nB. y")
        self.assertEqual(res["cover"]["rules"]["calculator"], "no calculator")
        self.assertNotIn("calculator allowed", out)

    def test_note_sheet_allowed(self):
        res, _ = run("One handwritten note sheet is allowed. Calculators are permitted.\n1. MARKA?\nA. x\nB. y")
        self.assertEqual(res["cover"]["rules"]["notes"], "notes or a note sheet allowed")
        self.assertEqual(res["cover"]["rules"]["calculator"], "calculator allowed")


class Questions(unittest.TestCase):
    def test_question_line_citing_a_range_is_still_counted(self):
        res, _ = run(COVER, "1. MARKA?\nA. x\nB. y\n2. MARKB?\nA. x\nB. y\n3. Using your answers to Questions 1–2, compute MARKC.")
        self.assertEqual(res["order"], [1, 2, 3])
        self.assertEqual(res["ranges"], [])
        self.assertEqual(res["backrefs"], [3])

    def test_reference_inside_a_question_keeps_its_options(self):
        res, _ = run(COVER, "4. MARKA, as in Questions 1–2 above,\nwhat is MARKB?\nA. x\nB. y\nC. z\nD. w")
        self.assertEqual(res["questions"][4]["opts"], 4)
        self.assertEqual(res["ranges"], [])

    def test_scenario_header_and_back_reference(self):
        res, _ = run(COVER, "Questions 5–8 refer to this scenario. MARKS market.\n5. MARKA?\nA. x\n"
                            "8. MARKB?\nA. x\n13. (8 points) Using the MARKS equations, find MARKC.")
        self.assertEqual(res["ranges"], [(2, 5, 8)])
        self.assertEqual(res["backrefs"], [13])
        self.assertEqual(res["questions"][13]["points"], 8)

    def test_points_inside_a_question_are_not_reported(self):
        res, out = run("5. If a MARKA score rises by 37 points, what happens?\nA. x\nB. y")
        self.assertIsNone(res["questions"][5]["points"])
        self.assertNotIn("37", out)

    def test_no_question_text_in_report(self):
        _, out = run(COVER, "Questions 1–2 refer to this scenario. MARKS bakery.\n1. MARKA?\nA. MARKO1\nB. MARKO2\n"
                            "2. MARKB?\nA. MARKO3\nB. MARKO4\n3. (10 points) From the scenario above, MARKC.")
        self.assertNotIn("MARK", out)


class FictionalSample(unittest.TestCase):
    PDF = ROOT / "evals/measures-sample-exam-unseen/files/sample_midterm.pdf"

    @unittest.skipUnless(PDF.exists() and importlib.util.find_spec("pypdf"), "needs pypdf and the eval sample")
    def test_econ_sample(self):
        from pypdf import PdfReader
        res, out = run(*[p.extract_text() or "" for p in PdfReader(self.PDF).pages])
        self.assertEqual(len(res["questions"]), 14)
        self.assertEqual([res["questions"][n]["opts"] for n in range(1, 15)], [4] * 12 + [0, 0])
        self.assertEqual([(a, b) for _, a, b in res["ranges"]], [(5, 8)])
        self.assertEqual(res["backrefs"], [13])
        self.assertEqual(res["cover"]["time"], ["50 minutes"])
        self.assertEqual(res["cover"]["rules"].get("calculator"), "no calculator")
        for word in ["marzipan", "thistlewood", "quokka", "zephyr", "saffron", "obsidian", "lantern", "pumice", "kelp", "walrus", "juniper", "gondola"]:
            self.assertNotIn(word, out.lower())


if __name__ == "__main__":
    unittest.main()
