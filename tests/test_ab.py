"""The A/B eval runner (evals/ab.py): setting up runs and reading their event streams, without running Claude."""
import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('study_ab', ROOT / 'evals/ab.py')
ab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ab)


def run(*args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            with mock.patch.object(sys, 'argv', ['ab.py', *map(str, args)]):
                ab.main()
            code = 0
        except SystemExit as e:
            code = e.code
    return code, out.getvalue()


class Prepare(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name) / 'out'

    def test_git_refs_and_paths_set_up_one_skill_per_run(self):
        skill = ROOT / 'skills/study-guide'
        code, log = run('run', self.out, '--config', 'A=git:HEAD', '--config', f'B={skill}', '--runs', '2', '--prepare-only')
        self.assertEqual(code, 0, log)
        self.assertEqual(sorted(p.name for p in self.out.iterdir()), ['A-1', 'A-2', 'B-1', 'B-2', 'meta.json', 'skills'])
        for name in ('A-1', 'B-2'):
            run_dir = self.out / name
            self.assertTrue((run_dir / '.claude/skills/study-guide/SKILL.md').exists())
            self.assertFalse(list(run_dir.rglob('__pycache__')))
            self.assertEqual(sorted(p.name for p in (run_dir / 'slides').iterdir()),
                             ['L01-supply-and-demand.pdf', 'L02-elasticity.pdf'])
        meta = json.loads((self.out / 'meta.json').read_text(encoding='utf-8'))
        self.assertRegex(meta['configs']['A'], r'^git HEAD at [0-9a-f]{7}$')
        self.assertEqual(meta['configs']['B'], str(skill))
        self.assertTrue(meta['prompt'].endswith('Use the study-guide skill.'))
        self.assertNotIn('---', meta['prompt'])

    def test_bad_configs_and_places_are_refused(self):
        for args, words in ((['--config', 'A1=git:HEAD'], 'letters only'),
                            (['--config', 'A=git:no-such-ref-here'], 'not a branch, tag or commit'),
                            (['--config', f'A={ROOT}'], 'has no SKILL.md')):
            with self.subTest(words=words):
                code, _ = run('run', Path(self.tmp.name) / words.replace(' ', '-'), *args, '--prepare-only')
                self.assertIn(words, str(code))
        code, _ = run('run', ROOT / 'evals/out', '--config', 'A=git:HEAD', '--prepare-only')
        self.assertIn('outside the repository', str(code))


class Grading(unittest.TestCase):
    """grade never runs on missing material and never reports a failed grader as done; no Claude is called."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name) / 'out'
        (self.out / 'grade/A-1').mkdir(parents=True)
        (self.out / 'grade/A-1/notes.md').write_text('notes', encoding='utf-8')
        (self.out / 'meta.json').write_text(json.dumps({'case': 'builds-page-from-slides', 'runs': 1, 'prompt': 'p'}),
                                            encoding='utf-8')

    def test_slides_are_read_page_by_page(self):
        try:
            import pypdf  # noqa: F401
        except ImportError:
            self.skipTest('needs pypdf')
        text = ab.slides_text(ROOT / 'evals/builds-page-from-slides/files/slides')
        self.assertIn('=== L01-supply-and-demand.pdf p.5\n', text)
        self.assertIn('=== L02-elasticity.pdf p.8\n', text)

    def test_unreadable_slides_stop_before_any_grader(self):
        folder = Path(self.tmp.name) / 'slides'
        folder.mkdir()
        for setup, words in ((lambda: None, 'no slide PDFs'),
                             (lambda: (folder / 'L1.pdf').write_bytes(b'not a pdf'), 'cannot read L1.pdf')):
            with self.subTest(words=words):
                setup()
                if words != 'no slide PDFs':
                    try:
                        import pypdf  # noqa: F401
                    except ImportError:
                        self.skipTest('needs pypdf')
                with self.assertRaises(SystemExit) as e:
                    ab.slides_text(folder)
                self.assertIn(words, str(e.exception.code))
        with mock.patch.dict(sys.modules, {'pypdf': None}), self.assertRaises(SystemExit) as e:
            ab.slides_text(folder)
        self.assertIn('needs pypdf', str(e.exception.code))
        with mock.patch.object(ab, 'slides_text', side_effect=SystemExit('cannot read L1.pdf')), \
                mock.patch.object(ab, 'claude') as grader:
            code, _ = run('grade', self.out)
        self.assertIn('cannot read', str(code))
        grader.assert_not_called()
        self.assertFalse((self.out / 'grade/A-1/slides.txt').exists())

    def grade_with(self, fake):
        with mock.patch.object(ab, 'slides_text', return_value='=== s.pdf p.1\ntext\n'), \
                mock.patch.object(ab.subprocess, 'run', side_effect=fake):
            return run('grade', self.out)

    def test_a_failed_or_incomplete_grader_is_reported_with_its_error(self):
        cases = (
            (lambda cmd, cwd, **kw: subprocess.CompletedProcess(cmd, 1, '', 'rate limited'), 'exited with 1: rate limited'),
            (lambda cmd, cwd, **kw: subprocess.CompletedProcess(cmd, 0, '{"total_cost_usd": 0.4}', ''), 'wrote no grade.json'),
            (writes('grade.json', '{"A": '), 'not valid JSON'),
            (writes('grade.json', {'A': 1}), "'A' needs a true/false 'pass'"))
        cases += tuple((writes('grade.json', grade), words) for grade, words in INCOMPLETE_GRADES)
        for fake, words in cases:
            with self.subTest(words=words):
                code, log = self.grade_with(fake)
                self.assertIn('1 grader(s) failed', str(code))
                self.assertIn('FAILED A-1: ', log)
                self.assertIn(words, log)
                self.assertNotIn('graded A-1', log)
                self.assertIn(words, (self.out / 'grade/A-1/grade.json.error.txt').read_text(encoding='utf-8'))
                self.assertFalse((self.out / 'grade/A-1/grade.json').exists())  # renamed, so a later run retries it
        code, log = self.grade_with(writes('grade.json', GOOD_GRADE, cost=0.4))
        self.assertEqual((code, log.strip()), (0, 'graded A-1 ($0.40)'))
        self.assertFalse((self.out / 'grade/A-1/grade.json.error.txt').exists())  # the earlier failure is cleared
        self.assertTrue((self.out / 'grade/A-1/slides.txt').read_text(encoding='utf-8').startswith('=== s.pdf p.1'))

    def test_an_earlier_result_is_reused_only_when_complete(self):
        path = self.out / 'grade/A-1/grade.json'
        path.write_text(json.dumps(GOOD_GRADE), encoding='utf-8')
        fake = mock.Mock(side_effect=writes('grade.json', GOOD_GRADE))
        self.assertEqual(self.grade_with(fake), (0, ''))
        fake.assert_not_called()
        for grade, words in INCOMPLETE_GRADES:
            with self.subTest(words=words):
                path.write_text(json.dumps(grade), encoding='utf-8')
                fake = mock.Mock(side_effect=writes('grade.json', GOOD_GRADE))
                code, log = self.grade_with(fake)
                self.assertEqual(code, 0, log)
                self.assertIn(f'regrading A-1: its earlier grade.json was unusable ({words}', log)
                self.assertEqual(fake.call_count, 1)
                self.assertEqual(json.loads(path.read_text(encoding='utf-8')), GOOD_GRADE)
                self.assertEqual(json.loads((path.parent / 'grade.invalid.json').read_text(encoding='utf-8')), grade)

    def test_pairwise_results_need_better_margin_and_why(self):
        (self.out / 'grade/B-1').mkdir()
        (self.out / 'grade/B-1/notes.md').write_text('notes', encoding='utf-8')

        def fake(pair):
            def run_grader(cmd, cwd, **kw):
                name = 'pair.json' if Path(cwd).name.startswith('pair') else 'grade.json'
                return writes(name, pair if name == 'pair.json' else GOOD_GRADE)(cmd, cwd)
            return run_grader
        for pair, words in (({'better': 'X'}, "'margin' must be slight, clear or large"),
                            ({'better': 'X', 'margin': 'clear'}, "'why' must be a non-empty text"),
                            ({'better': 'A', 'margin': 'clear', 'why': 'w'}, "'better' must be X, Y or tie")):
            with self.subTest(words=words):
                code, log = self.grade_with(fake(pair))
                self.assertIn('1 grader(s) failed', str(code))
                self.assertIn(f'FAILED pair-1: pair.json is incomplete: {words}', log)
        code, log = self.grade_with(fake({'better': 'tie', 'margin': 'slight', 'why': 'Both teach it equally.'}))
        self.assertEqual(code, 0, log)
        self.assertIn('compared pair-1', log)
        sides = json.loads((self.out / 'grade/pair-1.sides.json').read_text(encoding='utf-8'))
        self.assertEqual(sorted(sides.values()), ['A-1', 'B-1'])
        self.assertFalse(list((self.out / 'grade/pair-1').rglob('*.error.txt')))


GOOD_GRADE = dict({k: {'pass': True, 'why': 'Checked.'} for k in 'ABCDEF'},
                  scores={'notes_clarity': 5, 'figure_value': 4, 'coverage': 5}, comments='Fine.')
INCOMPLETE_GRADES = (
    (dict(GOOD_GRADE, A={'pass': True}), "'A' needs a non-empty 'why'"),
    (dict(GOOD_GRADE, F={'pass': 'yes', 'why': 'w'}), "'F' needs a true/false 'pass'"),
    (dict(GOOD_GRADE, scores={}), "'scores' must have exactly"),
    (dict(GOOD_GRADE, scores={'notes_clarity': 5}), "'scores' must have exactly"),
    (dict(GOOD_GRADE, scores=dict(GOOD_GRADE['scores'], coverage=6)), "'scores.coverage' must be a whole number from 1 to 5"),
    (dict(GOOD_GRADE, scores=dict(GOOD_GRADE['scores'], coverage=4.5)), "'scores.coverage' must be a whole number"),
    (dict(GOOD_GRADE, scores=dict(GOOD_GRADE['scores'], notes_clarity=True)), "'scores.notes_clarity' must be a whole"),
    ({k: v for k, v in GOOD_GRADE.items() if k != 'comments'}, "'comments' must be a non-empty text"),
)


def writes(name, content, cost=0.4):
    """A stand-in for the claude process that writes name (a dict as JSON, or raw text) into its folder."""
    def run_grader(cmd, cwd, **kw):
        body = content if isinstance(content, str) else json.dumps(content)
        Path(cwd, name).write_text(body, encoding='utf-8')
        return subprocess.CompletedProcess(cmd, 0, json.dumps({'total_cost_usd': cost}), '')
    return run_grader


class Metrics(unittest.TestCase):
    def test_counts_builds_writes_reads_and_usage(self):
        skill = '/x/run/.claude/skills/study-guide/'

        def use(i, name, inp):
            return {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'id': i, 'name': name, 'input': inp}]}}

        def result(i, text, error=False):
            return {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'tool_use_id': i, 'is_error': error,
                                                             'content': [{'type': 'text', 'text': text}]}]}}
        events = [
            use('1', 'Read', {'file_path': skill + 'references/content-standard.md'}),
            use('2', 'Write', {'file_path': '/x/run/c/sections/10-l1.md', 'content': 'abcd'}),
            use('3', 'Edit', {'file_path': '/x/run/c/practice.json', 'old_string': 'ab', 'new_string': 'abc'}),
            use('4', 'Bash', {'command': f'python3 {skill}scripts/build.py --init c'}), result('4', 'copied'),
            use('5', 'Bash', {'command': 'python3 build.py c'}), result('5', 'error: x\n1 error(s); nothing written.'),
            use('6', 'Bash', {'command': 'python3 build.py c --strict'}), result('6', 'warning: y\nwrote c/review.html'),
            use('7', 'Bash', {'command': 'python3 build.py c'}), result('7', 'wrote c/review.html (1 KB; 0 warning(s))'),
            {'type': 'result', 'subtype': 'success', 'total_cost_usd': 1.5, 'duration_ms': 61000, 'num_turns': 9,
             'usage': {'output_tokens': 1200, 'input_tokens': 10, 'cache_read_input_tokens': 900}},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / 'A-1.jsonl'
            log.write_text('\n'.join(json.dumps(e) for e in events) + '\nnot json\n', encoding='utf-8')
            m = ab.metrics(log)
        self.assertEqual((m['builds'], m['builds_failed'], m['builds_warned']), (3, 1, 1))
        self.assertEqual(m['written'], {'sections': 4, 'banks': 5})
        self.assertEqual(m['reads'], ['references/content-standard.md'])
        self.assertEqual((m['cost'], m['seconds'], m['turns'], m['output_tokens'], m['cache_read']), (1.5, 61, 9, 1200, 900))


if __name__ == '__main__':
    unittest.main()
