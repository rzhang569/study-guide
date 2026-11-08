#!/usr/bin/env python3
"""A/B runs of one eval case with two versions of the skill, through the Claude Code CLI.

    python3 evals/ab.py run OUT --config A=git:main --config B=git:batch4 [--runs 2] [--prepare-only]
    python3 evals/ab.py report OUT          # cost, tokens, turns, builds, characters written (OUT/report.json)
    node evals/ab_check.mjs OUT             # browser checks, and what the graders read
    python3 evals/ab.py grade OUT           # independent grading of each run, then blind pairwise comparisons

A config is NAME=git:REF (the skill folder at a branch, tag or commit of this repository) or NAME=PATH (a skill folder
on disk, the one that holds SKILL.md). NAME is letters only. --prepare-only sets up the folders without running
anything, which costs nothing.

`run` makes OUT/<config>-<n>/ for every run: the case's input files plus one version of the skill in
.claude/skills/study-guide, so each run sees exactly one version. All runs start at once with `claude -p` on the case
prompt; the user's CLAUDE.md and auto-memory are switched off so they cannot steer the runs. Each event stream is saved
to OUT/<config>-<n>.jsonl. `grade` needs the browser checks first (node evals/ab_check.mjs OUT), which also write the
material the graders read: the page's text and screenshots of its figures, never the source files, so a grader cannot
tell which authoring format a run used.

Keep OUT outside this repository, so a run cannot find the other version of the skill.
"""
import argparse
import concurrent.futures as cf
import io
import json
import logging
import random
import re
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
TOOLS = ["Read", "Glob", "Grep", "Skill", "Write", "Edit", "Bash"]


def prompt_of(case):
    text = (HERE / case / "prompt.md").read_text(encoding="utf-8")
    body = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S).strip()
    return body + "\n\nUse the study-guide skill."


def settings():
    return json.dumps({"claudeMdExcludes": [str(Path.home() / ".claude" / "CLAUDE.md"), "**/CLAUDE.md"],
                       "autoMemoryEnabled": False})


def run_one(folder, prompt, model, log, timeout):
    cmd = ["claude", "-p", prompt, "--model", model, "--output-format", "stream-json", "--verbose",
           "--max-turns", "80", "--allowedTools", *TOOLS, "--disallowedTools", "Bash(open:*)",
           "--permission-mode", "acceptEdits", "--settings", settings(), "--no-session-persistence"]
    start = time.time()
    with open(log, "w", encoding="utf-8") as out:
        try:
            p = subprocess.run(cmd, cwd=folder, stdout=out, stderr=subprocess.STDOUT, timeout=timeout,
                               stdin=subprocess.DEVNULL)
            code = p.returncode
        except subprocess.TimeoutExpired:
            code = "timeout"
    return folder.name, code, round(time.time() - start)


def skill_source(name, spec, out):
    """NAME=git:REF -> the skill folder exported from that ref into OUT/skills/NAME; NAME=PATH -> PATH.
    Returns (folder, a description for meta.json)."""
    if spec.startswith("git:"):
        ref = spec[4:]
        sha = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--verify", ref + "^{commit}"],
                             capture_output=True, text=True, encoding="utf-8")
        if sha.returncode:
            sys.exit(f"{name}: '{ref}' is not a branch, tag or commit here")
        data = subprocess.run(["git", "-C", str(REPO), "archive", sha.stdout.strip(), "skills/study-guide"],
                              capture_output=True, check=True).stdout
        dest = out / "skills" / name
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            if hasattr(tarfile, "data_filter"):  # Python 3.12+ and recent 3.9-3.11 patch releases
                tar.extractall(dest, filter="data")
            else:
                tar.extractall(dest)
        return dest / "skills" / "study-guide", f"git {ref} at {sha.stdout.strip()[:7]}"
    folder = Path(spec).resolve()
    return folder, str(folder)


def cmd_run(a):
    out = Path(a.out).resolve()
    if REPO in out.parents or out == REPO:
        sys.exit("OUT must be outside the repository")
    configs = dict(c.split("=", 1) for c in a.config)
    bad = [n for n in configs if not re.fullmatch(r"[A-Za-z]+", n)]
    if bad:
        sys.exit(f"config names are letters only, not {bad[0]!r}")
    if out.exists() and any(out.iterdir()):
        sys.exit(f"{out} is not empty; pick a new OUT")
    jobs, sources = [], {}
    for name, spec in configs.items():
        skill, sources[name] = skill_source(name, spec, out)
        if not (skill / "SKILL.md").exists():
            sys.exit(f"{skill} has no SKILL.md")
        for n in range(1, a.runs + 1):
            folder = out / f"{name}-{n}"
            shutil.copytree(HERE / a.case / "files", folder)
            shutil.copytree(skill, folder / ".claude" / "skills" / "study-guide",
                            ignore=shutil.ignore_patterns("__pycache__", "review.html"))
            jobs.append(folder)
    (out / "meta.json").write_text(json.dumps({"case": a.case, "model": a.model, "configs": sources, "runs": a.runs,
                                               "prompt": prompt_of(a.case), "started": time.strftime("%Y-%m-%d %H:%M")},
                                              indent=1), encoding="utf-8")
    prompt = prompt_of(a.case)
    if a.prepare_only:
        print(f"prepared {len(jobs)} run folders in {out}; nothing was run")
        return
    with cf.ThreadPoolExecutor(len(jobs)) as pool:
        for name, code, secs in pool.map(lambda f: run_one(f, prompt, a.model, out / f"{f.name}.jsonl", a.timeout), jobs):
            print(f"{name}: exit {code} after {secs} s")


def events(log):
    for line in log.read_text(encoding="utf-8").splitlines():
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def kind_of(path):
    p = str(path)
    if "/sections/" in p:
        return "sections"
    name = Path(p).name
    if name in ("practice.json", "mock.json", "short.json"):
        return "banks"
    if name == "course.json":
        return "course"
    return "other"


def metrics(log):
    calls, results, final = {}, {}, None
    for ev in events(log):
        if ev.get("type") == "assistant":
            for block in ev["message"].get("content", []):
                if block.get("type") == "tool_use":
                    calls[block["id"]] = (block["name"], block.get("input", {}))
        elif ev.get("type") == "user":
            content = ev.get("message", {}).get("content", [])
            for block in content if isinstance(content, list) else []:
                if block.get("type") == "tool_result":
                    body = block.get("content")
                    if isinstance(body, list):
                        body = "\n".join(x.get("text", "") for x in body if isinstance(x, dict))
                    results[block["tool_use_id"]] = (str(body or ""), bool(block.get("is_error")))
        elif ev.get("type") == "result":
            final = ev
    m = {"builds": 0, "builds_failed": 0, "builds_warned": 0, "written": {}, "reads": [], "tool_calls": len(calls)}
    for cid, (name, inp) in calls.items():
        res, is_err = results.get(cid, ("", False))
        if name == "Bash" and "build.py" in inp.get("command", "") and "--init" not in inp.get("command", ""):
            m["builds"] += 1
            if "nothing written" in res or re.search(r"^error:", res, re.M) or is_err:
                m["builds_failed"] += 1
            elif re.search(r"^warning:", res, re.M):
                m["builds_warned"] += 1
        elif name in ("Write", "Edit", "MultiEdit"):
            path = inp.get("file_path", "")
            n = len(inp.get("content", "")) + len(inp.get("new_string", "")) + len(inp.get("old_string", ""))
            for e in inp.get("edits", []):
                n += len(e.get("new_string", "")) + len(e.get("old_string", ""))
            k = kind_of(path)
            m["written"][k] = m["written"].get(k, 0) + n
        elif name == "Read":
            path = inp.get("file_path", "")
            if "/.claude/skills/study-guide/" in path:
                m["reads"].append(path.split("/.claude/skills/study-guide/", 1)[1])
    if final:
        u = final.get("usage", {})
        m.update(cost=final.get("total_cost_usd"), seconds=round((final.get("duration_ms") or 0) / 1000),
                 turns=final.get("num_turns"), status=final.get("subtype"), output_tokens=u.get("output_tokens"),
                 input_tokens=u.get("input_tokens"), cache_write=u.get("cache_creation_input_tokens"),
                 cache_read=u.get("cache_read_input_tokens"),
                 models={k: {"in": v.get("inputTokens"), "out": v.get("outputTokens"), "cost": v.get("costUSD")}
                         for k, v in (final.get("modelUsage") or {}).items()})
    return m


def cmd_report(a):
    out = Path(a.out)
    rows = {log.stem: metrics(log) for log in sorted(out.glob("*.jsonl"))}
    (out / "report.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    for name, m in rows.items():
        w = m["written"]
        print(f"{name}: ${m.get('cost') or 0:.2f}, {m.get('output_tokens')} output tokens, {m.get('turns')} turns, "
              f"{m.get('seconds')} s; builds {m['builds']} (failed {m['builds_failed']}, warned {m['builds_warned']}); "
              f"written chars: sections {w.get('sections', 0)}, banks {w.get('banks', 0)}, other {w.get('other', 0)}; "
              f"skill files read: {', '.join(sorted(set(m['reads'])))}")


GRADE = """You are grading a study page an AI agent built for a student. Everything you need is in this folder:
- slides.txt: the text of the two lecture slide decks (ECON 150 L1 supply and demand, L2 elasticity; fictional);
- request.txt: what the student asked for;
- notes.md: the text of the page's notes, in reading order, with each figure shown as [Figure N] and its caption;
- figures/: a screenshot of each figure (figN.png), as the student sees it;
- course.json, practice.json, mock.json and short.json (if present): the page's settings and question banks.
Read them all (look at every figure image). Then answer each item strictly, with evidence:

A. citations: do the notes cite specific slide pages (like "L1 p.5") at least 8 times, and do 3 citations you spot-check point to slides that contain that content?
B. options_explained: does every practice multiple-choice question explain each option (why it is right or wrong), not only the correct answer?
C. mock_own_questions: does the mock pool avoid repeating practice questions word for word or with only numbers or a word or two changed?
D. mock_shape: does the mock mirror the real exam (a multiple-choice part plus calculation/short-answer questions, roughly 12 + 2, with a 50-minute timed option)?
E. answer_keys: re-solve 6 questions across both lectures (include equilibrium P* = 20, Q* = 60 or the midpoint elasticity example if they appear). Are all keys right?
F. figures_correct: is every figure correct for the slides (right numbers, curves, labels) and legible (no overlapping text, nothing cut off)?

Then score 1-5 (5 best) for:
- notes_clarity: could a struggling student learn both lectures from the notes alone in one pass?
- figure_value: do the figures show the mechanisms with real numbers and help understanding?
- coverage: are all exam-relevant slide points covered, weighted sensibly?

Write ONLY this JSON (no prose) to grade.json in this folder:
{"A": {"pass": true, "why": "..."}, "B": {...}, "C": {...}, "D": {...}, "E": {...}, "F": {...},
 "scores": {"notes_clarity": n, "figure_value": n, "coverage": n}, "comments": "two or three sentences"}"""

PAIR = """Two AI agents each built a study page for the same student request (request.txt) from the same slides (slides.txt).
Folder X/ and folder Y/ each hold one page: notes.md (the notes' text, figures shown as [Figure N] with captions) and
figures/figN.png (screenshots of the figures). Read both completely and look at every figure.

Judge only the notes and figures (not the question banks): which would teach a struggling student these two lectures
better in one pass? Consider correctness, clarity, concrete examples before formulas, plain-language explanations,
trap warnings, slide citations, and whether figures are correct, legible and helpful. Length is not a virtue by itself.

Write ONLY this JSON (no prose) to pair.json in this folder:
{"better": "X" or "Y" or "tie", "margin": "slight" or "clear" or "large", "why": "three or four sentences"}"""


def slides_text(folder):
    """The text of every slide PDF in folder, page by page. Graders check citations and answers against it, so a
    PDF that cannot be read, or a page with no text, stops the grading."""
    try:
        import pypdf
    except ImportError:
        sys.exit("grading needs pypdf (python3 -m pip install pypdf) to give the graders the slides as text")
    logging.getLogger("pypdf").setLevel(logging.CRITICAL)  # its complaints about a damaged file are in the error below
    files = sorted(Path(folder).glob("*.pdf"))
    if not files:
        sys.exit(f"no slide PDFs in {folder}; the graders would have nothing to check the page against")
    out = []
    for f in files:
        try:
            texts = [(page.extract_text() or "").strip() for page in pypdf.PdfReader(str(f)).pages]
        except Exception as e:  # pypdf raises many kinds of errors on a damaged file
            sys.exit(f"cannot read {f.name} ({type(e).__name__}: {e}); not grading without the slides")
        empty = [str(i) for i, t in enumerate(texts, 1) if not t]
        if not texts or empty:
            sys.exit(f"{f.name}: no text on page {', '.join(empty) or '1'}; not grading without the slides")
        out += [f"=== {f.name} p.{i}\n{t}" for i, t in enumerate(texts, 1)]
    return "\n".join(out) + "\n"


def valid_result(name, data):
    """True when a grader's JSON file has the shape the prompt asks for."""
    if name == "grade.json":
        return (isinstance(data, dict) and all(isinstance(data.get(k), dict) and isinstance(data[k].get("pass"), bool)
                                               for k in "ABCDEF") and isinstance(data.get("scores"), dict))
    return isinstance(data, dict) and data.get("better") in ("X", "Y", "tie")


def claude(prompt, folder, model, expect, timeout=1200):
    """Run one grader in folder; it must write the JSON file expect. Returns (cost, error message or None).
    A failure is also written to <expect>.error.txt, and an unusable result is renamed so the next run retries it."""
    cmd = ["claude", "-p", prompt, "--model", model, "--output-format", "json", "--max-turns", "60",
           "--allowedTools", "Read", "Glob", "Grep", "Write", "--settings", settings(), "--no-session-persistence"]
    cost, error = None, None
    try:
        p = subprocess.run(cmd, cwd=folder, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=timeout, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        p, error = None, f"timed out after {timeout} s"
    except OSError as e:
        p, error = None, f"cannot start claude: {e}"
    if p is not None:
        try:
            info = json.loads(p.stdout)
        except json.JSONDecodeError:
            info = None
        cost = info.get("total_cost_usd") if isinstance(info, dict) else None
        if p.returncode != 0 or not isinstance(info, dict) or info.get("is_error"):
            tail = (p.stderr or p.stdout or "").strip()[-600:]
            error = f"claude exited with {p.returncode}: {tail or 'no output'}"
    target = Path(folder) / expect
    if error is None:
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
            if not valid_result(expect, data):
                error = f"{expect} does not have the fields the grading prompt asks for"
        except FileNotFoundError:
            error = f"the grader finished but wrote no {expect}"
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            error = f"{expect} is not valid JSON ({e})"
    log = target.with_name(expect + ".error.txt")
    if error:
        if target.exists():
            target.replace(target.with_name(target.stem + ".invalid.json"))
        log.write_text(error + "\n", encoding="utf-8")
    elif log.exists():
        log.unlink()  # an earlier attempt failed; this one worked
    return cost, error


def report_graders(names, results, verb):
    failed = 0
    for name, (cost, error) in zip(names, results):
        if error:
            failed += 1
            print(f"FAILED {name}: {error}")
        else:
            print(f"{verb} {name} (${cost or 0:.2f})")
    return failed


def cmd_grade(a):
    out = Path(a.out).resolve()
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    if meta["case"] != "builds-page-from-slides":
        sys.exit("the grading prompts are written for builds-page-from-slides only")
    packets = sorted(p for p in (out / "grade").iterdir() if p.is_dir() and (p / "notes.md").exists())
    if not packets:
        sys.exit("no grading packets; run node evals/ab_check.mjs OUT first")
    slides = slides_text(HERE / meta["case"] / "files" / "slides")  # stops here, before any grader runs
    (out / "grade" / "slides.txt").write_text(slides, encoding="utf-8")
    for p in packets:
        (p / "request.txt").write_text(meta["prompt"], encoding="utf-8")
        (p / "slides.txt").write_text(slides, encoding="utf-8")
    todo = [p for p in packets if not (p / "grade.json").exists()]
    with cf.ThreadPoolExecutor(max(1, len(todo))) as pool:
        failed = report_graders([p.name for p in todo],
                                list(pool.map(lambda p: claude(GRADE, p, a.model, "grade.json"), todo)), "graded")
    # blind pairwise: run n of config A against run n of config B, sides shuffled with a fixed seed
    names = sorted({p.name.split("-")[0] for p in packets})
    if len(names) == 2:
        rnd = random.Random(20261108)
        pairs = []
        for n in range(1, meta["runs"] + 1):
            a_dir, b_dir = out / "grade" / f"{names[0]}-{n}", out / "grade" / f"{names[1]}-{n}"
            if not (a_dir.exists() and b_dir.exists()):
                continue
            folder = out / "grade" / f"pair-{n}"
            if (folder / "pair.json").exists():
                continue
            if folder.exists():
                shutil.rmtree(folder)
            x, y = (a_dir, b_dir) if rnd.random() < 0.5 else (b_dir, a_dir)
            for side, src in (("X", x), ("Y", y)):
                shutil.copytree(src, folder / side,
                                ignore=shutil.ignore_patterns("*.json", "*.error.txt", "slides.txt", "request.txt"))
            (folder / "slides.txt").write_text(slides, encoding="utf-8")
            (folder / "request.txt").write_text(meta["prompt"], encoding="utf-8")
            # which run is X and which is Y, kept outside the folder the grader reads
            (out / "grade" / f"pair-{n}.sides.json").write_text(json.dumps({"X": x.name, "Y": y.name}), encoding="utf-8")
            pairs.append(folder)
        with cf.ThreadPoolExecutor(max(1, len(pairs))) as pool:
            failed += report_graders([f.name for f in pairs],
                                     list(pool.map(lambda f: claude(PAIR, f, a.model, "pair.json"), pairs)), "compared")
    if failed:
        sys.exit(f"{failed} grader(s) failed; their errors are in the .error.txt files. Run grade again to retry them.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("out")
    r.add_argument("--config", action="append", required=True, help="NAME=path to a skill folder (repeat)")
    r.add_argument("--case", default="builds-page-from-slides")
    r.add_argument("--runs", type=int, default=2)
    r.add_argument("--model", default="claude-opus-5-5")
    r.add_argument("--timeout", type=int, default=2400)
    r.add_argument("--prepare-only", action="store_true", help="set up the run folders without running claude")
    rp = sub.add_parser("report")
    rp.add_argument("out")
    g = sub.add_parser("grade")
    g.add_argument("out")
    g.add_argument("--model", default="claude-opus-5-5")
    a = ap.parse_args()
    {"run": cmd_run, "report": cmd_report, "grade": cmd_grade}[a.cmd](a)


if __name__ == "__main__":
    main()
