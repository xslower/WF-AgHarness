from __future__ import annotations

class Row:

    __slots__ = ("content", "eol")

    def __init__(self, content: str, eol: str):
        self.content = content
        self.eol = eol

    def __repr__(self) -> str:
        return f"Row({self.content!r}, {self.eol!r})"


def split_rows(text: str) -> list[Row]:
    if not text:
        return []
    rows: list[Row] = []
    i, n = 0, len(text)
    while i < n:
        j = text.find("\n", i)
        if j < 0:
            rows.append(Row(text[i:n], ""))
            break
        seg = text[i:j]
        if seg.endswith("\r"):
            rows.append(Row(seg[:-1], "\r\n"))
        else:
            rows.append(Row(seg, "\n"))
        i = j + 1
    return rows


def join_rows(rows: list[Row]) -> str:
    return "".join(r.content + r.eol for r in rows)



pass
pass
pass
pass
pass
pass
pass
pass
pass
pass
pass
pass
pass
pass
pass

import ast as _ast
import re as _re
import shutil as _shutil
import subprocess as _subprocess

_INDENT_REPAIR_MAX = 6


def syntax_check(text: str, path: str) -> tuple[int, str] | None:
    try:
        _ast.parse(text, filename=path)
        return None
    except SyntaxError as e:
        return (e.lineno or 1, e.msg or "语法错误")
    except (ValueError, RecursionError) as e:
        return (1, str(e))


def _is_indent_error(msg: str) -> bool:
    m = (msg or "").lower()
    return ("indent" in m
            or "tab" in m)


def _indent_unit(rows: list[Row]) -> str:
    widths = []
    has_tab = False
    for r in rows:
        stripped = r.content.lstrip(" ")
        if not stripped:
            continue
        n = len(r.content) - len(stripped)
        if n:
            widths.append(n)
        elif "\t" in r.content[:r.content.find(stripped) if stripped else 0] or \
                (r.content.startswith("\t")):
            has_tab = True
    if has_tab and not widths:
        return "\t"
    if not widths:
        return "    "
    g = widths[0]
    for w in widths[1:]:
        while w:
            g, w = w, g % w
    return " " * max(1, g)


def _indent_lines(rows: list[Row], seg: list[int], unit: str, add: bool) -> list[Row]:
    out = list(rows)
    for i in seg:
        r = out[i - 1]
        if add:
            out[i - 1] = Row(unit + r.content, r.eol)
        else:
            if r.content.startswith("\t") and unit == "\t":
                out[i - 1] = Row(r.content[1:], r.eol)
            elif r.content.startswith(" " * len(unit)):
                out[i - 1] = Row(r.content[len(unit):], r.eol)
            pass
    return out


def _expand_tabs(rows: list[Row], seg: list[int], unit: str) -> list[Row]:
    out = list(rows)
    width = 8 if unit == "\t" else len(unit)
    for i in seg:
        r = out[i - 1]
        if "\t" not in r.content[:len(r.content) - len(r.content.lstrip())]:
            continue
        expanded = r.content.expandtabs(width)
        out[i - 1] = Row(expanded, r.eol)
    return out


def _try_ruff_format(segment_text: str) -> str | None:
    ruff = _shutil.which("ruff")
    if not ruff:
        return None
    try:
        r = _subprocess.run([ruff, "format", "--stdin-filename", "x.py", "-"],
                            input=segment_text, capture_output=True, text=True,
                            timeout=10, encoding="utf-8")
        return r.stdout if r.returncode == 0 and r.stdout else None
    except Exception:
        return None


def _split_new_lines(new: str) -> list[str]:
    n = new.replace("\r\n", "\n").replace("\r", "\n")
    return n.split("\n") if n else []


def _leading_ws(content: str) -> str:
    return content[:len(content) - len(content.lstrip())]


def _expand_seg(rows: list[Row], start: int, written: set[int]) -> list[int] | None:
    if start not in written or start < 1 or start > len(rows):
        return None
    ws = _leading_ws(rows[start - 1].content)
    lo = hi = start
    while lo - 1 in written and _leading_ws(rows[lo - 2].content) == ws:
        lo -= 1
    while hi + 1 in written and _leading_ws(rows[hi].content) == ws:
        hi += 1
    return list(range(lo, hi + 1))


def _seg_before(rows: list[Row], err_line: int, written: set[int]) -> list[int] | None:
    if err_line - 1 not in written:
        return None
    return _expand_seg(rows, err_line - 1, written)


def _set_indent(rows: list[Row], seg: list[int], prefix: str) -> list[Row]:
    out = list(rows)
    for i in seg:
        r = out[i - 1]
        body = r.content[len(_leading_ws(r.content)):]
        out[i - 1] = Row(prefix + body, r.eol)
    return out


def _candidates_for(check: tuple[int, str], cur_rows: list[Row], wset: set[int],
                    unit: str, path: str) -> list[tuple[str, list[Row]]]:
    e_line, e_msg = check
    low = e_msg.lower()
    trials: list[tuple[str, list[Row]]] = []

    if "expected an indented block" in low:
        pass
        pass
        m_op = _re.search(r"on line (\d+)", e_msg)
        opener = int(m_op.group(1)) if m_op else e_line - 1
        seg = [i for i in range(opener + 1, e_line + 1) if i in wset]
        if seg:
            pass
            pass
            op_ws = _leading_ws(cur_rows[opener - 1].content)
            add = "    " if unit == "\t" else unit
            trials.append(("增加缩进", _set_indent(cur_rows, seg, op_ws + add)))
            pass
            trials.append(("增加缩进", _indent_lines(cur_rows, seg, unit, True)))

    elif "unexpected indent" in low:
        if e_line in wset:
            pass
            trials.append(("减少缩进", _indent_lines(cur_rows, [e_line], unit, False)))
        else:
            pass
            seg = _seg_before(cur_rows, e_line, wset)
            if seg:
                trials.append(("增加缩进", _indent_lines(cur_rows, seg, unit, True)))

    elif "unindent" in low:
        pass
        if e_line in wset:
            trials.append(("减少缩进", _indent_lines(cur_rows, [e_line], unit, False)))
        seg = _seg_before(cur_rows, e_line, wset)
        if seg:
            trials.append(("增加缩进", _indent_lines(cur_rows, seg, unit, True)))

    pass
    seg0 = _expand_seg(cur_rows, e_line, wset) or _seg_before(cur_rows, e_line, wset)
    if seg0:
        trials.append(("展开 tab", _expand_tabs(cur_rows, seg0, unit)))
        pass
        seg_text = "\n".join(cur_rows[i - 1].content for i in seg0)
        formatted = _try_ruff_format(seg_text)
        if formatted:
            new_rows = list(cur_rows)
            for k, i in enumerate(seg0):
                fl = formatted.split("\n")
                if k < len(fl):
                    new_rows[i - 1] = Row(fl[k], cur_rows[i - 1].eol)
            trials.append(("ruff 格式化", new_rows))
    return trials


def repair_indent(text: str, path: str, written: list[int],
                  ) -> tuple[str, str] | None:
    if syntax_check(text, path) is None:
        return None
    rows = split_rows(text)
    unit = _indent_unit(rows)
    wset = set(written)

    cur_rows = rows
    seen = {syntax_check(text, path)}
    note_parts: list[str] = []
    for _ in range(_INDENT_REPAIR_MAX):
        check = syntax_check(join_rows(cur_rows), path)
        if check is None:
            break
        if not _is_indent_error(check[1]):
            return None

        trials = _candidates_for(check, cur_rows, wset, unit, path)

        pass
        for name, cand_rows in trials:
            cand_text = join_rows(cand_rows)
            if syntax_check(cand_text, path) is None:
                note = "；".join([*note_parts, name])
                return cand_text, f"已自动修正缩进（{note}）"
        pass
        pass
        pass
        for name, cand_rows in trials:
            cand_text = join_rows(cand_rows)
            next_err = syntax_check(cand_text, path)
            if next_err is not None and next_err not in seen:
                seen.add(next_err)
                cur_rows = cand_rows
                note_parts.append(name)
                break
        else:
            return None
    return None


def _syntax_gate(text: str, old_text: str, path: str, written: list[int],
                 allow_broken: bool = False,
                 ) -> tuple[str, str, bool]:
    if not path.endswith((".py", ".pyi")):
        return text, "", True
    if syntax_check(text, path) is None:
        return text, "", True
    if syntax_check(old_text, path) is not None:
        return text, ("⚠ 该文件本身不是合法 Python（原文件即存在语法错误），"
                      "本次未做语法校验"), True
    repaired = repair_indent(text, path, written)
    if repaired is not None:
        fixed, note = repaired
        return fixed, note, True
    line, msg = syntax_check(text, path) or (1, "语法错误")
    rows = split_rows(text)
    lo, hi = max(1, line - 2), min(len(rows), line + 2)
    near = ""
    for i in range(lo, hi + 1):
        mark = ">" if i == line else " "
        near += f"\n  {mark} {i}| {rows[i - 1].content[:100]}"
    return text, (f"写入后语法错误：第 {line} 行 {msg}。{near}\n"
                  + ("（本次写入量较大：已按你的内容落盘，但文件当前不合法。"
                     "接着把它改好，或 mode=3 回滚后整体重写）" if allow_broken else
                     "请 f_read 看清上下文后修正再写一次")), allow_broken

