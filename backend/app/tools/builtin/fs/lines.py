import re

from .text import Row


pass
_SYMBOLS = str.maketrans({"～": "~", "，": ",", "－": "-", "　": " "})

pass
pass
_RANGE_RE = re.compile(r"^(-?\d+)\s*(?:-|~|:|\.\.|到|至)\s*(-?\d+)$")

pass
_OPEN_RE = re.compile(r"^(-?\d+)\s*(?:-|~|:|\.\.)\s*$")

pass
_SPACE_RE = re.compile(r"^(\d+)\s+(\d+)$")


def normalize_spec(spec: str) -> str:
    s = (spec or "").translate(_SYMBOLS).strip()
    if not s:
        return s
    if "," in s:
        a, _, b = s.partition(",")
        return f"{a.strip()},{b.strip()}"
    m = _RANGE_RE.match(s)
    if m:
        return f"{m.group(1)},{m.group(2)}"
    m = _SPACE_RE.match(s)
    if m:
        return f"{m.group(1)},{m.group(2)}"
    m = _OPEN_RE.match(s)
    if m:
        return f"{m.group(1)},"
    return s


class LinesError(ValueError):
    pass


def split_lines(text: str) -> tuple[list[str], bool, str]:
    nl = "\r\n" if "\r\n" in text else "\n"
    if not text:
        return [], False, nl
    rows = text.split("\n")
    trailing = rows[-1] == ""
    if trailing:
        rows = rows[:-1]
    return [r[:-1] if r.endswith("\r") else r for r in rows], trailing, nl


def join_lines(lines: list[str], trailing: bool, nl: str = "\n") -> str:
    body = nl.join(lines)
    return body + nl if body and trailing else body


def char_lines(text: str) -> list[tuple[int, int, int, str, str]]:
    out: list[tuple[int, int, int, str, str]] = []
    i, n = 0, len(text)
    while i < n:
        j = text.find("\n", i)
        if j < 0:
            out.append((i, n, n, text[i:n], ""))
            break
        seg = text[i:j]
        if seg.endswith("\r"):
            out.append((i, j - 1, j + 1, seg[:-1], "\r\n"))
        else:
            out.append((i, j, j + 1, seg, "\n"))
        i = j + 1
    return out


def line_no_of(lines: list[tuple[int, int, int, str, str]], off: int) -> int:
    lo, hi = 0, len(lines)
    while lo < hi:
        mid = (lo + hi) // 2
        if lines[mid][0] <= off:
            lo = mid + 1
        else:
            hi = mid
    return max(1, lo)


def _int(tok: str) -> int:
    t = (tok or "").strip()
    if not re.fullmatch(r"-?\d+", t):
        pass
        pass
        pass
        hint = ""
        m = re.fullmatch(r"(-?\d+)\s*[-~～]\s*(-?\d+)", t)
        if m:
            hint = f"；写成区间用逗号：lines=\"{m.group(1)},{m.group(2)}\""
        raise LinesError(
            f"行号必须是整数或逗号区间（-1 = 最后一行），收到: {tok!r}{hint}。"
            "可用形式：\"5\"、\"10,40\"、\"10,\"、\"-3,\"。")
    return int(t)


def _line_ref(tok: str, total: int) -> int:
    n = _int(tok)
    if n == 0:
        raise LinesError("第 0 行不存在（行号从 1 开始；负数才是从末尾倒数）")
    idx = n if n > 0 else total + 1 + n
    if idx < 1 or idx > total:
        raise LinesError(f"文件共 {total} 行，{n} 超出了范围")
    return idx


def _end_ref(tok: str, total: int) -> tuple[int, str]:
    want = _int(tok)
    if want > total:
        return total, f"文件最长就是 {total} 行，终点 {want} 已截到末尾"
    return _line_ref(tok, total), ""


def parse_read_range(spec: str | None, total: int
                     ) -> tuple[int, int, str] | None:
    s = normalize_spec(spec or "")
    if not s:
        return None
    if "," not in s:
        pass
        n = _line_ref(s, total)
        return n, n, ""
    a, _, b = s.partition(",")
    start = _line_ref(a, total)
    end, note = (total, "") if not b.strip() else _end_ref(b, total)
    if end < start:
        raise LinesError(f"区间结束行({end}) 小于起始行({start})")
    return start, end, note

def _pos_ref(tok: int | str | None, total: int, what: str) -> int:
    if tok is None:
        raise LinesError(f"缺少 {what}")
    n = _int(str(tok))
    if n == 0:
        raise LinesError(f"{what} 不能是 0（行号从 1 开始）")
    idx = n if n > 0 else total + 1 + n
    if idx < 1 or idx > total:
        raise LinesError(f"文件共 {total} 行，{what}={n} 超出范围")
    return idx


def parse_write_target(before=None, after=None, replace=None,
                       append: bool = False, total: int = 0) -> dict:
    given = [x for x in (before, after, replace) if x is not None]
    if append:
        given.append("append")
    if len(given) > 1:
        raise LinesError("before / after / replace / append 只能给一个")
    if append:
        return {"kind": "insert", "pos": total, "by": "append"}
    if before is not None:
        pass
        n = _int(str(before))
        if n == 0:
            return {"kind": "insert", "pos": 0, "by": "before"}
        if n < 0:
            pos = total + 1 + n - 1
            if pos < 0 or pos > total:
                raise LinesError(f"文件共 {total} 行，before={n} 超出范围")
            return {"kind": "insert", "pos": pos, "by": "before"}
        if n > total + 1:
            raise LinesError(f"文件共 {total} 行，第 {n} 行不存在"
                             f"（追加到末尾用 append=true）")
        return {"kind": "insert", "pos": n - 1, "by": "before"}
    if after is not None:
        pass
        n = _int(str(after))
        if n < 0:
            pos = total + 1 + n
            if pos < 0 or pos > total:
                raise LinesError(f"文件共 {total} 行，after={n} 超出范围")
            return {"kind": "insert", "pos": pos, "by": "after"}
        if n < 1 or n > total:
            raise LinesError(f"文件共 {total} 行，第 {n} 行不存在")
        return {"kind": "insert", "pos": n, "by": "after"}
    if replace is not None:
        s = normalize_spec(str(replace))
        if not s:
            raise LinesError("replace 不能为空")
        a, _, b = s.partition(",")
        start = _line_ref(a, total)
        pass
        pass
        pass
        pass
        pass
        pass
        if "," not in s:
            end, note = start, ""
        elif not b.strip():
            end, note = total, ""
        else:
            end, note = _end_ref(b, total)

        if end < start:
            raise LinesError(f"区间结束行({end}) 小于起始行({start})")
        return {"kind": "replace", "start": start, "end": end, "note": note}
    return {"kind": "overwrite"}



pass

pass
pass
ANCHOR_TOLERANCE = 1
pass
ANCHOR_TOLERANCE_UNIQUE = 3


def find_anchor(rows: list[Row], want: int, expect: str) -> tuple[int, str]:
    from .match import locate

    needle = (expect or "").strip()
    if not needle:
        return want, ""
    matches, fuzzy = locate(rows, expect)
    if not matches:
        near = _nearby(rows, want)
        raise LinesError(
            f"expect「{needle}」在文件里找不到。给的行号是第 {want} 行，"
            f"附近内容：\n{near}\n"
            f"行号可能已过期，请重新 f_read 确认")
    hits = [m.row_start + 1 for m in matches]
    fuzz = "（按忽略缩进/空行匹配）" if fuzzy else ""
    tol = ANCHOR_TOLERANCE if len(hits) > 1 else ANCHOR_TOLERANCE_UNIQUE
    within = [h for h in hits if abs(h - want) <= tol]
    if not within:
        where = "、".join(f"第 {h} 行" for h in hits[:6])
        raise LinesError(
            f"expect「{needle}」命中在 {where}，与你给的第 {want} 行差了 "
            f"{min(abs(h - want) for h in hits)} 行（容差 {tol} 行）。"
            f"内容可能已经变了，请重新 f_read 确认")
    if len(within) > 1:
        where = "、".join(f"第 {h} 行" for h in within)
        raise LinesError(
            f"expect「{needle}」在容差范围内命中多处（{where}），"
            f"无法判断你要改哪一处。请给更长的唯一片段，或改用 f_replace")
    hit = within[0]
    if hit == want:
        return hit, fuzz
    return hit, (f"（expect「{needle}」命中第 {hit} 行，你给的是第 {want} 行，"
                 f"已按实际命中行执行{fuzz}）")


def _nearby(rows: list[Row], line: int, radius: int = 2) -> str:
    if not rows:
        return "  （文件为空）"
    lo = max(1, line - radius)
    hi = min(len(rows), line + radius)
    return "\n".join(f"  {i}| {rows[i - 1].content[:120]}"
                     for i in range(lo, hi + 1))
