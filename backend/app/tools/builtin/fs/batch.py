from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ....util.jsonx import err, is_err, loads_lenient
from .common import physical_lines

if TYPE_CHECKING:
    from ... import ToolContext

pass
MAX_EDITS = 50

pass
_WRITE_KEYS = ("before", "after", "replace", "append", "expect")


def _coerce_edits(edits) -> tuple[list[dict] | None, str | None]:
    if isinstance(edits, str):
        pass
        pass
        edits, problem, _note = loads_lenient(edits, scene="edits")
        if problem:
            return None, f"edits 不是合法 JSON 数组：{problem}"
    if isinstance(edits, dict):
        edits = [edits]
    if not isinstance(edits, list):
        return None, "edits 必须是数组（每项是一个改动）"
    if not edits:
        return None, "edits 为空，没有要执行的改动"
    if len(edits) > MAX_EDITS:
        return None, f"一次最多 {MAX_EDITS} 处改动（本次 {len(edits)} 处），请分批"
    out = []
    for i, e in enumerate(edits, 1):
        if not isinstance(e, dict):
            return None, f"第 {i} 处不是对象（应含改动字段）"
        out.append(e)
    return out, None


def _ok(i: int, text: str) -> str:
    first = " ".join(text.split("\n", 1)[0].split())
    return f"#{i} ✓ {first}"


def _bad(i: int, text: str) -> str:
    first = " ".join(text.strip().split("\n", 1)[0].split())
    return f"#{i} ✗ {first}"


def _aggregate(results: list[tuple[bool, str]]) -> str:
    ok = sum(1 for good, _ in results if good)
    head = f"{len(results)} 处改动 → {ok} 成功 / {len(results) - ok} 失败"
    return head + "\n" + "\n".join(line for _, line in results)


def _is_error(text: str) -> bool:
    return is_err(text)


def _clean(text: str) -> str:
    if _is_error(text):
        try:
            obj = json.loads(text)
            return str(obj.get("error") or obj.get("reason") or text)
        except ValueError:
            return text
    return text


def _plan_edit_slots(items: list[dict], total: int):
    from .lines import LinesError, parse_write_target

    slots = []
    for i, item in enumerate(items, 1):
        kw = {k: item[k] for k in _WRITE_KEYS if k in item}
        try:
            t = parse_write_target(kw.get("before"), kw.get("after"),
                                   kw.get("replace"), bool(kw.get("append")),
                                   total)
        except LinesError as e:
            return None, f"第 {i} 处落点无效：{e}"
        kind = t["kind"]
        if kind == "overwrite":
            slots.append((0, total, True))
        elif kind == "insert":
            pos = t["pos"]
            slots.append((pos, pos, False))
        else:
            slots.append((t["start"] - 1, t["end"], False))
    return slots, None


def _conflicts(slots: list[tuple[int, int, bool]]) -> str | None:
    overwrites = [i for i, s in enumerate(slots, 1) if s[2]]
    if overwrites and len(slots) > 1:
        return f"第 {overwrites[0]} 处是整篇覆盖，不能与其它改动同批"
    reps = [(i, a, b) for i, (a, b, full) in enumerate(slots, 1)
            if not full and b > a]
    for x in range(len(reps)):
        for y in range(x + 1, len(reps)):
            i1, a1, b1 = reps[x]
            i2, a2, b2 = reps[y]
            if max(a1, a2) < min(b1, b2):
                return f"第 {i1} 处与第 {i2} 处的替换区间重叠，请合并成一处或分开调用"
    for i, a, b in reps:
        for j, (ia, ib, full) in enumerate(slots, 1):
            if full or ib > ia:
                continue
            if a < ia < b:
                return f"第 {j} 处的插入点落在第 {i} 处的替换区间内部，请拆开"
    return None


def _transactions_reset(ctx: "ToolContext", p, old_text: str) -> None:
    if not p.is_file():
        return
    from . import revert
    revert.reset(ctx, p, old_text)


def _before_text(path: str, ctx: "ToolContext") -> tuple[object, str]:
    from . import write as _w
    p = _w.resolve(ctx, path)
    text = p.read_bytes().decode("utf-8", "replace") if p.is_file() else ""
    return p, text


async def write_batch(path: str, ctx: "ToolContext", edits,
                      mode: int = 1, truncate_ok: bool = False) -> str:
    from . import write as _w
    items, problem = _coerce_edits(edits)
    if problem:
        return err(problem)
    pass
    if mode == 2:
        return await _w.f_write(path, ctx, content="", mode=2)
    prefix = ""
    if mode == 3:
        back = await _w.f_write(path, ctx, content="", mode=2)
        if _is_error(back):
            return back
        prefix = _clean(back) + "\n"
        mode = 1
    p, original = _before_text(path, ctx)
    pass
    pass
    total = len(physical_lines(original))
    slots, problem = _plan_edit_slots(items, total)
    if problem:
        return err(problem)
    conflict = _conflicts(slots)
    if conflict:
        return err(f"{conflict}（本次共 {len(items)} 处，已整批拒绝，未写入任何内容）")

    results: list[tuple[bool, str]] = [None] * len(items)
    for idx in sorted(range(len(items)), key=lambda k: (slots[k][0], slots[k][1]),
                      reverse=True):
        i = idx + 1
        item = items[idx]
        content = item.get("content")
        if content is None:
            results[idx] = (False, _bad(i, "缺 content（要写入的文本）"))
            continue
        kw = {k: item[k] for k in _WRITE_KEYS if k in item}
        try:
            text = await _w.f_write(path, ctx, content=content, mode=mode,
                                    truncate_ok=truncate_ok, **kw)
        except TypeError as e:
            text = err(f"参数错误: {e}")
        good = not _is_error(text)
        results[idx] = (good, _ok(i, text) if good else _bad(i, _clean(text)))
    results = [r for r in results if r is not None]
    if any(g for g, _ in results):
        _transactions_reset(ctx, p, original)
    return prefix + _aggregate(results)


async def replace_batch(path: str, ctx: "ToolContext", edits,
                        mode: int = 1) -> str:
    from . import write as _w
    items, problem = _coerce_edits(edits)
    if problem:
        return err(problem)
    pass
    if mode == 2:
        return await _w.f_replace(path, ctx, old="", new="", mode=2)
    prefix = ""
    if mode == 3:
        back = await _w.f_replace(path, ctx, old="", new="", mode=2)
        if _is_error(back):
            return back
        prefix = _clean(back) + "\n"
        mode = 1

    p, original = _before_text(path, ctx)
    results: list[tuple[bool, str]] = []
    for i, item in enumerate(items, 1):
        old, new = item.get("old"), item.get("new")
        if old in (None, "") or new is None:
            results.append((False, _bad(i, "缺 old 或 new")))
            continue
        count = item.get("replace_count", 0)
        try:
            text = await _w.f_replace(path, ctx, old=old, new=new, mode=mode,
                                      replace_count=count)
        except TypeError as e:
            text = err(f"参数错误: {e}")
        good = not _is_error(text)
        results.append((good, _ok(i, text) if good else _bad(i, _clean(text))))
    if any(g for g, _ in results):
        _transactions_reset(ctx, p, original)
    return prefix + _aggregate(results)
