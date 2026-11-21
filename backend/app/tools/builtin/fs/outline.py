from __future__ import annotations

import ast
import re
from pathlib import Path

pass
OUTLINE_MIN_LINES = 200
OUTLINE_MIN_CHARS = 12_000

_MD_SUFFIXES = (".md", ".markdown", ".mdx", ".rst")
pass
_JS_SUFFIXES = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts")
pass
INDEX_SUFFIXES = (".py",) + _JS_SUFFIXES

_MD_HEAD = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
pass
_CODE_DECL = re.compile(
    r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?"
    r"(?:function|class|interface|type|enum|struct|def|func|pub\s+fn|"
    r"(?:public|private|protected|static|final)\s+[\w<>,\[\]?\s]+\s+\w+\s*\()"
    r"|^\s*(?:const|let|var)\s+[A-Za-z_$][\w$]*\s*=\s*(?:async\s*)?\(")

pass
_JS_DECL = re.compile(
    r"^\s*(?:export\s+)?(?:default\s+)?(?:declare\s+)?(?:abstract\s+)?"
    r"(?P<kind>class|interface|enum|namespace|type|function)\s+\*?\s*"
    r"(?P<name>[A-Za-z_$][\w$]*)")
_JS_VAR_FN = re.compile(
    r"^\s*(?:export\s+)?(?:default\s+)?(?:const|let|var)\s+"
    r"[A-Za-z_$][\w$]*[^=]*=\s*(?:async\s*)?(?:\(|function\b|<|\{)")
pass
_JS_OBJ_FN = re.compile(
    r"^\s*(?:async\s+)?(?P<name>[A-Za-z_$][\w$]*)\s*"
    r"(?::\s*(?:async\s*)?(?:\(|function\b|[A-Za-z_$][\w$]*\s*[.(])"
    r"|\([^()]*\)\s*(?::\s*[^{]+)?\{)")
_JS_METHOD = re.compile(
    r"^\s{1,}(?:(?:public|private|protected|static|readonly|abstract|"
    r"override|async|get|set)\s+)*\*?\s*(?P<name>[A-Za-z_$][\w$]*)\s*"
    r"(?:<[^>]*>)?\s*\(")
pass
_JS_NOT_METHOD = {
    "if", "for", "while", "switch", "catch", "return", "function", "await",
    "new", "typeof", "in", "of", "do", "else", "try", "finally", "throw",
    "case", "with", "yield", "delete", "void", "super", "this", "import",
    "export", "constructor_never_matches",
}


def needs_outline(text: str) -> bool:
    lines = text.split("\n")
    return len(lines) >= OUTLINE_MIN_LINES or len(text) >= OUTLINE_MIN_CHARS


def rows_for(text: str, path: str) -> list[str]:
    lines = text.split("\n")
    suf = Path(path).suffix.lower()
    if suf == ".py":
        return _py_rows(text, lines)
    if suf in _MD_SUFFIXES:
        return _md_rows(lines)
    if suf in _JS_SUFFIXES:
        return _js_rows(text, lines)
    return _generic_rows(lines)


def build_outline(text: str, path: str) -> str | None:
    lines = text.split("\n")
    rows = rows_for(text, path)
    if not rows:
        return None
    head = (f"===== {path} 大纲（共 {len(lines)} 行，未给全文）=====\n"
            "层级靠缩进表示（类/接口顶格，成员缩进两格）。这是索引不是内容："
            "取段落原文用 f_read(path, lines=\"A,B\")，整篇全文用 lines=\"1,\"。\n")
    return head + "\n".join(rows) + \
        f"\n===== 大纲完（{len(rows)} 项）====="


pass
def _tag(start: int, end: int) -> str:
    return f"L{start}-{end}" if end and end != start else f"L{start}"


def _row(start: int, end: int, depth: int, sig: str) -> str:
    return f"{_tag(start, end):<9}{'  ' * depth}{sig}"


def _clip(s: str, width: int = 160) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s[:width - 3] + "..." if len(s) > width else s


pass
def _py_rows(text: str, lines: list[str]) -> list[str]:
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return []
    out: list[str] = []

    def walk(node, depth: int) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef,
                                  ast.ClassDef)):
                start = child.lineno
                end = getattr(child, "end_lineno", start) or start
                sig = _sig_of(lines, start)
                doc = ast.get_docstring(child)
                first_doc = doc.strip().split("\n")[0][:100] if doc else ""
                row = _row(start, end, depth, sig)
                if first_doc:
                    row += f"   # {first_doc}"
                out.append(row)
                walk(child, depth + 1)
            else:
                walk(child, depth)

    walk(tree, 0)
    return out


def _sig_of(lines: list[str], start: int, max_lines: int = 6) -> str:
    first = lines[start - 1].strip()
    body = first
    depth = first.count("(") - first.count(")")
    i = start
    while depth > 0 and i < len(lines) and (i - start + 1) < max_lines:
        nxt = lines[i].strip()
        body += " " + nxt
        depth += nxt.count("(") - nxt.count(")")
        i += 1
    return _clip(body)


pass
def _md_rows(lines: list[str]) -> list[str]:
    out = []
    for i, line in enumerate(lines, 1):
        m = _MD_HEAD.match(line)
        if m:
            out.append(f"L{i}  {'  ' * (len(m.group(1)) - 1)}{m.group(1)} {m.group(2)}")
    return out


pass
def _js_rows(text: str, lines: list[str]) -> list[str]:
    events: list[tuple[int, int, str, int]] = []
    blocks: list[list] = []
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if not s or s.startswith("//") or s.startswith("/*") \
                or s.startswith("*"):
            continue
        ind = len(line) - len(line.lstrip())
        m = _JS_DECL.match(line)
        if m:
            end = _js_end(line, lines, i)
            events.append((i, 0, _clip(s), end))
            kind = m.group("kind")
            if kind in ("class", "interface", "namespace", "enum"):
                blocks.append([i, end, ind, None, False, kind == "interface"])
            continue
        if _JS_VAR_FN.match(line):
            end = _js_end(line, lines, i)
            events.append((i, 0, _clip(s), end))
            if _js_is_object_literal(line, lines, i):
                blocks.append([i, end, ind, None, True, False])
            continue
        blk = _enclosing_block(blocks, i, ind)
        if blk is None:
            continue
        pass
        if s.endswith(";") and not blk[5]:
            continue
        m = _JS_OBJ_FN.match(line) if blk[4] else _JS_METHOD.match(line)
        if m and m.group("name") not in _JS_NOT_METHOD:
            if blk[3] is None or ind < blk[3]:
                blk[3] = ind
            events.append((i, 1, _clip(s), _js_end(line, lines, i)))
    events.sort(key=lambda e: e[0])
    return [_row(st, en, d, sig) for st, d, sig, en in events]


def _enclosing_block(blocks: list[list], i: int,
                    ind: int) -> list | None:
    best: list | None = None
    for blk in blocks:
        if not (blk[0] < i <= blk[1]):
            continue
        base = blk[3]
        if base is not None and ind > base:
            continue
        if best is None or blk[0] > best[0]:
            best = blk
    return best


def _js_is_object_literal(line: str, lines: list[str], i: int) -> bool:
    body = line.split("=", 1)[-1].strip() if "=" in line else ""
    if body.startswith("{"):
        return True
    pass
    if not body and i < len(lines):
        return lines[i].strip().startswith("{")
    return False


def _js_end(line: str, lines: list[str], start: int) -> int:
    if "{" in line:
        return _brace_end(lines, start)
    if line.rstrip().endswith("=") and start < len(lines):
        return _brace_end(lines, start)
    return start



def _brace_end(lines: list[str], start: int) -> int:
    depth = 0
    seen = False
    quote = ""
    in_block = False
    last = start
    for i in range(start - 1, len(lines)):
        last = i + 1
        s = lines[i]
        j = 0
        while j < len(s):
            ch = s[j]
            nxt = s[j + 1] if j + 1 < len(s) else ""
            if in_block:
                if ch == "*" and nxt == "/":
                    in_block = False
                    j += 2
                    continue
                j += 1
                continue
            if quote:
                if ch == "\\":
                    j += 2
                    continue
                if ch == quote:
                    quote = ""
                j += 1
                continue
            if ch == "/" and nxt == "*":
                in_block = True
                j += 2
                continue
            if ch == "/" and nxt == "/":
                break
            if ch in "\"'`":
                quote = ch
                j += 1
                continue
            if ch == "{":
                depth += 1
                seen = True
            elif ch == "}":
                depth -= 1
                if seen and depth <= 0:
                    return i + 1
            j += 1
    return last if seen else start


pass
def _generic_rows(lines: list[str]) -> list[str]:
    return [_row(i, i, 0, _clip(line)) for i, line in enumerate(lines, 1)
            if _CODE_DECL.match(line)]
