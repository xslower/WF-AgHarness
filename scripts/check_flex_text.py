#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend" / "src"
STYLE_CSS = ROOT / "frontend" / "src" / "styles.css"

pass
FLEX_TEXT_HOSTS = {"projhome-row-meta", "plugincard-actions"}

_CLASS_RE = re.compile(r'className\s*=\s*(?:"([^"]*)"|\{`([^`]*)`\}|\{"([^"]*)"\})')
_TAG_RE = re.compile(r"<([A-Za-z][\w.]*)")


def _classes_of(attrs: str) -> set[str]:
    out: set[str] = set()
    for m in _CLASS_RE.finditer(attrs):
        out.update((m.group(1) or m.group(2) or m.group(3) or "").split())
    return out


def _skip_open_tag(text: str, i: int) -> int:
    curly, quote = 0, ""
    i += 1
    while i < len(text):
        ch = text[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = ""
        elif ch in "\"'`":
            quote = ch
        elif ch == "{":
            curly += 1
        elif ch == "}":
            curly = max(0, curly - 1)
        elif ch == ">" and curly == 0:
            return i + 1
        i += 1
    return len(text)


def _skip_brace(text: str, i: int) -> int:
    depth, quote = 1, ""
    i += 1
    while i < len(text):
        ch = text[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = ""
        elif ch in "\"'`":
            quote = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return len(text)


def _skip_element(text: str, i: int) -> int:
    m = _TAG_RE.match(text, i)
    if not m:
        return i + 1
    tag = m.group(1)
    after_open = _skip_open_tag(text, i)
    if text[i:after_open].rstrip().endswith("/>"):
        return after_open
    depth, j = 1, after_open
    while j < len(text):
        if text.startswith(f"</{tag}>", j):
            depth -= 1
            j += len(tag) + 3
            if depth == 0:
                return j
            continue
        ch = text[j]
        if ch == "<":
            nm = _TAG_RE.match(text, j)
            if not nm:
                j += 1
                continue
            end = _skip_open_tag(text, j)
            if nm.group(1) == tag and not text[j:end].rstrip().endswith("/>"):
                depth += 1
            j = end
            continue
        if ch == "{":
            nxt = _skip_brace(text, j)
            j = nxt if nxt > j else j + 1
            continue
        j += 1
    return len(text)


def _bad_children(body: str) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(body):
        ch = body[i]
        if ch == "<":
            nxt = _skip_element(body, i)
            i = nxt if nxt > i else i + 1
            continue
        if ch == "{":
            end = _skip_brace(body, i)
            expr = body[i + 1:end - 1]
            pass
            if expr.strip().startswith("/*"):
                i = end if end > i else i + 1
                continue
            if "<" not in expr and expr.strip():
                out.append("{" + " ".join(expr.split())[:50] + "}")
            i = end if end > i else i + 1
            continue
        j = i
        while j < len(body) and body[j] not in "<{":
            j += 1
        if body[i:j].strip():
            out.append(" ".join(body[i:j].split())[:50])
        i = j
    return out


def _scan_file(path: Path) -> list[tuple[int, str]]:
    raw = path.read_text("utf-8")
    bad: list[tuple[int, str]] = []
    for m in _TAG_RE.finditer(raw):
        start = m.start()
        after_open = _skip_open_tag(raw, start)
        if raw[start:after_open].rstrip().endswith("/>"):
            continue
        hosts = _classes_of(raw[start:after_open]) & FLEX_TEXT_HOSTS
        if not hosts:
            continue
        elem_end = _skip_element(raw, start)
        body = raw[after_open:elem_end - len(m.group(1)) - 3]
        for frag in _bad_children(body):
            line_no = raw.count("\n", 0, start) + 1
            bad.append((line_no, f"{'/'.join(sorted(hosts))} 内直接渲染文本：{frag}"))
    return bad


def _rule_of(css: str, selector: str) -> str:
    i = css.find(f"{selector} {{")
    if i < 0:
        return ""
    return css[i:css.find("}", i)]


def _check_css() -> list[str]:
    if not STYLE_CSS.is_file():
        return []
    css = STYLE_CSS.read_text("utf-8")
    meta = _rule_of(css, ".projhome-row-meta")
    text = _rule_of(css, ".projhome-row-text")
    want = [
        ("`.projhome-row-meta` 允许收缩", meta, r"flex:\s*0\s+1\s+auto"),
        ("`.projhome-row-meta` min-width:0", meta, r"min-width:\s*0"),
        ("`.projhome-row-meta` overflow:hidden", meta, r"overflow:\s*hidden"),
        ("`.projhome-row-text` min-width:0", text, r"min-width:\s*0"),
        ("`.projhome-row-text` nowrap", text, r"white-space:\s*nowrap"),
        ("`.projhome-row-text` ellipsis", text, r"text-overflow:\s*ellipsis"),
        ("`.projhome-row-text` overflow:hidden", text, r"overflow:\s*hidden"),
    ]
    bad = [f"styles.css 缺少 {name}（规则被删/被改会让文本重新撑开行宽）"
           for name, rule, pat in want if not re.search(pat, rule)]
    if not re.search(r"\.projhome-row-meta button[^{]*\{[^}]*flex:\s*0\s+0\s+auto", css):
        bad.append("styles.css 缺少 `.projhome-row-meta button { flex:0 0 auto }`"
                   "（按钮会被一起压缩/顶出）")
    return bad


def _rel(p: Path) -> Path:
    try:
        return p.relative_to(ROOT)
    except ValueError:
        return p


def main(argv: list[str] | None = None) -> int:
    global FRONTEND
    argv = sys.argv[1:] if argv is None else argv
    for a in argv:
        if a.startswith("--root="):
            FRONTEND = Path(a.split("=", 1)[1])
    if not FRONTEND.is_dir():
        print(f"跳过：{FRONTEND} 不存在")
        return 0

    fails: list[tuple[str, int, str]] = []
    for p in sorted(FRONTEND.rglob("*.tsx")):
        for line_no, msg in _scan_file(p):
            fails.append((str(_rel(p)), line_no, msg))
    css_bad = _check_css()

    if not fails and not css_bad:
        print("布局检查通过（弹性行内无裸文本 + CSS 截断契约完整，"
              "操作按钮不会被长描述挤飞）")
        return 0

    if fails:
        print(f"布局检查失败：{len(fails)} 处弹性行容器内直接渲染了文本")
        for rel, line, msg in fails:
            print(f" - {rel}:{line}  {msg}")
        print("   解法：包一层 <span className=\"projhome-row-text\">…</span>\n")
    for msg in css_bad:
        print(f" - {msg}")
    print("\n为什么：Flex + nowrap 下裸文本节点无法被 CSS 截断，"
          "描述多长行就多宽，右侧按钮被顶出容器（2026-11-11 安装按钮消失事故）。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
