from __future__ import annotations

import json
import logging
import re
from typing import Any

from .llm_out import FENCE_RE

logger = logging.getLogger("harness.jsonfix")

__all__ = ["stats", "reset_stats", "json_error_detail", "strip_fences",
           "close_open_structs"]

pass
pass
pass

_STATS: dict[str, int] = {}

def _bump(key: str, n: int = 1) -> None:
    _STATS[key] = _STATS.get(key, 0) + n

def stats() -> dict[str, int]:
    return dict(_STATS)

def reset_stats() -> None:
    _STATS.clear()

pass
pass
pass


def json_error_detail(e: Exception, raw: str, window: int = 60) -> str:
    reason = getattr(e, "msg", None) or str(e)
    pos = getattr(e, "pos", None) or 0
    line, col = getattr(e, "lineno", None), getattr(e, "colno", None)
    where = f"第 {line} 行第 {col} 列" if line and col else "位置未知"
    text = raw or ""
    total = len(text)
    lo, hi = max(0, pos - window), min(total, pos + window)
    snippet = repr(text[lo:hi])
    left = "…" if lo else ""
    right = "…" if hi < total else ""
    return (f"{reason}（{where}，字符 {pos}/{total}）；"
            f"出错处附近：{left}{snippet}{right}；"
            "常见原因：字符串里的引号/换行没转义、漏了逗号或括号、"
            "参数被输出长度截断。请只修正这一处，再重新调用该工具，别改动其它调用。")

pass
pass
pass

_JSON_ESCAPES = frozenset('"\\/bfnrtu')

_CTRL = {"\n": "\\n", "\r": "\\r", "\t": "\\t"}

pass
pass
pass
_FENCE = FENCE_RE

def _balanced(text: str) -> bool:
    stack: list[str] = []
    in_str = esc = False
    for c in text:
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c in "{[(":
            stack.append(c)
        elif c in "}])":
            if not stack:
                return False
            stack.pop()
    return not stack and not in_str

def strip_fences(text: str) -> tuple[str, str]:
    s = (text or "").strip()
    m = _FENCE.search(s)
    if m:
        inner = m.group(2).strip()
        if inner:
            return inner, "剥掉代码围栏"
    pass
    lo = -1
    for ch in "{[":
        p = s.find(ch)
        if p != -1 and (lo == -1 or p < lo):
            lo = p
    hi = max(s.rfind("}"), s.rfind("]"))
    if lo > 0 or (hi != -1 and hi < len(s) - 1):
        if 0 <= lo < hi:
            pass
            pass
            pass
            pass
            pass
            prefix = s[s.rfind("\n", 0, lo) + 1:lo]
            head = prefix.split(":", 1)[0]
            if ":" in prefix and _YAML_KEY_RE.fullmatch(head.rstrip()):
                return s, ""
            cand = s[lo:hi + 1]
            if _balanced(cand):
                return cand, "剥掉前后多余说明文字"
    return s, ""

def _is_closing_quote(text: str, i: int) -> bool:
    j = i + 1
    while j < len(text) and text[j].isspace():
        j += 1
    return j >= len(text) or text[j] in ':,}]'

def _fix_string_literals(text: str) -> tuple[str, bool]:
    out: list[str] = []
    in_str = escaped = changed = False
    for i, c in enumerate(text):
        if not in_str:
            out.append(c)
            if c == '"':
                in_str = True
        elif escaped:
            out.append(c)
            escaped = False
        elif c == "\\":
            nxt = text[i + 1] if i + 1 < len(text) else ""
            if nxt in _JSON_ESCAPES:
                out.append(c)
                escaped = True
            else:
                out.append("\\\\")
                changed = True
        elif c == '"':
            if _is_closing_quote(text, i):
                out.append(c)
                in_str = False
            else:
                out.append('\\"')
                changed = True
        elif c in _CTRL:
            out.append(_CTRL[c])
            changed = True
        else:
            out.append(c)
    return "".join(out), changed

def _next_is_close(text: str, i: int) -> bool:
    j = i + 1
    while j < len(text) and text[j].isspace():
        j += 1
    return j < len(text) and text[j] in "}]"

def _drop_trailing_commas(text: str) -> tuple[str, bool]:
    out: list[str] = []
    in_str = escaped = changed = False
    for i, c in enumerate(text):
        if in_str:
            out.append(c)
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
            out.append(c)
        elif c == "," and _next_is_close(text, i):
            changed = True
        else:
            out.append(c)
    return "".join(out), changed

def _coerce_literals(text: str) -> tuple[str, bool]:
    out: list[str] = []
    in_str = escaped = changed = False
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
            i += 1
            continue
        hit = False
        for word, repl in (("True", "true"), ("False", "false"), ("None", "null")):
            if text.startswith(word, i):
                before = text[i - 1] if i else ""
                after = text[i + len(word)] if i + len(word) < n else ""
                if not (before.isalnum() or before == "_") and \
                        not (after.isalnum() or after == "_"):
                    out.append(repl)
                    i += len(word)
                    hit = changed = True
                    break
        if not hit:
            out.append(c)
            i += 1
    return "".join(out), changed

def close_open_structs(text: str) -> tuple[str, str]:
    stack: list[str] = []
    in_str = esc = False
    for c in text:
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c in "{[":
            stack.append(c)
        elif c in "}]":
            if not stack:
                return "", ""
            stack.pop()
    if in_str or not stack:
        return "", ""
    tail = "".join("}" if x == "{" else "]" for x in reversed(stack))
    return text + tail, "补齐末尾缺失的结构闭合符"

def _try_load(text: str) -> tuple[Any, bool]:
    try:
        return json.loads(text), True
    except (ValueError, RecursionError):
        return None, False


def _try_load5(text: str) -> tuple[Any, bool]:
    s = text or ""
    if "//" in s or "/*" in s:
        pass
        pass
        pass
        s = _STRIP_COMMENT.sub(lambda m: m.group(1) if m.group(1) else " ", s)
    v, ok = _try_load(s)
    if ok:
        return v, True
    s2, _hit = _drop_trailing_commas(s)
    return _try_load(s2)


pass
pass
pass
_YAML_KEY_RE = re.compile(r"[\w\u4e00-\u9fff.\-/\"']+")

pass
_STRIP_COMMENT = re.compile(
    r'("(?:[^"\\]|\\.)*")|/\*.*?\*/|//[^\n]*', re.S)
