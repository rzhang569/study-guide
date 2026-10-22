# Data format

All files are UTF-8 JSON. Text fields that say HTML may contain inline markup (`<b>`, `<sup>`, `<code>`, `<span class='m' data-tex='…'>`). Inside JSON strings, use single quotes for HTML attributes.

## course.json

| Field | Required | Meaning |
|---|---|---|
| `title` | yes | page title |
| `lang` | no (`zh`) | interface language: `zh` or `en` |
| `storageKey` | yes | progress namespace, letters/digits/`._-`; never change it after the student starts |
| `lectures` | recommended | ordered lecture labels used by groups, e.g. `["L1", "L2", "L3–L4"]` |
| `mock.sections` | no | paper layout: `[{ "cat": "tf"\|"single"\|"multi"\|"fill", "n": 10, "title"?: "…", "desc"?: "…", "short"?: "…" }]`. Default: 10 tf, 10 single, 5 multi, 5 fill |
| `mock.weights` | no | `{ "L1": 1, "L2": 2 }` draw proportions instead of pool sizes |
| `mock.minutes` | no | time limit choices: numbers or `{ "m": 45, "note": "suggested" }`; `0` = no limit |
| `mock.defaultMinutes` | no | preselected limit (default: the first entry) |
| `mock.note` | no | extra sentence (HTML) in the mock tab's intro |
| `practiceIntro`, `shortIntro` | no | override the intro text (HTML) of the practice center and the short-answer tab |
| `tfLabels` | no | true/false option labels, default `["True", "False"]` |
| `footer` | no | footer HTML (sources, disclaimers) |

## practice.json and mock.json

```json
{
  "groups": [{ "id": "p1", "lec": "L1", "sec": "l1", "title": "L1 · Counting", "desc": "optional HTML" }],
  "items": [ { "g": "p1", "id": "p1-1", "type": "single", "stem": "HTML", "src": "L1 p.8",
               "opts": [{ "t": "HTML", "why": "HTML" }], "ans": 0, "why": "HTML" } ]
}
```

- **Group fields:** `lec` must be one of `course.json` lectures. `sec` (practice only) is the id of the page section whose practice box shows this group. An item can override `lec` and `sec`.
- **`id`:** unique across practice, mock and short. Records are keyed by it.
- **`src`:** optional, shown in the question's meta line.

| `type` | Fields | Notes |
|---|---|---|
| `single` (default) | `opts`, `ans` (index) | display order shuffled per question (stable) |
| `tf` | `ans` (0 = True, 1 = False), `opts` = two `{ "why" }` | labels filled in; never shuffled |
| `multi` | `opts`, `ans` (list of indexes) | partial credit |
| `fill` | `accept` (list), `answer` (display HTML) | numbers compared by value |
| `card` | `answer` (HTML) | flashcard, practice only, unscored |

`fixed: true` on a choice question keeps the authored option order (for options like "All of the above").

`show: "B"` on a single-choice question puts its correct answer at that letter on screen; the other options keep their shuffled order. It changes only the display, never the stored option indexes, so use it to rebalance answer letters even after students have answered.

## short.json

```json
{
  "groups": [{ "id": "a", "lec": "L2", "sec": "l2", "kind": "Bayes' rule", "title": "① Bayes' rule (L2)", "desc": "HTML" }],
  "items": [{ "k": "a", "id": "sa-a1", "stem": "HTML", "note": "HTML", "opt": "HTML (marks it optional)",
    "steps": [
      { "ask": "HTML", "pts": 3, "accept": ["0.019"], "sol": "HTML" },
      { "ask": "HTML", "pts": 1, "opts": ["HTML", "…"], "ans": 0, "ow": { "1": "why option 1 is wrong" }, "sol": "HTML" },
      { "ask": "HTML", "pts": 2, "sol": "HTML (self-check step)" }
    ] }]
}
```

A group may use `"g": "<practice group id>"` instead of `lec` and `sec` to inherit them.

## Progress (what the page stores)

localStorage keys are `<storageKey>:practice` and `<storageKey>:mock`. When the page runs as a Claude artifact with the `db` capability, they are also mirrored to the db docs `progress/practice` and `progress/mock` as `{ v: 1, state, updatedAt }`. This sync is experimental and not yet tested end to end.

- `practice.state`:
  - `ans[id]` holds first-try records: `{ first, tried[] }` (single/tf), `{ first, sel[], submitted }` (multi), `{ first, last }` (fill), `{ seen }` (card).
  - `sa[id][stepIndex]` holds `{ v, ok, shown, tries, self, fix, tried }`.
  - `redo[id]` holds notebook redos.
  - Option indexes are the authored (original) indexes.
- `mock.state`:
  - `paper[]`: the current paper's ids.
  - `draft[id]`: answers on the current paper.
  - `flags`, `seen` and `pcount` track flags and draw history.
  - `history[]`: one entry per handed-in paper, `{ at, s, m, units: {lec: {s, m}}, wrong[], flags[], picks{}, used, limit, auto }`.

## Progress report (what you read)

The page rebuilds this summary after every answer. It is included as `report` in the **Export progress** JSON (tested) and available from the console as `StudyGuide.report()`. When artifact sync works, it is also stored as the db doc `progress/report` (experimental).

```json
{
  "kind": "study-guide-report", "v": 1, "course": "…", "key": "storageKey", "at": "ISO time",
  "practice": {
    "byLecture": { "L1": { "answered": 6, "firstScore": 4.5, "total": 8 } },
    "missed": [{ "id": "p2-4", "lec": "L2", "group": "…", "type": "single", "stem": "plain text",
                 "firstAnswer": "B (About 90%)", "correct": "A (About 15%)", "redoneRight": false }]
  },
  "shortAnswer": [{ "id": "sa-a1", "lec": "L2", "kind": "Bayes' rule", "firstScore": 6, "afterFixes": 9, "max": 10, "missedSteps": [1, 4] }],
  "mock": {
    "papers": 3, "recent": [55, 64, 73], "byLecture": { "L1": { "s": 9, "m": 12 } },
    "last": { "at": "…", "score": 8, "max": 11, "usedSec": 840,
              "wrong": [{ "id": "m2-5", "lec": "L2", "type": "single", "stem": "…", "answered": "B (95%)", "flagged": true }],
              "flaggedButRight": ["m1-4"] }
  }
}
```

The letters in `firstAnswer`, `correct` and `answered` are the letters the student saw, followed by the option text.
