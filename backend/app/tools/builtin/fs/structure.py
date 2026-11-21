from __future__ import annotations

_OPEN = set("([{")
_PAIRS = {")": "(", "]": "[", "}": "{"}


pass


def boundary_guard(old_text: str, new_text: str, path: str,
                   allow_loss: bool = False) -> str | None:
    if allow_loss or old_text == new_text:
        return None
    if path.endswith((".py", ".pyi")):
        return None
    return _unbalanced(old_text, new_text)
def _skip_str(text: str, i: int) -> tuple[int, int]:
    q = text[i]
    triple = text[i:i + 3] == q * 3
    j, n = i + (3 if triple else 1), len(text)
    while j < n:
        if text[j] == "\\":
            j += 2
            continue
        if triple and text[j:j + 3] == q * 3:
            return j + 3, text.count("\n", i, j + 3)
        if not triple and text[j] == q:
            return j + 1, text.count("\n", i, j + 1)
        if not triple and text[j] == "\n":
            return j + 1, 1
        j += 1
    return n, text.count("\n", i, n)


def _scan_brackets(text: str) -> str:
    stack: list[tuple[str, int]] = []
    line, i, n = 1, 0, len(text)
    while i < n:
        c = text[i]
        if c == "\n":
            line += 1
            i += 1
        elif c in "\"'`":
            i, dl = _skip_str(text, i)
            line += dl
        elif text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            line += text.count("\n", i, j)
            i = j
        elif c in _OPEN:
            stack.append((c, line))
            i += 1
        elif c in _PAIRS:
            if stack and stack[-1][0] == _PAIRS[c]:
                stack.pop()
            else:
                return f"第 {line} 行多了一个 {c}"
            i += 1
        else:
            i += 1
    if stack:
        ch, ln = stack[-1]
        return f"第 {ln} 行开的 {ch} 到此还没闭合"
    return ""


def _unbalanced(old_text: str, new_text: str) -> str | None:
    if _scan_brackets(old_text):
        return None
    bad = _scan_brackets(new_text)
    if not bad:
        return None
    return (f"替换后括号不配平：{bad}。整块替换函数/对象时请连同收尾的 "
            "}、)、] 一起包含（这是把函数尾巴改没了的典型症状）；"
            "确实要在此处拆开请传 truncate_ok=true。")
