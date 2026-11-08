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

## Authoring format A/B (2026-11-07): HTML vs Markdown sections

The question: does writing sections in Markdown with figure templates (commit `7448e41`) instead of HTML (`main` at `c2ce954`) save tokens and rework without hurting the page? Same case (`builds-page-from-slides`), two runs per version, claude-opus-5-5, run with `ab.py` and checked with `ab_check.mjs`:

```bash
python3 evals/ab.py run OUT --config A=<html skill> --config B=<markdown skill> --runs 2
python3 evals/ab.py report OUT
node evals/ab_check.mjs OUT
python3 evals/ab.py grade OUT
```

Each run had one version of the skill in `.claude/skills/`, the user's CLAUDE.md and memory switched off, and the prompt plus "Use the study-guide skill." Graders saw only the page's rendered text and figure screenshots, so they could not tell the formats apart; the two pairwise comparisons also hid which side was which.

Averages of the two runs (A = HTML, B = Markdown):

| Measure | A | B |
|---|---|---|
| Cost | $5.19 | $4.96 |
| Output tokens | 120.5k | 104.4k |
| Turns | 44.5 | 67.5 |
| Time | 1082 s | 1017 s |
| Characters written into sections | 40.4k | 27.5k |
| Characters written into the banks | 58.4k | 58.7k |
| Figures on the page | 5 | 7.5 |
| Builds (failed) | 3.5 (0) | 6 (0) |

Quality was the same:
- Both versions passed the browser checks in every run: no script errors, no sideways scroll at 375 px, answers kept after a reload, no overlapping figure text.
- Graded checks: every run passed citations, option explanations, mock shape, answer keys and figure correctness. One run of each version failed "mock uses its own questions": a few mock items reskin practice items. That is a question-writing weakness, not a format one.
- Scores: 5/5 for clarity and coverage in all four runs; figure value 4, 4 for A and 4, 5 for B. The blind pairwise comparisons split 1–1, both "slight".

What the numbers say:
- Markdown cut the characters written into sections by a third while the pages carried more figures. Static count on the demo: 8,885 tokens of HTML vs 4,110 of Markdown.
- The whole task saved less (13% of output tokens, 4% of cost), because the question banks are most of the writing and they are JSON either way. Writing the banks one item per line saves only about 7.5% of their tokens on the demo, so that was not adopted.
- B took more turns: the figure templates warned about labels that touched lines, mostly at line crossings, and the runs moved them by hand. `08cd156` now tries farther and flipped spots before warning, and treats `@` as a preference. Replaying the two B runs' first drafts, label problems went from 24 to 1. This has not been re-run end to end yet.
- With two runs per version, none of these gaps is a measured effect.

Cost of this experiment: $20.28 for the four runs, $5.74 for grading.

### Confirmation round (2026-11-08): new B at commit `08cd156`

Two more runs of B after the label-placement change, with the same case, model, settings and grading rubric. The results above are unchanged.

| Measure | A | old B | new B |
|---|---|---|---|
| Cost | $5.19 | $4.96 | $5.04 |
| Output tokens | 120.5k | 104.4k | 104.8k |
| Turns | 44.5 | 67.5 | 73.5 |
| Time | 1082 s | 1017 s | 1012 s |
| Figure warnings on the first build | 0 (no templates) | 6, 6 | 1, 3 |
| Figures on the page | 5 | 7.5 | 6.5 |

- **Turns did not go down.** Fewer warnings reached the runs, but the extra turns were mostly screenshot checks: starting a browser and looking at figure screenshots took 15–17 tool calls per A run and 28–30 per B run, old and new. Both B versions also read the template source a few times (0–4 calls) to learn options the docs leave out.
- **Quality:** both new runs passed the browser checks. The graders failed both on "mock uses its own questions" (reskinned practice items, as in one run of each earlier version). One run also failed "figures correct and legible": some curve labels were crossed by their own curve. The overlap check skipped a label's own line; `5bc6888` fixes that.
- Scores: 5/5/5 and 5/4/5 (clarity, figure value, coverage).
- The runs found a second template bug: a position hint written without a space ("A@sw") was shown as label text. `82e5ee5` fixes it.
- Neither fix has been run end to end.

Replay, listed separately because it is not a full run: the template code was run on the B runs' first-draft sections, with no agent involved. Label problems went from 24 to 1 with `08cd156`. On the new runs' final pages, `5bc6888` gives no warnings and no label crossing its own line (checked by screenshot).

Conclusion for this ECON task only:
- Markdown sections cut what the agent writes into sections by about a third and output tokens by about 13%.
- They did not cut cost, time or turns, and quality was the same apart from the template bug above.
- The cost of this round: $10.07 for the two runs, $2.18 for grading.

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
