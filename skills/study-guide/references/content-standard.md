# Content standard: writing the lecture sections

The goal is a page a struggling student can learn from in one pass, and a strong student can skim in ten minutes. Every rule below came from a student's complaint about an earlier version.

## Contents
1. Page skeleton
2. The lecture recipe
3. Markdown reference
4. Figures
5. Formulas
6. Writing style
7. Optional: interactive "try it" widgets
8. Sections written in HTML

## 1. Page skeleton

`sections/` files go into `<main>` in file-name order. Write them in Markdown (`.md`); `build.py` turns each into HTML. The build adds the contents sidebar, the practice center (placed at the end), the footer and the scripts.

- `00-hero.md`: the exam logistics (`::: facts`, an even number of items looks best) and a short `::: howto` box.
- `10-l1.md`, `20-l2.md`, …: one per lecture, or per merged pair of lectures.
- `90-traps.md`: a numbered list of the one-word twists true/false questions love, each pointing back to its topic number.
- Optional `95-sheet.md`: a dense printable summary in a `::: sheet` block (`####` headings and short paragraphs).

Each file starts with front matter:

```
---
id: l1                                       # section id; practice groups point here with "sec": "l1"
toc: L1 Counting and basics                  # sidebar label (default: the ## title)
part: Part 1 · L1                            # small line above the title
src: Slides L1 p.1–24 · reading: notes ch. 1
---
## Counting and probability basics
```

The hero uses `kind: hero` and an optional `eyebrow:` line instead, then `# Title`. `n: !` sets the sidebar marker (the traps list uses it).

A section's practice box is appended automatically when a practice group has `"sec": "<that section id>"`. Topic ids and their numbers ("2.3 …") feed the right-hand rail on wide screens.

## 2. The lecture recipe

For each lecture, in this order:

1. **Front matter and `##` title**, with `src` listing the slide ranges and readings used.
2. **"Only need these" box** (`::: must`), for math-heavy or abstract lectures. List exactly what the exam asks about this lecture, three to five items. Students who feel lost read this first.
3. **Glossary** (`::: terms`). Every new term gets a one-line, everyday definition. If the exam is in another language than the page, give each term in the exam's language too, and spell out every abbreviation at first use.
4. **Analogy table** when the lecture is abstract: one everyday analogy per key term (`::: terms Everyday analogies` or a table).
5. **Topics.** One `###` heading per idea, numbered `n.1`, `n.2`, … with an id and a priority: `p3` core (on the official practice material or worked on the slides), `p2` likely, `p1` background. Each topic has:
   - `src:` the slide pages for this topic ("L7 p.23–25"), and the official practice question numbers if any;
   - `lead:` **one sentence** saying the whole idea; a student who reads only leads should still pass;
   - the body: a concrete numeric example first (`::: eg`), then the rule or formula (`$$`), then details as a short list;
   - `::: plain`: an "in plain words" box for most topics (about four per lecture); this is the most-praised part of the page;
   - a figure where one helps (see below); every lecture should have at least one;
   - `::: trap`: what students confuse or what a true/false question would twist;
   - `::: more`: a derivation or proof the exam does not test, labelled as such.
6. For a hand-calculation topic, a **step-by-step walkthrough** of one complete example (`::: steps`), with every intermediate number.

Cover what the course actually tests. Weight topics by the official practice material, the quizzes and what the instructor stressed, not by slide count.

## 3. Markdown reference

Ordinary Markdown works: paragraphs, `**bold**`, `*italic*`, `` `code` ``, `[link](url)`, `-` and `1.` lists (indent two spaces to nest), pipe tables, ``` code blocks. Inline HTML such as `<sup>` passes through. A lone `$` (as in $5) stays a dollar sign; write `\$` if one is ever misread as math.

```
### 1.1 Equally likely outcomes {#l1-equally p3}
src: L1 p.6–9
lead: When every outcome is equally likely, a probability is a count.

$$P(A)=\frac{|A|}{|\Omega|}$$ optional note after the closing $$

::: eg
Roll a fair die 4 times. P(at least one six) = $1-(5/6)^4$ ≈ 0.518 (L1 p.14).
:::

::: plain
Write out every outcome so each one is equally likely, then count.
:::

::: trap
"There are 11 possible sums, so P(sum = 7) = 1/11" is wrong.
:::
```

Blocks open with `::: name` (optionally followed by a title that replaces the default label) and close with `:::`:

| Block | Holds |
|---|---|
| `::: eg`, `::: plain`, `::: trap` | the example, plain-words and trap boxes; `::: eg Check it with numbers` retitles one |
| `::: must Title` | the "only need these" list |
| `::: terms` | `- term: definition` lines (glossary); `::: terms Everyday analogies` for analogies |
| `::: facts` | `- When: Week 6, 30 minutes` lines (hero only) |
| `::: howto` | the hero's "how to use this page" list |
| `::: more Title` | folded derivation, "not on the exam" |
| `::: steps`, `::: traps` | one numbered list, styled as a walkthrough or the traps list |
| `::: twocol` | two `#### Column title` parts side by side |
| `::: flow` | one line: `input -> **key step** -> output` |
| `::: sheet` | the printable summary |
| `::: figure <template>` | a figure (section 4) |
| `::: html` | raw HTML, kept exactly (a hand-drawn SVG, a widget placeholder) |

The build stops with the file name and line number when a block is unknown or never closed.

## 4. Figures

- Show the mechanism with real numbers: the actual grid of outcomes, the tree with counts, the curve with the point marked. Avoid boxes of abstract words.
- Math-heavy topics get plotted curves (learning-rate schedules, likelihoods, distributions) computed from the formula, not sketched.
- The caption says what to notice, with the slide reference. Every figure needs one.

Four templates cover most figures; you write numbers and labels, the build draws the SVG. Plot labels are placed automatically where they clear every line, dot and other label; the build warns only when it finds no free spot (or, in a grid or tree, when labels are too long for the space).

````
::: figure grid                  # a table of outcomes, e.g. two dice
rows: 6
cols: 6
top: die 1                       # axis titles (optional)
left: die 2
col-heads: 1..6                  # or 1, 2, 3 / a b c
row-heads: 1..6
hl: r + c = 7                    # highlight: a rule in r, c (rows and columns count from 1) or cells "1,6 2,5"
wn: r + c = 2                    # warning colour; z: dashed cells; text: r + c writes a value in each cell
- ttl: Sum = 7: 6 of 36 cells    # notes to the right: ttl, acc, warn, small or plain; "-" alone is a gap
- acc: P = 6/36 = 1/6
caption: Count cells, not sums (L1 p.8).
:::

::: figure tree                  # root on the first line, children as an indented list
1000 people
- [1%] 10 sick                   # [edge label] node text {hl | wn | ghost}
  - 9 test + {hl}
  - 1 test − {ghost}
- [99%] 990 healthy
  - ≈50 test + {wn}
  - 940 test − {ghost}
caption: Only 9 of the 59 positives are sick (L2 p.24).
:::

::: figure bars
title: P(X = k), X ~ Bin(10, 0.5)
x: 0..10                         # labels: a range or a list (text labels work too)
y: comb(10, x) * 0.5^10          # values, or an expression in x
hl: 3..7                         # these bars dark, the rest light (default: all dark); wn: warning colour
mark: 5 | mean np = 5            # dashed line with a label
values: yes                      # print each value above its bar; fmt: 2 (decimals) or % or %1
caption: …
:::

::: figure plot
x: 0..100 | Quantity Q           # range | axis label
y: 0..50 | Price P
- curve: 50 - x/2 | Demand       # an expression in x, or points "0,50 100,0"; curve w (red), curve m (dashed)
- curve w: x/2 - 10 | Supply
- point guide: 60, 20 | E        # a dot; guide draws dashed lines to the axes; point w / point o
- hline w: 25 | P = 25           # dashed line across; vline: 60 | Q = 60
- area: 0,50 0,20 60,20 | consumer surplus      # shaded polygon; area w for red
- arrow: 50,30 70,30 | demand rises
- text acc: 80, 45 | a note      # free text at a data point (small, acc, warn, ttl)
caption: …
:::
````

Expressions use `+ - * / ^`, parentheses and `sqrt exp log ln sin cos abs min max comb factorial floor ceil round pi e`. To suggest a spot, end a label with `@x` (curves and lines: the x position), `@ne`, `@nw`, `@se`, `@sw`, `@n`, `@s`, `@e`, `@w` (points) or `@x,y` (areas); the build moves it if that spot is taken. Commas inside parentheses stay part of a label. Other optional keys: `height:` (pixels), `xticks:` / `yticks:` (a list, or `none`), `grid: yes`, `cell:` (grid cell size), `alt:` (screen-reader text; default: the caption).

When no template fits, draw inline SVG inside `::: html` (see section 8 for the classes) with a 560-wide viewBox, compute text extents (about 0.55 × font size per Latin character, 1 × per CJK character) and confirm with a screenshot that no text overlaps.

## 5. Formulas

- `$...$` inline and `$$...$$` on their own line for display; text after the closing `$$` becomes a small note. Formulas work in question stems, options and explanations too (there, in HTML: `<span class='m' data-tex='…'>fallback</span>`).
- The build writes a plain-text fallback (Greek letters, fractions as a/b), which MathJax replaces when it loads; if it doesn't, the page still reads fine.
- An inline formula that is too wide gets its own scrollable line automatically.

## 6. Writing style

- Match the student's level. If they said the material is over their head, assume no background: define every term, and say why a step is taken before how.
- Lead with a concrete case, then generalize. "Flip a coin 10 times and get 7 heads; the best guess for p is 0.7" comes before the likelihood formula.
- Short sentences. One idea per sentence. Bold only the word a true/false question would flip.
- Cite. Every non-obvious claim has a slide page or source. If the slides and your knowledge disagree, follow the slides and note the difference in a trap box.
- No filler: no "it is important to note", no motivational lines, no restating the heading.
- Keep mental-math values the exam needs (no-calculator exams) in one place, such as the hero's how-to box or the cheat sheet.

## 7. Optional: interactive "try it" widgets

For a topic students find hard to picture, add a sandbox in `extra.js`, such as a slider that redraws a curve, or a generator that makes endless practice variants with Check / Show answer. Keep it unscored and separate from the practice boxes. Put a placeholder line in the section (`<div class="try" id="try-momentum"></div>`), fill it from `extra.js`, and style it with the `.try*` classes in `page.css`. `extra.js` runs after the engine; `window.StudyGuide` exposes `el(tag, cls, html)`, `t(key)` and `renderTex(root)`. Use widgets sparingly; a good figure usually does the job.

## 8. Sections written in HTML

`.html` files in `sections/` are used as they are and can sit next to `.md` files. Each lecture is a `<section class="part" id="…" data-toc="…">` with `p.part-no`, `h2`, `p.part-src`, then `article.topic[id]` blocks holding `div.topic-head > h3 + span.pri.p3`, `p.src`, `p.lead > b`, `div.eg|plain|trap > b`, `div.must > p.must-t`, `p.terms-title + dl.terms > div > dt + dd`, `div.fx > span.tex-d[data-tex]`, `span.m[data-tex]`, `ol.steps`, `ol.traps`, `div.twocol`, `div.flow > span(.k) + i`, `div.tbl > table`, `pre.code`, `details.more > summary`. The hero is `header.hero#exam` with `p.eyebrow`, `h1`, `dl.facts` and `div.howto > h2`. The simplest way to see the exact HTML for any of these is to write it in Markdown and build.

Diagram classes inside `<figure><div class="dia"><svg>…</svg></div><figcaption>…</figcaption></figure>`: `text` (with `.small`, `.ttl`, `.mono`, `.mth`, `.atxt` accent, `.wtxt` warning, `.halo` for text over lines), `.node` (`.hl`, `.wn`, `.ghost`), `.edge` (`.acc`, `.wn`, `.ghost`, `.thin`), `.arrow` (`marker-end` arrowhead built in; `.wn` for red), `.axis`, `.grid`, `.box` (`.acc`, `.fill`, `.wfill`), `.cell` (`.hl`, `.wn`, `.z`), `.dot` (`.w`, `.o`), `.curve` (`.a`, `.w`, `.m` dashed), `.band` (`.w`), `.bar` (`.w`, `.l` light).
