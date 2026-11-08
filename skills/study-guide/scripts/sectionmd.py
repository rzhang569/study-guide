"""Turn a section written in Markdown (sections/*.md) into the page's section HTML.

build.py calls convert() for every .md file in sections/; .html files are used as they are, and the two can be
mixed. The format is described in references/content-standard.md ("Writing sections in Markdown").
Standard library only.
"""
import html
import re

LABELS = {
    "en": {"lead": "In one line", "plain": "In plain words", "eg": "Example", "trap": "Trap", "terms": "Glossary",
           "must": "The exam only asks these", "more": "Derivation (not on the exam)",
           "howto": "How to use this page", "p3": "core", "p2": "likely", "p1": "background"},
    "zh": {"lead": "一句话", "plain": "人话", "eg": "例子", "trap": "易错", "terms": "术语表",
           "must": "考试只考这几点", "more": "推导（不考）", "howto": "怎么用这个页面",
           "p3": "必考", "p2": "常考", "p1": "了解"},
}
FRONT_KEYS = {"kind", "id", "toc", "n", "part", "title", "src", "eyebrow"}
BOXES = {"plain", "eg", "trap"}
FENCES = BOXES | {"must", "terms", "facts", "more", "steps", "traps", "twocol", "flow", "howto", "sheet", "figure", "html"}
BLOCK_TAGS = ("address|article|aside|blockquote|details|div|dl|fieldset|figure|footer|form|h[1-6]|header|hr|iframe|"
              "nav|ol|p|pre|section|svg|table|ul|script|style|canvas")
RAW_START = re.compile(r"<(?:!--|/?(?:" + BLOCK_TAGS + r")\b)", re.I)
FENCE_OPEN = re.compile(r"^(:{3,})\s*([A-Za-z][\w-]*)\s*(.*?)\s*$")
FENCE_CLOSE = re.compile(r"^:{3,}\s*$")
LIST_ITEM = re.compile(r"^(\s*)([-*]|\d+[.)])\s+(.*)$")
HEADING = re.compile(r"^(#{1,4})\s+(.*?)\s*$")
KV_LINE = re.compile(r"^(src|lead)\s*[:：]\s*(.*)$")
ATTRS = re.compile(r"\s*\{([^{}]*)\}\s*$")
TAG = re.compile(r"</?[A-Za-z][A-Za-z0-9-]*(?:\s[^<>]*)?/?>|<!--.*?-->", re.S)
ENTITY = re.compile(r"&(?:#\d+|#x[0-9A-Fa-f]+|[A-Za-z][A-Za-z0-9]*);")
COMMENT = re.compile(r"\s{2,}#\s.*$")  # "key: value   # note" in front matter and figure blocks
# $x$ is math; a price such as $10 is not, because math never starts or ends with a space, never holds a bare $, and
# its closing $ is never followed by a digit (the Pandoc rule)
MATH = re.compile(r"(?<![\\$])\$(?=[^\s$])([^$]+?)(?<=[^\s\\])\$(?!\d)")


class MdError(Exception):
    def __init__(self, line, msg):
        super().__init__(msg)
        self.line, self.msg = line, msg


# ---------- inline text ----------

GREEK = ("alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi pi rho sigma tau upsilon phi chi psi "
         "omega").split()
SYMBOLS = {
    **dict(zip(GREEK, "αβγδεζηθικλμνξπρστυφχψω")),
    "varepsilon": "ε", "vartheta": "ϑ", "varphi": "φ", "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ",
    "Xi": "Ξ", "Pi": "Π", "Sigma": "Σ", "Phi": "Φ", "Psi": "Ψ", "Omega": "Ω",
    "cdot": "·", "times": "×", "div": "÷", "pm": "±", "mp": "∓", "le": "≤", "leq": "≤", "ge": "≥", "geq": "≥",
    "ne": "≠", "neq": "≠", "approx": "≈", "equiv": "≡", "sim": "~", "propto": "∝", "to": "→", "rightarrow": "→",
    "leftarrow": "←", "Rightarrow": "⇒", "Leftrightarrow": "⇔", "mapsto": "↦", "infty": "∞", "sum": "Σ",
    "prod": "∏", "int": "∫", "partial": "∂", "nabla": "∇", "cup": "∪", "cap": "∩", "in": "∈", "notin": "∉",
    "subset": "⊂", "subseteq": "⊆", "emptyset": "∅", "varnothing": "∅", "forall": "∀", "exists": "∃", "neg": "¬",
    "land": "∧", "lor": "∨", "mid": "|", "vert": "|", "ldots": "…", "cdots": "⋯", "dots": "…", "circ": "∘",
    "prime": "′", "quad": " ", "qquad": "  ", "lvert": "|", "rvert": "|", "langle": "⟨", "rangle": "⟩",
    "uparrow": "↑", "downarrow": "↓", "degree": "°", "%": "%", "$": "$", "{": "{", "}": "}", "_": "_", "&": "&",
}
DROP = {"left", "right", "big", "Big", "bigg", "Bigg", "mathrm", "mathbf", "mathit", "mathbb", "mathcal", "text",
        "textbf", "textit", "operatorname", "displaystyle", "boldsymbol", "limits", "nolimits", ",", ";", "!", ":", " "}
SUPS = str.maketrans("0123456789+-=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ")
SUBS = str.maketrans("0123456789+-=()", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎")


def tex_fallback(tex, markup=True):
    """A readable plain-text version of a formula, shown until MathJax replaces it (or if it never loads).
    markup=False gives text for an SVG label, where <sup> is not available."""
    s = tex
    group = r"\{([^{}]*)\}"
    for _ in range(6):  # innermost groups first, a few levels deep
        s0 = s
        s = re.sub(r"\\[dt]?frac\s*" + group + r"\s*" + group,
                   lambda m: f"{wrap(m.group(1))}/{wrap(m.group(2))}", s)
        s = re.sub(r"\\binom\s*" + group + r"\s*" + group, r"C(\1, \2)", s)
        s = re.sub(r"\\sqrt\s*" + group, lambda m: "√" + wrap(m.group(1)), s)
        s = re.sub(r"\\(?:hat|bar|overline|tilde|vec)\s*" + group, r"\1", s)
        s = re.sub(r"\\(?:" + "|".join(sorted((d for d in DROP if d.isalpha()), key=len, reverse=True)) + r")\s*" + group,
                   r"\1", s)
        if s == s0:
            break
    s = re.sub(r"\\([A-Za-z]+|.)", lambda m: SYMBOLS.get(m.group(1), "" if m.group(1) in DROP else m.group(1)), s)

    def script(m, table, tag):
        body = m.group(1) if m.group(1) is not None else m.group(2)
        if all(ord(ch) in table for ch in body):
            return body.translate(table)
        if markup:
            return f"<{tag}>{body}</{tag}>"  # escaped below with the rest of the text
        mark = "^" if tag == "sup" else "_"
        return mark + (body if len(body) == 1 else f"({body})")

    s = re.sub(r"\^(?:\{([^{}]*)\}|([^\s{}\\]))", lambda m: script(m, SUPS, "sup"), s)
    s = re.sub(r"_(?:\{([^{}]*)\}|([^\s{}\\]))", lambda m: script(m, SUBS, "sub"), s)
    s = s.replace("{", "").replace("}", "")
    s = re.sub(r"\s+", " ", s).strip()
    if not markup:
        return s
    # keep the <sup>/<sub> we made, escape everything else
    parts = re.split(r"(</?su[bp]>)", s)
    return "".join(p if re.fullmatch(r"</?su[bp]>", p) else html.escape(p, quote=False) for p in parts)


def wrap(x):
    x = x.strip()
    return x if re.fullmatch(r"[^\s+\-−*/=<>]+", x) else f"({x})"


def math_span(tex, cls="m"):
    return f'<span class="{cls}" data-tex="{html.escape(tex.strip(), quote=True)}">{tex_fallback(tex.strip())}</span>'


def escape_text(s):
    """Escape & and < except where they start an entity or an HTML tag the author wrote."""
    out, pos = [], 0
    for m in TAG.finditer(s):
        out.append(_esc(s[pos:m.start()]))
        out.append(m.group(0))
        pos = m.end()
    out.append(_esc(s[pos:]))
    return "".join(out)


def _esc(s):
    s = re.sub(r"&(?!(?:#\d+|#x[0-9A-Fa-f]+|[A-Za-z][A-Za-z0-9]*);)", "&amp;", s)
    return s.replace("<", "&lt;")


def inline(s):
    """Markdown inline text to HTML: `code`, $math$, **bold**, *italic*, [text](url), \\$ for a dollar sign.
    Inline HTML the author wrote passes through."""
    keep = []

    def hold(x):
        keep.append(x)
        return f"\x00{len(keep) - 1}\x00"

    s = re.sub(r"`([^`]+)`", lambda m: hold(f"<code>{html.escape(m.group(1), quote=False)}</code>"), s)
    s = MATH.sub(lambda m: hold(math_span(m.group(1))), s)
    s = s.replace("\\$", hold("$")).replace("\\*", hold("*"))
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)",
               lambda m: hold(f'<a href="{html.escape(m.group(2), quote=True)}">') + m.group(1) + hold("</a>"), s)
    s = escape_text(s)
    s = re.sub(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![*\w])\*(?=[^\s*])(.+?)(?<=[^\s*])\*(?![*\w])", r"<i>\1</i>", s)
    while "\x00" in s:
        s = re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], s)
    return s


def split_term(text, line):
    """'term: definition' -> (term, definition), splitting at the first ': ' or '：' outside $math$ and `code`."""
    inside = None
    for i, ch in enumerate(text):
        if ch in "$`" and (i == 0 or text[i - 1] != "\\"):
            inside = None if inside == ch else (inside or ch)
        elif inside is None and (ch == "：" or (ch == ":" and text[i + 1:i + 2] in (" ", ""))):
            return text[:i].strip(), text[i + 1:].strip()
    raise MdError(line, f"'{text[:40]}' needs the form 'term: definition'")


# ---------- blocks ----------

class Converter:
    def __init__(self, text, name, lang, rep):
        self.name, self.rep = name, rep
        self.lab = LABELS.get(lang, LABELS["en"])
        self.lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        self.topic_ids = set()

    # parse -------------------------------------------------------------
    def parse(self, lines, base):
        """lines with their first line number base -> a list of nodes (tuples whose 2nd item is the line number)."""
        nodes, i, n = [], 0, len(lines)
        while i < n:
            ln, line = base + i, lines[i]
            s = line.strip()
            if not s:
                i += 1
                continue
            if s.startswith("```"):
                j = i + 1
                while j < n and not lines[j].strip().startswith("```"):
                    j += 1
                if j >= n:
                    raise MdError(ln, "code block opened with ``` is never closed")
                nodes.append(("code", ln, "\n".join(lines[i + 1:j])))
                i = j + 1
                continue
            m = FENCE_OPEN.match(s)
            if m:
                name, title = m.group(2).lower(), m.group(3)
                if name not in FENCES:
                    raise MdError(ln, f"unknown block '::: {m.group(2)}'; known: {', '.join(sorted(FENCES))}")
                j, depth, in_code = i + 1, 1, False
                raw = name in ("html", "figure")
                while j < n:
                    t = lines[j].strip()
                    if t.startswith("```") and not raw:
                        in_code = not in_code
                    elif not in_code and FENCE_CLOSE.match(t):
                        depth -= 1
                        if depth == 0:
                            break
                    elif not in_code and not raw and FENCE_OPEN.match(t):
                        depth += 1
                    j += 1
                if j >= n:
                    raise MdError(ln, f"'::: {name}' is never closed; end it with a line of ':::'")
                nodes.append(("fence", ln, name, title, lines[i + 1:j], ln + 1))
                i = j + 1
                continue
            if FENCE_CLOSE.match(s):
                raise MdError(ln, "':::' closes a block that was never opened")
            if s.startswith("$$"):
                rest = s[2:]
                if "$$" in rest:  # $$ tex $$ note
                    tex, note = rest.split("$$", 1)
                    nodes.append(("math", ln, tex, note.strip()))
                    i += 1
                    continue
                j, buf = i + 1, [rest]
                while j < n and "$$" not in lines[j]:
                    buf.append(lines[j])
                    j += 1
                if j >= n:
                    raise MdError(ln, "display formula opened with $$ is never closed")
                tex_end, note = lines[j].split("$$", 1)
                buf.append(tex_end)
                nodes.append(("math", ln, "\n".join(buf), note.strip()))
                i = j + 1
                continue
            m = HEADING.match(s)
            if m and line.startswith("#"):
                text, attrs = m.group(2), ""
                am = ATTRS.search(text)
                if am:
                    text, attrs = text[:am.start()], am.group(1)
                nodes.append(("h", ln, len(m.group(1)), text, attrs))
                i += 1
                continue
            m = KV_LINE.match(s)
            if m and not line[:1].isspace():
                nodes.append(("kv", ln, m.group(1), m.group(2)))
                i += 1
                continue
            if s.startswith("|"):
                j = i
                while j < n and lines[j].strip().startswith("|"):
                    j += 1
                nodes.append(("table", ln, [lines[k].strip() for k in range(i, j)]))
                i = j
                continue
            if LIST_ITEM.match(line):
                j, nodes_ = self.take_list(lines, i, base)
                nodes.append(nodes_)
                i = j
                continue
            if RAW_START.match(s):
                j = i
                while j < n and lines[j].strip():
                    j += 1
                nodes.append(("raw", ln, "\n".join(lines[i:j])))
                i = j
                continue
            j, buf = i + 1, [s]
            while j < n and lines[j].strip() and not self.starts_block(lines[j]):
                buf.append(lines[j].strip())
                j += 1
            nodes.append(("p", ln, " ".join(buf)))
            i = j
        return nodes

    @staticmethod
    def starts_block(line):
        s = line.strip()
        return bool(s.startswith(("```", "$$", "|")) or FENCE_OPEN.match(s) or FENCE_CLOSE.match(s)
                    or (HEADING.match(s) and line.startswith("#")) or (KV_LINE.match(s) and not line[:1].isspace())
                    or LIST_ITEM.match(line) or RAW_START.match(s))

    def take_list(self, lines, i, base):
        first = LIST_ITEM.match(lines[i])
        indent, ordered = len(first.group(1)), first.group(2)[0].isdigit()
        items, j, n = [], i, len(lines)

        def lead(t):
            return len(t) - len(t.lstrip())

        def next_text(k):
            return next((x for x in lines[k:] if x.strip()), None)

        def sibling(t):
            m = LIST_ITEM.match(t) if t else None
            return m if m and len(m.group(1)) == indent and m.group(2)[0].isdigit() == ordered else None

        while j < n:
            m = sibling(lines[j])
            if not m:
                break
            content = m.start(3)
            body, k = [m.group(3)], j + 1
            while k < n:
                t = lines[k]
                if not t.strip():
                    nxt = next_text(k)
                    if nxt is None or lead(nxt) <= indent:  # the item ends at a blank line unless indented text follows
                        break
                    body.append("")
                elif lead(t) > indent:
                    body.append(t[min(lead(t), content):])
                elif body[-1] and not self.starts_block(t):
                    body.append(t.strip())  # a lazy continuation of the item's text
                else:
                    break
                k += 1
            items.append((base + j, body))
            j = k
            while j < n and not lines[j].strip():  # blank lines between two items of the same list
                if not sibling(next_text(j)):
                    break
                j += 1
        return j, ("list", base + i, ordered, items)

    # render ------------------------------------------------------------
    def render(self, nodes, topics=False, sid=None):
        out, topic = [], None
        for node in nodes:
            kind = node[0]
            if topics and kind == "h" and node[2] <= 3:
                if topic is not None:
                    out.append("</article>")
                    topic = None
                if node[2] == 3:
                    topic = self.open_topic(node, sid)
                    out.append(topic)
                    continue
            out.append(self.block(node))
        if topic is not None:
            out.append("</article>")
        return "\n".join(x for x in out if x)

    def open_topic(self, node, sid):
        _, ln, _, text, attrs = node
        tid, pri = None, None
        for tok in attrs.split():
            if tok.startswith("#"):
                tid = tok[1:]
            elif tok.lstrip(".") in ("p1", "p2", "p3"):
                pri = tok.lstrip(".")
            else:
                raise MdError(ln, f"unknown topic attribute '{tok}'; use {{#topic-id p3}} (p3 core, p2 likely, p1 background)")
        if not tid:
            tid = f"{sid}-t{len(self.topic_ids) + 1}"
        if not re.fullmatch(r"[A-Za-z][\w-]*", tid):
            raise MdError(ln, f"topic id '{tid}' should be letters, digits, '-' or '_', starting with a letter")
        if tid in self.topic_ids:
            raise MdError(ln, f"topic id '{tid}' is used twice")
        self.topic_ids.add(tid)
        tag = f'<span class="pri {pri}">{self.lab[pri]}</span>' if pri else ""
        return f'<article class="topic" id="{tid}">\n<div class="topic-head"><h3>{inline(text.strip())}</h3>{tag}</div>'

    def block(self, node):
        kind, ln = node[0], node[1]
        if kind == "p":
            return f"<p>{inline(node[2])}</p>"
        if kind == "h":
            level = node[2]
            return f"<h{level}>{inline(node[3].strip())}</h{level}>"
        if kind == "kv":
            if node[2] == "src":
                return f'<p class="src">{inline(node[3])}</p>'
            return f'<p class="lead"><b>{self.lab["lead"]}</b>{inline(node[3])}</p>'
        if kind == "code":
            return f'<pre class="code">{html.escape(node[2], quote=False)}</pre>'
        if kind == "math":
            note = f'<span class="note">{inline(node[3])}</span>' if node[3] else ""
            return f'<div class="fx">{math_span(node[2], "tex-d")}{note}</div>'
        if kind == "raw":
            return node[2]
        if kind == "table":
            return self.table(node[2], ln)
        if kind == "list":
            return self.list_html(node)
        if kind == "fence":
            return self.fence(*node[1:])
        raise AssertionError(kind)

    def item_html(self, body, ln):
        nodes = self.parse(body, ln)
        if len(nodes) == 1 and nodes[0][0] == "p":
            return inline(nodes[0][2])
        if nodes and nodes[0][0] == "p":  # "text" then a nested list: keep the text unwrapped
            return inline(nodes[0][2]) + "\n" + self.render(nodes[1:])
        return self.render(nodes)

    def list_html(self, node, cls=None, ordered=None):
        _, ln, is_ordered, items = node
        tag = "ol" if (is_ordered if ordered is None else ordered) else "ul"
        attr = f' class="{cls}"' if cls else ""
        lis = "".join(f"<li>{self.item_html(body, iln)}</li>" for iln, body in items)
        return f"<{tag}{attr}>{lis}</{tag}>"

    def table(self, rows, ln):
        def cells(row):
            row = row.strip()
            if row.startswith("|"):
                row = row[1:]
            if row.endswith("|") and not row.endswith("\\|"):
                row = row[:-1]
            out, cur, inside, i = [], "", None, 0
            while i < len(row):
                ch = row[i]
                if ch == "\\" and row[i + 1:i + 2] == "|":
                    cur += "|"
                    i += 2
                    continue
                if ch in "$`":
                    inside = None if inside == ch else (inside or ch)
                if ch == "|" and inside is None:
                    out.append(cur.strip())
                    cur = ""
                else:
                    cur += ch
                i += 1
            out.append(cur.strip())
            return out

        parsed = [cells(r) for r in rows]
        sep = len(parsed) > 1 and all(re.fullmatch(r":?-{2,}:?", c.replace(" ", "")) for c in parsed[1] if c)
        head, body = (parsed[0], parsed[2:]) if sep else (None, parsed)
        trs = []
        if head:
            trs.append("<tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr>")
        for r in body:
            trs.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
        return '<div class="tbl"><table>\n' + "\n".join(trs) + "\n</table></div>"

    def terms(self, body, ln, cls):
        nodes = self.parse(body, ln)
        if len(nodes) != 1 or nodes[0][0] != "list":
            raise MdError(ln, f"'::: {cls}' holds one list of '- term: definition' lines")
        rows = []
        for iln, item in nodes[0][3]:
            term, dfn = split_term(" ".join(x.strip() for x in item if x.strip()), iln)
            rows.append(f"<div><dt>{inline(term)}</dt><dd>{inline(dfn)}</dd></div>")
        return f'<dl class="{cls}">' + "".join(rows) + "</dl>"

    def fence(self, ln, name, title, body, body_ln):
        lab = self.lab
        if name in BOXES:
            nodes = self.parse(body, body_ln)
            if len(nodes) == 1 and nodes[0][0] == "p":
                inner = inline(nodes[0][2])
            else:
                inner = "\n" + self.render(nodes)
            return f'<div class="{name}"><b>{inline(title) if title else lab[name]}</b>{inner}</div>'
        if name == "must":
            head = f'<p class="must-t">{inline(title) if title else lab["must"]}</p>'
            return f'<div class="must">{head}\n{self.render(self.parse(body, body_ln))}</div>'
        if name == "terms":
            head = f'<p class="terms-title">{inline(title) if title else lab["terms"]}</p>'
            return head + "\n" + self.terms(body, body_ln, "terms")
        if name == "facts":
            return self.terms(body, body_ln, "facts")
        if name == "more":
            summary = inline(title) if title else lab["more"]
            return f'<details class="more"><summary>{summary}</summary>\n{self.render(self.parse(body, body_ln))}\n</details>'
        if name in ("steps", "traps"):
            nodes = self.parse(body, body_ln)
            if len(nodes) != 1 or nodes[0][0] != "list":
                raise MdError(ln, f"'::: {name}' holds one numbered list")
            return self.list_html(nodes[0], cls=name, ordered=True)
        if name == "twocol":
            cols, cur = [], None
            for k, line in enumerate(body):
                m = HEADING.match(line.strip())
                if m and len(m.group(1)) == 4:
                    cur = [m.group(2), [], body_ln + k + 1]
                    cols.append(cur)
                elif cur is not None:
                    cur[1].append(line)
                elif line.strip():
                    raise MdError(body_ln + k, "'::: twocol' starts each column with a '#### Column title' line")
            if len(cols) < 2:
                raise MdError(ln, "'::: twocol' needs two '#### Column title' lines")
            inner = "".join(f"<div><h4>{inline(t)}</h4>\n{self.render(self.parse(b, bl))}</div>" for t, b, bl in cols)
            return f'<div class="twocol">{inner}</div>'
        if name == "flow":
            text = " ".join(x.strip() for x in body if x.strip())
            steps = [x.strip() for x in re.split(r"\s*(?:->|→)\s*", text) if x.strip()]
            if len(steps) < 2:
                raise MdError(ln, "'::: flow' is one line of steps joined by ->, e.g. input -> **key step** -> output")
            spans = []
            for st in steps:
                m = re.fullmatch(r"\*\*(.+)\*\*", st)
                spans.append(f'<span class="k">{inline(m.group(1))}</span>' if m else f"<span>{inline(st)}</span>")
            return '<div class="flow">' + "<i>→</i>".join(spans) + "</div>"
        if name == "howto":
            head = f"<h2>{inline(title) if title else lab['howto']}</h2>"
            return f'<div class="howto">{head}\n{self.render(self.parse(body, body_ln))}</div>'
        if name == "sheet":
            return f'<div class="sheet">\n{self.render(self.parse(body, body_ln))}\n</div>'
        if name == "html":
            return "\n".join(body)
        if name == "figure":
            try:
                body = [COMMENT.sub("", x) for x in body]
                return figures().figure(title, body, body_ln, self.warn, inline, plain_label)
            except ValueError as e:
                line, msg = e.args if len(e.args) == 2 else (ln, str(e))
                raise MdError(line or ln, msg)
        raise AssertionError(name)

    def warn(self, line, msg):
        self.rep.warn(f"sections/{self.name} line {line}: {msg}")

    # document ----------------------------------------------------------
    def convert(self):
        lines, base, front = self.lines, 1, {}
        if lines and lines[0].strip() == "---":
            end = next((k for k in range(1, len(lines)) if lines[k].strip() == "---"), None)
            if end is None:
                raise MdError(1, "the front matter that starts with --- is never closed with ---")
            for k in range(1, end):
                t = COMMENT.sub("", lines[k]).strip()
                if not t:
                    continue
                m = re.match(r"^([A-Za-z]+)\s*:\s*(.*)$", t)
                if not m:
                    raise MdError(k + 1, f"front matter lines look like 'key: value', not '{t[:40]}'")
                key = m.group(1).lower()
                if key not in FRONT_KEYS:
                    raise MdError(k + 1, f"unknown front matter key '{m.group(1)}'; known: {', '.join(sorted(FRONT_KEYS))}")
                front[key] = m.group(2).strip()
            lines, base = lines[end + 1:], end + 2
        kind = front.get("kind", "part").lower()
        nodes = self.parse(lines, base)
        if kind == "hero":
            sid = front.get("id", "exam")
            eyebrow = f'<p class="eyebrow">{inline(front["eyebrow"])}</p>\n' if front.get("eyebrow") else ""
            title = f"<h1>{inline(front['title'])}</h1>\n" if front.get("title") else ""
            return f'<header class="hero" id="{html.escape(sid, quote=True)}">\n{eyebrow}{title}{self.render(nodes)}\n</header>\n'
        if kind != "part":
            raise MdError(1, f"kind is 'part' (the default) or 'hero', not '{kind}'")
        sid = front.get("id")
        if not sid:
            raise MdError(1, "a section needs an id in its front matter, e.g.\n---\nid: l1\ntoc: L1 Short title\n---")
        if not re.fullmatch(r"[A-Za-z][\w-]*", sid):
            raise MdError(1, f"section id '{sid}' should be letters, digits, '-' or '_', starting with a letter")
        attrs = f' id="{sid}"'
        if front.get("toc"):
            attrs += f' data-toc="{html.escape(front["toc"], quote=True)}"'
        if front.get("n"):
            attrs += f' data-n="{html.escape(front["n"], quote=True)}"'
        title = front.get("title")
        if title is None:  # the first heading, when it is a ## one, is the section title
            first = next((k for k, nd in enumerate(nodes) if nd[0] == "h"), None)
            if first is not None and nodes[first][2] == 2:
                title = nodes[first][3]
                nodes = nodes[:first] + nodes[first + 1:]
        head = []
        if front.get("part"):
            head.append(f'<p class="part-no">{inline(front["part"])}</p>')
        if title:
            head.append(f"<h2>{inline(title.strip())}</h2>")
        if front.get("src"):
            head.append(f'<p class="part-src">{inline(front["src"])}</p>')
        body = self.render(nodes, topics=True, sid=sid)
        return f'<section class="part"{attrs}>\n' + "\n".join(head + [body]) + "\n</section>\n"


def plain_label(s):
    """Markdown label text -> plain text for an SVG <text>: $math$ becomes readable characters, ** and * marks go."""
    s = MATH.sub(lambda m: tex_fallback(m.group(1), markup=False), s)
    s = s.replace("\\$", "$")
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"`([^`]+)`", r"\1", s)
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


_FIGURES = []


def figures():
    """figures.py from this folder, loaded on first use (build.py may itself be loaded by path, not as a package)."""
    if not _FIGURES:
        import importlib.util
        from pathlib import Path
        spec = importlib.util.spec_from_file_location("study_figures", Path(__file__).with_name("figures.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _FIGURES.append(mod)
    return _FIGURES[0]


def convert(text, name, lang, rep):
    """Markdown section text -> HTML, or None after reporting an error to rep."""
    try:
        return Converter(text, name, lang, rep).convert()
    except MdError as e:
        rep.err(f"sections/{name} line {e.line}: {e.msg}")
        return None
