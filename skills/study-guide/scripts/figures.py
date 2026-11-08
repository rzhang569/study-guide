"""Figure templates for Markdown sections: grid, tree, bars and plot.

Each template turns a few parameter lines into an inline SVG that uses the page's diagram classes, so an author
writes numbers and labels instead of coordinates. Text widths are estimated the way references/content-standard.md
suggests (about 0.56 x font size per Latin character, 1 x per CJK character); a label that would overlap another
label, a line or a dot, or run off the figure, is reported as a warning. Standard library only.
"""
import ast
import html
import math
import re

W = 560
SIZES = {"": 14, "small": 12.5, "ttl": 15, "mono": 13, "atxt": 14, "wtxt": 14}
NOTE_STYLES = {"ttl": "ttl", "acc": "atxt", "warn": "wtxt", "small": "small"}
COMMON = {"caption", "alt", "height"}
KEYS = {
    "grid": {"rows", "cols", "cell", "top", "left", "col-heads", "row-heads", "hl", "wn", "z", "text"},
    "tree": {"root"},
    "bars": {"x", "y", "hl", "wn", "title", "mark", "values", "fmt"},
    "plot": {"x", "y", "xticks", "yticks", "grid"},
}
FUNCS = {"sqrt": math.sqrt, "exp": math.exp, "log": math.log, "ln": math.log, "log10": math.log10, "log2": math.log2,
         "sin": math.sin, "cos": math.cos, "tan": math.tan, "abs": abs, "min": min, "max": max, "comb": math.comb,
         "factorial": math.factorial, "floor": math.floor, "ceil": math.ceil, "round": round}
CONSTS = {"pi": math.pi, "e": math.e}
OPS = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.IfExp, ast.Call, ast.Name, ast.Load,
       ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv, ast.USub, ast.UAdd, ast.And,
       ast.Or, ast.Not, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)


class Fig(ValueError):
    """(line, message); sectionmd turns it into a build error."""


def num(v):
    """A coordinate or value without needless digits."""
    s = f"{v:.1f}" if abs(v) >= 1 or v == 0 else f"{v:.3g}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def safe_pow(a, b):
    if abs(b) > 64 or (abs(a) > 1e6 and abs(b) > 4):
        raise OverflowError("power too large")
    return a ** b


class PowToCall(ast.NodeTransformer):
    def visit_BinOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, ast.Pow):
            return ast.copy_location(ast.Call(func=ast.Name(id="safe_pow", ctx=ast.Load()), args=[node.left, node.right],
                                              keywords=[]), node)
        return node


def expr(src, names, line, what):
    """Compile a small math expression in the given variable names. ^ means power; = in a condition means ==."""
    s = src.strip().replace("^", "**").replace("×", "*").replace("·", "*").replace("−", "-").replace("÷", "/")
    s = re.sub(r"(?<![<>=!])=(?!=)", "==", s)
    try:
        tree = ast.parse(s, mode="eval")
    except SyntaxError:
        hint = " (write 2*x, not 2x)" if re.search(r"\d[A-Za-z(]", s) else ""
        raise Fig(line, f"cannot read the {what} '{src}'{hint}")
    for node in ast.walk(tree):
        if not isinstance(node, OPS):
            raise Fig(line, f"the {what} '{src}' uses something other than numbers, {', '.join(names)}, + - * / ^ "
                            f"and functions like sqrt, exp, log, comb")
        if isinstance(node, ast.Name) and node.id not in names and node.id not in FUNCS and node.id not in CONSTS:
            raise Fig(line, f"the {what} '{src}' uses '{node.id}'; it may only use {', '.join(names)}")
        if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name) or node.func.id not in FUNCS or node.keywords):
            raise Fig(line, f"the {what} '{src}' calls something other than {', '.join(sorted(FUNCS))}")
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
            raise Fig(line, f"the {what} '{src}' may only contain numbers")
    code = compile(ast.fix_missing_locations(PowToCall().visit(tree)), "<figure>", "eval")
    env = {"__builtins__": {}, "safe_pow": safe_pow, **FUNCS, **CONSTS}

    def run(**kw):
        try:
            v = eval(code, env, kw)
        except (ArithmeticError, ValueError, TypeError):
            return None
        return v if isinstance(v, (bool, int, float)) else None
    return run


def number(s, line, what):
    try:
        v = float(s.strip().replace("−", "-"))
    except ValueError:
        raise Fig(line, f"{what} should be a number, not '{s.strip()}'")
    if not math.isfinite(v):
        raise Fig(line, f"{what} should be a finite number")
    return v


def tw(text, size, cls=""):
    """Estimated rendered width of a label in px."""
    per = 0.6 if cls in ("mono", "ttl") else 0.56
    return sum(size if (ord(ch) >= 0x2E80 or 0xFF00 <= ord(ch) <= 0xFFEF) else per * size for ch in text)


def labels(spec, line, what):
    """'0..10' -> ['0', ..., '10']; 'a, b, c' -> ['a', 'b', 'c']; 'a b c' -> ['a', 'b', 'c']."""
    spec = spec.strip()
    m = re.fullmatch(r"(-?\d+)\s*\.\.\s*(-?\d+)", spec)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if b < a or b - a > 60:
            raise Fig(line, f"{what} range '{spec}' should go up, with at most 60 steps")
        return [str(k) for k in range(a, b + 1)]
    parts = [p.strip() for p in (spec.split(",") if "," in spec else spec.split())]
    if not all(parts):
        raise Fig(line, f"{what} '{spec}' has an empty entry")
    return parts


class Canvas:
    """Collects SVG parts plus every label's box and every line, so overlaps can be checked at the end."""

    def __init__(self, kind, line, warn):
        self.kind, self.line, self.warn = kind, line, warn
        self.parts, self.boxes, self.segs, self.dots = [], [], [], []

    def add(self, s):
        self.parts.append(s)

    @staticmethod
    def box_of(x, y, s, cls, anchor):
        size = SIZES.get(cls.split()[0] if cls else "", 14)
        w = tw(s, size, cls.split()[0] if cls else "")
        x0 = x if anchor == "start" else x - w / 2 if anchor == "middle" else x - w
        return (x0, y - 0.78 * size, x0 + w, y + 0.22 * size)

    def free(self, box, owner, height):
        """True when a label box stays inside the figure and clear of other labels, lines and dots."""
        if box[0] < 2 or box[2] > W - 2 or box[1] < 2 or box[3] > height - 2:
            return False
        if any(hit(box, b["box"]) for b in self.boxes if owner is None or b["owner"] != owner):
            return False
        if any(seg_hits(box, sg) for sg in self.segs if owner is None or sg[5] != owner):
            return False
        return not any(hit(box, (cx - r, cy - r, cx + r, cy + r), 0) for cx, cy, r, _, o in self.dots if o != owner)

    def place(self, spots, s, cls, owner, height):
        """Draw a label at the first spot (x, y, anchor) where it fits; if none fits, at the first one, and check()
        reports the clash."""
        for x, y, anchor in spots:
            if self.free(self.box_of(x, y, s, cls, anchor), owner, height):
                return self.text(x, y, s, cls, anchor, owner=owner)
        x, y, anchor = spots[0]
        self.text(x, y, s, cls, anchor, owner=owner)

    def text(self, x, y, s, cls="", anchor="start", name=None, owner=None, obstacle=False):
        box = self.box_of(x, y, s, cls, anchor)
        self.boxes.append({"box": box, "name": name or s, "owner": owner, "check": not obstacle})
        attrs = f' class="{cls}"' if cls else ""
        if anchor != "start":
            attrs += f' text-anchor="{anchor}"'
        self.add(f'<text x="{num(x)}" y="{num(y)}"{attrs}>{html.escape(s, quote=False)}</text>')

    def seg(self, x1, y1, x2, y2, name, owner=None):
        self.segs.append((x1, y1, x2, y2, name, owner))

    def check(self, height, hint):
        found = []
        boxes = self.boxes
        for i, a in enumerate(boxes):
            if not a["check"]:
                continue
            bx = a["box"]
            if bx[0] < 1 or bx[2] > W - 1 or bx[1] < 1 or bx[3] > height - 1:
                side = "left" if bx[0] < 1 else "right" if bx[2] > W - 1 else "top" if bx[1] < 1 else "bottom"
                found.append(f'"{a["name"]}" runs past the {side} edge')
            for j, b in enumerate(boxes):
                if j == i or (b["check"] and j < i) or (a["owner"] is not None and a["owner"] == b["owner"]):
                    continue
                if hit(bx, b["box"]):
                    found.append(f'"{a["name"]}" overlaps "{b["name"]}"')
            for sg in self.segs:
                if sg[5] is not None and sg[5] == a["owner"]:
                    continue
                if seg_hits(bx, sg):
                    found.append(f'"{a["name"]}" overlaps {sg[4]}')
                    break
            for cx, cy, r, name, owner in self.dots:
                if owner == a["owner"]:
                    continue
                if hit(bx, (cx - r, cy - r, cx + r, cy + r), pad=0):
                    found.append(f'"{a["name"]}" covers {name}')
        if found:
            uniq = list(dict.fromkeys(found))
            more = f" (and {len(uniq) - 4} more)" if len(uniq) > 4 else ""
            self.warn(self.line, f"figure {self.kind}: " + "; ".join(uniq[:4]) + more + f". {hint}")

    def svg(self, height, alt):
        return (f'<div class="dia"><svg viewBox="0 0 {W} {num(height)}" role="img" aria-label="{html.escape(alt, quote=True)}">\n'
                + "\n".join(self.parts) + "\n</svg></div>")


def hit(a, b, pad=1.5):
    return a[0] < b[2] - pad and b[0] < a[2] - pad and a[1] < b[3] - pad and b[1] < a[3] - pad


def seg_hits(box, sg):
    x1, y1, x2, y2 = sg[:4]
    steps = max(2, int(math.hypot(x2 - x1, y2 - y1) / 3))
    return any(hit(box, (x1 + (x2 - x1) * t / steps, y1 + (y2 - y1) * t / steps) * 2, pad=0) for t in range(steps + 1))


def parse_body(kind, body, ln, strict=True):
    keys = KEYS[kind] | COMMON
    params, items, free = {}, [], []
    for k, raw in enumerate(body):
        line = ln + k
        if not raw.strip():
            continue
        m = re.match(r"^(\s*)-(?:\s+(.*))?$", raw.rstrip())
        if m:
            items.append((len(m.group(1).expandtabs(4)), (m.group(2) or "").strip(), line))
            continue
        m = re.match(r"^([A-Za-z][\w-]*)\s*:\s*(.*)$", raw.strip())
        if m and m.group(1).lower() in keys:
            params[m.group(1).lower()] = (m.group(2).strip(), line)
        elif m and strict:
            raise Fig(line, f"figure {kind}: unknown key '{m.group(1)}'; known: {', '.join(sorted(keys))}")
        else:
            free.append((raw.strip(), line))
    if free and strict:
        raise Fig(free[0][1], f"figure {kind}: lines look like 'key: value' or '- item', not '{free[0][0][:40]}'")
    return params, items, free


def figure(kind, body, ln, warn, inline, plain):
    """The ::: figure <kind> block -> <figure> HTML. inline renders caption Markdown; plain makes SVG label text."""
    kind = (kind or "").strip().lower()
    if kind not in KEYS:
        raise Fig(ln - 1, f"'::: figure' needs a template name: {', '.join(sorted(KEYS))} "
                          "(or use '::: html' for a hand-drawn SVG)")
    params, items, free = parse_body(kind, body, ln, strict=kind != "tree")
    if "caption" not in params:
        raise Fig(ln - 1, f"figure {kind}: add a 'caption:' line that says what to notice, with the slide page")
    cap, _ = params["caption"]
    c = Canvas(kind, ln - 1, warn)
    p = params
    if kind == "grid":
        height = grid(c, p, items, plain)
    elif kind == "tree":
        height = tree(c, p, items, free, plain)
    elif kind == "bars":
        height = bars(c, p, items, plain)
    else:
        height = plot(c, p, items, plain)
    alt = params["alt"][0] if "alt" in params else re.sub(r"<[^>]+>", "", inline(cap))
    return f"<figure>\n{c.svg(height, html.unescape(alt))}\n<figcaption>{inline(cap)}</figcaption>\n</figure>"


def int_param(p, key, lo, hi, default=None):
    if key not in p:
        if default is None:
            raise Fig(None, f"needs '{key}:'")
        return default
    v, line = p[key]
    if not re.fullmatch(r"\d+", v) or not lo <= int(v) <= hi:
        raise Fig(line, f"'{key}' should be a whole number from {lo} to {hi}, not '{v}'")
    return int(v)


# ---------- grid ----------

def cells(p, key, rows, cols):
    if key not in p:
        return set()
    spec, line = p[key]
    if re.fullmatch(r"\s*\(?\s*\d+\s*,\s*\d+\s*\)?(?:\s*[;\s]\s*\(?\s*\d+\s*,\s*\d+\s*\)?)*\s*", spec):
        out = {(int(a), int(b)) for a, b in re.findall(r"(\d+)\s*,\s*(\d+)", spec)}
        bad = [rc for rc in out if not (1 <= rc[0] <= rows and 1 <= rc[1] <= cols)]
        if bad:
            raise Fig(line, f"'{key}' names cell {bad[0]} outside the {rows} x {cols} grid (rows and columns start at 1)")
        return out
    f = expr(spec, ("r", "c"), line, f"'{key}' rule")
    return {(r, cc) for r in range(1, rows + 1) for cc in range(1, cols + 1) if f(r=r, c=cc)}


def grid(c, p, items, plain):
    try:
        rows, cols = int_param(p, "rows", 1, 24), int_param(p, "cols", 1, 24)
    except Fig as e:
        raise Fig(e.args[0] or c.line, f"figure grid {e.args[1]}")
    heads = {}
    for key, n in (("col-heads", cols), ("row-heads", rows)):
        if key in p:
            hs = labels(*p[key], key)
            if len(hs) != n:
                raise Fig(p[key][1], f"'{key}' has {len(hs)} entries but the grid has {n}")
            heads[key] = hs
    notes = []
    for _, text, line in items:
        m = re.match(r"^(ttl|acc|warn|small)\s*:\s*(.*)$", text)
        notes.append((NOTE_STYLES[m.group(1)], plain(m.group(2)), line) if m else ("", plain(text), line))
    left, top = plain(p.get("left", ("", 0))[0]), plain(p.get("top", ("", 0))[0])
    x0 = 12 + (tw(left, 12.5) + 10 if left else 0)
    if "row-heads" in heads:
        x0 += max(tw(h, 13, "mono") for h in heads["row-heads"]) + 12
    y0 = 12 + (20 if top else 0) + (22 if "col-heads" in heads else 0)
    notes_w = max((tw(t, SIZES[s], s) for s, t, _ in notes if t), default=0)
    room = W - 12 - x0 - (notes_w + 28 if notes else 0)
    cell = int_param(p, "cell", 12, 80, default=max(18, min(34 if notes else 40, int(room / cols))))
    gw, gh = cols * cell, rows * cell
    if top:
        c.text(x0 + gw / 2, 12 + 13, top, "small", "middle")
    if left:
        c.text(12, y0 + gh / 2 + 4, left, "small")
    for k, h in enumerate(heads.get("col-heads", [])):
        c.text(x0 + (k + 0.5) * cell, y0 - 8, h, "mono", "middle")
    for k, h in enumerate(heads.get("row-heads", [])):
        c.text(x0 - 8, y0 + (k + 0.5) * cell + 4.5, h, "mono", "end")
    marks = [("wn", cells(p, "wn", rows, cols)), ("hl", cells(p, "hl", rows, cols)), ("z", cells(p, "z", rows, cols))]
    texts = expr(p["text"][0], ("r", "c"), p["text"][1], "'text' rule") if "text" in p else None
    rects, labels_ = [], []
    for r in range(1, rows + 1):
        for cc in range(1, cols + 1):
            cls = next((name for name, s in marks if (r, cc) in s), "")
            x, y = x0 + (cc - 1) * cell, y0 + (r - 1) * cell
            rects.append(f'<rect class="cell{" " + cls if cls else ""}" x="{num(x)}" y="{num(y)}" width="{cell}" height="{cell}"/>')
            if texts:
                v = texts(r=r, c=cc)
                if v is not None and v is not False:
                    s = num(float(v)) if not isinstance(v, bool) else ""
                    labels_.append((x + cell / 2, y + cell / 2 + 4.5, s))
    c.add("<g>" + "".join(rects) + "</g>")
    for x, y, s in labels_:
        if tw(s, 13, "mono") > cell - 4:
            c.warn(c.line, f"figure grid: cell text '{s}' is wider than the {cell}px cells; set a larger 'cell:'")
            break
        c.text(x, y, s, "mono", "middle", obstacle=True)
    y = y0 + 16
    nx = x0 + gw + 28
    for style, text, line in notes:
        if not text:
            y += 12
            continue
        c.text(nx, y, text, style, name=text)
        y += 19 if style == "small" else 24
    height = max(y0 + gh, y - 10) + 14
    c.check(height, "Shorten the notes, split one into two, or set a smaller 'cell:'.")
    return height


# ---------- tree ----------

NODE = re.compile(r"^(?:\[(?P<edge>[^\]]*)\]\s*)?(?P<text>.*?)(?:\s*\{(?P<cls>hl|wn|ghost)\})?$")


def tree(c, p, items, free, plain):
    root_text = p["root"][0] if "root" in p else (free[0][0] if free else None)
    if not root_text:
        raise Fig(c.line + 1, "figure tree: start with the root on its own line (or 'root: ...'), then the "
                              "children as an indented '- ' list")
    if not items:
        raise Fig(c.line + 1, "figure tree: list the children under the root as '- child' lines, indented for "
                              "each level")

    def node(text, line):
        m = NODE.match(text.strip())
        return {"text": plain(m.group("text")), "edge": plain(m.group("edge") or ""), "cls": m.group("cls") or "",
                "kids": [], "line": line}

    root = node(root_text, c.line)
    stack = [(-1, root)]
    for indent, text, line in items:
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if not stack:
            raise Fig(line, "figure tree: this item is indented less than the first level")
        n = node(text, line)
        stack[-1][1]["kids"].append(n)
        stack.append((indent, n))

    def leaves(n):
        n["leaves"] = sum(leaves(k) for k in n["kids"]) or 1
        return n["leaves"]

    total = leaves(root)

    def depth(n):
        return 1 + max((depth(k) for k in n["kids"]), default=0)

    levels = depth(root)
    has_edge = any(True for _ in walk(root) if _["edge"])
    gap = 60 if has_edge else 44
    slot = (W - 20) / total

    def place(n, start, d):
        n["x"] = 10 + (start + n["leaves"] / 2) * slot
        n["y"] = 14 + d * (40 + gap)
        k0 = start
        for k in n["kids"]:
            place(k, k0, d + 1)
            k0 += k["leaves"]

    place(root, 0, 0)
    nodes = list(walk(root))
    for n in nodes:
        cls = "small" if n["cls"] == "ghost" else ""
        n["w"] = max(64, tw(n["text"], SIZES[cls]) + 24)
    for n in nodes:
        for k in n["kids"]:
            c.add(f'<line class="edge" x1="{num(n["x"])}" y1="{num(n["y"] + 40)}" x2="{num(k["x"])}" y2="{num(k["y"])}"/>')
    for n in nodes:
        x, w = n["x"], n["w"]
        cls = f'node {n["cls"]}'.strip()
        c.add(f'<rect class="{cls}" x="{num(x - w / 2)}" y="{num(n["y"])}" width="{num(w)}" height="40" rx="8"/>')
        c.boxes.append({"box": (x - w / 2, n["y"], x + w / 2, n["y"] + 40), "name": n["text"], "owner": id(n), "check": True})
        c.text(x, n["y"] + 25, n["text"], "small" if n["cls"] == "ghost" else "", "middle", owner=id(n), obstacle=True)
        for k in n["kids"]:
            if not k["edge"]:
                continue
            mx, my = (x + k["x"]) / 2, (n["y"] + 40 + k["y"]) / 2 + 4
            side = "end" if k["x"] < x - 1 else "start"
            c.text(mx + (-8 if side == "end" else 8), my, k["edge"], "small halo", side, owner=id(k))
    height = 14 + (levels - 1) * (40 + gap) + 40 + 14
    c.check(height, "Shorten the labels, or split the tree so fewer leaves share the width.")
    return height


def walk(n):
    yield n
    for k in n["kids"]:
        yield from walk(k)


# ---------- bars ----------

def value_fmt(vals, fmt):
    if fmt.startswith("%"):
        d = int(fmt[1:] or 0)
        return lambda v: f"{v * 100:.{d}f}%"
    if fmt:
        return lambda v: f"{v:.{int(fmt)}f}"
    if all(float(v).is_integer() for v in vals):
        return lambda v: str(int(v))
    return lambda v: f"{v:.3g}"


def bars(c, p, items, plain):
    if items:
        raise Fig(items[0][2], "figure bars: use 'key: value' lines only")
    for key in ("x", "y"):
        if key not in p:
            raise Fig(c.line + 1, f"figure bars needs '{key}:' (x: the labels, e.g. 0..10; y: the values or an "
                                  "expression in x)")
    xs = labels(*p["x"], "x")
    yspec, yline = p["y"]
    if re.fullmatch(r"[\s\d.,eE+−-]+", yspec) and ("," in yspec or len(xs) == 1):
        ys = [number(v, yline, "each y value") for v in yspec.split(",")]
    else:
        try:
            xv = [float(x) for x in xs]
        except ValueError:
            raise Fig(yline, "figure bars: y can be an expression only when the x labels are numbers")
        f = expr(yspec, ("x",), yline, "y expression")
        ys = []
        for x in xv:
            v = f(x=int(x) if x.is_integer() else x)
            if v is None or isinstance(v, bool):
                raise Fig(yline, f"figure bars: the y expression has no value at x = {num(x)}")
            ys.append(float(v))
    if len(ys) != len(xs):
        raise Fig(yline, f"figure bars: {len(xs)} x labels but {len(ys)} y values")
    if any(v < 0 for v in ys):
        raise Fig(yline, "figure bars: y values must be 0 or more")
    top_v = max(ys) or 1
    hl = set(labels(*p["hl"], "hl")) if "hl" in p else None
    wn = set(labels(*p["wn"], "wn")) if "wn" in p else set()
    for name, s in (("hl", hl or set()), ("wn", wn)):
        if s - set(xs):
            raise Fig(p[name][1], f"figure bars: '{name}' names {sorted(s - set(xs))[0]!r}, which is not an x label")
    show = p.get("values", ("", 0))[0].lower() in ("yes", "on", "true")
    fmt = value_fmt(ys, p.get("fmt", ("", 0))[0])
    height = int_param(p, "height", 160, 600, default=260)
    left, right, base = 40, W - 20, height - 40
    top = (34 if "title" in p else 16) + (16 if show else 0) + (20 if "mark" in p else 0)
    slot = (right - left) / len(xs)
    bw = min(60, slot * 0.78)
    if "title" in p:
        c.text(left + 10, 24, plain(p["title"][0]), "small")
    c.add(f'<line class="axis" x1="{left}" y1="{base}" x2="{right}" y2="{base}"/>')
    c.seg(left, base, right, base, "the axis", owner="axis")
    for k, (x, v) in enumerate(zip(xs, ys)):
        cx = left + (k + 0.5) * slot
        h = max(1.0, (base - top) * v / top_v) if v > 0 else 0
        cls = "bar w" if x in wn else "bar" if hl is None or x in hl else "bar l"
        if h:
            c.add(f'<rect class="{cls}" x="{num(cx - bw / 2)}" y="{num(base - h)}" width="{num(bw)}" height="{num(h)}"/>')
            c.boxes.append({"box": (cx - bw / 2, base - h, cx + bw / 2, base), "name": f"bar {x}", "owner": f"bar{k}",
                            "check": False})
        c.text(cx, base + 20, x, "mono", "middle")
        if show:
            c.text(cx, base - h - 6, fmt(v), "small", "middle", owner=f"bar{k}")
    if "mark" in p:
        spec, line = p["mark"]
        at, _, text = spec.partition("|")
        at = at.strip()
        if at in xs:
            mx = left + (xs.index(at) + 0.5) * slot
        else:
            try:
                xv = [float(x) for x in xs]
            except ValueError:
                raise Fig(line, f"figure bars: 'mark' should start with one of the x labels, not '{at}'")
            pos = number(at, line, "the mark position")
            step = (xv[-1] - xv[0]) / (len(xv) - 1) if len(xv) > 1 else 1
            mx = left + ((pos - xv[0]) / step + 0.5) * slot
        c.add(f'<line class="edge acc ghost" x1="{num(mx)}" y1="{top - (36 if show else 20)}" x2="{num(mx)}" y2="{base}"/>')
        text = plain(text.strip())
        if text:
            anchor, tx = ("start", mx + 8) if mx + 8 + tw(text, 14) < W - 4 else ("end", mx - 8)
            c.text(tx, top - (24 if show else 8), text, "atxt", anchor, owner="mark")
    c.check(height, "Shorten the labels, use fewer bars, or set a 'height:'.")
    return height


# ---------- plot ----------

def nice_ticks(a, b):
    span = b - a
    raw = span / 5
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw - 1e-12)
    first = math.ceil(a / step - 1e-9) * step
    out, v = [], first
    while v <= b + 1e-9:
        out.append(round(v, 10))
        v += step
    return out


def axis_spec(p, key, line_default):
    if key not in p:
        raise Fig(line_default, f"figure plot needs '{key}: from..to | label', e.g. '{key}: 0..100 | Quantity'")
    spec, line = p[key]
    rng, _, label = spec.partition("|")
    m = re.fullmatch(r"\s*(-?[\d.]+)\s*\.\.\s*(-?[\d.]+)\s*", rng)
    if not m:
        raise Fig(line, f"'{key}' should look like '0..100 | label', not '{spec}'")
    a, b = number(m.group(1), line, key), number(m.group(2), line, key)
    if b <= a:
        raise Fig(line, f"'{key}' range should go up")
    return a, b, label.strip()


def pairs(spec, line, what):
    found = re.findall(r"(-?[\d.]+)\s*,\s*(-?[\d.]+)", spec)
    rest = re.sub(r"\(?\s*-?[\d.]+\s*,\s*-?[\d.]+\s*\)?", "", spec).strip(" ;")
    if not found or rest:
        raise Fig(line, f"{what} should be points like '0,50 60,20', not '{spec.strip()}'")
    return [(number(a, line, what), number(b, line, what)) for a, b in found]


def plot(c, p, items, plain):
    x0, x1, xl = axis_spec(p, "x", c.line + 1)
    y0, y1, yl = axis_spec(p, "y", c.line + 1)

    def ticks(key, a, b):
        if key not in p:
            return nice_ticks(a, b)
        spec, line = p[key]
        if spec.strip().lower() == "none":
            return []
        return [number(v, line, key) for v in re.split(r"[,\s]+", spec.strip()) if v]

    xt, yt = ticks("xticks", x0, x1), ticks("yticks", y0, y1)
    height = int_param(p, "height", 180, 640, default=300)
    left = 16 + max((tw(num(v), 13, "mono") for v in yt), default=0) + 8
    right, top, bottom = W - 20, 30, height - 44

    def px(x):
        return left + (x - x0) / (x1 - x0) * (right - left)

    def py(y):
        return bottom - (y - y0) / (y1 - y0) * (bottom - top)

    parsed = []
    for _, text, line in items:
        m = re.match(r"^([a-z]+)((?:\s+[a-z]+)*)\s*:\s*(.*)$", text)
        if not m or m.group(1) not in ("curve", "point", "hline", "vline", "area", "arrow", "text"):
            raise Fig(line, "figure plot: items look like '- curve: 50 - x/2 | Demand', '- point: 60, 20 | label', "
                            "'- hline: 25 | label', '- vline', '- area', '- arrow' or '- text'")
        data, _, label = m.group(3).partition("|")
        label = label.strip()
        at = None
        am = re.search(r"\s@(\S+)$", " " + label)
        if am:
            at, label = am.group(1), label[:len(label) - len(am.group(0)) + 1].strip()
        parsed.append({"kind": m.group(1), "style": set(m.group(2).split()), "data": data.strip(),
                       "label": plain(label), "at": at, "line": line})
    if "grid" in p and p["grid"][0].lower() in ("yes", "on", "true"):
        for v in xt:
            c.add(f'<line class="grid" x1="{num(px(v))}" y1="{top}" x2="{num(px(v))}" y2="{bottom}"/>')
        for v in yt:
            c.add(f'<line class="grid" x1="{left}" y1="{num(py(v))}" x2="{right}" y2="{num(py(v))}"/>')
    labels_ = []  # drawn last, on top
    for k, it in enumerate(parsed):
        if it["kind"] != "area":
            continue
        pts = pairs(it["data"], it["line"], "an area")
        cls = "band w" if "w" in it["style"] else "band"
        c.add(f'<polygon class="{cls}" points="{" ".join(num(px(a)) + "," + num(py(b)) for a, b in pts)}"/>')
        if it["label"]:
            if it["at"]:
                ax, ay = pairs(it["at"], it["line"], "an @ position")[0]
            else:
                ax, ay = sum(a for a, _ in pts) / len(pts), sum(b for _, b in pts) / len(pts)
            cx, cy = px(ax), py(ay) + 4
            spots = [(cx, cy, "middle")] if it["at"] else [(cx + dx, cy + dy, "middle") for dx, dy in
                                                            ((0, 0), (0, -14), (0, 14), (-30, 0), (30, 0), (-30, -14), (30, 14))]
            labels_.append((spots, it["label"], "small", k))
    c.add(f'<line class="axis" x1="{num(left)}" y1="{num(bottom)}" x2="{num(right)}" y2="{num(bottom)}"/>')
    c.add(f'<line class="axis" x1="{num(left)}" y1="{num(bottom)}" x2="{num(left)}" y2="{num(top - 6)}"/>')
    c.seg(left, bottom, right, bottom, "the x axis", owner="axis")
    c.seg(left, bottom, left, top - 6, "the y axis", owner="axis")
    for v in xt:
        c.add(f'<line class="axis" x1="{num(px(v))}" y1="{num(bottom)}" x2="{num(px(v))}" y2="{num(bottom + 5)}"/>')
        c.text(px(v), bottom + 19, num(v), "mono", "middle")
    for v in yt:
        c.add(f'<line class="axis" x1="{num(left - 5)}" y1="{num(py(v))}" x2="{num(left)}" y2="{num(py(v))}"/>')
        c.text(left - 8, py(v) + 4.5, num(v), "mono", "end")
    if xl:
        c.text(right, bottom + 37, plain(xl), "small", "end")
    if yl:
        c.text(left + 8, top - 10, plain(yl), "small")
    tone = {"a": "atxt", "w": "wtxt", "m": "small"}
    for k, it in enumerate(parsed):
        kind, st, line = it["kind"], it["style"], it["line"]
        name = f'the {kind} "{it["label"]}"' if it["label"] else f"a {kind}"
        if kind in ("hline", "vline"):
            v = number(it["data"], line, f"the {kind} position")
            cls = "edge ghost" + (" wn" if "w" in st else " acc" if "a" in st else "")
            if kind == "hline":
                c.add(f'<line class="{cls}" x1="{num(left)}" y1="{num(py(v))}" x2="{num(right)}" y2="{num(py(v))}"/>')
                c.seg(left, py(v), right, py(v), name, owner=k)
                if it["label"]:
                    if it["at"]:
                        spots = [(px(number(it["at"], line, "@x")) + 4, py(v) - 7, "start")]
                    else:
                        spots = [(right - 4, py(v) - 7, "end"), (right - 4, py(v) + 17, "end"),
                                 (left + 6, py(v) - 7, "start"), (left + 6, py(v) + 17, "start")]
                    labels_.append((spots, it["label"], txt_cls(st), k))
            else:
                c.add(f'<line class="{cls}" x1="{num(px(v))}" y1="{num(bottom)}" x2="{num(px(v))}" y2="{num(top)}"/>')
                c.seg(px(v), bottom, px(v), top, name, owner=k)
                if it["label"]:
                    if it["at"]:
                        spots = [(px(v) + 6, py(number(it["at"], line, "@y")), "start")]
                    else:
                        spots = [(px(v) + 6, top + 12, "start"), (px(v) - 6, top + 12, "end"),
                                 (px(v) + 6, (top + bottom) / 2, "start"), (px(v) - 6, (top + bottom) / 2, "end")]
                    labels_.append((spots, it["label"], txt_cls(st), k))
        elif kind == "curve":
            data = it["data"]
            if re.fullmatch(r"[\s\d.,;()−-]+", data) and "," in data:
                pts = [(px(a), py(b)) for a, b in pairs(data, line, "a curve")]
                runs = [pts]
            else:
                f = expr(data, ("x",), line, "curve")
                runs, cur = [], []
                n = 240
                prev = None
                for s in range(n + 1):
                    x = x0 + (x1 - x0) * s / n
                    y = f(x=x)
                    ok = y is not None and not isinstance(y, bool) and math.isfinite(y)
                    inside = ok and y0 - 1e-9 <= y <= y1 + 1e-9
                    if inside:
                        if not cur and prev is not None and prev[1] is not None:  # entering: add the crossing
                            cur.append(cross(prev, (x, y), y0, y1))
                        cur.append((x, y))
                    elif cur:
                        if ok:
                            cur.append(cross(cur[-1], (x, y), y0, y1))
                        runs.append(cur)
                        cur = []
                    prev = (x, y if ok else None)
                if cur:
                    runs.append(cur)
                runs = [[(px(a), py(b)) for a, b in r] for r in runs if len(r) > 1]
                if not runs:
                    raise Fig(line, f"figure plot: the curve '{data}' never enters the y range {num(y0)}..{num(y1)}")
            cls = "curve " + ("w" if "w" in st else "m" if "m" in st else "a")
            for r in runs:
                c.add(f'<path class="{cls}" d="M{" L".join(num(a) + "," + num(b) for a, b in r)}"/>')
                for (ax, ay), (bx, by) in zip(r, r[1:]):
                    c.seg(ax, ay, bx, by, name, owner=k)
            if it["label"]:
                cand = [pt for r in runs for pt in r]
                if it["at"]:
                    xa = px(number(it["at"], line, "@x"))
                    anchors = [min(cand, key=lambda q: abs(q[0] - xa))]
                else:  # the end of the curve first, then points back along it
                    anchors = [runs[-1][-1]] + [cand[int(len(cand) * f)] for f in (0.85, 0.7, 0.55, 0.4, 0.25, 0.1)]
                spots = []
                for lx, ly in anchors:
                    spots += [(lx + 8, ly - 8, "start"), (lx - 8, ly - 10, "end"), (lx + 8, ly + 18, "start"),
                              (lx - 8, ly + 18, "end")]
                cls_t = tone["w" if "w" in st else "m" if "m" in st else "a"]
                labels_.append((spots, it["label"], cls_t, k))
        elif kind == "point":
            a, b = pairs(it["data"], line, "a point")[0]
            x, y = px(a), py(b)
            if "guide" in st:
                c.add(f'<line class="edge ghost thin" x1="{num(x)}" y1="{num(y)}" x2="{num(x)}" y2="{num(bottom)}"/>')
                c.add(f'<line class="edge ghost thin" x1="{num(left)}" y1="{num(y)}" x2="{num(x)}" y2="{num(y)}"/>')
            cls = "dot w" if "w" in st else "dot o" if "o" in st else "dot"
            c.add(f'<circle class="{cls}" cx="{num(x)}" cy="{num(y)}" r="5"/>')
            c.dots.append((x, y, 5, name, k))
            if it["label"]:
                dirs = {"ne": (8, -9, "start"), "nw": (-8, -9, "end"), "se": (8, 19, "start"), "sw": (-8, 19, "end"),
                        "e": (10, 4.5, "start"), "w": (-10, 4.5, "end"), "n": (0, -11, "middle"), "s": (0, 22, "middle")}
                order = [it["at"].lower()] if it["at"] else list(dirs)
                if order[0] not in dirs:
                    raise Fig(line, f"figure plot: a point label goes @ne, @nw, @se, @sw, @n, @s, @e or @w, not @{order[0]}")
                spots = [(x + dirs[d][0], y + dirs[d][1], dirs[d][2]) for d in order]
                labels_.append((spots, it["label"], txt_cls(st, ""), k))
        elif kind == "arrow":
            pts = pairs(it["data"], line, "an arrow")
            if len(pts) != 2:
                raise Fig(line, "figure plot: an arrow is two points, from and to: '30,35 45,35'")
            (a1, b1), (a2, b2) = [(px(a), py(b)) for a, b in pts]
            c.add(f'<line class="arrow{" wn" if "w" in st else ""}" x1="{num(a1)}" y1="{num(b1)}" x2="{num(a2)}" y2="{num(b2)}"/>')
            c.seg(a1, b1, a2, b2, name, owner=k)
            if it["label"]:
                mx = (a1 + a2) / 2
                spots = [(mx, min(b1, b2) - 8, "middle"), (mx, max(b1, b2) + 18, "middle")]
                labels_.append((spots, it["label"], txt_cls(st, "atxt"), k))
        elif kind == "text":
            a, b = pairs(it["data"], line, "a text position")[0]
            cls = {"small": "small", "acc": "atxt", "warn": "wtxt", "ttl": "ttl"}
            style = next((cls[s] for s in st if s in cls), "")
            labels_.append(([(px(a), py(b), "middle" if "center" in st else "start")], it["label"], style, k))
    for spots, s, cls, owner in labels_:
        c.place(spots, s, (cls + " halo").strip(), owner, height)
    c.check(height, "Move a label with @x for a curve or line, @ne/@sw/... for a point, or new x, y for a text.")
    return height


def txt_cls(st, default="small"):
    return "wtxt" if "w" in st else "atxt" if "a" in st else default


def cross(a, b, y0, y1):
    """Where the segment a-b crosses y = y0 or y = y1 (whichever lies between them)."""
    (xa, ya), (xb, yb) = a, b
    for edge in (y0, y1):
        if (ya - edge) * (yb - edge) <= 0 and ya != yb:
            t = (edge - ya) / (yb - ya)
            return (xa + (xb - xa) * t, edge)
    return b
