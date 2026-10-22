---
name: study-guide
description: Build an interactive exam review website for a course. It has lecture-by-lecture notes with slide references and plain-language explanations, a practice bank that explains every option, step-by-step short answers, timed mock exams drawn from a separate pool calibrated to the real exam, and a mistake notebook. Progress flows back so Claude can find weak spots and write targeted new drills. Use this whenever a student wants to prepare for a midterm, final or quiz, or asks for a study guide, review page, practice questions or a mock exam from their slides, notes or course website. Also use it when they share exam-prep progress and ask what to review next, even if they never say "website".
license: MIT
compatibility: Needs Python 3 to build (standard library only; count_exam.py also needs pypdf). Web access helps research the course; a browser helps check the page. The built page is one HTML file that works offline except for fonts and MathJax from public CDNs.
metadata:
  version: "0.1.0"
---

# Study guide

You produce **one self-contained HTML page** per exam, built from a course folder of plain files by `scripts/build.py`. The page has three parts:

- **Notes**, one section per lecture. Every claim cites a slide page. Each topic comes with plain-language boxes, worked examples, figures and red "trap" boxes. A practice box at the end of each section lets the student test themselves right after reading.
- **A practice center** with four tabs:
  - a practice bank with instant feedback and an explanation for every option;
  - step-by-step short answers with partial credit;
  - timed mock exams drawn from their own pool in the real exam's proportions;
  - a mistake notebook that fills itself.
- **A progress report**, which the page keeps for you. You read it later and write new drills that target what the student actually got wrong.

The engine (`assets/engine.js`) and the styles (`assets/page.css`) are finished and tested, so your job is the content and the questions. Most of what makes a page useful is in the reference files; read them when you reach that step.

| When you are about to... | Read |
|---|---|
| write the lecture sections | `references/content-standard.md` |
| write or audit questions, or calibrate the mock exam | `references/question-bank.md` |
| check a field name, the progress format or the db docs | `references/data-format.md` |

`examples/demo/` is a complete small course (fictional PROB 101, three lectures). Its built page is `examples/demo/review.html`. When unsure how something should look, copy the pattern from the demo.

## 1. Find out what the exam is

Get these facts before writing anything. Look them up when you can, and ask the student only for what you cannot find:

- **Exam:** date and time, length in minutes, which lectures are in scope, the format, and allowed materials. Format means question types, how many of each and their points. Materials means note sheets, a calculator or nothing.
- **Sources:** slides (PDFs or links), readings, the course website, and any official practice questions, quiz results or sample exam.
- **Student:** the language they want the page in (`lang`: `zh` or `en` for the interface; write the content in their language), and how strong their background is. A student who says "I'm lost" needs plain-language boxes on almost every topic.

If you can browse, research the course yourself: the schedule page, the syllabus and posted quiz results. Look for patterns worth telling the student, such as "the in-class checkpoint questions come right after a specific slide" or "the official bank says it uses the same format as the exam". Put the logistics in the page's hero section.

**Check the course's AI policy** in the syllabus. Some courses forbid AI-generated study material or ban AI help on graded work. If the policy forbids this, tell the student before building. Never put graded homework answers on the page.

## 2. Calibrate the mock exam without spoilers

Students often want to save the official sample exam for one timed run. Then do not read its questions; measure it instead:

```bash
python3 <skill-dir>/scripts/count_exam.py sample_exam.pdf
```

It prints the page count, question numbers, option-line counts and range headings such as "Questions 11–14". It never prints question text. Use the output to set the mock sections (types and counts) and the time limit. Ask before opening any sample or answer key. Even when the student allows reading it, use it only for calibration (structure, difficulty, style). Never copy its questions or scenarios into the page.

## 3. Set up the course folder

```bash
python3 <skill-dir>/scripts/build.py --init <course-dir>
```

This copies the demo course. Then edit `course.json`:

- `title`, `lang` and `lectures`. Lecture labels are exactly what questions and groups use, e.g. `"L1"` or `"L5–L6"`.
- `storageKey`: unique per course and exam, e.g. `"bio201-mt1"`. Progress is stored under it, so **never change it once the student has started**.
- `mock.sections`: one entry per question type, in exam order, with counts matching the real paper.
- `mock.minutes`: limits to choose from. Include the real one; if the mock omits long questions, also offer a proportionally shorter one.

Delete the demo's sections and questions as you replace them. See `references/data-format.md` for every field.

## 4. Write the sections

Write one file per lecture in `sections/` (`10-l1.html`, `20-l2.html`, …), plus `00-hero.html` for logistics and a final traps list. Each lecture is a `<section class="part" id="...">`. Its practice box appears automatically when a practice group points at that id with `"sec"`.

`references/content-standard.md` has the full recipe and the HTML for every component. In short: cite every claim, open hard lectures with a glossary and analogies, give each topic a one-line lead, a concrete example before any formula, a plain-language box, a figure where a picture helps, and a trap box for what true/false questions twist.

## 5. Write the questions

There are three banks. `references/question-bank.md` has the rules and the audit checklist.

- `practice.json`: 8–15 questions per lecture. Mix single choice, true/false, multi-select and fill-in, plus an occasional flashcard. Every option has its own explanation.
- `mock.json`: **its own questions**, never copies of practice items. Aim for about twice what one paper draws from each type, so repeat papers differ. Match the real exam's style.
- `short.json` (optional): step-by-step versions of the exam's short-answer types. Each step is a tolerant fill-in, a choice, or a self-check against the model answer.

## 6. Build and check

```bash
python3 <skill-dir>/scripts/build.py <course-dir>
```

Errors stop the build. Warnings are the bank audits; fix them unless you have a reason. For example, the correct answer may be the longest option in too many questions, or every multi-select may have the same number of answers. Then open `<course-dir>/review.html` in a browser and check:

- the console shows no errors and formulas render;
- answering a practice question, a short-answer step and a full mock paper works;
- at 375 px width nothing scrolls the page sideways (figures and tables scroll inside their own boxes);
- no text in a figure overlaps a line, an arrowhead or other text (take a screenshot).

## 7. Deliver

- **Claude Code / local:** give the file path. Progress is saved in that browser's localStorage. The **Export progress** button in the practice center gives the student JSON to paste back to you.
- **claude.ai artifact (experimental, not yet tested end to end):** publish the built HTML and grant the `db` capability. If `window.claude.use("db")` is available, the engine mirrors progress to the docs `progress/practice` and `progress/mock` and keeps a summary in `progress/report`. Before relying on it, answer one question on the published page and read `progress/report` back. If the doc is missing, tell the student to use **Export progress** instead.

Tell the student in two or three lines how to use the page: read a section, do its practice box, mock exams near the end, and the mistake notebook the day before.

## 8. Close the loop

When the student comes back, read their progress before changing anything. Use the exported JSON they paste or send (its `report` field), or the `progress/report` db doc if artifact sync is working. The report lists:

- first-try accuracy per lecture;
- every missed practice question with what they answered and the right answer;
- short-answer steps they missed;
- mock-exam history, plus the last paper's wrong and flagged questions.

Then:

1. **Name the weak spots** in a few lines. Count lectures below about 80% first-try accuracy, repeated misconceptions, and short-answer steps that keep failing. Also count questions flagged as unsure but answered right; those are shaky knowledge too.
2. **Write new drills** for each weak spot. Re-ask the same concept in different words, numbers or scenarios; never repeat the question they missed. Add them to `practice.json` with new ids, and to `mock.json` if the mock pool is thin there.
3. **Fix the explanation**, not just the questions. If a misconception repeats, the section probably explains it badly. Add a plain-language box, a worked example or a figure aimed at that exact mix-up.
4. Rebuild, then tell the student what changed and where.

### Keep saved progress valid when editing

Records are keyed by `storageKey`, question `id` and **original option index**. So:

- keep the `storageKey` and existing ids;
- don't reorder, insert or delete options in questions that have been answered (append a new question instead);
- don't reuse an old id for a different question.

The engine shuffles the order options are shown in with a seed from the id, so the stored indexes stay correct. Editing stems, explanations and section HTML is always safe.

## What students asked for

These lessons come from building review pages that were used for real exams:

- Abstract explanations didn't land. Students asked for concrete numbers first ("flip a coin 10 times…"), then the formula, with derivations folded away and labelled as not on the exam.
- Studying several lectures before practicing was exhausting. That is why every section ends with its own practice box.
- Format pickiness was infuriating, such as being marked wrong for `1/2` instead of `0.5`. The engine compares numeric answers by value; list text variants in `accept`.
- Students learn answer patterns fast. The correct answer was usually the longest option, every multi-select had 3 answers, and the correct answer was always B. The build audits the first two; the engine shuffles display order.
- A mock exam that reused practice questions measured memory, not understanding. That is why the mock pool is separate.
- Students wanted to select option text to copy it, and a timer that submits by itself when time runs out.
