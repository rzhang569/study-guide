#!/usr/bin/env python3
"""Runs the manual install commands from docs/GETTING-STARTED*.md, the way a reader would paste them.

On Windows it runs the ```powershell blocks with both Windows PowerShell 5.1 (`powershell`, what most
readers have) and PowerShell 7 (`pwsh`); elsewhere it runs the ```bash blocks. Only the blocks that clone
the repository are run (the `claude plugin` block needs the Claude CLI).

Two edits keep the run self-contained, and nothing else in the commands changes:
- the clone URL points at this checkout, so a pull request tests its own files;
- the home folder points at a fresh temporary folder: HOME (and USERPROFILE) are set to it, so bash's
  `~/` expands there, and PowerShell's `$HOME\\` is replaced by that path (the commands already quote it). The real ~/.claude and
  ~/.agents are never touched. The temp-folder variables point at a scratch folder, and Git runs
  with no global, system or environment config and an empty hooks folder.

Afterwards each installed copy must match skills/study-guide byte for byte and build the demo page.
Not covered: the public URL and its default branch, the plugin install, the ZIP route, and whether
an agent app then discovers the skill.

    python tests/install_docs.py
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
    """True when both folders hold the same files with the same bytes (ignoring __pycache__)."""
    cmp = filecmp.dircmp(a, b, ignore=["__pycache__"])
    if cmp.left_only or cmp.right_only or cmp.funny_files or cmp.common_funny:
        return False
    match, mismatch, errors = filecmp.cmpfiles(a, b, cmp.common_files, shallow=False)
    if mismatch or errors:
        return False
    return all(same_tree(Path(a) / d, Path(b) / d) for d in cmp.common_dirs)


def isolated_env(home, work):
    """Environment for the pasted commands: temp home and temp folder, and Git with no outside config or hooks."""
    env = {k: v for k, v in os.environ.items()
           if not k.upper().startswith("GIT_") and k.upper() not in ("BASH_ENV", "ENV", "CDPATH")}
    empty = home / ".gitconfig-empty"
    empty.write_text("", encoding="utf-8")
    no_hooks = home / ".no-git-hooks"
    no_hooks.mkdir(exist_ok=True)
    env.update(HOME=str(home), USERPROFILE=str(home), TMPDIR=work, TEMP=work, TMP=work,
               GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=str(empty),
               GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="core.hooksPath", GIT_CONFIG_VALUE_0=str(no_hooks))
    return env


def run(shell, cmd, home):
    work = tempfile.mkdtemp(prefix="sg-install-")
    src = ROOT.as_uri() if WIN else str(ROOT)
    assert f"git clone {URL}" in cmd, "the guide's clone command changed; update this test"
    script = cmd.replace(f"git clone {URL}", f'git clone "{src}"')
    if shell == "bash":
        assert "~/" in script, "the bash commands no longer use ~/; update this test"
        argv = ["bash", "--noprofile", "--norc", "-euo", "pipefail", "-c", script]
    else:
        assert "$HOME\\" in script, "the PowerShell commands no longer use $HOME\\; update this test"
        script = "$ErrorActionPreference = 'Stop'\n" + script.replace("$HOME\\", f"{home}\\")
        argv = [shell, "-NoProfile", "-NonInteractive", "-Command", script]
    print(f"$ ({shell}, in {work})\n{script}", flush=True)
    subprocess.run(argv, cwd=work, env=isolated_env(home, work), check=True)


def check(target):
    assert (target / "SKILL.md").is_file(), f"not installed: {target}"
    assert same_tree(ROOT / "skills" / "study-guide", target), f"installed copy differs from the repo: {target}"
    out = Path(tempfile.mkdtemp(prefix="sg-build-")) / "review.html"
    subprocess.run([sys.executable, str(target / "scripts" / "build.py"), str(target / "examples" / "demo"), "-o", str(out)], check=True)
    assert out.stat().st_size > 50_000, "built page is suspiciously small"
    print(f"ok: {target}", flush=True)


def main():
    lang = "powershell" if WIN else "bash"
    found = {doc: blocks(doc, lang) for doc in ("GETTING-STARTED.md", "GETTING-STARTED.zh.md")}
    assert found["GETTING-STARTED.md"] == found["GETTING-STARTED.zh.md"], "English and Chinese guides differ"
    cmds = found["GETTING-STARTED.md"]
    assert len(cmds) == 2, f"expected the Claude and Codex {lang} blocks, found {len(cmds)}"
    shells = [s for s in ("powershell", "pwsh") if shutil.which(s)] if WIN else ["bash"]
    assert shells, "no PowerShell found"
    if WIN and os.environ.get("CI") and len(shells) < 2:
        raise AssertionError(f"CI should test both Windows PowerShell and PowerShell 7, found {shells}")
    for shell in shells:
        home = Path(tempfile.mkdtemp(prefix="sg-home-"))
        for cmd in cmds:
            run(shell, cmd, home)
        for sub in (".claude", ".agents"):
            check(home / sub / "skills" / "study-guide")
    return 0


if __name__ == "__main__":
    sys.exit(main())
