/* Study guide engine: practice bank, step-by-step short answers, a practice box at the end of each
   page section, timed mock exams drawn from their own pool, and a mistake notebook.
   Input: window.STUDY_DATA = { config, practice, mock, short } (written by scripts/build.py).
   Progress lives in localStorage and is mirrored to the artifact db when the page runs as a Claude artifact. */
(function () {
  var DATA = window.STUDY_DATA || {};
  var CFG = DATA.config || {};
  var KEY = CFG.storageKey || "study-guide";

  /* ================= UI strings ================= */
  var STR = {
    zh: {
      partNo: "做题", title: "练习和考试",
      intro: "练习题和模拟考试的题互不重复。作答记录自动保存在这个浏览器里，和每节末尾「本节练习」是同一份。",
      tabPractice: "练习题", tabSA: "简答分步", tabMock: "模拟考试", tabBook: "错题本", tabBookN: "错题本（{n}）", tabsAria: "选择题库",
      scope: "范围", scopeAll: "全部（{n} 题）", scopeLec: "{lec}（{n} 题）", loading: "加载中",
      hintPractice: "选完马上看对错和解释，还能接着点别的选项，看它错在哪。多选题选好后点提交，按部分给分；填空题不分大小写、忽略空格，数值按大小判对。得分按第一次作答算。",
      hintSA: "每道拆成几步：先在纸上写，再填结果点「核对」；也可以直接看答案，对照标准答案自己判。按步骤给分。",
      hintMock: "每次从模拟题库里按各讲的比例随机抽一套：{parts}。作答时不显示对错，交卷后出成绩单，按讲和总分两个维度看表现，每个选项都有解释。「再抽一套」会优先抽还没做过的题。",
      hintTimer: "<b>计时：</b>做之前选好限时，点「开始计时」，倒计时显示在上面的条里，时间到自动交卷。",
      hintFlag: "<b>标记：</b>拿不准的题点题卡右上角的「🚩 标记」，题号会列在下面的条里，点题号直接跳过去；交卷后成绩单会告诉你标记的题错了几道、没标记的题又错了几道。",
      hintBook: "自动收集三类题：练习题第一次没做对的、模拟考交卷后做错的、模拟考里标记过的。每道题上面写着它是怎么进来的、你当时答的是什么。在这里重做不会改动原来的首次得分；重做对了就记为「重做对了」，默认只显示还没重做对的。",
      partSep: "、", partN: "{n} 道{name}",
      export: "导出进度", exportHint: "把这段内容交给 Claude（复制粘贴，或下载成文件），它会读出你的薄弱点，再出针对性的新题。", exportCopy: "复制", exportCopied: "已复制", exportSave: "下载 JSON",
      firstScore: "首次得分 {s}", fillAria: "填写答案", submit: "提交",
      fillRight: "<b>对了。</b>", fillWrong: "<b>不对。参考答案：{a}。</b>", fillFirst: "（第一次写的是「{v}」）",
      fillHint: "没认出这个答案，这次不算。写成数字或算式就行，比如 0.5、-1/2、2^-20、ln5；几个数用逗号隔开，比如 (1, -0.5)。",
      undo: "手滑了，这题重新算", undoArmed: "确定清掉这题的记录？再点一次", undoTitle: "清掉这道题的作答记录，下一次作答算作第一次", cancel: "取消",
      mRight: "✓ 选对了", mMissed: "漏选", mWrong: "✗ 不该选", mSkip: "不选，对", multiHint: "可以选多个，选好后点提交",
      reselect: "重新选", scoreNow: "这次得分 {s}（满分 1）", multiAns: "<b>正确答案：{a}。</b>",
      right: "正确答案", leadRight: "<b>第一次就选对了。</b>", leadWrong: "<b>第一次选了 {a}，正确答案是 {b}。</b>", moreOpts: "（还可以点其他选项，看它为什么不对）",
      optRight: "这个是对的。", optWrong: "这个不对，看下面的解释。",
      tMulti: "多选", tFill: "填空", tCard: "看答案", tSA: "简答",
      reveal: "看答案", answer: "<b>答案</b>",
      clearPractice: "清空练习记录", clearArmed: "确定清空？再点一次",
      practiceBar: "已答 <b>{d}</b> / {n} · 首次得分 <b>{s}</b>", pctParen: "（{p}%）",
      byLec: "按讲看正确率（按第一次作答算，全部范围）", noRecords: "还没有作答记录。", thLec: "讲", thScore: "得分", thPct: "正确率",
      emptyScope: "这个范围暂时没有题。",
      step: "第 {i} 步 · {p} 分", saBadge: "首次得分 {s} / {m}", saFixed: "（改对后 {f}）", optional: "选做 · 不计总分", optNote: "<b>不考推导：</b>",
      stepAria: "第 {i} 步的结果", tries: "不对{n}。改一下再核对，或者点「看答案」。", triesN: "（已经试了 {k} 次）",
      check: "核对", peek: "看答案", peekPaper: "写在纸上了，直接看答案", selfPeek: "写好了，看答案",
      stepRight: "<b>对了。</b>", fixedAfter: "（错了 {n} 次后改对）", stepWrong: "<b>不对。</b>", sol: "标准答案：",
      iRight: "我写对了", iWrong: "没写对", selfJudge: "对照标准答案自己判一下",
      redoStep: "改这一步，再做一次", override: "我觉得我写对了，算我对",
      redoSA: "重做这道题", saTotal: "这道题首次得分 {s} / {m}", saTotalFixed: "，改对后 {f} / {m}", saNote: "<b>小结：</b>",
      saBar: "已开始 <b>{a}</b> / {n} 道", saBarScore: " · 首次得分 <b>{s}</b> / {m}",
      secTitle: "本节练习", secMeta: "{n} 道题 · 已做 {d}", secPct: " · 第一次作答正确率 {p}%", secSA: " · 简答 {a} / {b}",
      close: "收起", start: "开始做题", resume: "接着做（还剩 {n} 题）", allDone: "全做完了，再看看",
      secSub: "简答 · 要写步骤", nextSec: "下一节 →", toMock: "去模拟考试 →",
      noAnswer: "没作答", noPick: "没选",
      notePractice: "练习第一次没做对，当时答的是 {a}", noteMock: "第 {k} 套模考做错", notePick: "，当时答的是 {a}",
      noteFlag: "第 {k} 套模考标记过", noteFlagOk: "，当时做对了",
      tagWrong: "错过", tagFlag: "🚩 标记过", tagOk: "重做对了", clearRedo: "清掉重做记录，再做一次", bookRemove: "从错题本移除", bookRemoveArmed: "确定移除？再点一次",
      bookBar: "错题本 <b>{n}</b> 道（错过 {w} · 标记过 {f}）· 还没重做对 <b>{l}</b> 道",
      fTodo: "还没重做对", fWrong: "只看错过的", fFlag: "只看标记过的", fAll: "全部",
      bookEmptyF: "这一类没有题了。", bookEmpty: "还没有错题。练习题第一次做错、模考交卷后做错或标记过的题，都会自动收进来。",
      score: "得分 {s}", flag: "🚩 标记", flagged: "🚩 已标记", flagTitle: "标记这道题，方便回头快速找到（再点一次取消）",
      correct: "<b>答对了。</b>", refAns: "<b>参考答案：{a}。</b>",
      youRight: "✓ 你选了，对", youWrong: "✗ 你选了，错", mockRight: "答对了。", mockWrong: "正确答案是 {a}。", mockMulti: "本题得分 {s}。",
      card: "答题卡", qn: "第 {i} 题", qOk: " · 对", qBad: " · 错", qAns: " · 已答", qUnans: " · 未答", qFlg: " · 标记了",
      legendDone: '<span class="qn ok sw"></span>对 <span class="qn bad sw"></span>错 <span class="qn flg sw"></span>标记过 · 点数字跳到那题',
      legendLive: '<span class="qn ans sw"></span>已答 <span class="qn sw"></span>未答 <span class="qn flg sw"></span>标记了 · 点数字跳到那题',
      flagHintStrip: "不确定的题点题卡右上角的 <b>🚩 标记</b>，这里会列出题号，点题号直接跳过去；交卷后也保留。",
      flagList: "<b>🚩 标记了 {n} 题：</b>", nextFlag: "跳到下一个标记", clearFlags: "清除全部标记", clearFlagsArmed: "确定清除？",
      redraw: "再抽一套", redrawArmed: "这套还没交，确定换一套？",
      mockBar: "模拟考试 · 已作答 <b>{a}</b> / {n}", fresh: " · 题库里还有 {u} 道没抽到过",
      limitAria: "限时", limitMin: "限时 {m} 分钟", noLimit: "不限时，只计用时", startTimer: "开始计时",
      submitAll: "交卷", submitLeft: "交卷（还有 {n} 题没答）", submitArmed: "还有 {n} 题没答，确定交卷？",
      submitted: "已交卷 · 得分 <b>{s}</b> / {m}（{p}%）", usedSuffix: " · 用时 {u}",
      report: "成绩单", prevPaper: "上一套：{p}%", outOf: "{s} / {m} 题", wrongList: "<b>没拿满分的题：</b>", allRight: "全对。",
      weakest: "这套里最弱的是 <b>{u}</b>，回去看这一讲，再到「练习题」里选这一讲练一遍。",
      autoSubmit: "<b>时间到，自动交卷。</b>", used: "用时 {u}", limitNote: "（限时 {m} 分钟）", noLimitNote: "（没有限时）",
      flaggedList: "<b>🚩 标记过的题：</b>", flagCal: "标记的 {n} 题里错了 {w} 题；没标记的题里还错了 {u} 题",
      flagCalBad: "，说明有些题你以为会其实不会，这类更要回头看。", flagCalGood: "，判断自己哪里不确定的感觉还挺准。",
      history: "历次模拟考试汇总（共 {n} 套）", recent: "最近几套的总分：",
      mockPart: "{no}、{title}（{n} 题）", nums: ["一", "二", "三", "四", "五", "六"],
      remain: "剩余", usedLbl: "已用",
      catTitle: { tf: "判断题", single: "单选题", multi: "多选题", fill: "填空题" },
      catDesc: { tf: "True / False。", single: "选一个最合适的。", multi: "可以选多个，按部分给分。", fill: "填最后的结果。数值按大小判对，分数、小数都行。" },
      catShort: { tf: "判断", single: "单选", multi: "多选", fill: "填空" },
      railK: "本节小节", railPrac: "本节练习 ↓"
    },
    en: {
      partNo: "Practice", title: "Practice and exams",
      intro: "Practice questions and mock exam questions never overlap. Your answers are saved in this browser and shared with the practice box at the end of each section.",
      tabPractice: "Practice", tabSA: "Short answer", tabMock: "Mock exam", tabBook: "Mistakes", tabBookN: "Mistakes ({n})", tabsAria: "Choose a bank",
      scope: "Scope", scopeAll: "All ({n})", scopeLec: "{lec} ({n})", loading: "Loading",
      hintPractice: "You see right or wrong and an explanation right away, and you can keep clicking other options to see why they are wrong. Multi-select questions need a Submit and earn partial credit; fill-ins ignore case and spaces, and numbers are compared by value. Scores count your first try.",
      hintSA: "Each question is split into steps. Work on paper, type the result and press Check, or reveal the model answer and mark yourself. Points are given per step.",
      hintMock: "Each paper is drawn at random from the mock pool in proportion to the lectures: {parts}. Answers stay hidden until you hand in; then you get a score report by lecture with an explanation for every option. New papers prefer questions you have not seen.",
      hintTimer: "<b>Timer:</b> pick a limit and press Start. The countdown sits in the bar above and the paper is handed in when it reaches zero.",
      hintFlag: "<b>Flags:</b> press 🚩 Flag on any question you are unsure about. Flagged numbers are listed below the bar for quick jumps, and the report compares flagged and unflagged mistakes.",
      hintBook: "Collects practice questions you missed on the first try, mock questions you got wrong, and mock questions you flagged. Each card says how it got here and what you answered. Redoing a question here never changes its first-try score; once you get it right it is marked as mastered.",
      partSep: ", ", partN: "{n} {name}",
      export: "Export progress", exportHint: "Give this to Claude (paste it or save it as a file). It reads your weak spots and writes new targeted questions.", exportCopy: "Copy", exportCopied: "Copied", exportSave: "Download JSON",
      firstScore: "First try {s}", fillAria: "Your answer", submit: "Submit",
      fillRight: "<b>Correct.</b>", fillWrong: "<b>Not quite. Answer: {a}.</b>", fillFirst: " (first try: “{v}”)",
      fillHint: "Could not read that answer, so it was not recorded. Type a number or an expression such as 0.5, -1/2, 2^-20 or ln5; separate several numbers with commas, e.g. (1, -0.5).",
      undo: "Misclick: reset this question", undoArmed: "Clear this question's record? Click again", undoTitle: "Clear this question's record so the next answer counts as the first", cancel: "Cancel",
      mRight: "✓ correct pick", mMissed: "missed", mWrong: "✗ should not pick", mSkip: "not picked, right", multiHint: "Pick all that apply, then submit",
      reselect: "Try again", scoreNow: "This try {s} (out of 1)", multiAns: "<b>Answer: {a}.</b>",
      right: "answer", leadRight: "<b>Right on the first try.</b>", leadWrong: "<b>First pick was {a}; the answer is {b}.</b>", moreOpts: " (click the other options to see why they are wrong)",
      optRight: "This one is correct.", optWrong: "This one is wrong; see the explanation below.",
      tMulti: "multi", tFill: "fill-in", tCard: "flashcard", tSA: "short answer",
      reveal: "Show answer", answer: "<b>Answer</b>",
      clearPractice: "Clear practice record", clearArmed: "Clear everything? Click again",
      practiceBar: "Answered <b>{d}</b> / {n} · first-try score <b>{s}</b>", pctParen: " ({p}%)",
      byLec: "First-try accuracy by lecture (all questions)", noRecords: "No answers yet.", thLec: "Lecture", thScore: "Score", thPct: "Accuracy",
      emptyScope: "No questions in this scope yet.",
      step: "Step {i} · {p} pt", saBadge: "First try {s} / {m}", saFixed: " (after fixes {f})", optional: "optional · not counted", optNote: "<b>Not on the exam:</b> ",
      stepAria: "Result of step {i}", tries: "Not right{n}. Edit and check again, or reveal the answer.", triesN: " ({k} tries so far)",
      check: "Check", peek: "Show answer", peekPaper: "Done on paper, show answer", selfPeek: "Done, show answer",
      stepRight: "<b>Correct.</b>", fixedAfter: " (fixed after {n} wrong tries)", stepWrong: "<b>Not right.</b>", sol: "Model answer: ",
      iRight: "I got it", iWrong: "I missed it", selfJudge: "Compare with the model answer and mark yourself",
      redoStep: "Redo this step", override: "My answer is right, count it",
      redoSA: "Redo this question", saTotal: "First-try score {s} / {m}", saTotalFixed: ", after fixes {f} / {m}", saNote: "<b>Summary:</b> ",
      saBar: "Started <b>{a}</b> / {n}", saBarScore: " · first-try score <b>{s}</b> / {m}",
      secTitle: "Practice for this section", secMeta: "{n} questions · {d} done", secPct: " · first-try accuracy {p}%", secSA: " · short answer {a} / {b}",
      close: "Close", start: "Start", resume: "Continue ({n} left)", allDone: "All done, review",
      secSub: "Short answer · show your steps", nextSec: "Next section →", toMock: "Go to the mock exam →",
      noAnswer: "no answer", noPick: "nothing picked",
      notePractice: "Missed on the first practice try; you answered {a}", noteMock: "Wrong on mock paper {k}", notePick: "; you answered {a}",
      noteFlag: "Flagged on mock paper {k}", noteFlagOk: ", answered correctly",
      tagWrong: "missed", tagFlag: "🚩 flagged", tagOk: "mastered", clearRedo: "Clear the redo and try again", bookRemove: "Remove from notebook", bookRemoveArmed: "Remove it? Click again",
      bookBar: "<b>{n}</b> questions (missed {w} · flagged {f}) · <b>{l}</b> not yet mastered",
      fTodo: "Not mastered", fWrong: "Missed", fFlag: "Flagged", fAll: "All",
      bookEmptyF: "Nothing left in this view.", bookEmpty: "No mistakes yet. First-try practice misses and wrong or flagged mock questions land here automatically.",
      score: "Score {s}", flag: "🚩 Flag", flagged: "🚩 Flagged", flagTitle: "Flag this question to find it again quickly (click again to remove)",
      correct: "<b>Correct.</b>", refAns: "<b>Answer: {a}.</b>",
      youRight: "✓ your pick, right", youWrong: "✗ your pick, wrong", mockRight: "Correct.", mockWrong: "The answer is {a}.", mockMulti: "Score {s}.",
      card: "Answer sheet", qn: "Question {i}", qOk: " · right", qBad: " · wrong", qAns: " · answered", qUnans: " · blank", qFlg: " · flagged",
      legendDone: '<span class="qn ok sw"></span>right <span class="qn bad sw"></span>wrong <span class="qn flg sw"></span>flagged · tap a number to jump',
      legendLive: '<span class="qn ans sw"></span>answered <span class="qn sw"></span>blank <span class="qn flg sw"></span>flagged · tap a number to jump',
      flagHintStrip: "Press <b>🚩 Flag</b> on a question you are unsure about; its number shows up here for a quick jump, and flags stay after you hand in.",
      flagList: "<b>🚩 {n} flagged:</b> ", nextFlag: "Next flag", clearFlags: "Clear all flags", clearFlagsArmed: "Clear them?",
      redraw: "New paper", redrawArmed: "This paper is not handed in. Switch anyway?",
      mockBar: "Mock exam · answered <b>{a}</b> / {n}", fresh: " · {u} questions in the pool not drawn yet",
      limitAria: "Time limit", limitMin: "{m} minutes", noLimit: "No limit, just time me", startTimer: "Start",
      submitAll: "Hand in", submitLeft: "Hand in ({n} blank)", submitArmed: "{n} still blank. Hand in anyway?",
      submitted: "Handed in · score <b>{s}</b> / {m} ({p}%)", usedSuffix: " · time {u}",
      report: "Score report", prevPaper: "Previous paper: {p}%", outOf: "{s} / {m}", wrongList: "<b>Not full marks:</b> ", allRight: "All correct.",
      weakest: "Your weakest lecture on this paper is <b>{u}</b>. Reread it, then practice that lecture in the Practice tab.",
      autoSubmit: "<b>Time ran out; the paper was handed in.</b> ", used: "Time {u}", limitNote: " (limit {m} min)", noLimitNote: " (no limit)",
      flaggedList: "<b>🚩 Flagged:</b> ", flagCal: "You got {w} of your {n} flagged questions wrong and {u} unflagged ones wrong",
      flagCalBad: ", so some questions you felt sure about need another look.", flagCalGood: ", so your sense of what you are unsure about is fairly accurate.",
      history: "All mock papers ({n})", recent: "Recent totals: ",
      mockPart: "Part {no}. {title} ({n})", nums: ["1", "2", "3", "4", "5", "6"],
      remain: "Left", usedLbl: "Used",
      catTitle: { tf: "True / False", single: "Multiple choice", multi: "Multiple select", fill: "Fill in" },
      catDesc: { tf: "True or false.", single: "Pick the best answer.", multi: "Pick all that apply; partial credit.", fill: "Type the final result. Numbers are compared by value; fractions and decimals both work." },
      catShort: { tf: "true/false", single: "multiple choice", multi: "multiple select", fill: "fill-in" },
      railK: "In this section", railPrac: "Section practice ↓"
    }
  };
  var S = STR[CFG.lang] || STR.zh, ZH = S === STR.zh;
  function t(k, v) {
    var s = S[k] != null ? S[k] : STR.zh[k];
    if (s == null) return k;
    return v ? String(s).replace(/\{(\w+)\}/g, function (m, n) { return v[n] != null ? v[n] : m; }) : s;
  }

  /* ================= data ================= */
  var L = ["A", "B", "C", "D", "E", "F", "G", "H"];
  var TF_LABELS = CFG.tfLabels || ["True", "False"];
  function seeded(str) {
    var h = 2166136261;
    for (var i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); }
    return function () { h += 0x6D2B79F5; var x = h; x = Math.imul(x ^ (x >>> 15), x | 1); x ^= x + Math.imul(x ^ (x >>> 7), x | 61); return ((x ^ (x >>> 14)) >>> 0) / 4294967296; };
  }
  function range(n) { for (var a = [], k = 0; k < n; k++) a.push(k); return a; }
  function shuffleWith(rnd, a) { for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(rnd() * (i + 1)); var x = a[i]; a[i] = a[j]; a[j] = x; } return a; }
  function shuffle(a) { return shuffleWith(Math.random, a); }
  function seededOrder(seed, n) { return shuffleWith(seeded(seed), range(n)); }
  /* answers are stored by original option index; only the display order is shuffled, with a seed from the
     question id so the order is stable across reloads. True/false keeps True first. */
  var ORDER = {};
  function displayOrder(q) {
    if (ORDER[q.id]) return ORDER[q.id];
    var n = q.opts.length, order;
    if (q.cat === "tf" || q.fixed || n < 3) order = range(n);
    else {
      order = seededOrder(KEY + ":" + q.id, n);
      /* "show": "B" puts a single-choice answer at that letter; it changes only the display, never the stored
         indexes, so it can rebalance answer letters without breaking anyone's saved answers */
      var at = q.type === "single" && q.show ? L.indexOf(String(q.show).toUpperCase()) : -1;
      if (at >= 0 && at < n) { order = order.filter(function (i) { return i !== q.ans; }); order.splice(at, 0, q.ans); }
    }
    ORDER[q.id] = order;
    return order;
  }
  function letterOf(q, i) { return L[displayOrder(q).indexOf(i)]; }

  function prep(bank, name) {
    bank = bank || {};
    var b = { key: name, groups: bank.groups || [], items: bank.items || [], gmap: {}, imap: {} };
    b.groups.forEach(function (g) { b.gmap[g.id] = g; });
    b.items.forEach(function (q) {
      var g = b.gmap[q.g] || {};
      if (!q.type) q.type = "single";
      if (q.type === "tf" && !q.opts) q.opts = [{}, {}];
      if (q.opts) q.opts = q.opts.map(function (x, i) {
        var o = typeof x === "string" ? { t: x } : x;
        if (q.type === "tf" && o.t == null) o.t = TF_LABELS[i];
        return o;
      });
      if (q.type === "single" && q.opts && q.opts.length === 2 && q.opts[0].t === TF_LABELS[0] && q.opts[1].t === TF_LABELS[1]) q.type = "tf";
      q.cat = q.type;
      q.lec = q.lec || g.lec || "";
      q.sec = q.sec || g.sec || "";
      b.imap[q.id] = q;
    });
    return b;
  }
  var BANKS = { practice: prep(DATA.practice, "practice"), mock: prep(DATA.mock, "mock") };
  BANKS.mock.items = BANKS.mock.items.filter(function (q) { return q.type !== "card"; });
  var SAD = DATA.short || {}, SA_GROUPS = SAD.groups || [], SA = SAD.items || [], SAG = {};
  SA_GROUPS.forEach(function (x) { SAG[x.id] = x; });
  SA.forEach(function (s) {
    var gr = SAG[s.k] || {}, pg = BANKS.practice.gmap[gr.g] || {};
    s.kind = s.kind || gr.kind || "";
    s.lec = s.lec || gr.lec || pg.lec || "";
    s.sec = s.sec || gr.sec || pg.sec || "";
  });

  var LECS = (CFG.lectures || []).slice();
  BANKS.practice.items.concat(BANKS.mock.items, SA).forEach(function (q) { if (q.lec && LECS.indexOf(q.lec) < 0) LECS.push(q.lec); });

  var MCFG = CFG.mock || {};
  var MOCK_SECTIONS = (MCFG.sections || [{ cat: "tf", n: 10 }, { cat: "single", n: 10 }, { cat: "multi", n: 5 }, { cat: "fill", n: 5 }]).filter(function (x) { return x.n > 0; });
  var WEIGHTS = MCFG.weights || null;
  var MINUTES = (MCFG.minutes || [45, 0]).map(function (m) { return typeof m === "number" ? { m: m } : m; });
  var DEF_MIN = MCFG.defaultMinutes != null ? MCFG.defaultMinutes : MINUTES[0].m;

  /* ================= storage: localStorage first, mirrored to the artifact db ================= */
  function blankPractice() { return { v: 1, scope: "all", ans: {}, sa: {}, redo: {}, updatedAt: "" }; }
  function blankMock() { return { v: 1, paper: [], draft: {}, flags: {}, seen: {}, pcount: 0, submitted: false, result: null, history: [], timer: { limit: DEF_MIN, startedAt: "" }, updatedAt: "" }; }
  function fix(key, raw) {
    var st = key === "practice" ? blankPractice() : blankMock();
    if (raw && typeof raw === "object" && raw.v === 1) Object.keys(raw).forEach(function (k) { st[k] = raw[k]; });
    if (key === "mock") {
      st.paper = (st.paper || []).filter(function (id) { return BANKS.mock.imap[id]; });
      st.draft = st.draft || {}; st.history = st.history || []; st.flags = st.flags || {}; st.seen = st.seen || {}; st.pcount = st.pcount || 0;
      if (!st.timer || typeof st.timer !== "object") st.timer = { limit: DEF_MIN, startedAt: "" };
    } else { st.ans = st.ans || {}; st.sa = st.sa || {}; st.redo = st.redo || {}; }
    return st;
  }
  function lsGet(k) { try { return localStorage.getItem(KEY + ":" + k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(KEY + ":" + k, v); } catch (e) {} }
  function readLocal(key) { try { var v = lsGet(key); return v ? JSON.parse(v) : null; } catch (e) { return null; } }
  function writeLocal(key, st) { lsSet(key, JSON.stringify(st)); }

  var dbp = (window.claude && window.claude.use) ? window.claude.use("db").catch(function () { return null; }) : Promise.resolve(null);
  var dbTimers = {}, dbBusy = {}, dbAgain = {};
  function pushDb(key) {
    clearTimeout(dbTimers[key]);
    dbTimers[key] = setTimeout(function () {
      dbp.then(function (db) {
        if (!db) return;
        if (dbBusy[key]) { dbAgain[key] = true; return; }
        dbBusy[key] = true;
        var doc = key === "report" ? buildReport() : { v: 1, state: JSON.parse(JSON.stringify(STATE[key])), updatedAt: STATE[key].updatedAt };
        db.doc("progress/" + key).set(doc)
          .catch(function () {})
          .then(function () { dbBusy[key] = false; if (dbAgain[key]) { dbAgain[key] = false; pushDb(key); } });
      });
    }, key === "report" ? 2500 : 900);
  }
  var STATE = {};
  function save(key) {
    var st = STATE[key];
    st.updatedAt = new Date().toISOString();
    writeLocal(key, st);
    pushDb(key); pushDb("report");
  }
  function hasData(key, st) {
    if (!st) return false;
    if (key === "practice") return Object.keys(st.ans || {}).length > 0 || Object.keys(st.sa || {}).length > 0;
    return (st.paper || []).length > 0 || (st.history || []).length > 0;
  }
  function syncFromDb(key) {
    dbp.then(function (db) {
      if (!db) return;
      db.doc("progress/" + key).get().then(function (snap) {
        var local = STATE[key];
        if (!snap.exists) { if (hasData(key, local)) pushDb(key); return; }
        var d = snap.data() || {};
        var remote = fix(key, d.state);
        if (!hasData(key, local) || (remote.updatedAt && remote.updatedAt > (local.updatedAt || ""))) {
          if (hasData(key, remote)) { STATE[key] = remote; writeLocal(key, remote); render(key); }
        } else if (JSON.stringify(remote) !== JSON.stringify(local)) {
          pushDb(key);
        }
      }).catch(function () {});
    });
  }

  /* ================= scoring ================= */
  function norm(s) {
    return String(s == null ? "" : s).toLowerCase()
      .replace(/[−–—]/g, "-").replace(/[，、]/g, ",").replace(/[×]/g, "x")
      .replace(/[`'"“”‘’()\[\]（）_]/g, "").replace(/\s+/g, "").replace(/[。.;；,，]+$/, "");
  }
  /* Numeric answers are compared by value, not by spelling: what was typed is evaluated (fractions, powers, logs,
     superscripts, vectors, "v3 = 5.42") and matched against the reference within rounding. */
  var SUPD = { "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9", "⁻": "-" };
  function evalExpr(src) {
    var s = String(src).toLowerCase()
      .replace(/[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+/g, function (m) { return "^(" + m.split("").map(function (c) { return SUPD[c]; }).join("") + ")"; })
      .replace(/[−–—]/g, "-").replace(/\*\*/g, "^").replace(/[×·*]/g, "*").replace(/÷/g, "/").replace(/√/g, "sqrt")
      .replace(/[（［【{]/g, "(").replace(/[）］】}]/g, ")").replace(/\s+/g, "");
    var i = 0;
    function fail() { throw new Error("parse"); }
    function expr() { var v = term(); while (s[i] === "+" || s[i] === "-") { var o = s[i++], x = term(); v = o === "+" ? v + x : v - x; } return v; }
    function term() {
      var v = unary();
      for (;;) {
        if (s[i] === "*" || s[i] === "/") { var o = s[i++], x = unary(); v = o === "*" ? v * x : v / x; }
        else if (s[i] === "(" || /[a-z\d.]/.test(s[i] || "")) v *= unary();
        else return v;
      }
    }
    function unary() { if (s[i] === "-") { i++; return -unary(); } if (s[i] === "+") { i++; return unary(); } return power(); }
    function power() { var b = atom(); if (s[i] === "^") { i++; return Math.pow(b, unary()); } return b; }
    function atom() {
      if (s[i] === "(" || s[i] === "[") { i++; var v = expr(); if (s[i] === ")" || s[i] === "]") i++; else fail(); return pc(v); }
      var m = s.slice(i).match(/^(\d+\.?\d*|\.\d+)(e[-+]?\d+)?/);
      if (m) { i += m[0].length; if (s[i] === ".") fail(); return pc(parseFloat(m[0])); }  /* "2.5.3" is not 2.5 × .3 */
      var fn = s.slice(i).match(/^(sqrt|ln|log|exp|pi|e)/);
      if (!fn) fail();
      i += fn[0].length;
      if (fn[1] === "pi") return Math.PI;
      if (fn[1] === "e") return Math.E;
      var a = power();
      return fn[1] === "sqrt" ? Math.sqrt(a) : fn[1] === "exp" ? Math.exp(a) : Math.log(a);
    }
    function pc(v) { if (s[i] === "%") { i++; return v / 100; } return v; }
    try { var v = expr(); return i === s.length && isFinite(v) ? v : null; } catch (e) { return null; }
  }
  function splitTop(s) {
    var out = [], depth = 0, cur = "";
    for (var k = 0; k < s.length; k++) {
      var c = s[k];
      if (c === "(" || c === "[") depth++;
      if (c === ")" || c === "]") depth--;
      if (depth === 0 && /[,，、;；]/.test(c)) { out.push(cur); cur = ""; } else cur += c;
    }
    out.push(cur);
    return out;
  }
  function numsOf(v, want) {
    var s = String(v == null ? "" : v).replace(/[`'"“”‘’]/g, "").trim().split(/[=≈]/).pop().replace(/^[~～]/, "").trim();
    if (!s) return null;
    /* "1,000" is one thousand when a single number is wanted; with a vector answer it stays the list (1, 0) */
    if (!(want > 1) && /^[-+−]?[1-9]\d{0,2}(,\d{3})+(\.\d+)?$/.test(s)) s = s.replace(/,/g, "");
    var inner = s.replace(/^[(\[（［【{]/, "").replace(/[)\]）］】}]$/, "");
    var parts = splitTop(inner);
    if (parts.length === 1 && want > 1 && /\s/.test(inner.trim())) parts = inner.trim().split(/\s+/);
    if (parts.length === 1) { var one = evalExpr(s); return one == null ? null : [one]; }
    var vals = parts.map(evalExpr);
    return vals.some(function (x) { return x == null; }) ? null : vals;
  }
  function approx(v, a) {
    var d = Math.abs(v - a), m = Math.abs(a);
    if (a === 0) return Math.abs(v) <= 0.0005;
    if (m >= 0.1) return d <= 0.011 + 0.005 * m;
    if (m >= 0.01) return d <= Math.max(0.0006, 0.03 * m);
    return d <= 0.1 * m;
  }
  /* true / false, or null when the answer could not be read at all (then nothing is recorded) */
  function fillCheck(q, v) {
    var n = norm(v);
    if (!n) return null;
    var acc = q.accept || [];
    /* Text normalization removes brackets, so numeric expressions must be evaluated first:
       (1+2)*3 and 1+2*3 have the same normalized text but different values. */
    if (acc.some(function (a) { return norm(a) === n && !numsOf(a, 1); })) return true;
    var refs = acc.map(function (a) { return numsOf(a, 1); }).filter(Boolean), readable = false;
    if (!refs.length) return false;
    var matched = refs.some(function (ref) {
      var got = numsOf(v, ref.length);
      if (!got) return false;
      readable = true;
      return got.length === ref.length && got.every(function (x, j) { return approx(x, ref[j]); });
    });
    return matched ? true : (readable ? false : null);
  }
  function fillOk(q, v) { return fillCheck(q, v) === true; }
  function scoreOf(q, sel) {
    if (sel == null) return 0;
    if (q.type === "single" || q.type === "tf") return sel === q.ans ? 1 : 0;
    if (q.type === "fill") return fillOk(q, sel) ? 1 : 0;
    if (q.type === "multi") {
      if (!sel.length) return 0;
      var K = q.ans.length, c = 0, w = 0;
      sel.forEach(function (i) { if (q.ans.indexOf(i) >= 0) c++; else w++; });
      return Math.max(0, (c - w) / Math.max(K, sel.length));
    }
    return 0;
  }
  function round2(x) { return Math.round(x * 100) / 100; }
  function fmt(x) { return round2(x).toString(); }
  function pct(s, m) { return m ? Math.round(s / m * 100) : 0; }
  function scoreClass(x) { return x >= 0.999 ? "sc-full" : (x > 0 ? "sc-part" : "sc-zero"); }
  function scoreBadge(x, text) { return span("qscore " + scoreClass(x), text); }
  /* the answer shown for a fill-in */
  function refAnswer(q) { return q.answer || (q.accept || [])[0]; }

  /* ================= helpers ================= */
  /* formulas: elements carry LaTeX in data-tex and plain-text fallback inside; MathJax (if it loads) swaps in SVG */
  var texCss = false;
  function renderTex(root) {
    var MJ = window.MathJax;
    if (!MJ || typeof MJ.tex2svg !== "function" || !root) return;
    if (!texCss && typeof MJ.svgStylesheet === "function") { try { document.head.appendChild(MJ.svgStylesheet()); } catch (e) {} texCss = true; }
    root.querySelectorAll("[data-tex]").forEach(function (e) {
      if (e.getAttribute("data-done")) return;
      try {
        var out = MJ.tex2svg(e.getAttribute("data-tex"), { display: e.classList.contains("tex-d") });
        if (out.querySelector("[data-mjx-error], merror")) return;
        e.textContent = ""; e.appendChild(out); e.setAttribute("data-done", "1");
      } catch (err) {}
    });
    fitTex();
  }
  /* an inline formula wider than its line gets its own scrollable line, so the page never scrolls sideways */
  function fitTex() {
    document.querySelectorAll(".m[data-done]").forEach(function (e) {
      e.classList.remove("mwide");
      var p = e.parentElement;
      if (p && p.clientWidth && e.getBoundingClientRect().width > p.clientWidth - 2) e.classList.add("mwide");
    });
  }
  var fitT;
  window.addEventListener("resize", function () { clearTimeout(fitT); fitT = setTimeout(fitTex, 150); });
  window.__renderTex = function () { renderTex(document.body); };
  /* a button that asks once before acting: the first click arms it and shows Cancel, and it disarms by itself after 5 s */
  function confirmBtn(label, armedLabel, onConfirm, cls, armedCls) {
    var wrap = el("span", "confirm");
    var b = button(cls, label);
    var x = button("reset", t("cancel")); x.hidden = true;
    var tm = null;
    function disarm() { clearTimeout(tm); b.dataset.armed = ""; b.textContent = label; b.className = cls; x.hidden = true; }
    b.addEventListener("click", function () {
      if (b.dataset.armed !== "1") {
        b.dataset.armed = "1"; b.textContent = armedLabel; if (armedCls) b.className = armedCls; x.hidden = false;
        clearTimeout(tm); tm = setTimeout(disarm, 5000);
        return;
      }
      clearTimeout(tm); onConfirm();
    });
    x.addEventListener("click", disarm);
    wrap.appendChild(b); wrap.appendChild(x);
    return wrap;
  }
  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function span(cls, html) { return '<span class="' + cls + '">' + html + "</span>"; }
  function button(cls, html) { var b = el("button", cls, html); b.type = "button"; return b; }
  function textInput(id, value, aria) {
    var inp = document.createElement("input");
    inp.type = "text"; inp.id = id; inp.value = value;
    inp.setAttribute("aria-label", aria); inp.autocomplete = "off"; inp.spellcheck = false;
    return inp;
  }
  /* a multi-select pick list with option i added or removed, kept sorted */
  function toggled(list, i) { var a = (list || []).slice(), k = a.indexOf(i); if (k >= 0) a.splice(k, 1); else a.push(i); return a.sort(); }
  function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;"); }
  /* plain text for the progress report; superscripts and subscripts keep their meaning (x<sup>2</sup> -> x^2) */
  function plain(h) {
    var d = document.createElement("div");
    d.innerHTML = String(h == null ? "" : h).replace(/<sup>(.*?)<\/sup>/g, "^$1").replace(/<sub>(.*?)<\/sub>/g, "_$1");
    return d.textContent.replace(/\s+/g, " ").trim();
  }
  function typeTag(q) {
    if (q.type === "multi") return span("qtype multi", t("tMulti"));
    if (q.type === "fill") return span("qtype fill", t("tFill"));
    if (q.type === "card") return span("qtype", t("tCard"));
    return "";
  }
  function metaLine(q, badge) { return [q.lec, q.src].filter(Boolean).join(" · ") + typeTag(q) + (badge || ""); }
  /* options are divs, not buttons, so their text can be selected with the mouse;
     a drag that ends with text selected does not count as choosing the option */
  function selecting() { var sl = window.getSelection ? window.getSelection() : null; return !!(sl && !sl.isCollapsed && String(sl).trim()); }
  function optEl() {
    var d = el("div", "opt");
    d.setAttribute("role", "button"); d.tabIndex = 0;
    var down = null;
    d.addEventListener("mousedown", function (e) { down = [e.clientX, e.clientY]; });
    d.addEventListener("click", function (e) {
      var dragged = down && Math.abs(e.clientX - down[0]) + Math.abs(e.clientY - down[1]) > 6;
      down = null;
      if (dragged && selecting()) e.stopImmediatePropagation();
    });
    d.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); d.click(); } });
    return d;
  }
  function optHtml(pos, text, label, exp, square) {
    return span("bub" + (square ? " sq" : ""), L[pos]) + span("obody", span("otext", text + (label ? span("olabel", label) : "")) + exp);
  }
  /* an option's own explanation, or a plain right / wrong note when it has none */
  function expOf(q, i) {
    var x = q.opts[i];
    if (x && x.why) return span("oexp", x.why);
    var correct = q.type === "multi" ? q.ans.indexOf(i) >= 0 : i === q.ans;
    return span("oexp", correct ? t("optRight") : t("optWrong"));
  }
  /* after answering, a hint to click the options not yet opened: the right one plus every wrong try are open */
  function moreHint(tried, ans, n) { return tried.filter(function (k) { return k !== ans; }).length + 1 < n ? " " + span("empty", t("moreOpts")) : ""; }

  /* ================= practice bank ================= */
  function firstScore(q, rec) { return (!rec || rec.first == null) ? null : scoreOf(q, rec.first); }
  /* the saved practice scope, or "all" once that lecture has no practice questions (the bank changed) */
  function scopeOf(st) {
    var sc = st.scope;
    return sc !== "all" && BANKS.practice.items.some(function (q) { return q.lec === sc; }) ? sc : "all";
  }
  function practiceList() {
    var sc = scopeOf(STATE.practice);
    return BANKS.practice.items.filter(function (q) { return sc === "all" || q.lec === sc; });
  }
  function notCard(q) { return q.type !== "card"; }
  function groupBox(title, desc) { return el("div", "qgroup", "<h3>" + title + "</h3>" + (desc ? '<p class="qdesc">' + desc + "</p>" : "")); }

  /* where: "p" practice center, "s" section box, "b" mistake notebook */
  function practiceCard(q, num, where) {
    where = where || "p";
    var st = STATE.practice;
    /* the notebook redoes a question under its own record, so first-try scores stay as they were */
    var store = where === "b" ? (st.redo = st.redo || {}) : st.ans;
    var c = el("div", "q"); c.id = "q-" + where + "-" + q.id; c.setAttribute("data-num", num);
    var fs = q.type === "card" ? null : firstScore(q, store[q.id]);
    c.appendChild(el("p", "qmeta", metaLine(q, fs != null ? scoreBadge(fs, t("firstScore", { s: fmt(fs) })) : "")));
    c.appendChild(el("div", "qstem", num + ". " + q.stem));
    function commit() { save("practice"); refreshQ(q); }
    /* a slip of the finger: wipe this question's record so the next answer counts as the first; outside the
       notebook its notebook redo goes too, or a later miss would show up as already mastered */
    function undoBtn() {
      var w = confirmBtn(t("undo"), t("undoArmed"), function () { delete store[q.id]; if (where !== "b") delete st.redo[q.id]; commit(); }, "reset undo", "reset undo armed");
      w.firstChild.title = t("undoTitle");
      return w;
    }
    function undoFoot() { var f = el("div", "qfoot"); f.appendChild(undoBtn()); return f; }

    if (q.type === "card") {
      var rec0 = store[q.id] || {};
      var why0 = el("div", "why", t("answer") + " " + (q.answer || ""));
      var btn0 = button("reveal", t("reveal"));
      if (rec0.seen) btn0.hidden = true; else why0.hidden = true;
      btn0.addEventListener("click", function () { store[q.id] = { seen: true }; commit(); });
      c.appendChild(btn0); c.appendChild(why0);
      return c;
    }

    if (q.type === "fill") {
      var recF = store[q.id] || {}, inId = "in-" + where + "-" + q.id;
      var row = el("div", "fillrow");
      var inp = textInput(inId, recF.last != null ? recF.last : "", t("fillAria"));
      var sub = button("btn", t("submit"));
      row.appendChild(inp); row.appendChild(sub); c.appendChild(row);
      var hintF = el("p", "fillhint"); hintF.hidden = true; c.appendChild(hintF);
      var submitFill = function () {
        var v = inp.value;
        if (!norm(v)) return;
        if (fillCheck(q, v) === null) { hintF.textContent = t("fillHint"); hintF.hidden = false; return; }
        var r = store[q.id] || {};
        if (r.first == null) r.first = v;
        r.last = v; store[q.id] = r;
        commit();
        var again = document.getElementById(inId); if (again) again.focus();
      };
      sub.addEventListener("click", submitFill);
      inp.addEventListener("keydown", function (e) { if (e.key === "Enter") submitFill(); });
      if (recF.last != null) {
        var ok = fillOk(q, recF.last);
        inp.className = ok ? "ok" : "bad";
        var head = ok ? t("fillRight") : t("fillWrong", { a: refAnswer(q) });
        if (recF.first != null && recF.first !== recF.last) head += t("fillFirst", { v: esc(recF.first) });
        c.appendChild(el("div", "why", head + (q.why || "")));
        if (!fillOk(q, recF.first)) { c.classList.add("missed"); c.appendChild(undoFoot()); }
      }
      return c;
    }

    var opts = el("div", "opts"); c.appendChild(opts);
    var rec = store[q.id] || {};
    if (q.type === "multi") {
      var sel = rec.sel || [], submitted = !!rec.submitted;
      displayOrder(q).forEach(function (i, pos) {
        var bt = optEl();
        var chosen = sel.indexOf(i) >= 0, isAns = q.ans.indexOf(i) >= 0, label = "", exp = "";
        if (submitted) {
          if (isAns && chosen) { bt.classList.add("right"); label = t("mRight"); }
          else if (isAns) { bt.classList.add("missed"); label = t("mMissed"); }
          else if (chosen) { bt.classList.add("wrong"); label = t("mWrong"); }
          else { label = t("mSkip"); }
          exp = expOf(q, i);
        } else if (chosen) { bt.classList.add("sel"); }
        bt.setAttribute("aria-pressed", chosen ? "true" : "false");
        bt.innerHTML = optHtml(pos, q.opts[i].t, label, exp, true);
        if (!submitted) bt.addEventListener("click", function () {
          var r = store[q.id] || {};
          r.sel = toggled(r.sel, i); store[q.id] = r; writeLocal("practice", st); refreshQ(q);
        });
        opts.appendChild(bt);
      });
      var foot = el("div", "qfoot");
      if (!submitted) {
        var sb = button("btn", t("submit")); sb.disabled = !sel.length;
        sb.addEventListener("click", function () {
          var r = store[q.id] || {};
          if (!(r.sel || []).length) return;
          if (r.first == null) r.first = r.sel.slice();
          r.submitted = true; store[q.id] = r; commit();
        });
        foot.appendChild(sb);
        foot.appendChild(el("span", "empty", t("multiHint")));
      } else {
        c.classList.add("done");
        var sNow = scoreOf(q, sel), sFirst = scoreOf(q, rec.first);
        if (sFirst < 0.999) c.classList.add("missed");
        var again = button("btn ghost", t("reselect"));
        again.addEventListener("click", function () { var r = store[q.id]; r.submitted = false; r.sel = []; commit(); });
        foot.appendChild(again);
        foot.appendChild(el("span", "qscore " + scoreClass(sNow), t("scoreNow", { s: fmt(sNow) })));
        if (sFirst < 0.999) foot.appendChild(undoBtn());
      }
      c.appendChild(foot);
      if (submitted) c.appendChild(el("div", "why", t("multiAns", { a: q.ans.map(function (i) { return letterOf(q, i); }).sort().join(ZH ? "、" : ", ") }) + (q.why || "")));
      return c;
    }

    var tried = rec.tried || [], answered = rec.first != null;
    displayOrder(q).forEach(function (i, pos) {
      var bt = optEl(), label = "", exp = "";
      if (answered && i === q.ans) { bt.classList.add("right"); label = t("right"); exp = expOf(q, i); }
      else if (tried.indexOf(i) >= 0) { bt.classList.add("wrong"); label = "✗"; exp = expOf(q, i); }
      bt.innerHTML = optHtml(pos, q.opts[i].t, label, exp, false);
      bt.addEventListener("click", function () {
        var r = store[q.id] || {};
        if (r.first == null) r.first = i;
        r.tried = r.tried || [];
        if (r.tried.indexOf(i) < 0) r.tried.push(i);
        store[q.id] = r; commit();
      });
      opts.appendChild(bt);
    });
    if (answered) {
      c.classList.add("done");
      if (rec.first !== q.ans) c.classList.add("missed");
      var lead = rec.first === q.ans ? t("leadRight") : t("leadWrong", { a: letterOf(q, rec.first), b: letterOf(q, q.ans) });
      c.appendChild(el("div", "why", lead + (q.why || "") + moreHint(tried, q.ans, q.opts.length)));
      if (rec.first !== q.ans) c.appendChild(undoFoot());
    }
    return c;
  }

  /* rebuild in place every copy of a card that is on the page (practice center, section box, notebook) */
  function swapCards(prefix, id, wheres, make) {
    wheres.forEach(function (w) {
      var old = document.getElementById(prefix + w + "-" + id);
      if (!old) return;
      var n = make(+old.getAttribute("data-num"), w);
      old.replaceWith(n); renderTex(n);
    });
  }
  function refreshQ(q) {
    swapCards("q-", q.id, ["p", "s", "b"], function (num, w) { return w === "b" ? bookCard(q, num) : practiceCard(q, num, w); });
    updatePracticeBar(); updateSecHead(q.sec); updateBookBar();
  }

  function zeroByLec() { var out = {}; LECS.forEach(function (u) { out[u] = { s: 0, m: 0 }; }); return out; }
  function unitStats(list, scoreFn) {
    var out = zeroByLec();
    list.forEach(function (q) { var sc = scoreFn(q); if (sc == null || !out[q.lec]) return; out[q.lec].m++; out[q.lec].s += sc; });
    return out;
  }
  function statsTable(us) {
    var rows = LECS.filter(function (u) { return us[u] && us[u].m > 0; }).map(function (u) {
      var x = us[u], p = pct(x.s, x.m);
      var bar = '<div class="gbar"><span class="' + (p < 80 ? "low" : "") + '" style="width:' + p + '%"></span></div>';
      return "<tr><td>" + u + '</td><td class="num">' + fmt(x.s) + " / " + x.m + '</td><td class="num">' + p + "%</td><td>" + bar + "</td></tr>";
    }).join("");
    return '<div class="tbl"><table class="gtable"><tr><th>' + t("thLec") + '</th><th class="num">' + t("thScore") + '</th><th class="num">' + t("thPct") + "</th><th></th></tr>" + rows + "</table></div>";
  }

  function updatePracticeBar() {
    var st = STATE.practice, list = practiceList().filter(notCard);
    var bar = document.getElementById("bar-practice"); if (!bar) return;
    var info = bar.querySelector(".score"), acts = bar.querySelector(".acts");
    acts.innerHTML = "";
    var done = 0, s = 0;
    list.forEach(function (q) { var f = firstScore(q, st.ans[q.id]); if (f != null) { done++; s += f; } });
    info.innerHTML = t("practiceBar", { d: done, n: list.length, s: fmt(s) }) + (done ? t("pctParen", { p: pct(s, done) }) : "");
    /* clears the practice bank (every scope) and its notebook redos; short answers and mock mistakes stay */
    acts.appendChild(confirmBtn(t("clearPractice"), t("clearArmed"), function () {
      Object.keys(st.ans).concat(BANKS.practice.items.map(function (q) { return q.id; })).forEach(function (id) { delete st.redo[id]; });
      st.ans = {}; save("practice"); render("practice");
    }, "reset", "reset armed"));
    var box = document.getElementById("sum-practice");
    var us = unitStats(BANKS.practice.items.filter(notCard), function (q) { return firstScore(q, st.ans[q.id]); });
    var any = LECS.some(function (u) { return us[u].m > 0; });
    var open = box.querySelector("details") && box.querySelector("details").open;
    box.innerHTML = '<details class="weak"' + (open ? " open" : "") + "><summary>" + t("byLec") + "</summary>" + (any ? statsTable(us) : '<p class="empty">' + t("noRecords") + "</p>") + "</details>";
    box.hidden = false;
  }

  function renderPractice() {
    var st = STATE.practice, root = document.getElementById("bank-practice"); if (!root) return;
    var sel = document.getElementById("scope-practice"); if (sel) sel.value = scopeOf(st);
    root.innerHTML = "";
    var list = practiceList(), num = 0;
    if (!list.length) root.appendChild(el("p", "empty", t("emptyScope")));
    BANKS.practice.groups.forEach(function (g) {
      var qs = list.filter(function (q) { return q.g === g.id; });
      if (!qs.length) return;
      var box = groupBox(g.title, g.desc);
      qs.forEach(function (q) { num++; box.appendChild(practiceCard(q, num)); });
      root.appendChild(box);
    });
    updatePracticeBar();
    renderTex(root);
  }

  /* ================= short answer, step by step ================= */
  function saRec(s) { return (STATE.practice.sa || {})[s.id] || {}; }
  function saStarted(s) { var r = saRec(s); return Object.keys(r).some(function (k) { return r[k] && (r[k].shown || r[k].tries); }); }
  /* a step answered by typing and judged by the checker, not marked by the student */
  function typedStep(p, rec) { return p.accept && rec.v != null && !rec.self; }
  /* a typed step is re-judged with the current checker, so older records benefit from looser matching too */
  function stepOk(p, rec) {
    if (!rec || !rec.shown) return null;
    if (rec.fix) return true;
    if (typedStep(p, rec)) return fillOk(p, rec.v);
    return rec.ok == null ? null : rec.ok;
  }
  /* first-try credit: right with no miss, or "count it" after one try (the checker misread a right answer) */
  function stepFirst(p, rec) { return stepOk(p, rec) === true && (!rec.tries || (!!rec.fix && rec.tries <= 1)); }
  function saScore(s) {
    var r = saRec(s), sc = 0, mx = 0, fin = 0;
    s.steps.forEach(function (p, i) {
      var pts = p.pts || 1;
      mx += pts;
      if (stepOk(p, r[i]) === true) { fin += pts; if (stepFirst(p, r[i])) sc += pts; }
    });
    return { s: sc, f: fin, m: mx };  /* s counts only steps right on the first try; f also counts steps fixed later */
  }
  function setStep(s, i, patch) {
    var st = STATE.practice; st.sa = st.sa || {};
    var r = st.sa[s.id] = st.sa[s.id] || {}, cur = r[i] || {};
    Object.keys(patch).forEach(function (k) { cur[k] = patch[k]; });
    r[i] = cur;
    save("practice"); refreshSA(s);
  }
  function refreshSA(s) {
    swapCards("sa-", s.id, ["p", "s"], function (num, w) { return saCard(s, num, w); });
    updateSABar(); updateSecHead(s.sec);
  }
  function saCard(s, num, where) {
    var r = saRec(s), sc = saScore(s), started = saStarted(s);
    var c = el("div", "q sa"); c.id = "sa-" + where + "-" + s.id; c.setAttribute("data-num", num);
    var badge = started ? scoreBadge(sc.s / sc.m, t("saBadge", { s: sc.s, m: sc.m }) + (sc.f > sc.s ? t("saFixed", { f: sc.f }) : "")) : "";
    c.appendChild(el("p", "qmeta", [s.lec, s.kind].filter(Boolean).join(" · ") + span("qtype fill", t("tSA")) + (s.opt ? span("qtype", t("optional")) : "") + badge));
    if (s.opt) c.appendChild(el("div", "why", t("optNote") + s.opt));
    c.appendChild(el("div", "qstem", num + ". " + s.stem));
    s.steps.forEach(function (p, i) {
      var rec = r[i] || {}, box = el("div", "sastep"), inId = "sa-in-" + where + "-" + s.id + "-" + i;
      function focusInput() { var e = document.getElementById(inId); if (e) { e.focus(); e.select(); } }
      box.appendChild(el("p", "saask", "<b>" + t("step", { i: i + 1, p: p.pts || 1 }) + "</b>" + p.ask));
      if (p.opts) {
        /* shown in a fixed shuffled order (stored answers keep the original index); after answering, the other
           options stay clickable to read why they are wrong, without touching the score */
        var row = el("div", "opts"), order = seededOrder(KEY + ":" + s.id + ":" + i, p.opts.length);
        var tried = rec.tried || (rec.shown && rec.v != null ? [rec.v] : []);
        order.forEach(function (j, n) {
          var b = optEl(), label = "", exp = "";
          if (rec.shown && j === p.ans) { b.classList.add("right"); label = t("right"); }
          else if (tried.indexOf(j) >= 0) { b.classList.add("wrong"); label = "✗"; if (p.ow && p.ow[j]) exp = span("oexp", p.ow[j]); }
          b.innerHTML = optHtml(n, p.opts[j], label, exp, false);
          b.addEventListener("click", function () {
            /* a reopened step keeps its earlier misses in tried */
            if (!rec.shown) setStep(s, i, { v: j, ok: j === p.ans, shown: true, tried: tried.indexOf(j) < 0 ? tried.concat([j]) : tried });
            else if (tried.indexOf(j) < 0) setStep(s, i, { tried: tried.concat([j]) });
          });
          row.appendChild(b);
        });
        box.appendChild(row);
      } else if (p.accept) {
        var fr = el("div", "fillrow"), inp = textInput(inId, rec.v != null ? rec.v : "", t("stepAria", { i: i + 1 }));
        fr.appendChild(inp);
        if (rec.shown) {
          inp.disabled = true;
          if (typedStep(p, rec)) inp.className = stepOk(p, rec) ? "ok" : "bad";
          box.appendChild(fr);
        } else {
          /* tries without a typed value come from reopening a self-marked step: it is still done on paper */
          var typedMiss = !!rec.tries && rec.v != null, msg = el("p", "fillhint");
          if (typedMiss) { inp.className = "bad"; msg.textContent = t("tries", { n: rec.tries > 1 ? t("triesN", { k: rec.tries }) : "" }); }
          else msg.hidden = true;
          var chk = button("btn", t("check"));
          var go = function () {
            var res = fillCheck(p, inp.value);
            if (res === null) { if (norm(inp.value)) { msg.textContent = t("fillHint"); msg.hidden = false; } return; }
            if (res) setStep(s, i, { v: inp.value, ok: true, shown: true });
            else { setStep(s, i, { v: inp.value, tries: (rec.tries || 0) + 1 }); focusInput(); }
          };
          chk.addEventListener("click", go);
          inp.addEventListener("keydown", function (e) { if (e.key === "Enter") go(); });
          var peek = button("btn ghost", typedMiss ? t("peek") : t("peekPaper"));
          peek.addEventListener("click", function () {
            if (typedMiss) setStep(s, i, { v: inp.value, ok: false, shown: true });
            else setStep(s, i, { shown: true, self: true });
          });
          fr.appendChild(chk); fr.appendChild(peek);
          box.appendChild(fr); box.appendChild(msg);
        }
      } else if (!rec.shown) {
        var pk = button("btn ghost", t("selfPeek"));
        pk.addEventListener("click", function () { setStep(s, i, { shown: true, self: true }); });
        box.appendChild(pk);
      }
      if (rec.shown) {
        var okS = stepOk(p, rec);
        var head = okS === true ? t("stepRight") + (rec.tries ? t("fixedAfter", { n: rec.tries }) : "") : (okS === false ? t("stepWrong") : "");
        box.appendChild(el("div", "why", head + t("sol") + p.sol + (p.opts ? moreHint(tried, p.ans, p.opts.length) : "")));
        var sf = el("div", "qfoot");
        if (okS == null) {
          var yes = button("btn", t("iRight")), no = button("btn ghost", t("iWrong"));
          yes.addEventListener("click", function () { setStep(s, i, { ok: true }); });
          no.addEventListener("click", function () { setStep(s, i, { ok: false }); });
          sf.appendChild(yes); sf.appendChild(no); sf.appendChild(el("span", "empty", t("selfJudge")));
        } else if (okS === false) {
          /* reopen just this step, keeping what was typed so it can be edited. The miss stays counted in tries
             (a typed miss already was), so a later right answer earns "after fixes" credit, never first-try credit */
          var redo = button("btn ghost", t("redoStep"));
          redo.addEventListener("click", function () {
            var r0 = STATE.practice.sa[s.id] || {};
            if (typedStep(p, rec)) r0[i] = { v: rec.v, tries: rec.tries || 1 };
            else {
              r0[i] = { tries: (rec.tries || 0) + 1 };
              if (p.opts) r0[i].tried = rec.tried || (rec.v != null ? [rec.v] : []);
            }
            save("practice"); refreshSA(s);
            focusInput();
          });
          sf.appendChild(redo);
          if (typedStep(p, rec)) {
            var fx = button("reset", t("override"));
            fx.addEventListener("click", function () { setStep(s, i, { ok: true, fix: true }); });
            sf.appendChild(fx);
          }
        }
        if (sf.childNodes.length) box.appendChild(sf);
      }
      c.appendChild(box);
    });
    if (started) {
      var f = el("div", "qfoot"), rs = button("btn ghost", t("redoSA"));
      rs.addEventListener("click", function () { delete STATE.practice.sa[s.id]; save("practice"); refreshSA(s); });
      f.appendChild(rs);
      if (s.steps.every(function (p, i) { return stepOk(p, r[i]) != null; })) f.appendChild(el("span", "qscore " + scoreClass(sc.s / sc.m), t("saTotal", { s: sc.s, m: sc.m }) + (sc.f > sc.s ? t("saTotalFixed", { f: sc.f, m: sc.m }) : "")));
      c.appendChild(f);
      if (s.note && s.steps.every(function (p, i) { return r[i] && r[i].shown; })) c.appendChild(el("div", "why", t("saNote") + s.note));
    }
    return c;
  }
  function updateSABar() {
    var bar = document.getElementById("bar-sa"); if (!bar) return;
    var started = 0, sc = 0, mx = 0;
    SA.forEach(function (x) { if (saStarted(x)) { started++; if (x.opt) return; var k = saScore(x); sc += k.s; mx += k.m; } });
    bar.querySelector(".score").innerHTML = t("saBar", { a: started, n: SA.length }) + (started ? t("saBarScore", { s: sc, m: mx }) : "");
  }
  function renderSA() {
    var root = document.getElementById("bank-sa"); if (!root) return;
    root.innerHTML = "";
    var num = 0;
    SA_GROUPS.forEach(function (gr) {
      var xs = SA.filter(function (x) { return x.k === gr.id; });
      if (!xs.length) return;
      var box = groupBox(gr.title || gr.kind || "", gr.desc);
      xs.forEach(function (x) { num++; box.appendChild(saCard(x, num, "p")); });
      root.appendChild(box);
    });
    updateSABar(); renderTex(root);
  }

  /* ================= section practice: a collapsible box at the end of each page section ================= */
  var SECS = [];
  function openMap() { try { return JSON.parse(lsGet("open") || "{}") || {}; } catch (e) { return {}; } }
  function setOpen(id, v) { var o = openMap(); if (v) o[id] = 1; else delete o[id]; lsSet("open", JSON.stringify(o)); }
  function secItems(id) { return BANKS.practice.items.filter(function (q) { return q.sec === id; }); }
  function secSA(id) { return SA.filter(function (x) { return x.sec === id; }); }
  function updateSecHead(id) {
    var box = document.getElementById("sp-" + id); if (!id || !box || !box.querySelector(".sp-meta")) return;
    var st = STATE.practice, qs = secItems(id), sas = secSA(id), done = 0, scored = 0, s = 0;
    qs.forEach(function (q) {
      if (q.type === "card") { if ((st.ans[q.id] || {}).seen) done++; return; }
      var f = firstScore(q, st.ans[q.id]); if (f != null) { done++; scored++; s += f; }
    });
    var saDone = sas.filter(saStarted).length;
    box.querySelector(".sp-meta").textContent = plain(t("secMeta", { n: qs.length, d: done }) + (scored ? t("secPct", { p: pct(s, scored) }) : "") + (sas.length ? t("secSA", { a: saDone, b: sas.length }) : ""));
    var open = !!openMap()[id], left = qs.length - done + sas.length - saDone;
    var bt = box.querySelector(".sp-toggle");
    bt.textContent = open ? t("close") : (done + saDone === 0 ? t("start") : (left > 0 ? t("resume", { n: left }) : t("allDone")));
    bt.className = "btn sp-toggle" + (open || !left ? " ghost" : "");
    bt.setAttribute("aria-expanded", open ? "true" : "false");
  }
  function renderSecBox(id, k) {
    var box = document.getElementById("sp-" + id); if (!box) return;
    var open = !!openMap()[id];
    box.innerHTML = '<div class="sp-head"><div class="sp-hl"><p class="sp-title">' + t("secTitle") + '</p><p class="sp-meta"></p></div><button type="button" class="btn sp-toggle"></button></div>';
    box.querySelector(".sp-toggle").addEventListener("click", function () { setOpen(id, !openMap()[id]); renderSecBox(id, k); });
    if (open) {
      var body = el("div", "sp-body");
      secItems(id).forEach(function (q, i) { body.appendChild(practiceCard(q, i + 1, "s")); });
      var sas = secSA(id);
      if (sas.length) {
        body.appendChild(el("p", "sp-sub", t("secSub")));
        sas.forEach(function (x, i) { body.appendChild(saCard(x, i + 1, "s")); });
      }
      var foot = el("div", "sp-foot");
      var close = button("btn ghost", t("close"));
      close.addEventListener("click", function () { setOpen(id, false); renderSecBox(id, k); box.scrollIntoView({ block: "start" }); });
      foot.appendChild(close);
      var nxt = SECS[k + 1], a = el("a", "btn", nxt ? t("nextSec") : t("toMock"));
      a.href = "#" + (nxt || "practice");
      foot.appendChild(a);
      body.appendChild(foot);
      box.appendChild(body);
      renderTex(body);
    }
    updateSecHead(id);
  }
  function renderSecBoxes() { SECS.forEach(function (id, k) { renderSecBox(id, k); }); }
  function buildSecBoxes() {
    var want = {};
    BANKS.practice.items.forEach(function (q) { if (q.sec) want[q.sec] = 1; });
    SA.forEach(function (s) { if (s.sec) want[s.sec] = 1; });
    SECS = [].slice.call(document.querySelectorAll("section[id]")).map(function (x) { return x.id; }).filter(function (id) { return want[id]; });
    SECS.forEach(function (id) {
      if (document.getElementById("sp-" + id)) return;
      var box = el("div", "secprac"); box.id = "sp-" + id;
      document.getElementById(id).appendChild(box);
    });
  }

  /* ================= mistake notebook: first-try misses in practice, misses and flags from handed-in mock papers ================= */
  var BOOK_FILTER = "todo";
  function pickText(q, v) {
    if (v == null || v === "") return t("noAnswer");
    if (q.type === "fill") return ZH ? "「" + esc(v) + "」" : "“" + esc(v) + "”";
    if (Array.isArray(v)) return v.length ? v.map(function (i) { return letterOf(q, i); }).sort().join(ZH ? "、" : ", ") : t("noPick");
    return q.opts && q.opts[v] ? letterOf(q, v) + " (" + plain(q.opts[v].t).slice(0, 40) + ")" : t("noAnswer");
  }
  /* Mock mistakes have their own store, so they outlast the 20-paper history and keep their paper numbers:
     mock.book = { v: 1, papers: <papers handed in so far>, items: { id: [{ paper, wrong, flagged, pick? }] } }.
     pick is the stored answer (original option indexes). An entry stays until the student removes it; a right
     redo marks it mastered. A save from before the store is rebuilt from the history it still has: until the
     next hand-in that is done on the fly, so loading never rewrites the old state. */
  function bookAdd(book, h, k) {
    var wrong = h.wrong || [], flags = h.flags || [];
    wrong.concat(flags).forEach(function (id) {
      var w = wrong.indexOf(id) >= 0, hit = { paper: k, wrong: w, flagged: flags.indexOf(id) >= 0 };
      /* skip questions left blank, so an unfinished paper does not flood the notebook */
      if (w && h.picks && !answeredDraft(h.picks[id])) return;
      var list = book.items[id] = Array.isArray(book.items[id]) ? book.items[id] : [];
      if (list.some(function (x) { return x.paper === k; })) return;
      if (h.picks && answeredDraft(h.picks[id])) hit.pick = h.picks[id];
      list.push(hit);
    });
  }
  function mockBook() {
    var st = STATE.mock, b = st.book;
    if (b && b.v === 1 && b.items && typeof b.items === "object") return b;
    b = { v: 1, papers: 0, items: {} };
    (st.history || []).forEach(function (h) { bookAdd(b, h, ++b.papers); });
    return b;
  }
  function bookEntries() {
    var out = {}, order = [];
    function add(q, note, kind) {
      if (!out[q.id]) { out[q.id] = { q: q, notes: [], wrong: false, flag: false }; order.push(q.id); }
      var e = out[q.id];
      if (e.notes.indexOf(note) < 0) e.notes.push(note);
      if (kind === "wrong") e.wrong = true; else e.flag = true;
    }
    var ps = STATE.practice;
    BANKS.practice.items.forEach(function (q) {
      if (q.type === "card") return;
      var r = ps.ans[q.id], f = firstScore(q, r);
      if (f != null && f < 0.999) add(q, t("notePractice", { a: pickText(q, r.first) }), "wrong");
    });
    var items = mockBook().items;
    Object.keys(items).filter(function (id) { return BANKS.mock.imap[id] && Array.isArray(items[id]) && items[id].length; })
      .sort(function (a, b) { return items[a][0].paper - items[b][0].paper; })
      .forEach(function (id) {
        var q = BANKS.mock.imap[id];
        items[id].forEach(function (h) {
          if (h.wrong) add(q, t("noteMock", { k: h.paper }) + ("pick" in h ? t("notePick", { a: pickText(q, h.pick) }) : ""), "wrong");
          if (h.flagged) add(q, t("noteFlag", { k: h.paper }) + (h.wrong ? "" : t("noteFlagOk")), "flag");
        });
      });
    return order.map(function (id) { return out[id]; });
  }
  function mastered(q) { var r = (STATE.practice.redo || {})[q.id]; var f = firstScore(q, r); return f != null && f >= 0.999; }
  function bookCard(q, num) {
    var c = practiceCard(q, num, "b");
    var e = (bookEntries().filter(function (x) { return x.q.id === q.id; })[0]) || { notes: [], wrong: false, flag: false };
    var tags = (e.wrong ? span("wbt bad", t("tagWrong")) : "") + (e.flag ? span("wbt flg", t("tagFlag")) : "") + (mastered(q) ? span("wbt ok", t("tagOk")) : "");
    var box = el("div", "wbk", tags + span("wbn", e.notes.join(ZH ? "；" : "; ")));
    if (STATE.practice.redo[q.id]) {  /* practiceCard(q, num, "b") made sure redo exists */
      var again = button("reset", t("clearRedo"));
      again.addEventListener("click", function () { delete STATE.practice.redo[q.id]; save("practice"); refreshQ(q); });
      box.appendChild(again);
    }
    if (mockBook().items[q.id]) box.appendChild(confirmBtn(t("bookRemove"), t("bookRemoveArmed"), function () {
      var b = STATE.mock.book = mockBook();
      delete b.items[q.id]; save("mock");
      if (STATE.practice.redo[q.id]) { delete STATE.practice.redo[q.id]; save("practice"); }
      renderBook();
    }, "reset", "reset armed"));
    c.insertBefore(box, c.children[1]);
    return c;
  }
  /* what each notebook filter shows */
  var BOOK_VIEWS = {
    todo: function (x) { return !mastered(x.q); },
    wrong: function (x) { return x.wrong; },
    flag: function (x) { return x.flag; },
    all: function () { return true; }
  };
  function updateBookBar() {
    var bar = document.getElementById("bar-book"); if (!bar) return;
    var all = bookEntries(), left = all.filter(BOOK_VIEWS.todo).length;
    var nw = all.filter(BOOK_VIEWS.wrong).length, nf = all.filter(BOOK_VIEWS.flag).length;
    bar.querySelector(".score").innerHTML = t("bookBar", { n: all.length, w: nw, f: nf, l: left });
    var tab = document.querySelector('[data-tab="book"]'); if (tab) tab.textContent = left ? t("tabBookN", { n: left }) : t("tabBook");
  }
  function renderBook() {
    var root = document.getElementById("bank-book"), bar = document.getElementById("bar-book"); if (!root || !bar) return;
    var acts = bar.querySelector(".acts"); acts.innerHTML = "";
    var seg = el("div", "seg");
    [["todo", t("fTodo")], ["wrong", t("fWrong")], ["flag", t("fFlag")], ["all", t("fAll")]].forEach(function (x) {
      var b = button("", x[1]); b.setAttribute("aria-pressed", BOOK_FILTER === x[0] ? "true" : "false");
      b.addEventListener("click", function () { BOOK_FILTER = x[0]; renderBook(); });
      seg.appendChild(b);
    });
    acts.appendChild(seg);
    var all = bookEntries(), list = all.filter(BOOK_VIEWS[BOOK_FILTER]);
    root.innerHTML = "";
    if (!list.length) root.appendChild(el("p", "empty", all.length ? t("bookEmptyF") : t("bookEmpty")));
    list.forEach(function (x, i) { root.appendChild(bookCard(x.q, i + 1)); });
    updateBookBar(); renderTex(root);
  }

  /* ================= mock exam ================= */
  /* Each section of the paper takes its quota from the lectures in proportion to their pool size (or to
     config.mock.weights), capped by what each lecture has. seen[id] = number of the last paper that used it;
     never-used questions come first, then the ones used longest ago. */
  function drawPaper(seen) {
    var items = BANKS.mock.items, paper = [];
    seen = seen || {};
    function age(id) { return seen[id] == null ? -1 : seen[id]; }
    MOCK_SECTIONS.forEach(function (sec) {
      var byU = {}, N = 0, W = 0;
      LECS.forEach(function (u) { byU[u] = []; });
      items.forEach(function (q) { if (q.cat === sec.cat && byU[q.lec]) byU[q.lec].push(q.id); });
      function wt(u) { return !byU[u].length ? 0 : (WEIGHTS ? (WEIGHTS[u] || 0) : byU[u].length); }
      LECS.forEach(function (u) { if (wt(u) > 0) N += byU[u].length; W += wt(u); });
      var T = Math.min(sec.n, N);
      if (!T || !W) return;
      var quotas = LECS.map(function (u) { var ex = T * wt(u) / W; return { u: u, f: Math.min(Math.floor(ex), byU[u].length), r: ex - Math.floor(ex) }; });
      var left = T - quotas.reduce(function (s, x) { return s + x.f; }, 0);
      var ranked = shuffle(quotas.slice()).sort(function (a, b) { return b.r - a.r; });
      for (var pass = 0; left > 0 && pass < T; pass++) {
        ranked.forEach(function (x) { if (left > 0 && wt(x.u) > 0 && x.f < byU[x.u].length && (pass > 0 || x.r > 0)) { x.f++; left--; } });
      }
      var picked = [];
      quotas.forEach(function (x) {
        var pool = shuffle(byU[x.u].slice());
        pool.sort(function (a, b) { return age(a) - age(b); });
        picked = picked.concat(pool.slice(0, x.f));
      });
      paper = paper.concat(shuffle(picked));
    });
    return paper;
  }
  function newPaper() {
    var st = STATE.mock;
    st.seen = st.seen || {}; st.pcount = st.pcount || 0;
    (st.paper || []).forEach(function (id) { st.seen[id] = st.pcount; });
    if ((st.paper || []).length) st.pcount++;
    st.paper = drawPaper(st.seen); st.draft = {}; st.flags = {}; st.submitted = false; st.result = null;
    st.timer = { limit: (st.timer && st.timer.limit != null) ? st.timer.limit : DEF_MIN, startedAt: "" };
    save("mock");
  }
  function answeredDraft(d) { return d != null && !(typeof d === "string" && !d.trim()) && !(Array.isArray(d) && !d.length); }

  function mockCard(q, num) {
    var st = STATE.mock, locked = st.submitted;
    var c = el("div", "q"); c.id = "q-m-" + q.id;
    var badge = "";
    if (locked) { var es = scoreOf(q, st.draft[q.id]); badge = scoreBadge(es, t("score", { s: fmt(es) })); }
    var flagged = !!(st.flags && st.flags[q.id]);
    if (flagged) c.classList.add("flagged");
    var meta = el("p", "qmeta", span("qmetatxt", q.lec + typeTag(q) + badge));
    var fb = button("flagbtn" + (flagged ? " on" : ""), flagged ? t("flagged") : t("flag"));
    fb.title = t("flagTitle");
    fb.setAttribute("aria-pressed", flagged ? "true" : "false");
    fb.addEventListener("click", function () {
      st.flags = st.flags || {};
      if (st.flags[q.id]) delete st.flags[q.id]; else st.flags[q.id] = 1;
      commit();
    });
    meta.appendChild(fb);
    c.appendChild(meta);
    c.appendChild(el("div", "qstem", num + ". " + q.stem));
    function commit() { save("mock"); var n = mockCard(q, num); c.replaceWith(n); updateMockBar(); renderTex(n); }

    if (q.type === "fill") {
      var cur = st.draft[q.id] || "";
      var row = el("div", "fillrow"), inp = textInput("in-m-" + q.id, cur, t("fillAria"));
      row.appendChild(inp); c.appendChild(row);
      if (locked) {
        inp.disabled = true;
        var okE = fillOk(q, cur);
        inp.className = okE ? "ok" : "bad";
        c.appendChild(el("div", "why", (okE ? t("correct") : t("refAns", { a: refAnswer(q) })) + (q.why || "")));
        if (!okE) c.classList.add("missed");
      } else {
        var tmr;
        inp.addEventListener("input", function () {
          st.draft[q.id] = inp.value;
          clearTimeout(tmr); tmr = setTimeout(function () { save("mock"); updateMockBar(); }, 400);
        });
      }
      return c;
    }

    var multi = q.type === "multi";
    var opts = el("div", "opts"); c.appendChild(opts);
    var dsel = st.draft[q.id];
    displayOrder(q).forEach(function (i, pos) {
      var bt = optEl();
      var chosen = multi ? (dsel || []).indexOf(i) >= 0 : dsel === i, label = "", exp = "";
      if (locked) {
        var isAns = multi ? q.ans.indexOf(i) >= 0 : i === q.ans;
        if (isAns && chosen) { bt.classList.add("right"); label = t("youRight"); }
        else if (isAns) { bt.classList.add(multi ? "missed" : "right"); label = multi ? t("mMissed") : t("right"); }
        else if (chosen) { bt.classList.add("wrong"); label = t("youWrong"); }
        exp = expOf(q, i);
      } else if (chosen) { bt.classList.add(multi ? "sel" : "picked"); }
      bt.setAttribute("aria-pressed", chosen ? "true" : "false");
      bt.innerHTML = optHtml(pos, q.opts[i].t, label, exp, multi);
      if (!locked) bt.addEventListener("click", function () {
        if (multi) { var a = toggled(st.draft[q.id], i); if (a.length) st.draft[q.id] = a; else delete st.draft[q.id]; }
        else st.draft[q.id] = i;
        commit();
      });
      opts.appendChild(bt);
    });
    if (locked) {
      c.classList.add("done");
      var s = scoreOf(q, dsel);
      if (s < 0.999) c.classList.add("missed");
      var head = s >= 0.999 ? t("mockRight") : (multi ? t("mockMulti", { s: fmt(s) }) : t("mockWrong", { a: letterOf(q, q.ans) }));
      c.appendChild(el("div", "why", "<b>" + head + "</b>" + (q.why || "")));
    }
    return c;
  }

  var NAV_OPEN = false;
  function jumpTo(id) {
    var c = document.getElementById("q-m-" + id); if (!c) return;
    var bar = document.getElementById("bar-mock");
    var y = c.getBoundingClientRect().top + window.pageYOffset - (bar ? bar.getBoundingClientRect().height : 0) - 16;
    try { window.scrollTo({ top: y, behavior: "instant" }); } catch (e) { window.scrollTo(0, y); }
    c.classList.add("pulse"); setTimeout(function () { c.classList.remove("pulse"); }, 1200);
  }
  function paperNav(bar) {
    var st = STATE.mock, nav = bar.querySelector(".pnav");
    if (!nav) { nav = el("div", "pnav"); bar.appendChild(nav); }
    nav.innerHTML = "";
    if (!st.paper.length) { nav.hidden = true; return; }
    nav.hidden = false;
    var tg = button("btn ghost small", t("card") + " " + (NAV_OPEN ? "▴" : "▾"));
    tg.setAttribute("aria-expanded", NAV_OPEN ? "true" : "false");
    tg.addEventListener("click", function () { NAV_OPEN = !NAV_OPEN; paperNav(bar); });
    nav.appendChild(tg);
    if (!NAV_OPEN) return;
    var grid = el("div", "qgrid"), wrong = st.submitted && st.result ? st.result.wrong : [];
    st.paper.forEach(function (id, i) {
      var cls = "qn", tip = t("qn", { i: i + 1 }), fl = !!(st.flags && st.flags[id]);
      if (st.submitted) { var ok = wrong.indexOf(id) < 0; cls += ok ? " ok" : " bad"; tip += ok ? t("qOk") : t("qBad"); }
      else { var an = answeredDraft(st.draft[id]); if (an) cls += " ans"; tip += an ? t("qAns") : t("qUnans"); }
      if (fl) { cls += " flg"; tip += t("qFlg"); }
      var cb = button(cls, String(i + 1)); cb.title = tip; cb.setAttribute("aria-label", tip);
      cb.addEventListener("click", function () { NAV_OPEN = false; paperNav(bar); jumpTo(id); });
      grid.appendChild(cb);
    });
    nav.appendChild(grid);
    nav.appendChild(el("p", "legend", st.submitted ? t("legendDone") : t("legendLive")));
  }

  /* a link to a card on the current paper, labelled with its question number */
  function qLink(id, cls, tail) {
    return "<a" + (cls ? ' class="' + cls + '"' : "") + ' href="#q-m-' + id + '">' + t("qn", { i: STATE.mock.paper.indexOf(id) + 1 }) + (tail || "") + "</a>";
  }
  function flaggedIds() {
    var st = STATE.mock, f = st.flags || {};
    return st.paper.filter(function (id) { return f[id]; });
  }
  function jumpToNextFlag() {
    var ids = flaggedIds(); if (!ids.length) return;
    var cards = ids.map(function (id) { return document.getElementById("q-m-" + id); }).filter(Boolean);
    var next = cards.filter(function (c) { return c.getBoundingClientRect().top > 90; })[0] || cards[0];
    jumpTo(next.id.replace("q-m-", ""));
  }
  function renderFlagStrip() {
    var st = STATE.mock, box = document.getElementById("flags-mock"); if (!box) return;
    var ids = flaggedIds();
    box.innerHTML = "";
    if (!ids.length) { box.innerHTML = '<p class="flaghint">' + t("flagHintStrip") + "</p>"; box.hidden = false; return; }
    var links = ids.map(function (id) {
      var cls = "flaglink";
      if (st.submitted) cls += scoreOf(BANKS.mock.imap[id], st.draft[id]) >= 0.999 ? " ok" : " bad";
      else if (!answeredDraft(st.draft[id])) cls += " blank";
      return qLink(id, cls);
    }).join(" ");
    var p = el("p", "flaglist", t("flagList", { n: ids.length }) + links);
    var nb = button("btn ghost small", t("nextFlag"));
    nb.addEventListener("click", jumpToNextFlag);
    var cb = confirmBtn(t("clearFlags"), t("clearFlagsArmed"), function () { st.flags = {}; save("mock"); render("mock"); }, "btn ghost small", "btn warn small");
    var acts2 = el("div", "flagacts"); acts2.appendChild(nb); acts2.appendChild(cb);
    box.appendChild(p); box.appendChild(acts2); box.hidden = false;
  }

  function updateMockBar() {
    var st = STATE.mock, bar = document.getElementById("bar-mock"); if (!bar) return;
    var info = bar.querySelector(".score"), acts = bar.querySelector(".acts");
    acts.innerHTML = "";
    renderFlagStrip();
    paperNav(bar);
    var n = st.paper.length;
    function drawNew() {
      newPaper(); render("mock");
      var top = document.getElementById("wrap-mock"); if (top) top.scrollIntoView({ block: "start" });
    }
    var started = !st.submitted && Object.keys(st.draft).some(function (k) { return answeredDraft(st.draft[k]); });
    var redo;
    if (started) redo = confirmBtn(t("redraw"), t("redrawArmed"), drawNew, "btn ghost", "btn warn");
    else { redo = button(st.submitted ? "btn" : "btn ghost", t("redraw")); redo.addEventListener("click", drawNew); }
    if (!st.submitted) {
      var a = st.paper.filter(function (id) { return answeredDraft(st.draft[id]); }).length;
      var unseen = BANKS.mock.items.filter(function (q) { return st.seen[q.id] == null && st.paper.indexOf(q.id) < 0; }).length;
      info.innerHTML = t("mockBar", { a: a, n: n }) + clockHtml() + span("fresh", t("fresh", { u: unseen }));
      if (!st.timer.startedAt) {
        var lim = el("select", "limsel"); lim.setAttribute("aria-label", t("limitAria"));
        MINUTES.forEach(function (x) { lim.appendChild(new Option(x.m ? t("limitMin", { m: x.m }) + (x.note ? (ZH ? "（" + x.note + "）" : " (" + x.note + ")") : "") : t("noLimit"), String(x.m))); });
        lim.value = String(st.timer.limit);
        lim.addEventListener("change", function () { st.timer.limit = +lim.value; save("mock"); });
        var go = button("btn", t("startTimer"));
        go.addEventListener("click", function () { st.timer.startedAt = new Date().toISOString(); save("mock"); updateMockBar(); });
        acts.appendChild(lim); acts.appendChild(go);
      }
      var left = n - a, sb;
      if (left) sb = confirmBtn(t("submitLeft", { n: left }), t("submitArmed", { n: left }), function () { submitMock(false); }, "btn", "btn warn");
      else { sb = button("btn", t("submitAll")); sb.disabled = !n; sb.addEventListener("click", function () { submitMock(false); }); }
      acts.appendChild(sb);
      acts.appendChild(redo);
    } else {
      var r = st.result || { s: 0, m: 0 };
      info.innerHTML = t("submitted", { s: fmt(r.s), m: r.m, p: pct(r.s, r.m) }) + (r.used != null ? t("usedSuffix", { u: mmss(r.used) }) : "");
      acts.appendChild(redo);
    }
  }

  function submitMock(auto) {
    var st = STATE.mock, items = st.paper.map(function (id) { return BANKS.mock.imap[id]; });
    var used = null, limit = st.timer.limit;
    if (st.timer.startedAt) { used = Math.max(0, Math.round((Date.now() - Date.parse(st.timer.startedAt)) / 1000)); if (limit) used = Math.min(used, limit * 60); }
    var s = 0, wrong = [];
    var us = unitStats(items, function (q) { return scoreOf(q, st.draft[q.id]); });
    items.forEach(function (q) { var sc = scoreOf(q, st.draft[q.id]); s += sc; if (sc < 0.999) wrong.push(q.id); });
    var units = {};
    LECS.forEach(function (u) { if (us[u].m) units[u] = { s: round2(us[u].s), m: us[u].m }; });
    var flags = flaggedIds(), picks = {};
    /* a fill that was typed and then cleared is blank, not an answer */
    wrong.concat(flags).forEach(function (id) { if (answeredDraft(st.draft[id])) picks[id] = st.draft[id]; });
    var res = { at: new Date().toISOString(), s: round2(s), m: items.length, units: units, wrong: wrong, flags: flags, picks: picks, used: used, limit: used != null ? limit : null, auto: !!auto };
    st.result = res; st.submitted = true;
    var book = st.book = mockBook();
    bookAdd(book, res, ++book.papers);
    /* a new miss makes a question a mistake again, even if it was redone right before */
    var ps = STATE.practice, again = wrong.filter(function (id) { return id in picks && ps.redo[id]; });
    again.forEach(function (id) { delete ps.redo[id]; });
    st.history = (st.history || []).concat([res]).slice(-20);
    save("mock"); if (again.length) save("practice"); render("mock");
    var sum = document.getElementById("sum-mock"); if (sum) sum.scrollIntoView({ block: "start" });
  }

  function mockSummary() {
    var st = STATE.mock, box = document.getElementById("sum-mock");
    box.innerHTML = ""; box.hidden = true;
    var hist = st.history || [];
    if (st.submitted && st.result) {
      var r = st.result, p = pct(r.s, r.m), us = {};
      LECS.forEach(function (u) { us[u] = r.units[u] || { s: 0, m: 0 }; });
      var prev = hist.filter(function (h) { return h.at !== r.at; }).slice(-1)[0];
      var cmp = prev ? span("sub", t("prevPaper", { p: pct(prev.s, prev.m) })) : "";
      /* a question removed from the pool since this paper was handed in has no card to link to */
      var wrongHere = r.wrong.filter(function (id) { return st.paper.indexOf(id) >= 0; });
      var wl = wrongHere.length ? wrongHere.map(function (id) { return qLink(id); }).join(" ") : (r.wrong.length ? "" : t("allRight"));
      var ranked = LECS.filter(function (u) { return us[u].m > 0; }).sort(function (x, y) { return pct(us[x].s, us[x].m) - pct(us[y].s, us[y].m); });
      var weakest = ranked[0];
      var tip = weakest && pct(us[weakest].s, us[weakest].m) < 80 ? '<p style="margin:8px 0 0">' + t("weakest", { u: weakest }) + "</p>" : "";
      var tline = "";
      if (r.used != null) tline = '<p class="timeline">' + (r.auto ? t("autoSubmit") : "") + t("used", { u: mmss(r.used) }) + (r.limit ? t("limitNote", { m: r.limit }) : t("noLimitNote")) + "</p>";
      var fids = flaggedIds(), fline = "";
      if (fids.length) {
        var fwrong = fids.filter(function (id) { return r.wrong.indexOf(id) >= 0; }).length;
        var unflaggedWrong = r.wrong.filter(function (id) { return fids.indexOf(id) < 0; }).length;
        var fl = fids.map(function (id) {
          var bad = r.wrong.indexOf(id) >= 0;
          return qLink(id, "flaglink " + (bad ? "bad" : "ok"), bad ? " ✗" : " ✓");
        }).join(" ");
        fline = '<p class="wrongs">' + t("flaggedList") + fl + "</p>" +
          '<p class="flagcal">' + t("flagCal", { n: fids.length, w: fwrong, u: unflaggedWrong }) + (unflaggedWrong > fwrong ? t("flagCalBad") : t("flagCalGood")) + "</p>";
      }
      box.innerHTML = '<div class="summary"><h3>' + t("report") + '</h3><div class="sumtop"><span class="big">' + p + '%</span><span class="sub">' + t("outOf", { s: fmt(r.s), m: r.m }) + "</span>" + cmp + "</div>" + tline + statsTable(us) + (wl ? '<p class="wrongs">' + t("wrongList") + wl + "</p>" : "") + fline + tip + "</div>";
      box.hidden = false;
    }
    if (hist.length > 1) {
      var agg = zeroByLec();
      hist.forEach(function (h) { Object.keys(h.units || {}).forEach(function (u) { if (agg[u]) { agg[u].s += h.units[u].s; agg[u].m += h.units[u].m; } }); });
      var trend = hist.slice(-8).map(function (h) { return pct(h.s, h.m) + "%"; }).join(" → ");
      box.appendChild(el("details", "weak", "<summary>" + t("history", { n: hist.length }) + '</summary><p class="empty" style="margin:8px 0 0">' + t("recent") + trend + "</p>" + statsTable(agg)));
      box.hidden = false;
    }
  }

  function renderMock() {
    var st = STATE.mock, root = document.getElementById("bank-mock"); if (!root) return;
    if (!st.paper.length) newPaper();
    root.innerHTML = "";
    var items = st.paper.map(function (id) { return BANKS.mock.imap[id]; });
    var num = 0;
    MOCK_SECTIONS.forEach(function (sec, ci) {
      var qs = items.filter(function (q) { return q.cat === sec.cat; });
      if (!qs.length) return;
      var head = t("mockPart", { no: S.nums[ci] || ci + 1, title: sec.title || S.catTitle[sec.cat] || sec.cat, n: qs.length });
      var box = el("div", "qgroup", "<h3>" + head + "</h3>" + '<p class="qdesc">' + (sec.desc || S.catDesc[sec.cat] || "") + "</p>");
      qs.forEach(function (q) { num++; box.appendChild(mockCard(q, num)); });
      root.appendChild(box);
    });
    mockSummary();
    updateMockBar();
    renderTex(root);
  }

  function mmss(sec) { sec = Math.max(0, Math.round(sec)); var m = Math.floor(sec / 60), x = sec % 60; return m + ":" + (x < 10 ? "0" : "") + x; }
  function clockState() {
    var tm = STATE.mock.timer;
    if (!tm || !tm.startedAt) return null;
    var e = (Date.now() - Date.parse(tm.startedAt)) / 1000;
    return tm.limit ? { left: tm.limit * 60 - e, limit: tm.limit } : { used: e };
  }
  function clockText(c) {
    if (c.limit) return t("remain") + ' <b class="clock' + (c.left < 300 ? " low" : "") + '">' + mmss(c.left) + "</b>";
    return t("usedLbl") + ' <b class="clock">' + mmss(c.used) + "</b>";
  }
  function clockHtml() { var c = clockState(); return c ? " · " + span("clockwrap", clockText(c)) : ""; }
  setInterval(function () {
    var st = STATE.mock; if (!st || st.submitted) return;
    var c = clockState(); if (!c) return;
    if (c.limit && c.left <= 0) { submitMock(true); return; }
    var w = document.querySelector("#bar-mock .clockwrap"); if (w) w.innerHTML = clockText(c);
  }, 1000);

  function render(key) { if (key === "practice") { renderPractice(); renderSA(); renderSecBoxes(); } else renderMock(); renderBook(); }

  /* ================= progress report for Claude (export panel + db doc "progress/report") ================= */
  function buildReport() {
    var ps = STATE.practice, ms = STATE.mock, lec = {}, missed = [], sa = [];
    LECS.forEach(function (u) { lec[u] = { answered: 0, firstScore: 0, total: 0 }; });
    BANKS.practice.items.forEach(function (q) {
      if (q.type === "card" || !lec[q.lec]) return;
      lec[q.lec].total++;
      var r = ps.ans[q.id], f = firstScore(q, r);
      if (f == null) return;
      lec[q.lec].answered++; lec[q.lec].firstScore += f;
      if (f < 0.999) missed.push({ id: q.id, lec: q.lec, group: (BANKS.practice.gmap[q.g] || {}).title || q.g, type: q.type, stem: plain(q.stem).slice(0, 240), firstAnswer: plain(pickText(q, r.first)), correct: plain(q.type === "fill" ? refAnswer(q) : pickText(q, q.ans)), redoneRight: mastered(q) });
    });
    LECS.forEach(function (u) { lec[u].firstScore = round2(lec[u].firstScore); });
    SA.forEach(function (s) {
      if (!saStarted(s)) return;
      var k = saScore(s), r = saRec(s);
      sa.push({ id: s.id, lec: s.lec, kind: s.kind, firstScore: k.s, afterFixes: k.f, max: k.m, missedSteps: s.steps.map(function (p, i) { return stepFirst(p, r[i]) ? null : i + 1; }).filter(Boolean) });
    });
    var hist = ms.history || [], agg = {};
    hist.forEach(function (h) { Object.keys(h.units || {}).forEach(function (u) { agg[u] = agg[u] || { s: 0, m: 0 }; agg[u].s += h.units[u].s; agg[u].m += h.units[u].m; }); });
    var last = hist[hist.length - 1];
    return {
      kind: "study-guide-report", v: 1, course: CFG.title || "", key: KEY, at: new Date().toISOString(),
      practice: { byLecture: lec, missed: missed },
      shortAnswer: sa,
      mock: {
        papers: hist.length, recent: hist.slice(-8).map(function (h) { return pct(h.s, h.m); }), byLecture: agg,
        last: last ? { at: last.at, score: last.s, max: last.m, usedSec: last.used, wrong: (last.wrong || []).map(function (id) {
          var q = BANKS.mock.imap[id]; if (!q) return { id: id };
          return { id: id, lec: q.lec, type: q.type, stem: plain(q.stem).slice(0, 240), answered: last.picks && id in last.picks ? plain(pickText(q, last.picks[id])) : null, flagged: (last.flags || []).indexOf(id) >= 0 };
        }), flaggedButRight: (last.flags || []).filter(function (id) { return (last.wrong || []).indexOf(id) < 0; }) } : null
      }
    };
  }
  function exportPanel(host) {
    var wrap = el("div", "export"), btn = button("reset", t("export"));
    var panel = el("div", "export-panel"); panel.hidden = true;
    btn.addEventListener("click", function () {
      panel.hidden = !panel.hidden;
      if (panel.hidden) return;
      var json = JSON.stringify({ report: buildReport(), state: { practice: STATE.practice, mock: STATE.mock } }, null, 1);
      panel.innerHTML = "";
      panel.appendChild(el("p", "modehint", t("exportHint")));
      var ta = document.createElement("textarea"); ta.readOnly = true; ta.value = json; ta.rows = 6; ta.setAttribute("aria-label", t("export"));
      panel.appendChild(ta);
      var row = el("div", "qfoot");
      var cp = button("btn", t("exportCopy"));
      cp.addEventListener("click", function () {
        function done() { cp.textContent = t("exportCopied"); setTimeout(function () { cp.textContent = t("exportCopy"); }, 1500); }
        function fallback() { ta.select(); try { document.execCommand("copy"); done(); } catch (e) {} }
        try { navigator.clipboard.writeText(json).then(done, fallback); } catch (e) { fallback(); }
      });
      var dl = el("a", "btn ghost", t("exportSave"));
      dl.href = "data:application/json;charset=utf-8," + encodeURIComponent(json);
      dl.download = KEY + "-progress.json";
      row.appendChild(cp); row.appendChild(dl);
      panel.appendChild(row);
    });
    wrap.appendChild(btn); wrap.appendChild(panel);
    host.appendChild(wrap);
  }

  /* ================= practice center markup ================= */
  function buildCenter() {
    var sec = document.getElementById("practice"); if (!sec) return;
    var tabs = [["practice", t("tabPractice")]];
    if (SA.length) tabs.push(["sa", t("tabSA")]);
    if (BANKS.mock.items.length) tabs.push(["mock", t("tabMock")]);
    tabs.push(["book", t("tabBook")]);
    var parts = MOCK_SECTIONS.map(function (x) { return t("partN", { n: x.n, name: x.short || S.catShort[x.cat] || x.cat }); }).join(t("partSep"));
    function bar(id) { return '<div class="bank-bar" id="bar-' + id + '"><p class="score">' + t("loading") + '</p><div class="acts"></div></div>'; }
    var h = '<p class="part-no">' + t("partNo") + "</p><h2>" + t("title") + '</h2><p class="part-src">' + (CFG.practiceIntro || t("intro")) + "</p>" +
      '<div class="pc-controls"><div class="seg" role="group" aria-label="' + t("tabsAria") + '">' +
      tabs.map(function (x, i) { return '<button type="button" data-tab="' + x[0] + '" aria-pressed="' + (i ? "false" : "true") + '">' + x[1] + "</button>"; }).join("") +
      '</div><span id="export-host"></span></div>' +
      '<div class="bankwrap" id="wrap-practice"><div class="pc-controls"><label for="scope-practice">' + t("scope") + ' <select id="scope-practice"></select></label></div>' +
      '<p class="modehint">' + t("hintPractice") + "</p>" + bar("practice") + '<div id="sum-practice" hidden></div><div id="bank-practice"></div></div>';
    if (SA.length) h += '<div class="bankwrap" id="wrap-sa" hidden><p class="modehint">' + (CFG.shortIntro || t("hintSA")) + "</p>" + bar("sa") + '<div id="bank-sa"></div></div>';
    if (BANKS.mock.items.length) h += '<div class="bankwrap" id="wrap-mock" hidden><p class="modehint">' + t("hintMock", { parts: parts }) + (MCFG.note ? " " + MCFG.note : "") + "</p>" +
      '<p class="modehint">' + t("hintTimer") + '</p><p class="modehint">' + t("hintFlag") + "</p>" + bar("mock") +
      '<div class="flagbar" id="flags-mock" hidden></div><div id="sum-mock" hidden></div><div id="bank-mock"></div></div>';
    h += '<div class="bankwrap" id="wrap-book" hidden><p class="modehint">' + t("hintBook") + "</p>" + bar("book") + '<div id="bank-book"></div></div>';
    sec.innerHTML = h;
    exportPanel(document.getElementById("export-host"));
  }

  /* Scroll position: highlight the current section in the left contents; on wide screens list its topics in the right rail. */
  function initSpy() {
    var parts = [].slice.call(document.querySelectorAll("main > header[id], main > section[id]"));
    var links = {};
    document.querySelectorAll(".toc a[href^='#']").forEach(function (a) { links[a.getAttribute("href").slice(1)] = a; });
    var rail = document.querySelector(".rail"), curPart = null, curTopic = null, items = {}, ticking = false;
    function buildRail(part) {
      items = {}; if (!rail) return;
      rail.innerHTML = "";
      var topics = part ? [].slice.call(part.querySelectorAll("article.topic[id]")) : [];
      if (!topics.length) { rail.hidden = true; return; }
      rail.hidden = false;
      var h2 = part.querySelector("h2"), no = part.querySelector(".part-no");
      rail.appendChild(el("p", "rail-k", t("railK")));
      var tt = el("p", "rail-t"); tt.textContent = (no ? no.textContent.replace(/\s+/g, " ").trim() + " · " : "") + (h2 ? h2.textContent : ""); rail.appendChild(tt);
      var ol = el("ol");
      topics.forEach(function (tp) {
        var h3 = tp.querySelector("h3"); if (!h3) return;
        var m = h3.textContent.match(/^(\d+\.\d+)\s*(.*)$/);
        var a = el("a"); a.href = "#" + tp.id;
        if (m) { a.appendChild(el("span", "n", m[1])); a.appendChild(document.createTextNode(m[2])); } else a.textContent = h3.textContent;
        items[tp.id] = a;
        var li = el("li"); li.appendChild(a); ol.appendChild(li);
      });
      rail.appendChild(ol);
      var sp = part.querySelector(".secprac[id]");
      if (sp) { var pa = el("a", "prac", t("railPrac")); pa.href = "#" + sp.id; rail.appendChild(pa); }
    }
    /* the last of these elements whose top has scrolled above the line */
    function lastAbove(list, line) {
      var last = null;
      for (var i = 0; i < list.length; i++) { if (list[i].getBoundingClientRect().top <= line) last = list[i]; else break; }
      return last;
    }
    function update() {
      ticking = false;
      var line = window.innerHeight * 0.3, p = lastAbove(parts, line) || parts[0];
      if (p !== curPart) {
        if (curPart && links[curPart.id]) links[curPart.id].classList.remove("on");
        curPart = p; curTopic = null;
        if (p && links[p.id]) links[p.id].classList.add("on");
        buildRail(p);
      }
      var tp = p ? lastAbove(p.querySelectorAll("article.topic[id]"), line) : null, tid = tp ? tp.id : null;
      if (tid !== curTopic) {
        if (curTopic && items[curTopic]) items[curTopic].classList.remove("on");
        curTopic = tid;
        if (tid && items[tid]) items[tid].classList.add("on");
      }
    }
    function onScroll() { if (!ticking) { ticking = true; requestAnimationFrame(update); } }
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    update();
  }

  function boot() {
    ["practice", "mock"].forEach(function (key) { STATE[key] = fix(key, readLocal(key)); });
    buildCenter();
    buildSecBoxes();
    var sel = document.getElementById("scope-practice");
    if (sel && !sel.options.length) {
      var P = BANKS.practice.items;
      sel.appendChild(new Option(t("scopeAll", { n: P.length }), "all"));
      LECS.forEach(function (u) {
        var n = P.filter(function (q) { return q.lec === u; }).length;
        if (n) sel.appendChild(new Option(t("scopeLec", { lec: u, n: n }), u));
      });
      sel.addEventListener("change", function () { STATE.practice.scope = sel.value; save("practice"); renderPractice(); });
    }
    render("practice"); if (BANKS.mock.items.length) render("mock");
    syncFromDb("practice"); if (BANKS.mock.items.length) syncFromDb("mock");
    document.querySelectorAll("[data-tab]").forEach(function (tb) {
      tb.addEventListener("click", function () {
        var which = tb.getAttribute("data-tab");
        document.querySelectorAll("[data-tab]").forEach(function (x) { x.setAttribute("aria-pressed", x === tb ? "true" : "false"); });
        document.querySelectorAll(".bankwrap").forEach(function (w) { w.hidden = w.id !== "wrap-" + which; });
        if (which === "book") renderBook();
        lsSet("tab", which);
      });
    });
    var tab = lsGet("tab");
    if (tab) { var tb = document.querySelector('[data-tab="' + tab + '"]'); if (tb) tb.click(); }
    renderTex(document.body);
    initSpy();
  }

  window.StudyGuide = { t: t, el: el, renderTex: function (root) { renderTex(root || document.body); }, report: buildReport };
  boot();
})();
