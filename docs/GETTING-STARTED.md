# Getting started (no coding experience needed)

[中文版](GETTING-STARTED.zh.md)

This guide takes you from nothing installed to your first review page. You never have to write code: you talk to an AI assistant, and it does the technical steps.

**Short version:** install the Claude or ChatGPT app (step 2), open a folder for your exam, and send this one message, with your own course details:

> Install this skill for me so I can use it in every project: https://github.com/rzhang569/study-guide. Then read its SKILL.md and use it right away to make me a review page: my BIO 201 midterm is next Tuesday, it covers lectures 1–8, multiple choice plus two short answers. The slides are in this folder; if they aren't, get them yourself if you can.

Approve what it asks to do. If it needs Python, it installs it and tells you which button to click. The rest of this guide explains each step and what to do if something goes wrong.

## 1. What you need

- **A Mac or a Windows computer.**
- **One AI assistant** (pick one):
  - **Claude**: the Claude desktop app, using its **Code** tab. The Code tab needs a paid Claude plan (Pro, Max, Ultra, Team or Enterprise).
  - **Codex**: the ChatGPT desktop app, in **Codex** mode. Any ChatGPT account can sign in; Free and Go get a smaller model, so a paid plan works better for long exams.
- **Python 3**, which builds the page. If it's missing, the AI installs it for you (step 3).
- **Your course slides** as PDFs, or let the AI fetch them (step 5).

## 2. Install the AI app

**Claude**

1. Download the Claude app for [macOS](https://claude.ai/api/desktop/darwin/universal/dmg/latest/redirect) or [Windows](https://claude.ai/api/desktop/win32/x64/setup/latest/redirect) ([Windows on ARM](https://claude.ai/api/desktop/win32/arm64/setup/latest/redirect)) and run the installer.
2. Open Claude and sign in.
3. Click **Code** at the top of the sidebar. If it asks you to upgrade, you need a paid plan first.
4. Under the prompt box, click the folder control, choose **Open folder…**, and pick (or create) a folder for this exam, for example `Documents/BIO201-midterm`.
5. Windows only: if Claude asks for **Git for Windows**, install it from [git-scm.com](https://git-scm.com/downloads/win) and restart Claude.

**Codex**

1. Download the ChatGPT desktop app from [chatgpt.com/download](https://chatgpt.com/download/) and install it.
2. Open it, sign in, and switch to **Codex**.
3. Under **Choose where to work**, open (or create) a folder for this exam, for example `Documents/BIO201-midterm`.

## 3. Check that Python is installed

You can skip this step: when the AI needs Python and it's missing, it installs it for you. You only click the button it tells you about (on a Mac, **Install** in Apple's window; on Windows, **Yes** if Windows asks for permission).

To check ahead of time, ask your AI:

> Check whether Python 3 is installed on this computer. If it isn't, install it for me and tell me what to click.

Or check yourself:

- **Mac:** open **Terminal** (press `Cmd` + `Space`, type `Terminal`, press `Enter`) and type `python3 --version`, then `Enter`. If you see `Python 3.x.x`, you're done. If a window offers to install the **command line developer tools**, click **Install** and wait; that installs Python 3 (and Git).
- **Windows:** install the **Python install manager** from [python.org/downloads](https://www.python.org/downloads/) or from the **Microsoft Store** (search for "Python install manager"). If it asks whether to add a folder to your PATH, say yes. To check, open **PowerShell** (Start menu, type `PowerShell`) and type `py --version`.

## 4. Install the skill

### Easiest: let the AI install it

Send the one message from the top of this guide: it installs the skill and makes your first page in the same chat. (If you want the AI to get your slides from Canvas, do step 5 first.)

To only install it for now, send:

> Please install this skill for me so I can use it in every project: https://github.com/rzhang569/study-guide

Approve when it asks to download or copy files, or to run Python. When it says it's done, start a new chat before you ask for a review page, so the skill loads (or tell it to read the skill's SKILL.md and continue).

Tested with Codex (it installs the skill into `~/.codex/skills/study-guide` by itself) and with Claude Code on Windows. In the Claude test, the first try copied the whole repository into the skills folder, which doesn't work: only the `skills/study-guide` folder belongs there. If the skill doesn't show up later (see **Check that it worked**), tell the AI: *"Copy only the skills/study-guide folder into the skills folder, so SKILL.md is directly inside it."*

If the AI says a step needs your approval, approve it. If it says a step was refused or blocked by a setting, run that step yourself with the commands below.

### Or install it by hand

You can paste these into **Terminal** (Mac) or **PowerShell** (Windows). They need **Git**. Check first by typing `git --version`:

- **Mac:** if it isn't installed, a window offers the **command line developer tools**; click **Install** (or type `xcode-select --install`).
- **Windows:** install [Git for Windows](https://git-scm.com/downloads/win), then open a new PowerShell window.

No Git? Skip to **Without Git** below.

The commands download the repository into a new temporary folder, then copy the skill out of it; the copy only runs if the download worked. Running them again later updates the skill.

**Claude**, if you also have the `claude` command (the Claude Code command-line tool):

```bash
claude plugin marketplace add rzhang569/study-guide
claude plugin install study-guide@study-guide
```

**Claude (desktop app only)**, Mac:

```bash
d=$(mktemp -d) && git clone https://github.com/rzhang569/study-guide.git "$d/study-guide" && mkdir -p ~/.claude/skills && cp -R "$d/study-guide/skills/study-guide" ~/.claude/skills/
```

**Claude (desktop app only)**, Windows PowerShell:

```powershell
$d = Join-Path $env:TEMP "study-guide-$(Get-Random)"
git clone https://github.com/rzhang569/study-guide.git "$d\study-guide"
if ($LASTEXITCODE -eq 0) {
  New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
  Copy-Item -Recurse -Force "$d\study-guide\skills\study-guide" "$HOME\.claude\skills\"
}
```

**Codex**, Mac:

```bash
d=$(mktemp -d) && git clone https://github.com/rzhang569/study-guide.git "$d/study-guide" && mkdir -p ~/.agents/skills && cp -R "$d/study-guide/skills/study-guide" ~/.agents/skills/
```

**Codex**, Windows PowerShell:

```powershell
$d = Join-Path $env:TEMP "study-guide-$(Get-Random)"
git clone https://github.com/rzhang569/study-guide.git "$d\study-guide"
if ($LASTEXITCODE -eq 0) {
  New-Item -ItemType Directory -Force "$HOME\.agents\skills" | Out-Null
  Copy-Item -Recurse -Force "$d\study-guide\skills\study-guide" "$HOME\.agents\skills\"
}
```

**Without Git:** on the [repository page](https://github.com/rzhang569/study-guide), click **Code → Download ZIP** and unzip it. Copy the folder `skills/study-guide` into the skills folder from the commands above (`.claude/skills` for Claude, `.agents/skills` for Codex, inside your home folder). These folders start with a dot, so they are hidden: on a Mac, press `Cmd` + `Shift` + `.` in Finder to show them; on Windows, paste `%USERPROFILE%` into the File Explorer address bar and create the folders if they don't exist.

### Check that it worked

Start a new chat, then:

- **Claude:** type `/` and look for **study-guide** in the list.
- **Codex app:** type `@` and look for **study-guide**. (In the Codex command line, type `$study-guide`.)

Not there? Open the skills folder and check that `SKILL.md` is directly inside `study-guide` (for Claude, `.claude/skills/study-guide/SKILL.md` in your home folder), not inside another `skills/study-guide` folder deeper down.

## 5. Optional: let the AI fetch your files from Canvas

Without this, you download your slides yourself and drag them into the chat. With it, the AI can open Canvas (or Moodle, Blackboard…) in **your** Chrome, where you're already signed in, and download the slides for you.

**Claude**

1. In Chrome, open the [Claude extension in the Chrome Web Store](https://chromewebstore.google.com/detail/claude/fcoeoabgfenejglbffodgkkbkcdhcgfn) and click **Add to Chrome**.
2. Sign in to the extension with the **same Claude account** as the app.
3. Pin it: click the puzzle-piece icon, then the pin next to **Claude**.

This needs a paid Claude plan. Claude uses it when a task needs your signed-in browser; if it says the browser tools are off, turn **Claude in Chrome** on for that chat (look for it among the connectors or tools next to the prompt box). If Claude says it can't reach your browser:

- in the Claude app, open **Settings → Customize → Connectors**, find **Claude in Chrome**, click **Configure** and turn it on;
- make sure the extension is signed in to the same Claude account as the app;
- restart Chrome and try again.

**Codex**

1. In the ChatGPT app, open **Settings → Computer Use**.
2. Select your browser and click **Install**; add the ChatGPT extension from the store page that opens.
3. Back in **Computer Use**, check that your browser now shows **Manage**.
4. In a Codex chat, type `@` and pick your browser (for example **@Chrome**) so Codex works in it. Use the Chrome profile where you installed the extension and are signed in to Canvas.

Codex asks before it uses each new website.

**What the AI may do with it:** the skill tells the AI to name the site, the course and the files and ask you first (if you already asked it to get the files from Canvas or another signed-in site, that counts as your yes), and to download only course material for your exam (never homework solutions or answer keys). If a sign-in page appears, you sign in; the AI never types your password. You can always say no and download the files yourself: on Canvas, open the course, go to **Files**, tick the slides you need, and click **Download** to get one zip. If the course has no **Files** link, open **Modules** and download each slide file from there.

## 6. Make your first review page

If you sent the one-message start, the AI is already doing this; skip to the end of this step. Otherwise, in the exam folder you opened in step 2, tell the AI about your exam, in your own words. For example:

> My BIO 201 midterm is next Tuesday. It covers lectures 1–8, 50 minutes, multiple choice plus two short answers, no calculator. The slides are in this folder. Make me a review page.

Or, if you have nothing downloaded yet:

> My BIO 201 midterm covers lectures 1–8. Help me get the slides and make me a review page.

The AI reads the slides, writes notes and questions, and builds one file, usually `review.html` inside a new folder. This can take a while for many lectures. When it's done:

- **Open the page** by double-clicking `review.html`; the AI should also open it for you in your usual (default) browser. Study in that browser, not in a preview pane inside the AI app. No internet is needed except for fonts and math formatting.
- **Keep using the same browser and the same file location**: your answers are saved in that browser.

## 7. Study, then come back for targeted practice

1. Read a lecture, then do the practice box at the end of it.
2. Take a timed mock exam from **Practice and exams → Mock exam**.
3. Click **Export progress**, then **Copy**, paste the report into the chat, and ask: *"Here's my progress. What should I review, and can you add drills for it?"* The AI writes new questions for exactly what you got wrong.

## 8. If something goes wrong

- **The AI doesn't seem to use the skill.** Say its name: *"Use the study-guide skill."* In Codex you can also pick it with `@` (app) or `$study-guide` (command line).
- **Python doesn't run on Windows.** Typing `python3` prints nothing or opens the Microsoft Store, or PowerShell says `python` "is not recognized". Use `py` instead (the AI should do this by itself; if it doesn't, tell it "use py on Windows"). If `py` is missing too, install the Python install manager (step 3) and open a new PowerShell window.
- **The Code tab asks you to upgrade.** Claude Code needs a paid Claude plan.
- **Formulas show as plain text.** You're offline; connect once and reload the page. The text version stays readable.
- **My answers disappeared.** Progress lives in the browser you used, so open the same `review.html` in the same browser. Switching computers or browsers starts the page fresh: **Export progress** saves a report the AI can read to write drills, but it can't be loaded back into the page.
- **Check your course's AI policy.** Some courses don't allow AI-made study material. The AI checks the syllabus, but you're responsible for following your course's rules.
