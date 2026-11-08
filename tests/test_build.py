"""Small, fictional courses only; all writes and CLI output live in TemporaryDirectory."""
import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/study-guide/scripts/build.py'
spec = importlib.util.spec_from_file_location('study_build', SCRIPT)
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
DEMO = b.EXAMPLE


def choice(qid='q1', **kw):
    return dict({'id': qid, 'g': 'g', 'stem': 'Pick a value.', 'opts': [
        {'t': 'one', 'why': 'First value.'}, {'t': 'two', 'why': 'Second value.'}], 'ans': 0}, **kw)


def fixture():
    return {'course': {'title': 'Fictional test', 'storageKey': 'test.exam-1_0', 'lectures': ['L1']},
            'practice': {'groups': [{'id': 'g', 'lec': 'L1', 'sec': 'l1', 'title': 'Values'}],
                         'items': [choice()]},
            'mock': {'groups': [{'id': 'm', 'lec': 'L1'}],
                     'items': [choice('m1', g='m', stem='Select the other value.')]},
            'short': {'groups': [{'id': 's', 'g': 'g', 'kind': 'Values'}],
                      'items': [{'id': 's1', 'k': 's', 'stem': 'Work in steps.', 'steps': [
                          {'ask': 'Value?', 'pts': 2, 'accept': ['1'], 'sol': 'one'},
                          {'ask': 'Pick?', 'pts': 1, 'opts': ['one', 'two'], 'ans': 0, 'sol': 'one'},
                          {'ask': 'Explain?', 'pts': 3, 'sol': 'A self check.'}]}]}}


class CourseCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.course = Path(self.tmp.name) / 'course'
        self.course.mkdir()
        (self.course / 'sections').mkdir()
        (self.course / 'sections/10-main.html').write_text(
            '<section id="l1"><h2>Test &amp; values</h2></section>', encoding='utf-8')
        self.data = fixture()

    def write(self):
        for name in ('course', 'practice', 'mock', 'short'):
            p = self.course / (name + '.json')
            if name in self.data:
                p.write_text(json.dumps(self.data[name], ensure_ascii=False), encoding='utf-8')
            elif p.exists():
                p.unlink()

    def check(self):
        self.write()
        return b.check(self.course)[0]

    def invalid(self, word):
        rep = self.check()
        self.assertTrue(rep.errors, f'expected error containing {word!r}')
        self.assertIn(word, '\n'.join(rep.errors))
        # A diagnostic must also stop output and preserve any previous build.
        out = self.course / 'review.html'
        out.write_text('previous output', encoding='utf-8')
        with contextlib.redirect_stdout(io.StringIO()) as log:
            self.assertEqual(b.build(self.course, out), 1)
        self.assertIn('error:', log.getvalue())
        self.assertNotIn('Traceback', log.getvalue())
        self.assertEqual(out.read_text(encoding='utf-8'), 'previous output')

    def cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], cwd=ROOT,
                              capture_output=True, text=True, encoding='utf-8')


class DataRules(CourseCase):
    def test_minimal_course_and_default_language(self):
        self.data = {'course': {'title': '小测试', 'storageKey': 'x'},
                     'practice': {'groups': [], 'items': []}}
        self.assertEqual(self.check().errors, [])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(b.build(self.course, self.course / 'review.html'), 0)
        self.assertIn('<html lang="zh-CN">', (self.course / 'review.html').read_text(encoding='utf-8'))

    def test_missing_required_files_and_empty_sections(self):
        self.write()
        for name in ('course.json', 'practice.json'):
            with self.subTest(name=name):
                old = (self.course / name).read_bytes()
                (self.course / name).unlink()
                self.assertIn(name + ' is missing', b.check(self.course)[0].errors)
                (self.course / name).write_bytes(old)
        (self.course / 'sections/10-main.html').unlink()
        self.invalid('sections/')

    def test_invalid_json_reports_filename_line_column(self):
        self.write()
        for name in self.data:
            with self.subTest(name=name):
                p = self.course / (name + '.json')
                old = p.read_bytes()
                p.write_text('{\n  "bad": }', encoding='utf-8')
                self.assertRegex('\n'.join(b.check(self.course)[0].errors),
                                 name + r'.json: invalid JSON at line 2 col \d+')
                p.write_bytes(old)

    def test_required_config_fields(self):
        for field in ('title', 'storageKey'):
            for value in (None, '', 4, [], {}):
                with self.subTest(field=field, value=value):
                    self.data = fixture()
                    self.data['course'][field] = value
                    self.invalid(field)
            self.data = fixture()
            del self.data['course'][field]
            self.invalid(field)

    def test_config_types(self):
        cases = [('lang', 'fr'), ('lang', []), ('storageKey', 'with space'),
                 ('storageKey', '中文'), ('lectures', 'L1'), ('lectures', [3]),
                 ('tfLabels', ['yes']), ('tfLabels', [True, False]),
                 ('practiceIntro', []), ('shortIntro', 1), ('footer', {})]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                self.data = fixture()
                self.data['course'][field] = value
                self.invalid(field)

    def test_root_and_container_types(self):
        for name in ('course', 'practice', 'mock', 'short'):
            for value in ([], 'bad', 3, None):
                with self.subTest(name=name, value=value):
                    self.data = fixture()
                    self.data[name] = value
                    self.invalid(name + '.json')
        for bank in ('practice', 'mock', 'short'):
            for field in ('groups', 'items'):
                for value in (None, {}, 'bad', [None], [3]):
                    with self.subTest(bank=bank, field=field, value=value):
                        self.data = fixture()
                        self.data[bank][field] = value
                        self.invalid(field)

    def test_group_ids_references_and_overrides(self):
        for bank in ('practice', 'mock', 'short'):
            for value in ('', None, 5, []):
                with self.subTest(bank=bank, id=value):
                    self.data = fixture()
                    self.data[bank]['groups'][0]['id'] = value
                    self.invalid('id')
            self.data = fixture()
            self.data[bank]['groups'] *= 2
            self.invalid('duplicate group id')
            self.data = fixture()
            self.data[bank]['groups'][0]['lec'] = 'L9'
            self.invalid('lectures')
            self.data = fixture()
            item = self.data[bank]['items'][0]
            item['k' if bank == 'short' else 'g'] = 'missing'
            self.invalid('not defined')
        for bank in ('practice', 'mock', 'short'):
            self.data = fixture()
            self.data[bank]['items'][0]['lec'] = 'L9'
            self.invalid('lectures')
        self.data = fixture()
        self.data['short']['groups'][0]['g'] = 'missing'
        self.invalid('links practice group')

    def test_missing_sections_are_warnings(self):
        for bank in ('practice', 'short'):
            with self.subTest(bank=bank):
                self.data = fixture()
                self.data[bank]['groups'][0]['sec'] = 'missing'
                rep = self.check()
                self.assertEqual(rep.errors, [])
                self.assertIn('missing', '\n'.join(rep.warnings))

    def test_global_question_ids(self):
        for bank in ('practice', 'mock', 'short'):
            for value in ('', None, 2, []):
                with self.subTest(bank=bank, id=value):
                    self.data = fixture()
                    self.data[bank]['items'][0]['id'] = value
                    self.invalid('id')
            self.data = fixture()
            self.data[bank]['items'] *= 2
            self.invalid('id already used')
        for left, right in (('practice', 'mock'), ('practice', 'short'), ('mock', 'short')):
            self.data = fixture()
            self.data[right]['items'][0]['id'] = self.data[left]['items'][0]['id']
            self.invalid('id already used')

    def test_question_types_stems_options_answers(self):
        for bank in ('practice', 'mock'):
            cases = [({'type': 'essay'}, 'unknown type'), ({'stem': ''}, 'stem'),
                     ({'opts': None}, 'options'), ({'opts': []}, 'options'),
                     ({'opts': ['one']}, 'options'), ({'opts': ['x'] * 9}, 'options'),
                     ({'opts': [{}, {'t': 'two'}]}, "text 't'"),
                     ({'opts': [4, 'two']}, 'option'),
                     ({'type': 'tf', 'opts': [{}, {}, {}]}, 'exactly 2'),
                     ({'type': 'fill', 'accept': []}, 'accept'),
                     ({'type': 'fill', 'accept': '1'}, 'accept'),
                     ({'type': 'card', 'answer': ''}, 'answer')]
            for patch, message in cases:
                with self.subTest(bank=bank, patch=patch):
                    self.data = fixture()
                    self.data[bank]['items'][0].update(patch)
                    self.invalid(message)
            for typ in ('single', 'tf', 'multi'):
                bad = (None, -1, 2, 0.5, True, '0') if typ != 'multi' else (
                    None, [], 0, [0, 0], [-1], [2], [True], ['0'], [[0]])
                for ans in bad:
                    with self.subTest(bank=bank, type=typ, ans=ans):
                        self.data = fixture()
                        self.data[bank]['items'][0].update(type=typ, ans=ans)
                        self.invalid('ans')

    def test_valid_question_kinds_and_html(self):
        self.data['practice']['items'] = [choice('a'), choice('b', type='tf', opts=[{}, {}]),
            choice('c', type='multi', ans=[0, 1]),
            {'id': 'd', 'g': 'g', 'type': 'fill', 'stem': '<b>数值</b>', 'accept': ['1/2', 0.5], 'answer': '½'},
            {'id': 'e', 'g': 'g', 'type': 'card', 'stem': 'Recall.', 'answer': '<sup>2</sup>'}]
        self.data['practice']['items'][0]['opts'] = ['one', 'two']
        self.assertEqual(self.check().errors, [])
        self.data['practice']['items'][1].pop('opts')
        self.assertEqual(self.check().errors, [])

    def test_show_and_fixed(self):
        for patch in ({'show': 'Z'}, {'show': 'AB'}, {'show': 0},
                      {'type': 'multi', 'ans': [0], 'show': 'B'}, {'fixed': 'false'}):
            with self.subTest(patch=patch):
                self.data = fixture()
                self.data['practice']['items'][0].update(patch)
                self.invalid('fixed' if 'fixed' in patch else 'show')
        self.data = fixture()
        self.data['practice']['items'][0].update(show='b', fixed=True)
        self.assertEqual(self.check().errors, [])

    def test_short_steps(self):
        for patch, message in [({'steps': []}, 'steps'), ({'steps': 'bad'}, 'steps'),
                               ({'steps': [None]}, 'steps')]:
            self.data = fixture()
            self.data['short']['items'][0].update(patch)
            self.invalid(message)
        for patch, message in [({'ask': ''}, 'ask'), ({'sol': ''}, 'sol'),
                               ({'accept': []}, 'accept'), ({'accept': '1'}, 'accept'),
                               ({'pts': -1}, 'pts'), ({'pts': '2'}, 'pts')]:
            self.data = fixture()
            self.data['short']['items'][0]['steps'][0].update(patch)
            self.invalid(message)
        for ans in (None, -1, 2, True, '0', 0.5):
            self.data = fixture()
            self.data['short']['items'][0]['steps'][1]['ans'] = ans
            self.invalid('ans')

    def test_mock_configuration_even_without_pool(self):
        cases = [({'sections': [{'cat': 'essay', 'n': 1}]}, 'cat'),
                 ({'sections': 'bad'}, 'sections'), ({'sections': [None]}, 'sections'),
                 ({'sections': [{'cat': 'tf', 'n': -1}]}, 'n'),
                 ({'sections': [{'cat': 'tf', 'n': True}]}, 'n'),
                 ({'sections': [{'cat': 'tf', 'n': '2'}]}, 'n'),
                 ({'minutes': []}, 'minutes'), ({'minutes': ['45']}, 'minutes'),
                 ({'minutes': [-1]}, 'minutes'), ({'minutes': [True]}, 'minutes'),
                 ({'minutes': [{}]}, 'minutes'), ({'defaultMinutes': -1}, 'defaultMinutes'),
                 ({'weights': {'L1': -1}}, 'weights'), ({'weights': {'L1': '2'}}, 'weights'),
                 ({'note': []}, 'note')]
        for cfg, message in cases:
            for has_pool in (True, False):
                with self.subTest(cfg=cfg, pool=has_pool):
                    self.data = fixture()
                    if not has_pool:
                        del self.data['mock']
                    self.data['course']['mock'] = cfg
                    self.invalid(message)

    def test_mock_pool_and_citation_policies(self):
        # Citations are optional HTML text shown in the meta line, not parsed slide references.
        for src in ('', 'Fictional L1 p.2', '<b>Source</b>'):
            self.data['practice']['items'][0]['src'] = src
            self.assertEqual(self.check().errors, [])
        for src in (None, 5, [], {}):
            with self.subTest(src=src):
                self.data = fixture()
                self.data['mock']['items'][0]['src'] = src
                self.invalid('src')
        self.data = fixture()
        self.data['course']['mock'] = {'sections': [{'cat': 'single', 'n': 2}], 'weights': {'L2': 1}}
        warnings = '\n'.join(self.check().warnings)
        self.assertIn('wants 2 questions but the pool has 1', warnings)
        self.assertIn('weights give no share', warnings)
        self.data['course']['mock']['sections'][0]['n'] = 1
        self.assertIn('about 2x', '\n'.join(self.check().warnings))

    def test_documented_ambiguities_remain_characterized(self):
        # The reference says practice-only cards and fill answer HTML, but the engine
        # explicitly skips mock cards and falls back to accept[0]; don't choose policy here.
        self.data['mock']['items'] = [{'id': 'mc', 'g': 'm', 'type': 'card', 'stem': 'Recall', 'answer': 'one'}]
        self.data['practice']['items'] = [{'id': 'f', 'g': 'g', 'type': 'fill', 'stem': 'Value?', 'accept': ['1']}]
        rep = self.check()
        self.assertEqual(rep.errors, [])
        self.assertIn('flashcards are skipped', '\n'.join(rep.warnings))

    def test_empty_mock_sections_is_an_error_and_zero_sections_are_dropped(self):
        self.data['course']['mock'] = {'sections': []}
        self.invalid('mock.sections is empty')
        self.assertIn('delete the key', '\n'.join(self.check().errors))
        self.assertEqual(self.check().warnings, [])
        # the engine drops n: 0 sections, so their pools are not audited
        self.data = fixture()
        self.data['course'].update(lectures=['L1', 'L2'], mock={
            'sections': [{'cat': 'tf', 'n': 0}, {'cat': 'single', 'n': 1}], 'weights': {'L1': 1}})
        self.data['mock']['groups'].append({'id': 'm2', 'lec': 'L2'})
        self.data['mock']['items'] += [choice('m-tf', g='m2', type='tf', stem='A claim.'), choice('m-2', g='m', stem='Other value.')]
        rep = self.check()
        self.assertEqual(rep.errors, [])
        self.assertEqual(rep.warnings, [])

    def test_a_mock_layout_with_only_zero_sections_is_an_error(self):
        # one type may be 0, but the paper as a whole must ask something
        self.data['course']['mock'] = {'sections': [{'cat': 'tf', 'n': 0}, {'cat': 'single', 'n': 0}]}
        self.invalid('every mock section has n: 0')
        self.assertIn("at least one section's n must be greater than 0", '\n'.join(self.check().errors))
        self.data = fixture()
        self.data['course']['mock'] = {'sections': [{'cat': 'tf', 'n': 0}, {'cat': 'single', 'n': 1}]}
        self.assertEqual(self.check().errors, [])

    def test_mock_items_need_a_lecture(self):
        del self.data['mock']['groups'][0]['lec']
        self.invalid("needs a 'lec'")
        self.data['mock']['items'][0]['lec'] = 'L1'
        self.assertEqual(self.check().errors, [])
        # practice items may leave the lecture out
        self.data = fixture()
        del self.data['practice']['groups'][0]['lec']
        self.assertEqual(self.check().errors, [])

    def test_short_group_without_id_is_reported_with_its_items(self):
        for gid in (None, ''):
            with self.subTest(id=gid):
                self.data = fixture()
                group = self.data['short']['groups'][0]
                group.pop('id') if gid is None else group.update(id=gid)
                errors = '\n'.join(self.check().errors)
                self.assertIn('short: a group has no id', errors)
                self.assertIn("short item 's1': group 's' is not defined", errors)
                self.data['short']['items'][0]['k'] = gid
                if gid is None:
                    self.data['short']['items'][0].pop('k')
                self.invalid("short item 's1': needs 'k'")

    def test_one_run_reports_errors_from_every_independent_file(self):
        self.data['practice']['items'][0]['ans'] = 5
        self.data['short']['items'][0]['stem'] = ''
        self.write()
        (self.course / 'mock.json').write_text('{"groups": [}', encoding='utf-8')
        errors = '\n'.join(b.check(self.course)[0].errors)
        self.assertIn('mock.json: invalid JSON', errors)
        self.assertIn("practice item 'q1': 'ans'", errors)
        self.assertIn("short item 's1': empty stem", errors)
        # a broken course.json still lets the banks be checked
        self.data['course']['lang'] = []
        self.write()
        errors = '\n'.join(b.check(self.course)[0].errors)
        self.assertIn("'lang' must be str", errors)
        self.assertIn("practice item 'q1': 'ans'", errors)
        # a file whose structure is broken is not checked any further
        self.data = fixture()
        self.data['practice']['groups'] = 'bad'
        self.data['practice']['items'][0]['ans'] = 5
        self.write()
        errors = b.check(self.course)[0].errors
        self.assertIn('practice.json: groups must be a list of objects', errors)
        self.assertNotIn("'ans'", '\n'.join(errors))
        self.assertNotIn('links practice group', '\n'.join(errors))

    def test_a_malformed_item_next_to_a_broken_file_is_reported_not_crashed_on(self):
        # once one file is broken the build keeps checking the others, so the audits must never see an item
        # whose options or answer failed validation (e.g. "opts": 7 used to raise TypeError in audit())
        for opts in (7, {'a': 1}, 'ab'):
            with self.subTest(opts=opts):
                self.data = fixture()
                self.data['practice']['items'][0]['opts'] = opts
                self.write()
                (self.course / 'mock.json').write_text('{"groups": [}', encoding='utf-8')
                result = self.cli(self.course)
                self.assertEqual(result.returncode, 1)
                self.assertNotIn('Traceback', result.stderr + result.stdout)
                out = result.stderr + result.stdout
                self.assertIn('mock.json: invalid JSON', out)
                self.assertIn("practice item 'q1': needs at least 2 options", out)

    def test_json_with_a_byte_order_mark_is_accepted(self):
        self.write()
        for name in ('course', 'practice', 'mock', 'short'):
            p = self.course / (name + '.json')
            p.write_bytes(b'\xef\xbb\xbf' + p.read_bytes())
        (self.course / 'sections/10-main.html').write_bytes(
            b'\xef\xbb\xbf' + (self.course / 'sections/10-main.html').read_bytes())
        self.assertEqual(b.check(self.course)[0].errors, [])
        self.assertEqual(self.cli(self.course).returncode, 0)
        self.assertNotIn('\ufeff', (self.course / 'review.html').read_text(encoding='utf-8'))


class BuildOutput(CourseCase):
    def test_embeds_assets_data_sorted_sections_and_escapes_script_close(self):
        self.data['course'].update(title='<Fictional & title>', footer='<b>footer</b>', lang='en')
        self.data['practice']['items'][0]['stem'] = '“数值” </script><script>bad()</script> <!--<script>'
        (self.course / 'sections/00-first.html').write_text('<header id="exam">FIRST</header>', encoding='utf-8')
        (self.course / 'extra.css').write_text('/* extra css */', encoding='utf-8')
        (self.course / 'extra.js').write_text('/* extra js */', encoding='utf-8')
        self.write()
        out = self.course / 'review.html'
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(b.build(self.course, out), 0)
        page = out.read_text(encoding='utf-8')
        self.assertIn((b.ASSETS / 'engine.js').read_text(encoding='utf-8'), page)
        self.assertIn((b.ASSETS / 'page.css').read_text(encoding='utf-8'), page)
        self.assertIn('/* extra css */', page)
        self.assertIn('/* extra js */', page)
        self.assertIn('<title>&lt;Fictional &amp; title&gt;</title>', page)
        self.assertIn('<footer><b>footer</b></footer>', page)
        self.assertLess(page.index('FIRST'), page.index('<section id="l1">'))
        self.assertEqual(page.count('id="practice"'), 1)
        self.assertNotRegex(page, r'(?:src|href)="(?:[^"\n]*/)?(?:engine.js|page.css)"')
        blob = re.search(r'window.STUDY_DATA = (.*?);</script>', page).group(1)
        self.assertNotIn('<', blob)
        self.assertEqual(json.loads(blob), dict(config=self.data['course'],
            **{k: self.data[k] for k in ('practice', 'mock', 'short')}))
        self.assertNotIn('tex-svg-full', page)
        self.data['practice']['items'][0]['stem'] = "<span data-tex='x'>x</span>"
        self.write()
        with contextlib.redirect_stdout(io.StringIO()):
            b.build(self.course, out)
        self.assertIn('tex-svg-full', out.read_text(encoding='utf-8'))
        # a formula only in the notes loads MathJax too
        self.data = fixture()
        self.write()
        (self.course / 'sections/20-tex.html').write_text("<section id=\"l2\"><span data-tex='x^2'>x</span></section>", encoding='utf-8')
        with contextlib.redirect_stdout(io.StringIO()):
            b.build(self.course, out)
        self.assertIn('tex-svg-full', out.read_text(encoding='utf-8'))

    def test_existing_practice_anchor_is_not_duplicated(self):
        (self.course / 'sections/90-practice.html').write_text('<section id="practice"></section>', encoding='utf-8')
        self.write()
        self.assertEqual(self.cli(self.course).returncode, 0)
        self.assertEqual((self.course / 'review.html').read_text(encoding='utf-8').count('id="practice"'), 1)

    def test_cli_check_writes_nothing_and_a_missing_folder_fails(self):
        # --out and errors on the CLI: test_out_path_in_a_new_folder_and_unwritable_out, test_strict_exit_codes
        self.write()
        checked = self.cli(self.course, '--check')
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        self.assertFalse((self.course / 'review.html').exists())
        self.assertEqual(self.cli(self.course / 'absent').returncode, 1)

    def test_init_new_empty_and_refuses_nonempty(self):
        for target in (self.course / 'new', self.course / 'empty'):
            if target.name == 'empty':
                target.mkdir()
            result = self.cli('--init', target)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse((target / 'review.html').exists())
            for source in DEMO.rglob('*'):
                if source.is_file() and source.name != 'review.html':
                    self.assertEqual((target / source.relative_to(DEMO)).read_bytes(), source.read_bytes())
            before = (target / 'course.json').read_bytes()
            self.assertEqual(self.cli('--init', target).returncode, 1)
            self.assertEqual((target / 'course.json').read_bytes(), before)
            self.assertEqual(self.cli(target, '--check').returncode, 0)

    def test_init_refuses_a_file_without_traceback(self):
        target = self.course / 'existing-file'
        target.write_text('keep me', encoding='utf-8')
        result = self.cli('--init', target)
        self.assertEqual(result.returncode, 1)
        self.assertIn('not a folder', result.stdout)
        self.assertNotIn('Traceback', result.stderr)
        self.assertEqual(target.read_text(encoding='utf-8'), 'keep me')

    def test_toc_labels_markers_and_skip(self):
        entries = b.toc_entries('<header id="exam"></header><section id="x"><h2>A &amp; B</h2></section>'
            '<section id="y" data-toc="Custom" data-n="!"></section>'
            '<section id="hidden" data-toc-skip></section><section id="practice"></section>', b.UI['en'])
        self.assertEqual(entries, [('exam', '0', 'Exam info'), ('x', '1', 'A &amp; B'),
                                   ('y', '!', 'Custom'), ('practice', '?', 'Practice and exams')])

    def test_toc_stays_inside_top_level_sections(self):
        entries = b.toc_entries(
            '<section id="empty"></section><section id="next"><h2>Next</h2>'
            '<section id="inner"><h2>Inner</h2></section></section>'
            '<section data-id="fake" id="real"><h2>Real</h2></section>'
            '<div><section data-id="no-id"><h2>No id</h2></section></div>'
            '<!-- <section id="commented"> -->', b.UI['en'])
        self.assertEqual(entries, [('empty', '1', 'empty'), ('next', '2', 'Next'), ('real', '3', 'Real')])
        self.assertEqual(b.section_ids('<section data-id="x"></section><section id="y"><section id="z">'), {'y', 'z'})

    def test_out_path_in_a_new_folder_and_unwritable_out(self):
        self.write()
        out = Path(self.tmp.name) / 'new' / 'deeper' / 'page.html'
        built = self.cli(self.course, '-o', out)
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        self.assertTrue(out.exists())
        blocked = self.cli(self.course, '-o', self.course / 'sections')
        self.assertEqual(blocked.returncode, 1)
        self.assertIn('error: cannot write', blocked.stdout)
        self.assertNotIn('Traceback', blocked.stderr)

    def test_demo_builds_with_no_warnings_into_a_temp_folder(self):
        # the built demo is not checked in; building it elsewhere must leave the demo folder exactly as it was
        def snapshot():
            return {f.relative_to(DEMO).as_posix(): f.read_bytes() for f in DEMO.rglob('*') if f.is_file()}
        before = snapshot()
        out = Path(self.tmp.name) / 'demo-out' / 'review.html'
        built = self.cli(DEMO, '-o', out, '--strict')
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)   # --strict: no warnings either
        self.assertTrue(out.exists())
        self.assertEqual(snapshot(), before)

    def test_page_has_lf_line_endings_even_from_crlf_sources(self):
        # a Windows build must be byte-identical to a macOS/Linux one: no CRLF from the sources or from writing
        self.write()
        files = {'sections/10-main.html': '<section id="l1">\n<h2>Test</h2>\n</section>\n',
                 'extra.css': '/* one */\n/* two */\n', 'extra.js': '// one\n// two\n'}
        for rel, text in files.items():
            (self.course / rel).write_bytes(text.encode('utf-8'))
        lf = Path(self.tmp.name) / 'lf.html'
        self.assertEqual(self.cli(self.course, '-o', lf).returncode, 0)
        for rel, text in files.items():
            (self.course / rel).write_bytes(text.replace('\n', '\r\n').encode('utf-8'))
        crlf = Path(self.tmp.name) / 'crlf.html'
        self.assertEqual(self.cli(self.course, '-o', crlf).returncode, 0)
        self.assertNotIn(b'\r', crlf.read_bytes())
        self.assertEqual(crlf.read_bytes(), lf.read_bytes())

    def test_strict_exit_codes(self):
        # 0 clean, 1 errors (nothing written), 2 warnings with --strict (the page is still written)
        self.data['course']['mock'] = {'sections': [{'cat': 'single', 'n': 1}]}   # a pool twice the draw: no warnings
        self.data['mock']['items'].append(choice('m2', g='m', stem='Choose the smaller value.'))
        self.write()
        out = self.course / 'review.html'
        for args in (('--strict',), ('--check', '--strict')):
            with self.subTest(args=args):
                clean = self.cli(self.course, *args)
                self.assertEqual(clean.returncode, 0, clean.stdout + clean.stderr)
                self.assertNotIn('--strict', clean.stdout)
        self.data['practice']['groups'][0]['sec'] = 'missing'   # a warning, not an error
        self.write()
        out.unlink()
        self.assertEqual(self.cli(self.course).returncode, 0)
        out.unlink()
        self.assertEqual(self.cli(self.course, '--check').returncode, 0)
        checked = self.cli(self.course, '--check', '--strict')
        self.assertEqual(checked.returncode, 2, checked.stdout + checked.stderr)
        self.assertIn('warning:', checked.stdout)
        self.assertIn('--strict: 1 warning(s), so the exit code is 2.', checked.stdout)
        self.assertFalse(out.exists())
        built = self.cli(self.course, '--strict')
        self.assertEqual(built.returncode, 2, built.stdout + built.stderr)
        self.assertTrue(out.exists())
        self.data['course']['title'] = ''   # an error as well: errors win, exit 1, nothing written
        self.write()
        out.unlink()
        for args in (('--strict',), ('--check', '--strict')):
            with self.subTest(args=args):
                failed = self.cli(self.course, *args)
                self.assertEqual(failed.returncode, 1, failed.stdout + failed.stderr)
                self.assertIn('nothing written', failed.stdout)
                self.assertFalse(out.exists())
        self.assertIn('--strict', self.cli('--help').stdout)

    def test_cli_prints_utf8_on_a_legacy_windows_code_page(self):
        # a Windows pipe or console on cp1252 cannot encode Chinese; the CLI must print UTF-8, not crash
        env = dict(os.environ, PYTHONIOENCODING='cp1252')
        self.data['practice']['items'][0].pop('id')
        self.data['practice']['items'][0]['stem'] = '掷两颗骰子'
        self.write()
        failed = subprocess.run([sys.executable, str(SCRIPT), str(self.course)], capture_output=True,
                                encoding='utf-8', env=env)
        self.assertEqual(failed.returncode, 1, failed.stdout + failed.stderr)
        self.assertIn("practice: an item has no id (stem: '掷两颗骰子')", failed.stdout)
        self.assertNotIn('UnicodeEncodeError', failed.stderr)
        self.data = fixture()
        self.write()
        out = Path(self.tmp.name) / '复习页' / 'review.html'
        built = subprocess.run([sys.executable, str(SCRIPT), str(self.course), '-o', str(out)], capture_output=True,
                               encoding='utf-8', env=env)
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        self.assertIn(f'wrote {out} (', built.stdout)
        self.assertNotIn('UnicodeEncodeError', built.stderr)

class Audits(unittest.TestCase):
    def test_options_without_a_why_are_a_warning(self):
        # the other audits and their thresholds: test_warning_threshold_boundaries
        rep = b.Report()
        b.audit('test', [choice('x', opts=['x', 'y'])], rep)
        self.assertIn("lack a 'why'", '\n'.join(rep.warnings))

    def test_number_swapped_stems_and_math_symbols(self):
        self.assertEqual(b.stem_tokens('<b>Roll 3 dice</b>'), b.stem_tokens('Roll 9 dice'))
        self.assertNotEqual(b.stem_tokens('P(A ∪ B)'), b.stem_tokens('P(A ∩ B)'))
        data = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            course = Path(tmp)
            (course / 'sections').mkdir()
            (course / 'sections/10.html').write_text('<section id="l1"></section>', encoding='utf-8')
            data['practice']['items'][0]['stem'] = 'Roll 3 dice and count the even outcomes.'
            data['mock']['items'][0]['stem'] = 'Roll 9 dice and count the even outcomes.'
            for name, bank in data.items():
                (course / (name + '.json')).write_text(json.dumps(bank), encoding='utf-8')
            self.assertIn('m1 ~ q1', '\n'.join(b.check(course)[0].warnings))

    def assert_advice(self, rep):
        for w in rep.warnings:
            self.assertNotIn('\n', w)
            self.assertNotRegex(w, r'[:;(,]\s*$', 'warning ends without its advice')

    def test_letter_warning_advice_is_never_empty(self):
        # every answer at the top letter got there through its own "show": advise changing those letters
        items = [choice(str(i), opts=['one', 'two', 'three', 'four'], show='B') for i in range(8)]
        rep = b.Report()
        b.letter_audit('practice', items, 'test', rep)
        self.assertIn('change some of them', rep.warnings[0])
        self.assert_advice(rep)
        # answers shuffled to the same letter: suggest "show" letters
        at_a = [i for i in range(300) if b.seeded_order(f'test:q{i}', 4)[0] == 0][:8]
        rep = b.Report()
        b.letter_audit('practice', [choice(f'q{i}', opts=['one', 'two', 'three', 'four']) for i in at_a], 'test', rep)
        self.assertIn('shown as A in 8/8', rep.warnings[0])
        self.assertIn('"show": "', rep.warnings[0])
        self.assert_advice(rep)
        # fixed: true keeps the authored order, so those questions are not audited
        rep = b.Report()
        b.letter_audit('practice', [choice(str(i), opts=['one', 'two', 'three', 'four'], show='B', fixed=True)
                                    for i in range(8)], 'test', rep)
        self.assertEqual(rep.warnings, [])

    def test_warning_threshold_boundaries(self):
        def warnings(items, fn=b.audit):
            rep = b.Report()
            fn('test', items, 'test', rep) if fn is b.letter_audit else fn('test', items, rep)
            self.assert_advice(rep)
            return '\n'.join(rep.warnings)

        def singles(longest, total=10):  # the correct option is the single longest one in `longest` questions
            return [choice(str(i), opts=[{'t': 'long answer', 'why': 'w'}, {'t': 'x', 'why': 'w'}],
                           ans=0 if i < longest else 1) for i in range(total)]
        self.assertNotIn('single longest', warnings(singles(3)))   # 30% is allowed
        self.assertIn('single longest', warnings(singles(4)))      # 40% is not
        self.assertNotIn('single longest', warnings(singles(5, 5)))  # fewer than 6 questions: no audit

        def tfs(true, total=10):
            return [choice(str(i), type='tf', ans=0 if i < true else 1) for i in range(total)]
        for true, warned in ((2, True), (3, False), (7, False), (8, True)):
            with self.subTest(true=true):
                self.assertEqual('true/false' in warnings(tfs(true)), warned)
        self.assertNotIn('true/false', warnings(tfs(5, 5)))

        multis = [choice(str(i), type='multi', ans=[0]) for i in range(4)]
        self.assertIn('exactly 1 correct', warnings(multis))
        self.assertNotIn('exactly', warnings(multis[:3]))
        multis[0]['ans'] = [0, 1]
        self.assertNotIn('exactly', warnings(multis))

        def lettered(at_a, total=10):  # `at_a` answers shown as A, the rest spread over B, C, D
            return [choice(str(i), opts=['one', 'two', 'three', 'four'],
                           show='A' if i < at_a else 'BCD'[i % 3]) for i in range(total)]
        self.assertEqual(warnings(lettered(4), b.letter_audit), '')        # 40% is allowed
        self.assertEqual(warnings(lettered(4, 9), b.letter_audit), '')     # 4/9: a fair shuffle does this often
        self.assertEqual(warnings(lettered(5), b.letter_audit), '')        # 5/10: also common by chance
        self.assertIn('shown as A in 6/10', warnings(lettered(6), b.letter_audit))
        self.assertEqual(warnings(lettered(7, 7), b.letter_audit), '')     # fewer than 8 questions: no audit

    def test_true_false_labelled_single_is_audited_as_true_false(self):
        # engine.js treats a single-choice question whose options are exactly the tf labels as true/false
        items = [choice(str(i), opts=[{'t': 'True', 'why': 'w'}, {'t': 'False', 'why': 'w'}], ans=1) for i in range(6)]
        text = self.audit_text(items)
        self.assertNotIn('single longest', text)
        self.assertIn('0% of true/false answers are True', text)
        labelled = [dict(q, opts=['Yes', 'No'], ans=0) for q in items]
        self.assertIn('single longest', self.audit_text(labelled))
        self.assertIn('100% of true/false answers are True', self.audit_text(labelled, ['Yes', 'No']))
        self.assertEqual(b.cat_of(items[0]), 'tf')
        self.assertEqual(b.cat_of(choice(type='multi', opts=['True', 'False'])), 'multi')

    def audit_text(self, items, labels=None):
        rep = b.Report()
        b.audit('test', items, rep, labels)
        return '\n'.join(rep.warnings)

    def test_seeded_order_matches_engine_golden_values(self):
        # values printed by engine.js seededOrder under node
        self.assertEqual(b.seeded_order('test:x', 8), [1, 7, 6, 5, 4, 0, 3, 2])
        self.assertEqual(b.seeded_order('k:题😀', 6), [1, 5, 3, 0, 4, 2])
        self.assertEqual(b.seeded_order('', 5), [4, 0, 2, 1, 3])
        key = json.loads((DEMO / 'course.json').read_text(encoding='utf-8'))['storageKey']
        self.assertEqual(key, 'demo-prob101-mt1')
        golden = {'p1-1': [3, 1, 2, 0], 'p1-4': [0, 1, 2, 3], 'p1-6': [0, 3, 1, 2],
                  'm1-4': [0, 3, 1, 2], 'm1-5': [2, 3, 1, 0], 'm1-10': [2, 0, 3, 1]}
        for qid, order in golden.items():
            self.assertEqual(b.seeded_order(f'{key}:{qid}', 4), order, qid)
        p1 = next(q for q in json.loads((DEMO / 'practice.json').read_text(encoding='utf-8'))['items'] if q['id'] == 'p1-1')
        self.assertEqual(b.display_order(p1, key), [3, 0, 1, 2])   # "show": "B" moves the answer (index 0) to B

class EdgeCases(CourseCase):
    def test_non_json_numeric_constants_are_rejected(self):
        self.write()
        for token in ('NaN', 'Infinity', '-Infinity'):
            with self.subTest(token=token):
                (self.course / 'course.json').write_text(
                    '{"title":"test", "storageKey":"test", "extra":' + token + '}', encoding='utf-8')
                self.assertIn('invalid JSON', '\n'.join(b.check(self.course)[0].errors))

    def test_non_utf8_json_has_a_clear_diagnostic(self):
        self.write()
        (self.course / 'practice.json').write_bytes(b'{"bad": "\xff"}')
        self.assertIn('UTF-8', '\n'.join(b.check(self.course)[0].errors))

    def test_non_utf8_sections_and_extras_are_one_line_errors(self):
        files = ('sections/20-bad.html', 'extra.css', 'extra.js')
        for rel in files:
            with self.subTest(file=rel):
                for other in files:
                    (self.course / other).unlink(missing_ok=True)
                (self.course / rel).write_bytes(b'/* \xff */')
                self.invalid(rel + ': must be UTF-8')
                self.assertNotIn('sections/ has no .html or .md files', '\n'.join(self.check().errors))

    def test_unhashable_mock_category_and_oversized_show_do_not_crash(self):
        self.data['course']['mock'] = {'sections': [{'cat': [], 'n': 1}]}
        self.invalid('cat')
        self.data = fixture()
        self.data['practice']['items'][0].update(opts=['value'] * 9, show='Z')
        self.invalid('at most 8')

    def test_documented_optional_config_values_embed_without_loss(self):
        self.data['course'].update(lang='en', tfLabels=['是', '否'],
            practiceIntro='<b>Practice</b>', shortIntro='<i>Steps</i>', footer='<p>Fictional source</p>',
            mock={'sections': [{'cat': 'single', 'n': 1, 'title': 'Part', 'desc': '<b>Choose</b>', 'short': 'choice'}],
                  'weights': {'L1': 0.5}, 'minutes': [0, {'m': 2.5, 'note': 'test'}],
                  'defaultMinutes': 2.5, 'note': '<i>Intro</i>'})
        self.assertEqual(self.check().errors, [])
        self.assertEqual(self.cli(self.course).returncode, 0)
        blob = re.search(r'window.STUDY_DATA = (.*?);</script>', (self.course / 'review.html').read_text(encoding='utf-8')).group(1)
        self.assertEqual(json.loads(blob)['config'], self.data['course'])

    def test_short_option_shapes_and_optional_metadata_types(self):
        for value in (None, {}, 'bad', [], [1, 2]):
            with self.subTest(opts=value):
                self.data = fixture()
                self.data['short']['items'][0]['steps'][1]['opts'] = value
                self.invalid('opts')
        for where, key in [('group', 'desc'), ('item', 'stem'), ('item', 'answer'), ('option', 'why')]:
            self.data = fixture()
            row = (self.data['practice']['groups'][0] if where == 'group' else
                   self.data['practice']['items'][0]['opts'][0] if where == 'option' else
                   self.data['practice']['items'][0])
            row[key] = []
            self.invalid(key)

    def test_mock_weight_audit_uses_item_lecture_overrides(self):
        self.data['course']['lectures'].append('L2')
        self.data['course']['mock'] = {'sections': [{'cat': 'single', 'n': 1}], 'weights': {'L2': 1}}
        self.data['mock']['items'][0]['lec'] = 'L2'
        rep = self.check()
        self.assertEqual(rep.errors, [])
        self.assertNotIn('weights give no share', '\n'.join(rep.warnings))
        del self.data['mock']['items'][0]['lec']   # without the override the item is its group's L1, which gets no share
        self.assertIn("weights give no share to ['L1']", '\n'.join(self.check().warnings))

    def test_missing_lecture_labels_do_not_crash_weight_audit(self):
        self.data['course']['lectures'].append('L2')
        self.data['course']['mock'] = {'sections': [{'cat': 'single', 'n': 2}], 'weights': {'L1': 1}}
        del self.data['mock']['groups'][0]['lec']
        self.data['mock']['groups'].append({'id': 'm2', 'lec': 'L2'})
        self.data['mock']['items'].append(choice('m2-q', g='m2', stem='A second value.'))
        rep = self.check()
        self.assertIn("mock item 'm1': needs a 'lec'", '\n'.join(rep.errors))
        self.assertIn("weights give no share to ['L2']", '\n'.join(rep.warnings))

    def test_explicit_mock_object_types_and_section_metadata(self):
        for value in (None, [], 'mock'):
            self.data = fixture()
            self.data['course']['mock'] = value
            self.invalid('mock')
        for config, message in [({'sections': [{'cat': 'tf'}]}, 'n'),
                                ({'sections': [{'cat': 'tf', 'n': 1, 'title': 3}]}, 'title'),
                                ({'minutes': [{'m': 1, 'note': []}]}, 'note'),
                                ({'weights': []}, 'weights')]:
            self.data = fixture()
            self.data['course']['mock'] = config
            self.invalid(message)


class AnswerChecks(CourseCase):
    def test_fill_ins_need_answers_a_student_can_match(self):
        # the engine can never mark "", null or an object right, so these are build errors
        for bad in ([], [''], ['  '], [None], [{}], [True], ['0.5', '']):
            with self.subTest(accept=bad):
                self.data = fixture()
                self.data['practice']['items'] = [{'id': 'f', 'g': 'g', 'type': 'fill', 'stem': 'Value?', 'accept': bad}]
                self.invalid("'accept'")
                self.data = fixture()
                self.data['short']['items'][0]['steps'][0]['accept'] = bad
                self.invalid("'accept'")
        self.data = fixture()
        self.data['practice']['items'] = [{'id': 'f', 'g': 'g', 'type': 'fill', 'stem': 'Value?', 'accept': [0.5, '1/2']}]
        self.assertEqual(self.check().errors, [])


class AuditDetails(unittest.TestCase):
    def near_copies(self, practice_stem, mock_stem):
        data = fixture()
        data['practice']['items'][0]['stem'] = practice_stem
        data['mock']['items'][0]['stem'] = mock_stem
        with tempfile.TemporaryDirectory() as tmp:
            course = Path(tmp)
            (course / 'sections').mkdir()
            (course / 'sections/10.html').write_text('<section id="l1"></section>', encoding='utf-8')
            for name, bank in data.items():
                (course / (name + '.json')).write_text(json.dumps(bank), encoding='utf-8')
            return 'm1 ~ q1' in '\n'.join(b.check(course)[0].warnings)

    def test_near_copy_audit_catches_one_changed_word_but_not_a_new_scenario(self):
        stem = 'A bag holds red and blue marbles and two are drawn without replacement; find the chance both are red.'
        self.assertTrue(self.near_copies(stem, stem.replace('bag', 'box')))
        self.assertFalse(self.near_copies(stem, 'A factory makes parts on two lines; given a defect, which line most likely made it?'))
        self.assertFalse(self.near_copies('Find the mean.', 'Find the median.'))   # under 6 words: never fuzzy-matched

    def test_letter_warning_suggestions_remove_the_pile_up(self):
        at_a = [i for i in range(300) if b.seeded_order(f'test:q{i}', 4)[0] == 0][:9]
        items = [choice(f'q{i}', opts=['one', 'two', 'three', 'four']) for i in at_a]
        rep = b.Report()
        b.letter_audit('practice', items, 'test', rep)
        tips = re.findall(r'(q\d+): "show": "([A-D])"', rep.warnings[0])
        self.assertTrue(tips)
        for qid, letter in tips:
            next(q for q in items if q['id'] == qid)['show'] = letter
        rep = b.Report()
        b.letter_audit('practice', items, 'test', rep)
        self.assertEqual(rep.warnings, [])


if __name__ == '__main__':
    unittest.main()
