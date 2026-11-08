"""The A/B eval runner (evals/ab.py): setting up runs and reading their event streams, without running Claude."""
import contextlib
import importlib.util
import io
import json
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
