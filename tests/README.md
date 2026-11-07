# Test coverage and data-format audit

Run from the repository root (on Windows, `python` or `py -3` instead of `python3`):

```bash
python3 -m unittest -v
node --test
node tests/browser/run.mjs   # real headless Chrome; prints SKIP without a browser or Python
```

The browser tests build the demo in English and Chinese into a temporary folder and drive
headless Chrome over the DevTools protocol (`tests/browser/cdp.mjs`, no npm packages). They
cover the practice center, short-answer redo, a full mock paper and its score report, and the
mistake notebook. CI runs all three suites (`.github/workflows/test.yml`) on Ubuntu (Python
3.9 and 3.13) and on Windows (Python 3.13), with `REQUIRE_BROWSER=1`, so a missing browser
fails the job instead of skipping.

For refactors of `engine.js`, `page.css` or `build.py` there is also a before/after check (not part of CI):

```bash
node tests/browser/compare.mjs main          # about 3 minutes; --quick: 1280 px only, about 1 minute
```

It builds the current demo with the skill folder from a git ref (default `main`) and with the
working tree, drives both pages through the same scripted tour in headless Chrome (English and
Chinese, six window widths and print media, with a seeded `Math.random` and a frozen clock) and
compares every element's tag, attributes, text and full computed style, `::before`/`::after`
included. It exits 1 at the first checkpoint that differs and prints what changed. A refactor
should end with `same: N checkpoints match`; it only sees the states the tour reaches, so a CSS
class that the demo never renders still needs a source search before it is removed.

The Node side finds what it needs by itself:

- Browser: `CHROME_PATH`, then the usual Chrome locations on macOS, Linux and Windows
  (Program Files, Program Files (x86), `%LOCALAPPDATA%`), then Edge, then the `PATH`.
- Python, to build the demo (`tests/build-demo.cjs`): `PYTHON`, then `python3`, `python`,
  `py -3` (`python` first on Windows). Without one, the browser tests and the engine test
  that boots the built demo skip.

Python uses only the standard library. Node uses built-in modules (`node:test`,
`node:vm`, filesystem/path loading, and assertions); there are no npm packages.
`tests/__init__.py` enables discovery with the exact Python command above, including
`test_count_exam.py`. That existing test retains its optional pypdf/eval PDF check.

All authored test courses are tiny fictional fixtures in `TemporaryDirectory`.
The demo and drills-from-progress files are read-only test inputs. Demo builds and
`--init` tests target temporary copies. Tests never edit eval fixtures or source
courses. The built demo page is not checked in (`.gitignore` keeps a local build out):
the tests and the Pages workflow build it from the sources. `evals/drills-from-progress`
keeps its own built page as an eval fixture.

## build.py exit codes

- 0: success (the page is written, or `--check` passed)
- 1: errors; nothing is written
- 2: `--strict` and at least one warning; the page is still written (with `--check`,
  nothing is written either way)

`test_strict_exit_codes` covers all three, with and without `--check`. Note that
argparse also exits with 2 on a usage error.

## Windows

- `build.py` and `count_exam.py` print UTF-8 whatever the console code page, so a
  Chinese stem or the "–" in a count_exam report cannot raise `UnicodeEncodeError` on
  cp1252 or cp437. Tests run both CLIs with `PYTHONIOENCODING` set to such a code page.
- Every file read and write in the scripts and tests names `encoding="utf-8"`. Check with
  `python3 -X warn_default_encoding -W error::EncodingWarning -m unittest` (Python 3.10+):
  no EncodingWarning.
- `review.html` is written with LF line endings, so a Windows build is byte-identical to a
  macOS/Linux build, also from CRLF sources.
- `.gitattributes` keeps LF in every checkout: the engine test compares the engine embedded
  in the built demo with `assets/engine.js`.

## Rule table

Source: `skills/study-guide/references/data-format.md`, read with the other two
references. **Before** describes the original validator; **now** describes the final
validator. E = build error; W = warning; runtime = engine responsibility; manual =
not verifiable from one course's files. The examples in the spec are not treated as
a complete closed JSON schema: unknown extension fields remain supported.

| Rule | Before | Now / tests |
|---|---|---|
| Files contain UTF-8 JSON objects | JSON syntax E; decode/type exceptions possible; non-JSON NaN/Infinity accepted | Clear UTF-8, JSON, root/container type E; `DataRules`, `EdgeCases` |
| Text marked HTML can contain inline markup; single-quoted attributes advised | Passed through, no sanitizer/style enforcement | Same; embedding, Unicode, entities, script-close escaping tested in `BuildOutput` |
| `title` required | Truthiness E; non-string accepted | Non-empty string E; `test_required_config_fields` |
| `lang` optional, default zh, only zh/en | Membership E, malformed type could crash | Type and membership E; default zh and en output tested |
| `storageKey` required, letters/digits/`._-` | Required/regex E, malformed type could crash | Non-empty string/regex E; positive punctuation and invalid Unicode/space cases |
| Storage namespace unique per course/exam and unchanged after use | Manual | Manual; runtime namespace isolation and appended-question compatibility tested |
| `lectures` recommended, ordered labels | No container/element type check | List-of-strings E; order retained; omission remains allowed |
| `mock` optional object | No shape check | Object E, including absent pool |
| `mock.sections`: tf/single/multi/fill categories, integer counts | Category E only with nonempty pool; counts unchecked | Shape/category/nonnegative-integer E even without pool; zero permitted |
| Default mock layout: 10 tf, 10 single, 5 multi, 5 fill | Implemented | Default audit and runtime category/order/count tests; `sections: []` is now a build error and `n: 0` sections are dropped |
| Section `title`, `desc`, `short` override text | Unchecked | String E if present; valid values embedded unchanged |
| `mock.weights`: lecture-to-number draw proportions | Missing weight keys W; values unchecked | Object/finite nonnegative-number E, missing keys W (honors item lecture overrides); runtime weighted/capped/zero-weight draws tested |
| `mock.minutes`: numbers or `{m,note}`, zero unlimited | Unchecked | Nonempty array, finite nonnegative m, string note E; timed/unlimited/unstarted runtime cases |
| `mock.defaultMinutes`: optional, defaults to first choice | Unchecked | Finite nonnegative-number E; runtime default and persisted limit tests; membership in choices not required by spec |
| `mock.note`, `practiceIntro`, `shortIntro`, `footer`: optional HTML | Unchecked | String E; embedded unchanged |
| `tfLabels`: optional two labels, default True/False | Unchecked | Two strings E; engine defaults/localized labels and no shuffle tested |
| Bank `groups`/`items` collections and object members | Unchecked shapes; exceptions possible | List/object E; empty/omitted collections remain permitted |
| Group ids present, distinct within a bank; item `g`/short `k` resolves | E for practice/mock; short ids silently overwritten | E in all banks, with contextual diagnostics |
| Group `lec` belongs to configured lectures | E when both supplied | Same; item override membership now E too; omission ambiguity below |
| Practice `sec` targets page section; items may override `lec`/`sec` | Missing group section W; override unchecked | Same W; override types and lecture membership E; engine inheritance/override tested; missing item section still unchecked |
| Question ids unique across all three banks | E, but non-string/unhashable ids unsafe | String/nonempty/global uniqueness E, including within-bank duplicates |
| `stem` contains question HTML | Empty stem E in practice/mock only | String/empty E in all banks |
| `src` optional, displayed citation metadata | No citation syntax/content validation | Same; absent, empty and authored citations accepted; source accuracy remains manual |
| `single` is default; `opts`, integer `ans` indexes a real option | E for count/index; some malformed option entries accepted | Option shape/text E; 2–8 options, integer non-bool answer; default and strings compatibility tested |
| Choice option `{t,why}` text and explanation | Missing t E, missing why W | Shape/type E, missing why W retained; no new explanation requirement |
| `tf`: ans 0/1, two options, generated labels, no shuffle | E on count/index; omitted opts permitted | Same; tests pin omitted opts compatibility and localized runtime labels |
| `multi`: nonempty distinct answer indexes; partial credit | Index E but bool accepted; nested values could crash | Strict integer/non-bool/distinct/range E; documented partial-credit formula tested |
| `fill`: nonempty accept list, display answer HTML, compare numbers by value | accept E, display answer optional in code | accept E retained; answer string checked if supplied; runtime expression/vector/tolerance tests; missing display answer ambiguity below |
| `card`: answer HTML, practice-only, unscored | Missing answer E; mock presence only W | Same policy; runtime unscored/skip/report behavior tested |
| `fixed: true` preserves authored option order | No type validation | Boolean E; runtime fixed order tested |
| `show`: a valid letter on a single choice; only display changes | E on invalid type/letter; oversized options could crash diagnostic | E retained without crash; runtime shown letters and original-index persistence tested; precedence ambiguity below |
| Short groups may link `g` to inherit practice lecture/section | Missing linked group E | Same; engine inheritance tested |
| Short item `note`, `opt`; group `kind`, `title`, `desc` | No type checks | String E if present; optional-total behavior tested at runtime |
| Short questions need steps with ask/sol | E on missing steps/ask/sol; malformed shapes unsafe | List/object/nonempty/string E with contextual errors |
| Short `pts` supplies step marks | Unchecked; runtime default 1 | Positive finite-number E if supplied; missing still uses runtime default 1 |
| Short fill `accept` | Nonempty-list E | Same; wrong/unreadable/retry/first/fixed/self/override state paths tested |
| Short choice `opts`+`ans`, optional `ow` explanations | Index E but bool accepted; opts shape unchecked; ow unchecked | At least two text options and integer non-bool index E; ow retained as optional passthrough; click scoring tested |
| Short self-check step has neither opts nor accept | Allowed | Still allowed; reveal/self-mark scoring tested |
| Progress keys `<storageKey>:practice` / `:mock` | Runtime, not build input | Namespace/save/reload/corrupt/version/blocked-storage tests |
| Practice ans records: first/tried, first/sel/submitted, first/last, seen | Runtime | Real choice/fill/multi/card event handlers, first-score preservation and reload tests |
| Short records `{v,ok,shown,tries,self,fix,tried}`; notebook `redo` | Runtime | Complete state roundtrip; typed reevaluation, first vs fixed scoring and independent notebook mastery tests |
| Stored option indexes are authored indexes | Runtime | Stable seeded order, forced shown letters, legacy eval state, append/remove and redo tests |
| Mock paper/draft/flags/seen/pcount/history, per-lecture scores, picks, used/limit/auto | Runtime | Draw freshness/order/proportions/caps, draft persistence, flags, blank/partial scoring, timing and history tests |
| Artifact db docs `{v:1,state,updatedAt}` and report mirror | Experimental runtime | Sync logic tested against a fake db (debounced writes, newer side wins on boot, local progress pushed, db failures fall back to localStorage); not tested against a live artifact db |
| Report kind/v/course/key/at; practice answered/firstScore/total and missed records | Runtime | Public `StudyGuide.report()`, first-score precision, scope independence, plain HTML/sup/sub text, redoneRight |
| Report short firstScore/afterFixes/max/missedSteps | Runtime | Typed/choice/self score paths and eval summary compatibility |
| Report mock papers/recent/byLecture/last/wrong/flaggedButRight | Runtime | Partial totals, history aggregation, recent-eight cap, blanks/flags/removed ids and eval compatibility |
| Export JSON contains report and raw practice/mock state | Runtime | Actual Export button textarea and downloadable JSON compared, schema recursively matched to eval export, raw state preserved |
| Report answer letters represent shown option order and text | Runtime | Single/tf shown letters/text tested; multi-select text ambiguity below |

The pool size, near-copy, per-option why, longest-correct-option, multi answer-count,
true/false balance and shown-letter audits come from `question-bank.md`, rather
than additional hard data-format constraints. Tests cover their W severity,
thresholds, fixed-order exclusion, numeric stem normalization and distinct math
symbols. A deficient pool warns; it does not prevent a build. Runtime draws use only
available questions and exclude missing/zero-weight lectures.

## Bugs reproduced and fixed

- Malformed JSON root/container/text/option/step/config types could crash or pass
  validation. Added a shape-checking boundary before semantic checks, with errors
  naming the file/field. Non-UTF-8 files and non-JSON numeric constants now fail
  clearly. Invalid mock configuration is checked even without a populated pool.
- Mock weight warnings ignored item lecture overrides and could crash while sorting
  mixed missing/named lecture labels. The audit now uses effective item lectures
  and sorts diagnostics safely.
- Multi-select and short-choice boolean answer keys were accepted as integers;
  nested multi answer keys could raise instead of reporting an error.
- Short group ids could be missing or duplicated; short stems and item lecture
  overrides escaped the semantic checks.
- An invalid `show` combined with more than eight options could crash its error
  message; `--init` on an existing file raised a traceback. Both now fail cleanly.
- Fill checking compared numeric values against only the first numeric reference.
  A later `2/3` in accept failed for equivalent `4/6`. All numeric references now
  participate, while unreadable input still is not recorded.
- Bracket-stripping text equality incorrectly accepted `1+2*3` for `(1+2)*3`.
  Numeric references now use evaluation before text normalization. Quoted numeric
  expressions such as `“1/2”` are recognized too.
- Zero-weight lectures entered quota redistribution. They now remain excluded.
- A hard 50-pass cap could underfill a large weighted paper despite available
  questions. Redistribution now has a quota-derived bound.
- Per-lecture practice totals rounded each partial score before adding the next,
  making three one-third scores total 0.99. They now round the final sum once.

Each regression was run against the old behavior before its fix. The first Python
run had 56 failing and 46 erroring subcases. The initial Node run had two product
failures and one cross-realm array assertion problem in the test itself; the latter
was corrected by comparing host-realm arrays. Later edge cases were also reproduced
before fixing them. The production engine has no test API or module extraction;
only the VM's in-memory copy exposes closure bindings before calling real boot().

## Spec mismatches left unchanged

- The reference lists fill `answer` and two tf `opts`; code deliberately provides
  fallbacks for both. Mock flashcards are described as practice-only but code warns
  and skips them rather than rejecting the bank. Characterization tests retain this.
- `show` is ignored for two-option choices and when `fixed` is true. The spec does
  not define precedence between those display rules. Existing behavior is pinned.
- Lecture membership is checked only when labels and the configured lecture list
  are supplied. Group lecture labels can be missing, and item `sec` targets are not
  checked for existence. The reference does not clearly assign requiredness/error
  severity for those cases. Short `ow` contents are likewise not schema-validated.
- Multi-select report answers contain shown letters only, although the final report
  prose describes letters followed by option text. Existing export shape is retained.
- Missing short `pts` defaults to one, while the example always supplies points;
  requiredness is not stated. Explicit points must now be finite and positive.

## Assumptions and limits

- Counts and option indexes are integers; booleans are not indexes. Explicit times
  and weights must be finite and nonnegative; explicit step points positive.
- The spec does not promise unit conversion. Numeric answers with units/currency
  are unreadable and unrecorded unless the exact text is explicitly accepted.
  Tests cover this without inventing a unit system or changing rounding tolerance.
- HTML is trusted authored content; no citation authenticity, markup sanitizer,
  locale decimal-comma convention or single-quote style enforcement is inferred.
- Stable persistence means retaining storageKey, ids and original option indexes;
  raw historical state is preserved, while reports may reevaluate with the improved
  checker and current shown letters.
- These are logic/serialization/build tests, not browser layout, MathJax/CDN,
  clipboard permissions, live artifact db or end-to-end visual tests. One
  uninstrumented engine boot and the embedded demo engine also run in the VM.
- Fonts and MathJax remain the documented CDN exceptions to self-contained HTML.
- No courses, eval inputs, archive content or reference specs were edited.

## Final verification

On Python 3.12.10 and Node.js 20.20.2, both exact commands passed four consecutive
runs on the final code: **46 Python tests and 79 Node tests**, zero failures,
errors, skips or todos. `git diff --check` is clean. The demo rebuild reports zero
warnings; rebuilding it again is byte-identical. Relative to the starting HEAD,
the then checked-in demo `review.html` changed only where the fixed `engine.js` is embedded. No demo data,
section HTML, eval fixture, reference document or archive content changed.
