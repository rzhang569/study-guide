"""Markdown sections (scripts/sectionmd.py) and figure templates (scripts/figures.py)."""
import contextlib
import io
import re
import unittest

from tests.test_build import DEMO, CourseCase, b

md = b.sectionmd()
figures = md.figures()


def convert(text, lang='en'):
    rep = b.Report()
    return md.convert(text, 'x.md', lang, rep), rep


class Markdown(unittest.TestCase):
    def html(self, text, lang='en'):
        out, rep = convert(text, lang)
        self.assertEqual(rep.errors, [])
        return out

    def test_front_matter_title_and_topics(self):
        h = self.html('---\nid: l1\ntoc: L1 Short  # sidebar\npart: Part 1 · L1\nsrc: Slides L1 p.1–9\n---\n'
                      '## Basics & more\n\n### 1.1 Counting {#l1-count p3}\nsrc: L1 p.6\nlead: Count, then divide.\n\n'
                      'Body text.\n\n### 1.2 Next {p1}\nMore.\n')
        self.assertTrue(h.startswith('<section class="part" id="l1" data-toc="L1 Short">\n<p class="part-no">Part 1 · L1</p>\n'
                                     '<h2>Basics &amp; more</h2>\n<p class="part-src">Slides L1 p.1–9</p>\n'), h)
        self.assertIn('<article class="topic" id="l1-count">\n<div class="topic-head"><h3>1.1 Counting</h3>'
                      '<span class="pri p3">core</span></div>\n<p class="src">L1 p.6</p>\n'
                      '<p class="lead"><b>In one line</b>Count, then divide.</p>\n<p>Body text.</p>\n</article>', h)
        self.assertIn('<article class="topic" id="l1-t2">\n<div class="topic-head"><h3>1.2 Next</h3>'
                      '<span class="pri p1">background</span></div>\n<p>More.</p>\n</article>\n</section>', h)

    def test_boxes_use_the_page_language_unless_retitled(self):
        src = '---\nid: a\n---\n::: plain\nOne line.\n:::\n::: eg Check it\nTwo.\n:::\n::: trap\nFirst.\n\n- a\n- b\n:::\n'
        en, zh = self.html(src), self.html(src, 'zh')
        self.assertIn('<div class="plain"><b>In plain words</b>One line.</div>', en)
        self.assertIn('<div class="eg"><b>Check it</b>Two.</div>', en)
        self.assertIn('<div class="trap"><b>Trap</b>\n<p>First.</p>\n<ul><li>a</li><li>b</li></ul></div>', en)
        self.assertIn('<div class="plain"><b>人话</b>One line.</div>', zh)
        self.assertIn('<div class="trap"><b>易错</b>', zh)

    def test_terms_must_more_steps_twocol_and_flow(self):
        h = self.html('---\nid: a\n---\n::: terms\n- sample space $\\Omega$: every outcome: listed\n- 术语：中文定义\n:::\n'
                      '::: must Only these\n1. First\n2. Second\n:::\n::: more\nProof here.\n:::\n'
                      '::: steps\n1. Add $2+2$.\n2. Get 4.\n:::\n::: twocol\n#### Left\nL text\n#### Right\nR text\n:::\n'
                      '::: flow\ninput -> **key** -> output\n:::\n')
        for part in ('<p class="terms-title">Glossary</p>\n<dl class="terms"><div><dt>sample space '
                     '<span class="m" data-tex="\\Omega">Ω</span></dt><dd>every outcome: listed</dd></div>'
                     '<div><dt>术语</dt><dd>中文定义</dd></div></dl>',
                     '<div class="must"><p class="must-t">Only these</p>\n<ol><li>First</li><li>Second</li></ol></div>',
                     '<details class="more"><summary>Derivation (not on the exam)</summary>\n<p>Proof here.</p>\n</details>',
                     '<ol class="steps"><li>Add <span class="m" data-tex="2+2">2+2</span>.</li><li>Get 4.</li></ol>',
                     '<div class="twocol"><div><h4>Left</h4>\n<p>L text</p></div><div><h4>Right</h4>\n<p>R text</p></div></div>',
                     '<div class="flow"><span>input</span><i>→</i><span class="k">key</span><i>→</i><span>output</span></div>'):
            self.assertIn(part, h)

    def test_hero(self):
        h = self.html('---\nkind: hero\neyebrow: X 101 · Midterm\n---\n# Review\n\nIntro with [a link](https://e.x/?a=1&b=2).\n\n'
                      '::: facts\n- When: Week 6\n:::\n::: howto\n- **Tags:** read\n:::\n')
        self.assertTrue(h.startswith('<header class="hero" id="exam">\n<p class="eyebrow">X 101 · Midterm</p>\n<h1>Review</h1>'))
        self.assertIn('<a href="https://e.x/?a=1&amp;b=2">a link</a>', h)
        self.assertIn('<dl class="facts"><div><dt>When</dt><dd>Week 6</dd></div></dl>', h)
        self.assertIn('<div class="howto"><h2>How to use this page</h2>\n<ul><li><b>Tags:</b> read</li></ul></div>', h)

    def test_inline_math_prices_escapes_and_html(self):
        h = self.html('---\nid: a\n---\nA $10 tax, then $3 more; a < b & c &amp; d; \\$x$ stays; $x^2 \\le \\frac{1}{2}$, '
                      '<sup>2</sup>, `a<b`, *it*, 2*3*4 and $10–$20.\n')
        self.assertIn('<p>A $10 tax, then $3 more; a &lt; b &amp; c &amp; d; $x$ stays; '
                      '<span class="m" data-tex="x^2 \\le \\frac{1}{2}">x² ≤ 1/2</span>, <sup>2</sup>, <code>a&lt;b</code>, '
                      '<i>it</i>, 2*3*4 and $10–$20.</p>', h)

    def test_lists_tables_code_display_math_and_raw_html(self):
        h = self.html('---\nid: a\n---\n- one\n  - nested\n- two\n  continued\n\n1. first\n2. second\n\n'
                      '| A | B |\n|---|---|\n| $P(A \\mid B)$ | x \\| y |\n\n```\ncode <b>\n```\n\n$$\na = b\n$$ the note\n\n'
                      '<div class="try" id="try-x"></div>\n')
        for part in ('<ul><li>one\n<ul><li>nested</li></ul></li><li>two continued</li></ul>',
                     '<ol><li>first</li><li>second</li></ol>',
                     '<div class="tbl"><table>\n<tr><th>A</th><th>B</th></tr>\n<tr><td><span class="m" '
                     'data-tex="P(A \\mid B)">P(A | B)</span></td><td>x | y</td></tr>\n</table></div>',
                     '<pre class="code">code &lt;b&gt;</pre>',
                     '<div class="fx"><span class="tex-d" data-tex="a = b">a = b</span><span class="note">the note</span></div>',
                     '<div class="try" id="try-x"></div>'):
            self.assertIn(part, h)

    def test_formula_fallbacks_read_as_plain_text(self):
        for tex, text in (('\\frac{a+b}{2}', '(a+b)/2'), ('\\binom{8}{3}', 'C(8, 3)'), ('x_i^2', 'x<sub>i</sub>²'),
                          ('\\sqrt{np(1-p)}', '√(np(1-p))'), ('\\mathrm{Var}(aX+b)', 'Var(aX+b)'),
                          ('\\alpha \\cdot \\beta_{12}', 'α · β₁₂'), ('\\left( \\frac{|A|}{|\\Omega|} \\right)', '( |A|/|Ω| )'),
                          ('P(B)>0, x^{a<b}', 'P(B)&gt;0, x<sup>a&lt;b</sup>')):
            with self.subTest(tex=tex):
                self.assertEqual(md.tex_fallback(tex), text)
        self.assertEqual(md.plain_label('**P** = $x^{ab}$'), 'P = x^(ab)')

    def test_mistakes_stop_the_build_with_file_and_line(self):
        for text, line, words in (
                ('---\nid: a\n---\n::: box\nx\n:::\n', 4, "unknown block '::: box'"),
                ('---\nid: a\n---\ntext\n::: plain\nnever closed\n', 5, 'is never closed'),
                ('---\nid: a\ncolour: red\n---\n', 3, "unknown front matter key 'colour'"),
                ('## No front matter\n', 1, 'needs an id'),
                ('---\nid: a\n---\n### T {#t hot}\n', 4, "unknown topic attribute 'hot'"),
                ('---\nid: a\n---\n### A {#t}\n### B {#t}\n', 5, "topic id 't' is used twice"),
                ('---\nid: a\n---\n::: terms\n- no colon here\n:::\n', 5, "the form 'term: definition'"),
                ('---\nid: a\n---\n:::\n', 4, 'never opened'),
                ('---\nid: a\n---\n$$x\n', 4, 'never closed'),
                ('---\nid: a\n---\n::: figure\nx: 1\n:::\n', 4, 'needs a template name'),
                ('---\nid: a\n---\n::: figure bars\nx: 0..2\ny: 1, 2, 3\n:::\n', 4, "add a 'caption:'"),
                ('---\nid: a\n---\n::: figure grid\nrows: 2\ncols: 2\ncolor: red\ncaption: c\n:::\n', 7, "unknown key 'color'"),
                ('---\nid: a\n---\n::: figure bars\nx: 0..2\ny: 1, 2\ncaption: c\n:::\n', 6, '3 x labels but 2 y values')):
            with self.subTest(words=words):
                out, rep = convert(text)
                self.assertIsNone(out)
                self.assertEqual(len(rep.errors), 1)
                self.assertIn(f'sections/x.md line {line}: ', rep.errors[0])
                self.assertIn(words, rep.errors[0])


def figure(kind, body):
    out, rep = convert(f'---\nid: a\n---\n::: figure {kind}\n{body}\n:::\n')
    if out is None:
        raise AssertionError(rep.errors)
    return out, rep.warnings


class Figures(unittest.TestCase):
    def test_grid_rule_and_cell_list_mark_the_same_cells(self):
        rule, _ = figure('grid', 'rows: 3\ncols: 3\nhl: r = c\nwn: r + c = 4   # the other diagonal\ncaption: c')
        cells, _ = figure('grid', 'rows: 3\ncols: 3\nhl: 1,1 2,2 3,3\nwn: (1,3) (2,2) (3,1)\ncaption: c')
        self.assertEqual(rule, cells)
        self.assertEqual(rule.count('class="cell hl"'), 2)  # 2,2 is on both diagonals; wn wins
        self.assertEqual(rule.count('class="cell wn"'), 3)
        _, warns = figure('grid', 'rows: 2\ncols: 2\ntext: r * 100000 + c\ncaption: c')
        self.assertIn('wider than', warns[0])

    def test_bars_compute_their_values(self):
        h, warns = figure('bars', 'x: 0..4\ny: comb(4, x) * 0.5^4\nvalues: yes\nfmt: 4\nhl: 1..3\nmark: 2 | mean\ncaption: c')
        self.assertEqual(warns, [])
        self.assertEqual(re.findall(r'class="small"[^>]*>([\d.]+)<', h), ['0.0625', '0.2500', '0.3750', '0.2500', '0.0625'])
        self.assertEqual(h.count('class="bar l"'), 2)
        heights = [float(v) for v in re.findall(r'class="bar[^"]*"[^>]* height="([\d.]+)"', h)]
        self.assertAlmostEqual(heights[1] / heights[2], 4 / 6, places=2)
        h, _ = figure('bars', 'x: buyers (inelastic, |Ed| = 0.5), sellers (elastic)\ny: 0.8, 0.2\ncaption: c')
        self.assertIn('>buyers (inelastic, |Ed| = 0.5)</text>', h)

    def test_demo_figures_have_no_warnings(self):
        rep = b.Report()
        for f in sorted((DEMO / 'sections').glob('*.md')):
            self.assertIsNotNone(md.convert(f.read_text(encoding='utf-8'), f.name, 'en', rep))
        self.assertEqual((rep.errors, rep.warnings), ([], []))

    def test_tree_layout_and_crowded_leaves(self):
        h, warns = figure('tree', 'root\n- [1%] a\n  - c {hl}\n  - d {ghost}\n- b {wn}\ncaption: c')
        self.assertEqual(warns, [])
        self.assertEqual(h.count('<rect class="node'), 5)
        self.assertIn('class="small halo" text-anchor="end">1%</text>', h)
        _, warns = figure('tree', 'root\n' + '\n'.join(f'- a rather long leaf label {k}' for k in range(5)) + '\ncaption: c')
        self.assertIn('overlaps', warns[0])

    def test_plot_clips_curves_and_places_labels_clear_of_lines(self):
        h, warns = figure('plot', 'x: 0..100 | Q\ny: 0..30 | P\n- curve: 50 - x/2 | Demand\n- curve w: x/2 - 10 | Supply\n'
                                  '- point guide: 60, 20 | E\n- hline: 25 | P = 25\ncaption: c')
        self.assertEqual(warns, [])
        top, bottom = 30, 300 - 44
        for path in re.findall(r'<path class="curve [aw]" d="M([^"]+)"', h):
            ys = [float(p.split(',')[1]) for p in path.split(' L')]
            self.assertTrue(all(top - 0.1 <= y <= bottom + 0.1 for y in ys), path)
        self.assertEqual(re.findall(r'class="atxt halo"[^>]*>([^<]+)<', h), ['Demand'])

    def test_labels_move_to_a_free_spot_and_crowding_is_reported(self):
        h, warns = figure('plot', 'x: 0..10 | x\ny: 0..10 | y\n- curve: x | rising\n- curve w: 10 - x | falling\n'
                                  '- point: 5, 5 | where they cross @ne\n- point: 5, 5 | same spot @ne\ncaption: c')
        self.assertEqual(warns, [])  # @ne is taken by the first label and crossed by both lines: both move
        self.assertEqual(len(re.findall(r'class="halo"', h)), 2)
        h, warns = figure('plot', 'x: 0..100 | Q\ny: 0..50 | P\n- curve: 0,50 100,0 | Demand: Qd = 100 − 2P @15\ncaption: c')
        self.assertEqual(warns, [])  # a label must clear its own line too, also on a curve given as two points
        m = re.search(r'<text x="([\d.]+)" y="([\d.]+)" class="atxt halo"(?: text-anchor="(\w+)")?>([^<]+)<', h)
        box = figures.Canvas.box_of(float(m[1]), float(m[2]), m[4], 'atxt halo', m[3] or 'start')
        line = [tuple(map(float, p.split(','))) for p in re.search(r'class="curve a" d="M([^"]+)"', h)[1].split(' L')]
        self.assertFalse(figures.seg_hits(box, (*line[0], *line[1])), (box, line))
        h, _ = figure('plot', 'x: 0..10 | x\ny: 0..10 | y\n- curve: x | D₁@8\n- point: 5, 5 | A@sw\n- hline: 3 | P @ 2\ncaption: c')
        self.assertEqual(re.findall(r'halo"[^>]*>([^<]+)<', h), ['D₁', 'A', 'P'])  # hints without a space are read too
        _, warns = figure('plot', 'x: 0..10 | x\ny: 0..10 | y\nheight: 180\n' + ''.join(
            f'- point: 5, 5 | a long label number {k}\n' for k in range(30)) + 'caption: c')
        self.assertEqual(len(warns), 1)
        self.assertRegex(warns[0], r'sections/x\.md line 4: figure plot: "a long label number \d+" (overlaps|runs past)')

    def test_expressions_allow_only_math(self):
        for bad in ("__import__('os')", 'x.real', '[1][0]', "open('f')", 'lambda: 1', '2x', 'y + 1'):
            with self.subTest(expr=bad):
                out, rep = convert(f'---\nid: a\n---\n::: figure plot\nx: 0..1 | x\ny: 0..1 | y\n- curve: {bad}\ncaption: c\n:::\n')
                self.assertIsNone(out)
                self.assertIn('line 7', rep.errors[0])
        out, rep = convert('---\nid: a\n---\n::: figure bars\nx: 0..2\ny: 9^9^9 + x\ncaption: c\n:::\n')
        self.assertIn('no value at x = 0', rep.errors[0])


class MarkdownCourse(CourseCase):
    def test_markdown_sections_build_with_contents_practice_box_and_mathjax(self):
        (self.course / 'sections/10-main.html').unlink()
        (self.course / 'sections/00-hero.html').write_text('<header class="hero" id="exam"><h1>Hi</h1></header>', encoding='utf-8')
        (self.course / 'sections/10-l1.md').write_text(
            '---\nid: l1\ntoc: L1 Values\n---\n## Values\n\n### 1.1 One {#l1-one p3}\nlead: $x^2$ grows.\n', encoding='utf-8')
        self.assertEqual(self.check().errors, [])  # practice group 'g' points at sec 'l1', which only the .md file has
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(b.build(self.course, self.course / 'review.html'), 0)
        page = (self.course / 'review.html').read_text(encoding='utf-8')
        self.assertIn('<a href="#exam"><span class="n">0</span>', page)
        self.assertIn('<a href="#l1"><span class="n">1</span>L1 Values</a>', page)
        self.assertLess(page.index('id="exam"'), page.index('id="l1"'))
        self.assertIn('tex-svg-full', page)
        self.assertIn('<span class="pri p2">', b.sectionmd().convert('---\nid: a\n---\n### T {p2}\n', 'a.md', 'zh', b.Report()))

    def test_a_broken_markdown_file_stops_the_build(self):
        (self.course / 'sections/20-bad.md').write_text('---\nid: l2\n---\n::: plain\nnever closed\n', encoding='utf-8')
        self.invalid('sections/20-bad.md line 4: ')

    def test_same_name_as_html_and_md_is_a_warning(self):
        (self.course / 'sections/10-main.md').write_text('---\nid: l9\n---\nText.\n', encoding='utf-8')
        self.assertIn('sections/10-main.html and sections/10-main.md share a name', '\n'.join(self.check().warnings))

    def test_demo_keeps_its_section_and_topic_ids(self):
        page = io.StringIO()
        rep, _, _, _, _, sections, _ = b.check(DEMO)
        body = '\n'.join(s for _, s in sections)
        ids = re.findall(r'<(?:section|header|article)\b[^>]*\bid="([^"]+)"', body)
        self.assertEqual(ids, ['exam', 'l1', 'l1-equally', 'l1-rules', 'l1-count', 'l2', 'l2-cond', 'l2-indep', 'l2-bayes',
                               'l3', 'l3-exp', 'l3-lin', 'l3-var', 'traps'])
        del page


if __name__ == '__main__':
    unittest.main()
