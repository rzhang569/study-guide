#!/usr/bin/env python3
"""Runs the manual install commands from docs/GETTING-STARTED*.md, the way a reader would paste them.

On Windows it runs the ```powershell blocks, elsewhere the ```bash blocks, that clone the repository
(the `claude plugin` block needs the Claude CLI and is skipped). The clone URL is pointed at this
checkout so a pull request tests its own files. Each command installs into the real home folder, so
this runs only in CI (CI=true) or with --yes. Afterwards the installed copies must match the repo's
skills/study-guide and build the demo page.

    python tests/install_docs.py          # in CI
    python tests/install_docs.py --yes    # on your own machine, if you accept writing to ~/.claude and ~/.agents
"""
import filecmp
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
URL = "https://github.com/rzhang569/study-guide.git"
WIN = os.name == "nt"


def blocks(doc, lang):
    text = (ROOT / "docs" / doc).read_text(encoding="utf-8")
    return [b for b in re.findall(r"```" + lang + r"\n(.*?)```", text, re.S) if "git clone" in b]


def same_tree(a, b):
    cmp = filecmp.dircmp(a, b, ignore=["__pycache__"])
    if cmp.left_only or cmp.right_only or cmp.diff_files:
        return False
    return all(same_tree(Path(a) / d, Path(b) / d) for d in cmp.common_dirs)


def main():
    if not (os.environ.get("CI") or "--yes" in sys.argv):
        print("SKIP: writes to ~/.claude/skills and ~/.agents/skills; run in CI or pass --yes")
        return 0
    lang = "powershell" if WIN else "bash"
    found = {doc: blocks(doc, lang) for doc in ("GETTING-STARTED.md", "GETTING-STARTED.zh.md")}
    # both languages must document the same commands
    assert found["GETTING-STARTED.md"] == found["GETTING-STARTED.zh.md"], "English and Chinese guides differ"
    cmds = found["GETTING-STARTED.md"]
    assert len(cmds) == 2, f"expected the Claude and Codex {lang} blocks, found {len(cmds)}"
    home = Path.home()
    targets = [home / ".claude" / "skills" / "study-guide", home / ".agents" / "skills" / "study-guide"]
    for t in targets:
        shutil.rmtree(t, ignore_errors=True)
    for cmd in cmds:
        work = tempfile.mkdtemp(prefix="sg-install-")
        src = ROOT.as_uri() if WIN else str(ROOT)
        assert f"git clone {URL}" in cmd, "the guide's clone command changed; update this test"
        script = cmd.replace(f"git clone {URL}", f'git clone "{src}" study-guide')   # same folder name as a real clone
        shell = ["pwsh", "-NoProfile", "-Command", script] if WIN else ["bash", "-euo", "pipefail", "-c", script]
        print(f"$ ({lang}, in {work})\n{script}")
        subprocess.run(shell, cwd=work, check=True)
    for t in targets:
        assert (t / "SKILL.md").is_file(), f"not installed: {t}"
        assert same_tree(ROOT / "skills" / "study-guide", t), f"installed copy differs from the repo: {t}"
        out = Path(tempfile.mkdtemp(prefix="sg-build-")) / "review.html"
        subprocess.run([sys.executable, str(t / "scripts" / "build.py"), str(t / "examples" / "demo"), "-o", str(out)], check=True)
        assert out.stat().st_size > 50_000, "built page is suspiciously small"
        print(f"ok: {t}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
