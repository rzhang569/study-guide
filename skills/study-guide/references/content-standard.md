# Content standard: writing the lecture sections

The goal is a page a struggling student can learn from in one pass, and a strong student can skim in ten minutes. Every rule below came from a student's complaint about an earlier version.

## Contents
1. Page skeleton
2. The lecture recipe
3. Component reference (HTML)
4. Figures
5. Formulas
6. Writing style
7. Optional: interactive "try it" widgets

## 1. Page skeleton

`sections/` files are concatenated in file-name order inside `<main>`. The build adds the contents sidebar, the practice center (`<section id="practice">`, placed at the end unless you put an empty one somewhere yourself), the footer and the scripts.

- `00-hero.html`: one `<header class="hero" id="exam">` holding the logistics (`dl.facts`, an even number of items looks best) and a short "how to use this page" box.
- `10-l1.html`, `20-l2.html`, …: one `<section class="part" id="l1" data-toc="L1 Short title">` per lecture, or per merged pair of lectures. `data-toc` is the sidebar label; without it the build uses the `<h2>` text.
- `90-traps.html`: a numbered list of the one-word twists true/false questions love, each pointing back to its topic number.
- Optional `95-sheet.html`: a dense printable summary (`div.sheet` with `h4` headings and short `p`s).

A section's practice box is appended automatically when a practice group has `"sec": "<that section id>"`. Topic ids (`article.topic[id]`) and their `h3` numbers ("2.3 …") feed the right-hand rail on wide screens.

## 2. The lecture recipe

For each lecture, in this order:

1. **Header:** `p.part-no` (e.g. "Part 3 · L5–L6"), `h2` title, `p.part-src` listing the slide ranges and readings used.
2. **"Only need these" box** (`div.must`), for math-heavy or abstract lectures. List exactly what the exam asks about this lecture, three to five items. Students who feel lost read this first.
3. **Glossary** (`p.terms-title` + `dl.terms`). Every new term gets a one-line, everyday definition. If the exam is in another language than the page, give each term in the exam's language too, and spell out every abbreviation at first use.
4. **Analogy table**, when the lecture is abstract: one everyday analogy per key term, in a `div.tbl > table`.
5. **Topics.** One `article.topic` per idea, numbered `n.1`, `n.2`, … Each has:
   - `div.topic-head` with the `h3` and a priority tag: `span.pri.p3` core (on the official practice material or worked on the slides), `p2` likely, `p1` background;
   - `p.src`: slide pages for this topic ("L7 p.23–25"), and the official practice question numbers if any;
   - `p.lead`: **one sentence** saying the whole idea; a student who reads only leads should still pass;
   - the body: a concrete numeric example first (`div.eg`), then the rule or formula (`div.fx`), then details as a short list;
   - `div.plain`: an "in plain words" box for most topics (about four per lecture); this is the most-praised part of the page;
   - a figure where one helps (see below); every lecture should have at least one;
   - `div.trap`: what students confuse or what a true/false question would twist;
   - `details.more`: a derivation or proof the exam does not test, labelled as such.
6. For a hand-calculation topic, a **step-by-step walkthrough** of one complete example (`ol.steps`), with every intermediate number.

Cover what the course actually tests. Weight topics by the official practice material, the quizzes and what the instructor stressed, not by slide count.

## 3. Component reference (HTML)

Copy these; the classes are styled in `assets/page.css`. Use `&lt;` for a literal `<` in text.

```html
<p class="lead"><b>In one line</b>The whole idea in one sentence.</p>
<p class="src">L4 p.12–14 · official bank Q3</p>
<span class="pri p3">core</span>  <span class="pri p2">likely</span>  <span class="pri p1">background</span>

<div class="must"><p class="must-t">The exam only asks these three things</p><ol><li>…</li></ol></div>

<p class="terms-title">Glossary</p>
<dl class="terms"><div><dt>term</dt><dd>everyday definition</dd></div></dl>

<div class="plain"><b>In plain words</b>…</div>
<div class="eg"><b>Example</b>…</div>
<div class="trap"><b>Trap</b>…</div>

<div class="fx"><span class="tex-d" data-tex="E[X]=\sum_x x\,p(x)">E[X] = Σ x · p(x)</span><span class="note">optional note</span></div>
<span class="m" data-tex="\sigma(0)=0.5">σ(0) = 0.5</span>      <!-- inline math -->

<ol class="steps"><li>First compute …</li><li>…</li></ol>
<div class="twocol"><div><h4>Option A</h4>…</div><div><h4>Option B</h4>…</div></div>
<div class="flow"><span>input</span><i>→</i><span class="k">key step</span><i>→</i><span>output</span></div>
<div class="tbl"><table><tr><th>…</th></tr><tr><td>…</td></tr></table></div>
<pre class="code"><span class="c"># comment</span>
<span class="k">keyword</span> …</pre>
<details class="more"><summary>Derivation (not on the exam)</summary>…</details>
<ol class="traps"><li>… (2.3)</li></ol>
```

Diagram classes inside `div.dia > svg`: `text` (with `.small`, `.ttl`, `.mono`, `.mth`, `.atxt` accent, `.wtxt` warning, `.halo` for text over lines), `.node` (`.hl`, `.wn`, `.ghost`), `.edge` (`.acc`, `.wn`, `.ghost`, `.thin`), `.arrow` (`marker-end` arrowhead built in; `.wn` for red), `.axis`, `.grid`, `.box` (`.acc`, `.fill`, `.wfill`), `.cell` (`.hl`, `.wn`, `.z`), `.dot` (`.w`, `.o`), `.curve` (`.a`, `.w`, `.m` dashed), `.band`, `.bar` (`.w`, `.l` light).

## 4. Figures

- Draw inline SVG inside `<figure><div class="dia"><svg viewBox="0 0 560 H" role="img" aria-label="…">…</svg></div><figcaption>…</figcaption></figure>`. Use a 560-wide viewBox: the box keeps a 560 px minimum width and scrolls sideways on phones instead of shrinking the text.
- Show the mechanism with real numbers: the actual grid of outcomes, the tree with counts, the curve with the point marked. Avoid boxes of abstract words.
- Math-heavy topics get plotted curves (learning-rate schedules, likelihoods, distributions) computed from the formula, not sketched.
- Use colors only through the classes above, so figures match the page.
- Before delivering, check that no text overlaps another label, a line or an arrowhead. Compute text extents (about 0.55 × font size per Latin character, 1 × per CJK character), then confirm with a screenshot.
- The caption says what to notice, with the slide reference.

## 5. Formulas

- Write LaTeX in `data-tex` and a readable plain-text fallback inside the element (`σ(z) = 1/(1+e<sup>−z</sup>)`). MathJax replaces the fallback when it loads; if it doesn't, the page still reads fine.
- `span.m` for inline, `div.fx > span.tex-d` for display. An inline formula that is too wide gets its own scrollable line automatically.
- Formulas are welcome in question stems, options and explanations too.

## 6. Writing style

- Match the student's level. If they said the material is over their head, assume no background: define every term, and say why a step is taken before how.
- Lead with a concrete case, then generalize. "Flip a coin 10 times and get 7 heads; the best guess for p is 0.7" comes before the likelihood formula.
- Short sentences. One idea per sentence. Bold only the word a true/false question would flip.
- Cite. Every non-obvious claim has a slide page or source. If the slides and your knowledge disagree, follow the slides and note the difference in a trap box.
- No filler: no "it is important to note", no motivational lines, no restating the heading.
- Keep mental-math values the exam needs (no-calculator exams) in one place, such as the hero's how-to box or the cheat sheet.

## 7. Optional: interactive "try it" widgets

For a topic students find hard to picture, add a sandbox in `extra.js`, such as a slider that redraws a curve, or a generator that makes endless practice variants with Check / Show answer. Keep it unscored and separate from the practice boxes. Put a placeholder in the section (`<div class="try" id="try-momentum"></div>`), fill it from `extra.js`, and style it with the `.try*` classes in `page.css`. `extra.js` runs after the engine; `window.StudyGuide` exposes `el(tag, cls, html)`, `t(key)` and `renderTex(root)`. Use widgets sparingly; a good figure usually does the job.
