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
