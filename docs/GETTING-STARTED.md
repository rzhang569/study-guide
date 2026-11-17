# Getting started (no coding experience needed)

[中文版](GETTING-STARTED.zh.md)

This guide takes you from nothing installed to your first review page, in about 15 minutes. You never have to write code: you talk to an AI assistant, and it does the technical steps.

## 1. What you need

- **A Mac or a Windows computer.**
- **One AI assistant** (pick one):
  - **Claude**: the Claude desktop app, using its **Code** tab. The Code tab needs a paid Claude plan (Pro, Max, Ultra, Team or Enterprise).
  - **Codex**: the ChatGPT desktop app, in **Codex** mode. Any ChatGPT account can sign in; Free and Go get a smaller model, so a paid plan works better for long exams.
- **Python 3**, which builds the page (step 3 checks it).
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

The easiest way is to ask your AI:

> Check whether Python 3 is installed on this computer. If it isn't, tell me how to install it, step by step.

Or check yourself:

- **Mac:** open **Terminal** (press `Cmd` + `Space`, type `Terminal`, press `Enter`) and type `python3 --version`, then `Enter`. If you see `Python 3.x.x`, you're done. If a window offers to install the **command line developer tools**, click **Install** and wait; that installs Python 3 (and Git).
- **Windows:** install the **Python install manager** from [python.org/downloads](https://www.python.org/downloads/) or from the **Microsoft Store** (search for "Python install manager"). If it asks whether to add a folder to your PATH, say yes. To check, open **PowerShell** (Start menu, type `PowerShell`) and type `py --version`.

## 4. Install the skill

### Easiest: let the AI install it

Paste this into your AI and send it:

> Please install this skill for me so I can use it in every project: https://github.com/rzhang569/study-guide

Approve when it asks to download or copy files. When it says it's done, **start a new chat** so the skill loads.

(Tested with Codex: it installs the skill into `~/.codex/skills/study-guide` by itself.)

### Or install it by hand

You can paste these into **Terminal** (Mac) or **PowerShell** (Windows). They need **Git**. Check first by typing `git --version`:

- **Mac:** if it isn't installed, a window offers the **command line developer tools**; click **Install** (or type `xcode-select --install`).
- **Windows:** install [Git for Windows](https://git-scm.com/downloads/win), then open a new PowerShell window.

No Git? Skip to **Without Git** below.

**Claude**, if you also have the `claude` command (the Claude Code command-line tool):

```bash
claude plugin marketplace add rzhang569/study-guide
claude plugin install study-guide@study-guide
```

**Claude (desktop app only)**, Mac:

```bash
git clone https://github.com/rzhang569/study-guide.git
mkdir -p ~/.claude/skills && cp -R study-guide/skills/study-guide ~/.claude/skills/
```

**Claude (desktop app only)**, Windows PowerShell:

```powershell
git clone https://github.com/rzhang569/study-guide.git
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Copy-Item -Recurse -Force study-guide\skills\study-guide "$HOME\.claude\skills\"
```

**Codex**, Mac:

```bash
git clone https://github.com/rzhang569/study-guide.git
mkdir -p ~/.agents/skills && cp -R study-guide/skills/study-guide ~/.agents/skills/
```

**Codex**, Windows PowerShell:

```powershell
git clone https://github.com/rzhang569/study-guide.git
New-Item -ItemType Directory -Force "$HOME\.agents\skills" | Out-Null
Copy-Item -Recurse -Force study-guide\skills\study-guide "$HOME\.agents\skills\"
```

**Without Git:** on the [repository page](https://github.com/rzhang569/study-guide), click **Code → Download ZIP** and unzip it. Copy the folder `skills/study-guide` into the skills folder from the commands above (`.claude/skills` for Claude, `.agents/skills` for Codex, inside your home folder). These folders start with a dot, so they are hidden: on a Mac, press `Cmd` + `Shift` + `.` in Finder to show them; on Windows, paste `%USERPROFILE%` into the File Explorer address bar and create the folders if they don't exist.

### Check that it worked

Start a new chat, then:

- **Claude:** type `/` and look for **study-guide** in the list.
- **Codex app:** type `@` and look for **study-guide**. (In the Codex command line, type `$study-guide`.)

## 5. Optional: let the AI fetch your files from Canvas

Without this, you download your slides yourself and drag them into the chat. With it, the AI can open Canvas (or Moodle, Blackboard…) in **your** Chrome, where you're already signed in, and download the slides for you.

**Claude**

1. In Chrome, open the [Claude extension in the Chrome Web Store](https://chromewebstore.google.com/detail/claude/fcoeoabgfenejglbffodgkkbkcdhcgfn) and click **Add to Chrome**.
2. Sign in to the extension with the **same Claude account** as the app.
3. Pin it: click the puzzle-piece icon, then the pin next to **Claude**.

Claude uses it when a task needs your signed-in browser. This needs a paid Claude plan. If Claude says it can't reach your browser:

- in the Claude app, open **Settings → Customize → Connectors**, find **Claude in Chrome**, click **Configure** and turn it on;
- make sure the extension is signed in to the same Claude account as the app;
- restart Chrome and try again.

**Codex**

1. In the ChatGPT app, open **Settings → Computer Use**.
2. Select your browser and click **Install**; add the ChatGPT extension from the store page that opens.
3. Back in **Computer Use**, check that your browser now shows **Manage**.
4. In a Codex chat, type `@` and pick your browser (for example **@Chrome**) so Codex works in it. Use the Chrome profile where you installed the extension and are signed in to Canvas.

Codex asks before it uses each new website.

**What the AI may do with it:** the skill tells the AI to ask you first, naming the site, the course and the files, and to download only course material for your exam (never homework solutions or answer keys). If a sign-in page appears, you sign in; the AI never types your password. You can always say no and download the files yourself: on Canvas, open the course, go to **Files**, tick the slides you need, and click **Download** to get one zip.

## 6. Make your first review page

In the exam folder you opened in step 2, tell the AI about your exam, in your own words. For example:

> My BIO 201 midterm is next Tuesday. It covers lectures 1–8, 50 minutes, multiple choice plus two short answers, no calculator. The slides are in this folder. Make me a review page.

Or, if you have nothing downloaded yet:

> My BIO 201 midterm covers lectures 1–8. Help me get the slides and make me a review page.

The AI reads the slides, writes notes and questions, and builds one file, usually `review.html` inside a new folder. This can take a while for many lectures. When it's done:

- **Open the page** by double-clicking `review.html`, or ask the AI to open it. It opens in your web browser; no internet is needed except for fonts and math formatting.
- **Keep using the same browser and the same file location**: your answers are saved in that browser.

## 7. Study, then come back for targeted practice

1. Read a lecture, then do the practice box at the end of it.
2. Take a timed mock exam from **Practice and exams → Mock exam**.
3. Click **Export progress**, then **Copy**, paste the report into the chat, and ask: *"Here's my progress. What should I review, and can you add drills for it?"* The AI writes new questions for exactly what you got wrong.

## 8. If something goes wrong

- **The AI doesn't seem to use the skill.** Say its name: *"Use the study-guide skill."* In Codex you can also pick it with `@` (app) or `$study-guide` (command line).
- **"python: command not found" on Windows.** Use `py` instead of `python`. If `py` is missing too, install the Python install manager (step 3) and open a new PowerShell window.
- **The Code tab asks you to upgrade.** Claude Code needs a paid Claude plan.
- **Formulas show as plain text.** You're offline; connect once and reload the page. The text version stays readable.
- **My answers disappeared.** Progress lives in the browser you used, so open the same `review.html` in the same browser. Switching computers or browsers starts the page fresh: **Export progress** saves a report the AI can read to write drills, but it can't be loaded back into the page.
- **Check your course's AI policy.** Some courses don't allow AI-made study material. The AI checks the syllabus, but you're responsible for following your course's rules.
