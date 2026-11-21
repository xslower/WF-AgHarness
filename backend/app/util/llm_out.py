from __future__ import annotations

import json
import re
from typing import Any

pass
pass
pass
FENCE_RE = re.compile(r"```[ \t]*([A-Za-z0-9_.+-]*)[ \t]*\r?\n?(.*?)```", re.S)

pass
pass
_FENCE_LINE_RE = re.compile(r"^[ \t]*```[ \t]*([A-Za-z0-9_.+-]*)[ \t]*$")

_TAGS = {
    "json": {"json", "jsonc", "json5"},
    "yaml": {"yaml", "yml"},
}


def fenced_blocks(text: str) -> list[tuple[str, str]]:
    lines = (text or "").split("\n")
    stack: list[tuple[str, int]] = []
    out: list[tuple[str, str]] = []
    for i, raw in enumerate(lines):
        m = _FENCE_LINE_RE.match(raw.rstrip("\r"))
        if not m:
            continue
        tag = m.group(1)
        if tag:
            stack.append((tag, i))
        elif stack:
            open_tag, start = stack.pop()
            if not stack:
                out.append((open_tag, "\n".join(lines[start + 1:i])))
        else:
            stack.append(("", i))
    for open_tag, start in stack:
        out.append((open_tag, "\n".join(lines[start + 1:])))
    return out


def fence_prompt(fmt: str) -> str:
    return (
        "\n\n[输出协议]\n"
        "你可以先自由分析、推理（正文不限，写多少都行），但回复的**最后**必须给出结果，"
        "形式为唯一一个代码块：\n"
        f"```{fmt}\n"
        f"（把最终结果放在这里）\n"
        "```\n"
        f"块内必须是完整可解析的 {fmt.upper()}，不要在代码块之后再写任何文字。"
    )


def retry_hint(fmt: str, err: str) -> str:
    return (
        f"你上一条输出不符合要求（{err}）。请重新回答：\n"
        f"1. 最后必须给出唯一一个 ```{fmt} 代码块，块内是完整可解析的 {fmt.upper()}；\n"
        "2. 代码块之后不要再写任何文字；\n"
        "3. 如果上面有分析，保留分析也可以，但结果必须放在那个代码块里。"
    )


def extract_fenced(text: str, fmt: str) -> tuple[str | None, str]:
    blocks = fenced_blocks(text)
    if not blocks:
        return None, f"输出里没有代码块（要求最后用 ```{fmt} 给出结果）"
    want = _TAGS.get(fmt, {fmt})
    matching = [body for tag, body in blocks if tag.strip().lower() in want]
    if matching:
        pick = matching[-1]
    else:
        pass
        loose = [body for tag, body in blocks
                 if not tag.strip() or tag.strip().lower() in {"json", "yaml", "yml"}]
        if not loose:
            return None, f"找到代码块，但没有 ```{fmt} 标记的块（实际标记: " + \
                ", ".join(repr(t) for t, _ in blocks[:3]) + "）"
        pick = loose[-1]
    if not pick.strip():
        return None, "代码块内容为空"
    return pick, ""


def scan_json_values(text: str) -> list[tuple[int, Any]]:
    dec = json.JSONDecoder()
    out: list[tuple[int, Any]] = []
    i, n = 0, len(text or "")
    while i < n:
        if text[i] in "{[":
            try:
                obj, end = dec.raw_decode(text, i)
            except (ValueError, RecursionError):
                i += 1
                continue
            out.append((i, obj))
            i = max(end, i + 1)
        else:
            i += 1
    return out


def last_json_value(text: str) -> Any | None:
    vals = [obj for _, obj in scan_json_values(text)
            if isinstance(obj, (dict, list))]
    return vals[-1] if vals else None


_YAML_START_RE = re.compile(r"^(?:- |[^\s#][^:]*:(?:\s|$)|\{[^\n]*\}|\[[^\n]*\])")


def yaml_tail_candidates(text: str) -> list[str]:
    lines = (text or "").splitlines()
    starts = [i for i, ln in enumerate(lines) if _YAML_START_RE.match(ln)]
    return ["\n".join(lines[i:]) for i in starts]
