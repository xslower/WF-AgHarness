from __future__ import annotations

import json

from .diff import ctx_slice, render_block
from .lines import LinesError, find_anchor
from .text import Row, join_rows, split_rows

pass
CONTEXT_LINES = 3


def split_body(content: str) -> list[str]:
    body = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if body and body[-1] == "":
        body.pop()
    if body == [""]:
        body = []
    return body


def anchor_for_insert(rows: list[Row], pos: int, expect: str,
                      by: str) -> tuple[int, str]:
    want = (pos + 1) if by == "before" else pos
    hit, note = find_anchor(rows, want, expect)
    new_pos = hit - 1 if by == "before" else hit
    return new_pos, note


def anchor_for_replace(rows: list[Row], start: int, end: int, expect: str
                       ) -> tuple[int, int, str]:
    hit, note = find_anchor(rows, start, expect)
    shift = hit - start
    if not shift:
        return start, end, note
    s, e = start + shift, end + shift
    if e > len(rows):
        e = len(rows)
    if s > len(rows):
        raise LinesError(
            f"按 expect 命中第 {hit} 行后，起始行超出文件末尾（共 {len(rows)} 行）")
    return s, e, note


def build_overwrite(content: str, rows: list[Row]) -> tuple[str, str, str]:
    before_rows = len(rows)
    after_rows = len(split_rows(content))
    summary = f"原 {before_rows} 行 → 新 {after_rows} 行"
    return content, summary, summary


def _where_text(pos: int, total: int) -> str:
    if pos == 0:
        return "文件最前"
    if pos == total:
        return "文件末尾"
    return f"第 {pos + 1} 行前"


def build_insert(rows: list[Row], target: dict, body: list[str],
                 expect: str | None) -> tuple[str, str, str, list[int]]:
    pos = int(target["pos"])
    anchor_note = ""
    if expect:
        pos, anchor_note = anchor_for_insert(rows, pos, expect,
                                             str(target.get("by") or "before"))
    if pos < 0 or pos > len(rows):
        raise LinesError(f"插入位置越界：pos={pos}，文件共 {len(rows)} 行")
    if not body:
        raise LinesError("插入内容为空，未写入")

    eol = rows[0].eol if rows else "\n"
    new_rows = rows[:pos] + [Row(line, eol) for line in body] + rows[pos:]
    where = _where_text(pos, len(rows))
    cb = ctx_slice(rows, max(0, pos - CONTEXT_LINES), pos)
    ca = ctx_slice(rows, pos, min(len(rows), pos + CONTEXT_LINES))
    detail = (f"在{where}插入 {len(body)} 行{anchor_note}\n"
              + render_block(pos + 1, pos, [], body, cb, ca))
    summary = f"在{where}插入 {len(body)} 行{anchor_note}"
    written = list(range(pos + 1, pos + 1 + len(body)))
    return join_rows(new_rows), summary, detail, written


def build_replace(rows: list[Row], target: dict, body: list[str],
                  expect: str | None) -> tuple[str, str, str, list[int]]:
    start, end = int(target["start"]), int(target["end"])
    notes = [str(target.get("note") or "")]
    if expect:
        start, end, anchor_note = anchor_for_replace(rows, start, end, expect)
        notes.append(anchor_note)
    note = "".join(n for n in notes if n)


    eol = rows[0].eol if rows else "\n"
    if not body:
        new_rows = rows[:start - 1] + rows[end:]
    else:
        new_rows = (rows[:start - 1] + [Row(line, eol) for line in body]
                    + rows[end:])
    cb = ctx_slice(rows, max(0, start - 1 - CONTEXT_LINES), start - 1)
    ca = ctx_slice(rows, end, min(len(rows), end + CONTEXT_LINES))
    detail = render_block(start, end, [r.content for r in rows[start - 1:end]],
                          body, cb, ca)
    if note:
        detail = note.lstrip("（").rstrip("）") + "\n" + detail
    summary = f"原第 {start}~{end} 行 → 现 {len(body)} 行{note}"
    written = list(range(start, start + len(body)))
    return join_rows(new_rows), summary, detail, written


def check_truncation(target: dict, rows: list[Row], old_text: str,
                     new_text: str, existed: bool,
                     truncate_ok: bool, guard_lines: int) -> str | None:
    if (target["kind"] != "overwrite" or truncate_ok or not existed
            or len(rows) < guard_lines or len(new_text) * 3 >= len(old_text)):
        return None
    after = len(split_rows(new_text))
    return json.dumps({"error": "疑似误覆盖：原文 "
                                f"{len(rows)} 行 → 新内容 {after} 行。"
                                "整篇覆盖大量丢失内容时请显式传 truncate_ok=true；"
                                "想在末尾追加请用 append=true",
                       "before_lines": len(rows),
                       "after_lines": after},
                      ensure_ascii=False)
