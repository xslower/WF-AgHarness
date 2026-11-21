from __future__ import annotations


from .text import Row


class Match:

    __slots__ = ("row_start", "row_end", "col_start", "col_end", "block")

    def __init__(self, row_start: int, row_end: int,
                 col_start: int | None = None, col_end: int | None = None,
                 block: bool = True):
        self.row_start = row_start
        self.row_end = row_end
        self.col_start = col_start
        self.col_end = col_end
        self.block = block


def _indent_of(line: str) -> str:
    return line[:len(line) - len(line.lstrip())]


def _pattern(old: str) -> tuple[list[str], bool]:
    norm = old.replace("\r\n", "\n").replace("\r", "\n")
    raw = norm.split("\n")
    ends_nl = False
    if len(raw) > 1 and raw[-1] == "":
        raw.pop()
        ends_nl = True
    pat = [line.strip() for line in raw if line.strip()]
    return pat, (len(raw) > 1 or ends_nl)


def _was_literal(rows: list[Row], old: str, fuzzy: bool) -> bool:
    if not fuzzy:
        return True
    needle = old.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    return bool(needle) and needle in "\n".join(r.content for r in rows)


def _match_blocks(rows: list[Row], pat: list[str]) -> list[Match]:
    m = len(pat)
    if m == 0:
        return []
    body = [(i, r.content) for i, r in enumerate(rows) if r.content.strip()]
    if m > len(body):
        return []
    keys = [c.strip() for _, c in body]
    out: list[Match] = []
    for k in range(len(keys) - m + 1):
        if keys[k:k + m] != pat:
            continue
        first, last = body[k][0], body[k + m - 1][0]
        out.append(Match(first, last + 1, block=True))
    return out


def _match_frags(rows: list[Row], old: str, trim: bool) -> list[Match]:
    needle = old.strip() if trim else old
    if not needle:
        return []
    out: list[Match] = []
    for i, r in enumerate(rows):
        pos = r.content.find(needle)
        if pos >= 0:
            out.append(Match(i, i + 1, pos, pos + len(needle), block=False))
    return out


def locate(rows: list[Row], old: str) -> tuple[list[Match], bool]:
    pat, block_mode = _pattern(old)
    if not pat:
        return [], False
    if block_mode:
        hits = _match_blocks(rows, pat)
        return hits, not _was_literal(rows, old, bool(hits))
    hits = _match_frags(rows, old, trim=False)
    if hits:
        return hits, False
    return _match_frags(rows, old, trim=True), True


def apply_matches(rows: list[Row], matches: list[Match],
                  new: str) -> list[Row]:
    new_norm = new.replace("\r\n", "\n").replace("\r", "\n")
    new_lines = new_norm.split("\n") if new_norm else []
    out = list(rows)
    for m in sorted(matches, key=lambda x: x.row_start, reverse=True):
        row = out[m.row_start]
        eol = row.eol
        if m.block:
            new_rows = _block_rows(new_lines, out[m.row_start:m.row_end], eol)
            out = out[:m.row_start] + new_rows + out[m.row_end:]
        else:
            out = _frag_rows(out, m, new_lines, eol)
    return out


def _block_rows(new_lines: list[str], old_rows: list[Row],
                eol: str) -> list[Row]:
    if not new_lines:
        return []
    filled = [line for line in new_lines if line.strip()]
    if any(line[:1].isspace() for line in filled):
        return [Row(line, eol) for line in new_lines]
    olds = [_indent_of(r.content) for r in old_rows if r.content.strip()]
    if not olds:
        return [Row(line, eol) for line in new_lines]
    if len(olds) != len(filled):
        base = olds[0]
        return [Row(base + line if line.strip() else line, eol)
                for line in new_lines]
    out: list[Row] = []
    k = 0
    for line in new_lines:
        if not line.strip():
            out.append(Row(line, eol))
            continue
        out.append(Row(olds[k] + line.strip(), eol))
        k += 1
    return out


def _frag_rows(out: list[Row], m: Match, new_lines: list[str],
               eol: str) -> list[Row]:
    row = out[m.row_start]
    head = row.content[:m.col_start]
    tail = row.content[m.col_end:]
    if not new_lines:
        merged = head + tail
        new_rows = [Row(merged, eol)] if merged else []
    else:
        new_rows = [Row(line, eol) for line in new_lines[:-1]]
        new_rows.append(Row(new_lines[-1] + tail, eol))
        new_rows[0] = Row(head + new_rows[0].content, eol)
    return out[:m.row_start] + new_rows + out[m.row_start + 1:]
