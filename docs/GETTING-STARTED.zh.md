# 新手指南（不需要会写代码）

[English](GETTING-STARTED.md)

跟着这份指南，从什么都没装，到做出第一个复习网页，大约 15 分钟。全程不用写代码：你只需要跟 AI 助手说话，技术上的步骤都由它来做。

## 1. 需要准备什么

- **一台 Mac 或 Windows 电脑。**
- **一个 AI 助手**（二选一）：
  - **Claude**：用 Claude 桌面版里的 **Code** 标签页。Code 需要 Claude 付费账号（Pro、Max、Ultra、Team 或 Enterprise）。
  - **Codex**：用 ChatGPT 桌面版里的 **Codex** 模式。任何 ChatGPT 账号都能登录；免费版和 Go 版用的是较小的模型，复习范围大的话，付费版效果更好。
- **Python 3**：生成网页要用，第 3 步会检查。
- **课件**：PDF 格式最好；也可以让 AI 帮你去拿（第 5 步）。

## 2. 安装 AI 助手

**Claude**

1. 下载 Claude 桌面版：[Mac](https://claude.ai/api/desktop/darwin/universal/dmg/latest/redirect)、[Windows](https://claude.ai/api/desktop/win32/x64/setup/latest/redirect)（[ARM 芯片的 Windows](https://claude.ai/api/desktop/win32/arm64/setup/latest/redirect)），运行安装程序。
2. 打开 Claude，登录。
3. 点侧边栏顶部的 **Code**。如果提示升级，说明需要先开通付费账号。
4. 在输入框下面点文件夹按钮，选 **Open folder…**，选一个专门放这次考试的文件夹（没有就新建一个），比如 `文稿/BIO201期中`。
5. 仅限 Windows：如果 Claude 提示要装 **Git for Windows**，到 [git-scm.com](https://git-scm.com/downloads/win) 下载安装，然后重启 Claude。

**Codex**

1. 从 [chatgpt.com/download](https://chatgpt.com/download/) 下载 ChatGPT 桌面版并安装。
2. 打开、登录，切换到 **Codex**。
3. 在 **Choose where to work** 里打开（或新建）一个放这次考试的文件夹，比如 `文稿/BIO201期中`。

## 3. 检查有没有装 Python

最简单的办法是直接问 AI：

> 帮我检查这台电脑有没有装 Python 3。如果没有，一步一步告诉我怎么装。

也可以自己检查：

- **Mac**：打开**终端**（按 `Cmd` + `空格`，输入 `终端` 或 `Terminal`，回车），输入 `python3 --version` 后回车。看到 `Python 3.x.x` 就说明装好了。如果弹出窗口问要不要安装"命令行开发者工具"，点**安装**，等它装完，Python 3 和 Git 就都有了。
- **Windows**：从 [python.org/downloads](https://www.python.org/downloads/) 或 **Microsoft Store**（搜 "Python install manager"）安装 **Python 安装管理器**。如果它问要不要把某个文件夹加到 PATH，选同意。检查方法：打开 **PowerShell**（开始菜单里搜 `PowerShell`），输入 `py --version`。

## 4. 安装 skill

### 最简单：让 AI 帮你装

把下面这句话复制给 AI，发送：

> Please install this skill for me so I can use it in every project: https://github.com/rzhang569/study-guide

它问能不能下载、复制文件或者运行 Python 时，点同意。它说装好之后，**新开一个对话**，skill 才会加载。

已用 Codex（它会自己把 skill 装到 `~/.codex/skills/study-guide`）和 Windows 上的 Claude Code 实测。Claude 那次第一遍把整个仓库都复制进了 skills 文件夹，这样是用不了的：skills 文件夹里只该放 `skills/study-guide` 这一个文件夹。如果后面发现 skill 没出现（见下面"检查装好没有"），就跟 AI 说：*"只把 skills/study-guide 这个文件夹复制到 skills 文件夹里，让 SKILL.md 直接在它下面。"*

如果 AI 说某一步要你批准，点同意就行。如果它说某一步被设置拒绝或拦住了，就用下面的命令自己来。

### 或者手动安装

下面的命令可以粘贴进**终端**（Mac）或 **PowerShell**（Windows）运行。这些命令需要 **Git**，先输入 `git --version` 检查一下：

- **Mac**：没装的话会弹窗问要不要安装"命令行开发者工具"，点**安装**（或者输入 `xcode-select --install`）。
- **Windows**：安装 [Git for Windows](https://git-scm.com/downloads/win)，装完重新打开一个 PowerShell 窗口。

不想装 Git？直接看下面的"没有 Git 的话"。

这些命令会先把仓库下载到一个新的临时文件夹，再从里面把 skill 复制出来；只有下载成功才会复制。以后再运行一次，就是更新 skill。

**Claude**，如果你装了 `claude` 命令（Claude Code 的命令行版）：

```bash
claude plugin marketplace add rzhang569/study-guide
claude plugin install study-guide@study-guide
```

**Claude（只装了桌面版）**，Mac：

```bash
cd "$(mktemp -d)" && git clone https://github.com/rzhang569/study-guide.git && mkdir -p ~/.claude/skills && cp -R study-guide/skills/study-guide ~/.claude/skills/
```

**Claude（只装了桌面版）**，Windows PowerShell：

```powershell
Set-Location (New-Item -ItemType Directory -Path "$env:TEMP\study-guide-$(Get-Random)")
git clone https://github.com/rzhang569/study-guide.git
if ($LASTEXITCODE -eq 0) {
  New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
  Copy-Item -Recurse -Force study-guide\skills\study-guide "$HOME\.claude\skills\"
}
```

**Codex**，Mac：

```bash
cd "$(mktemp -d)" && git clone https://github.com/rzhang569/study-guide.git && mkdir -p ~/.agents/skills && cp -R study-guide/skills/study-guide ~/.agents/skills/
```

**Codex**，Windows PowerShell：

```powershell
Set-Location (New-Item -ItemType Directory -Path "$env:TEMP\study-guide-$(Get-Random)")
git clone https://github.com/rzhang569/study-guide.git
if ($LASTEXITCODE -eq 0) {
  New-Item -ItemType Directory -Force "$HOME\.agents\skills" | Out-Null
  Copy-Item -Recurse -Force study-guide\skills\study-guide "$HOME\.agents\skills\"
}
```

**没有 Git 的话**：打开[仓库页面](https://github.com/rzhang569/study-guide)，点 **Code → Download ZIP**，解压。把里面的 `skills/study-guide` 文件夹，复制到上面命令里的 skills 文件夹：Claude 是个人文件夹下的 `.claude/skills`，Codex 是 `.agents/skills`。这两个文件夹名字以点开头，默认是隐藏的：Mac 上在访达里按 `Cmd` + `Shift` + `.` 就能显示；Windows 上在文件资源管理器的地址栏里粘贴 `%USERPROFILE%` 回车，没有这两个文件夹就自己新建。

### 检查装好没有

新开一个对话，然后：

- **Claude**：输入 `/`，在列表里找 **study-guide**。
- **Codex 桌面版**：输入 `@`，找 **study-guide**。（Codex 命令行版输入 `$study-guide`。）

找不到？打开 skills 文件夹看一眼：`SKILL.md` 要直接放在 `study-guide` 里面（Claude 的话是个人文件夹下的 `.claude/skills/study-guide/SKILL.md`），而不是更深一层的另一个 `skills/study-guide` 里。

## 5. 可选：让 AI 自己去 Canvas 拿资料

不装这一步：你自己下载课件，拖进对话框就行。装了这一步：AI 可以在**你自己的** Chrome 里（你已经登录了 Canvas、Moodle、Blackboard 等）打开课程页面，帮你下载课件。

**Claude**

1. 在 Chrome 里打开 [Chrome 应用商店的 Claude 插件页](https://chromewebstore.google.com/detail/claude/fcoeoabgfenejglbffodgkkbkcdhcgfn)，点**添加至 Chrome**。
2. 用和桌面版**同一个 Claude 账号**登录插件。
3. 固定插件：点浏览器右上角的拼图图标，再点 **Claude** 旁边的图钉。

这个插件需要 Claude 付费账号。需要用到你登录的浏览器时，Claude 会用上它；如果它说浏览器工具没打开，就给这个对话打开 **Claude in Chrome**（在输入框旁边的连接器或工具菜单里找）。如果 Claude 说连不上你的浏览器：

- 在 Claude 桌面版里打开 **Settings → Customize → Connectors**，找到 **Claude in Chrome**，点 **Configure** 并打开开关；
- 确认插件登录的是和桌面版同一个 Claude 账号；
- 重启 Chrome 再试。

**Codex**

1. 在 ChatGPT 桌面版里打开 **Settings → Computer Use**。
2. 选你的浏览器，点 **Install**，在弹出的扩展商店页面里添加 ChatGPT 插件。
3. 回到 **Computer Use**，确认你的浏览器旁边显示 **Manage**。
4. 在 Codex 对话里输入 `@`，选你的浏览器（比如 **@Chrome**），Codex 才会在里面操作。要用装了插件、并且登录了 Canvas 的那个 Chrome 用户。

Codex 每碰到一个新网站，都会先问你同不同意。

**AI 会用它做什么**：skill 要求 AI 先说清楚是哪个网站、哪门课、哪些文件，问过你再动手（如果你本来就让它去 Canvas 这类要登录的网站拿资料，这就算同意了），而且只下载考试范围内的课程资料，作业答案、参考答案一律不拿。碰到登录页，你自己登录，AI 绝不替你输密码。你随时可以拒绝，自己下载：在 Canvas 里进入这门课，点 **Files**，勾选需要的课件，点 **Download**，就会打包成一个 zip。如果这门课没有 **Files**，就进 **Modules**，一个一个下载课件。

## 6. 做第一个复习网页

在第 2 步打开的考试文件夹里，用自己的话把考试情况告诉 AI，比如：

> 我下周二考 BIO 201 期中，考第 1 到 8 讲，50 分钟，选择题加两道简答，不能用计算器。课件在这个文件夹里。帮我做一个复习网页。

如果你还什么都没下载：

> 我 BIO 201 期中考第 1 到 8 讲。帮我把课件拿下来，再做一个复习网页。

AI 会读课件、写笔记和题目，最后生成一个文件，一般是新文件夹里的 `review.html`。讲数多的话要花一些时间。做好之后：

- **打开网页**：双击 `review.html`；AI 也应该会用你平时的（默认）浏览器帮你打开。就在那个浏览器里复习，别在 AI 应用自带的预览窗口里做题。除了字体和公式显示，不需要联网。
- **固定用同一个浏览器、别挪文件位置**：你的作答记录存在这个浏览器里。

## 7. 刷题，然后让 AI 针对性加练

1. 读完一讲，就做这一讲末尾的练习。
2. 在 **练习和考试 → 模拟考试** 里做一套计时模拟考（英文界面是 Practice and exams → Mock exam）。
3. 点 **导出进度**（Export progress），再点 **复制**，把进度报告粘贴到对话框里问：*"这是我的进度，我该复习什么？能针对这些加几道练习吗？"* AI 会专门针对你错的地方出新题。

## 8. 遇到问题怎么办

- **AI 好像没用这个 skill**：直接点名，说"用 study-guide 这个 skill"。Codex 里也可以输入 `@`（桌面版）或 `$study-guide`（命令行版）来选它。
- **Windows 上 Python 运行不了**：输入 `python3` 没反应或者弹出 Microsoft Store，或者 PowerShell 说无法识别 `python`。改用 `py`（AI 应该会自己换；没换的话就跟它说"Windows 上用 py"）。如果 `py` 也找不到，按第 3 步装好 Python 安装管理器，再重新打开一个 PowerShell 窗口。
- **Code 标签页提示升级**：Claude Code 需要 Claude 付费账号。
- **公式显示成普通文字**：电脑没联网。联网后刷新一下页面就好；没联网时文字版也能看懂。
- **作答记录不见了**：记录存在你当时用的浏览器里，所以要用同一个浏览器打开同一个 `review.html`。换电脑或换浏览器，网页会从头开始：**导出进度**生成的报告可以交给 AI，让它针对性出题，但不能再导回网页里恢复记录。
- **注意课程的 AI 政策**：有些课不允许用 AI 做复习材料。AI 会去查教学大纲，但遵守课程规定是你自己的责任。
