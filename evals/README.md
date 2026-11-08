# Evals

Three test cases for the `study-guide` skill. Each case folder has `prompt.md`, `case.yaml`, `graders/` (one assertion per file) and `files/`, in the layout `claude plugin eval` reads.

Every input is fictional:
- the ECON 150 slides and sample exam were written for these tests, with marker words planted in every exam question;
- the progress export was made on the fictional PROB 101 demo.

| Case | What it checks |
|---|---|
| `builds-page-from-slides` | Turning two slide decks into a review page. The page must open offline, cite slides, explain every option, keep the mock pool separate and shaped like the real exam, have correct answer keys, work on a phone and keep saved progress. |
| `measures-sample-exam-unseen` | Describing a sample exam's format for a student who is saving it for a timed run, without reading or leaking any question content. |
| `drills-from-progress` | Reading an exported progress file, naming the real weak spots, and adding targeted drills without breaking saved progress. |

## How to run

Use the skill-creator skill's eval workflow:
1. Run each prompt once with the skill and once without it.
2. Grade each run against its `graders/` with an independent agent.
3. Compare the two configurations.

Keep the run folders outside this repository, so that runs without the skill cannot find it.

The cases follow the `claude plugin eval` layout, but running them through that CLI from this location has not been tried.

### Comparing two versions of the skill

`ab.py` and `ab_check.mjs` run one case with two versions of the skill and compare them. They need the Claude Code CLI (`claude`), Python with pypdf, Node 20 or newer (on Node 20 `ab_check.mjs` turns on WebSocket itself) and Chrome.

```bash
python3 evals/ab.py run OUT --config A=git:main --config B=git:some-branch --runs 2   # --prepare-only: set up, run nothing
python3 evals/ab.py report OUT        # cost, output tokens, turns, time, builds, characters written per kind of file
node evals/ab_check.mjs OUT           # browser checks, plus the material the graders read
python3 evals/ab.py grade OUT         # one grader per run, then blind pairwise comparisons
```

- A version is `NAME=git:REF` (a branch, tag or commit of this repository) or `NAME=PATH` (a skill folder).
- Each run gets exactly one version in `.claude/skills/`.
- The user's CLAUDE.md and auto-memory are switched off. `open` is blocked, so no browser window pops up.
- OUT must be outside the repository.
- Graders see only the page's rendered text and figure screenshots, so they cannot tell how a page was authored. Pairwise comparisons also hide which side is which.
- The grading prompt is written for `builds-page-from-slides` only.
- `grade` stops before any grader runs if a slide PDF cannot be read or has a page without text, because the graders check citations and answers against the slides.
- A grader that fails or writes no usable result is reported as `FAILED`, with its error kept in `<file>.error.txt`; `grade` then exits with an error, and running it again retries only those.
- The reload check answers the bank's first question the way its type needs (choice, multi-select, fill-in or flashcard) and compares its saved record and card before and after the reload.
- `run` and `grade` call Claude and cost money; `--prepare-only`, `report` and `ab_check.mjs` do not.

## Authoring-format experiment (2026-11-07 to 11-08): HTML vs Markdown sections

**Decision: HTML stays the default.** Markdown sections and figure templates stay an experiment on the branch `batch4`.

The question was whether writing sections in Markdown, with templates for figures, saves tokens and rework without hurting the page. Everything below comes from one case, `builds-page-from-slides` (ECON 150), on claude-opus-5-5, and holds for that case only.

The versions:
- **A:** HTML sections (`main` at `c2ce954`).
- **Old B:** Markdown sections plus figure templates (`batch4` at `7448e41`).
- **New B:** old B after a label-placement change (`08cd156`).

### Full runs

Each column averages two runs.

| Measure | A | Old B | New B |
|---|---|---|---|
| Cost | $5.19 | $4.96 | $5.04 |
| Output tokens | 120.5k | 104.4k | 104.8k |
| Turns | 44.5 | 67.5 | 73.5 |
| Time | 1082 s | 1017 s | 1012 s |
| Characters written into sections | 40.4k | 27.5k | 27.9k |
| Characters written into the banks | 58.4k | 58.7k | 59.0k |
| Figures on the page | 5 | 7.5 | 6.5 |
| Figure warnings on the first build | – | 6, 6 | 1, 3 |

- **Writing:** Markdown cut what went into sections by about a third and output tokens by about 13%. The banks, which are JSON either way, are most of the writing. Cost, time and turns did not go down.
- **Turns:** the extra turns were mostly screenshot checks of the larger number of figures. Starting a browser and looking at screenshots took 15–17 tool calls per A run and 28–30 per B run. B runs also read the template source a few times to learn options the docs left out.

Every quality failure, by run (the browser checks found no script errors, no sideways scroll at 375 px, no lost answers after a reload and no overlapping figure text in any of the six runs):
- **A-1:** failed "mock uses its own questions": some mock items reskin practice items.
- **A-2:** passed everything.
- **Old B-1:** passed everything.
- **Old B-2:** failed "mock uses its own questions".
- **New B-1:** failed "mock uses its own questions".
- **New B-2:** failed "mock uses its own questions". It also failed "figures correct and legible": some curve labels were crossed by their own curve, a template bug.
- **Scores** (clarity, figure value, coverage, each out of 5): A 5/4/5 and 5/4/5; old B 5/4/5 and 5/5/5; new B 5/5/5 and 5/4/5.
- **Blind pairwise comparisons** (notes and figures only): old B-1 slightly better than A-1; A-2 slightly better than old B-2.

Cost: $30.35 for the six runs, $7.92 for grading.

### Replay (not a full run)

The template code was run on the old B runs' first-draft sections, with no agent involved. Label problems went from 24 (old B) to 1 (`08cd156`). This does not stand in for the full runs above: there, turns still went up.

### Fixed after the runs, not re-run end to end

Both fixes are on `batch4`, with tests. They are checked only on the saved pages, not in new runs.
- `5bc6888`: a label must clear its own line. New B-2's final sections, rebuilt, give no warnings, and a screenshot shows the labels off their curves.
- `82e5ee5`: a position hint written without a space ("A@sw") was shown as label text.

### If this is picked up again

Test it on a real course that needs many figures, with the same checks and grading, before changing the default.

## Iteration 1 (2026-10-22): the version at commit e980bb9

These results describe the skill as it was at commit `e980bb9`, before the changes listed at the end of this section. **They do not test the current version.** Iteration 2 has not been run yet.

Method:
- Each case ran once with the skill and once without it, on claude-opus-5-5.
- Independent agents graded the results; phone layout and saved progress were checked in a real browser.
- The runs and grading files live outside this repository.

| Case | With the skill (original) | Without (original) | With the skill (revised) | Without (revised) |
|---|---|---|---|---|
| builds-page-from-slides | 8/8 | 6/8 | 7/8 | 6/8 |
| measures-sample-exam-unseen | 4/5 | 4/5 | 4/6 | 4/6 |
| drills-from-progress | 6/6 | 6/6 | 5/6 | 5/6 |
| Assertions passed | 18/19 | 16/19 | 16/20 | 15/20 |
| Mean pass rate per case | 93% | 85% | 79% | 75% |

- **Original:** graded against the assertions as first written.
- **Revised:** the same outputs graded against the current assertions. Unchanged assertions keep their verdicts. The four changed or added assertions were re-graded by independent agents that did not see the earlier grades.
- **Cost:** with the skill, runs averaged 884 s and 209k tokens; without it, 620 s and 161k tokens.

With one run per configuration, neither gap is a measured effect. Under the revised assertions the two configurations differ by one assertion: with the skill, every practice option was explained; without it, most practice questions explained only the correct answer.

Weaknesses both configurations showed (revised assertions):
- **Number-swapped mock questions.** Mock questions repeated practice questions with only their numbers or a word or two changed: 10 of 30 mock items with the skill, 7 without. The first wording of the assertion only caught word-for-word copies, so the original grading missed this.
- **Sample exam.** Both runs saw some question content while measuring the sample exam. Both called question 13 standalone, though it uses the questions 5–8 scenario.
- **Drills that copy a miss.** Both added drills that copy a missed question and change only its numbers. For the run with the skill, this verdict depends on a loose reading of "changes one number": its two copies changed two numbers each.

Changes made after iteration 1, not yet re-evaluated:
- **`count_exam.py`** now reports point values, the time limit, calculator and notes rules, part headings, and questions that refer back to a scenario, still without printing question text. Regression tests are in `tests/`.
- **`build.py`** now warns when one letter is the shown answer too often, and when a mock question looks like a practice question with new numbers. These warnings flag the problem; they do not prevent it.
- **A `"show"` field** rebalances answer letters without touching stored options, so saved answers stay valid.
- **The evals themselves:**
  - moved out of the skill folder, where runs with the skill could see the grader file names;
  - fixed a swapped L2/L3 tally in `progress.json`;
  - added the question 13 assertion;
  - judged "one self-contained page" by whether it opens offline;
  - counted number-swapped copies as repeats.

**Not covered yet:**
- whether Claude picks the skill on its own in a normal conversation (every run here was told to use it);
- claude.ai upload and artifact progress sync;
- other agents;
- more than one run per configuration.
