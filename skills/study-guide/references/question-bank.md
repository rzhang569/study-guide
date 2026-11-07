# Question bank: writing, auditing, calibrating

## Contents
1. What each bank is for
2. Writing a good choice question
3. True/false
4. Multi-select
5. Fill-in
6. Short answers, step by step
7. Calibrating the mock exam
8. Audit checklist
9. Drills from the progress report

## 1. What each bank is for

| Bank | Purpose | Size |
|---|---|---|
| `practice.json` | learn: instant feedback, retry, explanation for every option | 8–15 per lecture |
| `mock.json` | measure: exam conditions, nothing shown until hand-in | about 2× what one paper draws per type |
| `short.json` | rehearse the exam's long questions one step at a time | 2–4 per short-answer type |

The mock pool is **separate**. If a mock question is a practice question in disguise, the mock score measures memory. Write mock questions about the same concepts in a different scenario, not the same sentence with new numbers. The build warns when a mock stem matches a practice stem except for numbers or a word or two, but other kinds of near-copy are still up to you to catch.

If the course publishes official practice questions, the practice bank may include them, but only with the student's agreement and labelled with `src`. Never include the sample exam the student is saving for a timed run. Never publish verbatim course material (questions, slide text) in a public page.

## 2. Writing a good choice question

- **Stem:** one clear question in the exam's language and style. If the real exam groups questions under a scenario ("A team's git history…"), do the same: a group `desc` holds the scenario.
- **Distractors are real misconceptions.** Each wrong option should be what a student who misunderstands one specific thing would pick: the other direction of a conditional, forgetting to square, the number from one branch only. A distractor nobody would pick is wasted.
- **Every option gets a `why`:**
  - for the right option, the reason it's right;
  - for a wrong one, the mistake that produces it ("That is P(+ | D), the other direction"). Name the mistake instead of only saying "wrong".
- **Parallel options:** similar length and grammar. Don't make the right one the most careful or most complete-sounding.
- **The question-level `why`** gives the method in one or two sentences ("List the 36 pairs and count").
- Keep numbers easy to work by hand when the exam bans calculators.

## 3. True/false

Write `"type": "tf"`; the options default to True/False (override the labels with `tfLabels` in course.json). Both options still get a `why`:

- **For a false statement:** the False option's `why` gives the corrected sentence. The True option's `why` names the likely mix-up.
- **For a true statement:** the True option's `why` says why it holds. The False option's `why` names the trap that makes it look false.

Write false statements the way instructors do: change one word in a true sentence from the slides (always → sometimes, increases → decreases, input → output). Keep roughly half true and half false.

## 4. Multi-select

Use multi-select only if the exam has it, or to practice a "which of these always hold" skill. Mix the number of correct answers across questions: some with 1, some 2, 3 or 4. Students notice when every question has 3. Partial credit is `max(0, (right picks − wrong picks) / max(#correct, #picked))`.

## 5. Fill-in

`accept` lists the reference answers. Numbers are compared by value within rounding, so `0.5`, `1/2`, `50%` and `2^-1` all match `"0.5"`. The checker also reads fractions, powers, `sqrt`, `ln`, `log`, `exp`, `pi`, `e`, superscripts, vectors such as `(1, -0.5)`, and "v3 = 5.42", where it takes the part after `=`. For non-numeric answers, list the spellings you accept; matching ignores case, spaces, quotes, brackets and trailing punctuation. `answer` is the display text, which can include working: "1 − (5/6)⁴ ≈ 0.518". Ask for "3 decimals or an expression" so the student knows what form works.

## 6. Short answers, step by step

Mirror the exam's short-answer types. If the official bank's short answer is "compute the gradient of sigmoid + BCE for one example", write 2–4 versions with different numbers and break each into the steps a grader gives points for.

- **A step** has `ask`, `pts`, `sol` (the model answer with working) and one of:
  - `accept`: a tolerant fill-in. A wrong answer stays editable and the answer is not revealed until the student asks.
  - `opts` + `ans` (+ `ow` explanations for wrong options): a choice, shown shuffled.
  - neither: the student writes on paper, reveals `sol` and marks themselves.
- **Points should add up** to the exam's points for that question type.
- `note` is a one-line summary shown when all steps are done.
- `opt` marks a derivation the exam does not test. It's shown as optional and left out of the total.

## 7. Calibrating the mock exam

Match the real paper on:

- **Sections:** types, in order, with counts. Set them in `course.json` → `mock.sections`. Example: 20 true/false, 10 multiple choice and 5 fill-in for an exam with those parts. If the exam has long short answers the mock cannot grade, leave them to the short-answer tab and offer a shorter time limit in proportion.
- **Coverage:** each section is drawn in proportion to how many pool questions each lecture has. If the instructor said the weighting differs, set `mock.weights` (`{"L1": 1, "L2": 2, …}`).
- **Time:** `mock.minutes` offers the real limit and a suggested one.
- **Style and difficulty:** scenario groups, option count (four or five), option length, and how much computation a question takes. Use `count_exam.py` when the sample must stay unseen.

New papers prefer questions not drawn before, so the pool should hold at least twice what a paper draws from each type; the build warns when it doesn't.

## 8. Audit checklist

`build.py` checks these automatically, as errors (E) or warnings (W):

- (E) ids unique across all banks, groups exist, answers index real options, fill-ins have `accept`;
- (W) every choice option has a `why`;
- (W) the right answer is the single longest option in at most about 30% of single-choice questions;
- (W) multi-select questions don't all have the same number of correct answers;
- (W) true/false answers are between 30% and 70% True;
- (W) no letter is the shown correct answer in more than 40% of single-choice questions, counting only pile-ups a fair shuffle would produce less than 10% of the time (4 of 9 at one letter is normal; 6 of 10 is not). The engine shuffles options per question with a fixed seed, so a small bank can still come out lopsided. The warning suggests a `"show"` letter for a few questions. `show` moves the answer on screen without touching the stored options, so it is safe even for questions students have already answered;
- (W) no mock stem is a practice stem with only numbers or a word or two changed;
- (W) each mock section's pool can fill the paper, ideally twice over.

Check these yourself:

- a distractor is not accidentally also correct (re-solve each question);
- no question gives away another's answer in the same paper;
- explanations agree with the notes and the slides;
- numbers work out cleanly by hand.

## 9. Drills from the progress report

When the report shows a weak spot:

- **Find the misconception, not just the topic.** "Picked P(+ | D) for P(D | +) twice" is a misconception; "missed two L2 questions" is a topic.
- **Write 2–4 new questions per misconception.** Use a new scenario and new numbers, and make the tempting wrong answer an option, so a correct answer shows the misconception is gone.
- **Questions they flagged but got right** are worth one new question each; the knowledge is shaky.
- **Short-answer steps** that fail repeatedly need a new walkthrough in the section (`ol.steps`) as well as new practice.
- **Add with new ids**, in the same group as the original, so the section box and lecture stats pick them up. Never edit the options of answered questions.
- **Tell the student** which questions are new and why. A line like "3 new questions on reading conditionals backwards, in the L2 box" is enough.
