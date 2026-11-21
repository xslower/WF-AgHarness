from __future__ import annotations

from typing import TYPE_CHECKING

from ....util.jsonx import err, is_err

if TYPE_CHECKING:
    from ... import ToolContext

_WRITE_KEYS = ("content", "before", "after", "replace", "expect",
               "append", "truncate_ok")
_REPLACE_KEYS = ("old", "new", "replace_all", "replace_count")


def _guessed(tool: str, out: str) -> str:
    return out if is_err(out) else f"（猜你想调用 {tool}，已按 {tool} 执行）\n{out}"


def _all_items(edits, keys: tuple, exclude: tuple) -> bool:
    return (isinstance(edits, list) and bool(edits)
            and all(isinstance(e, dict) and any(k in e for k in keys)
                    and not any(k in e for k in exclude) for e in edits))


async def f_write_entry(**kw):
    ctx = kw.pop("ctx")
    path = kw.pop("path", "")
    edits = kw.pop("edits", None)
    top = any(k in kw for k in _REPLACE_KEYS)
    batch = _all_items(edits, ("old", "new"), _WRITE_KEYS)
    if top or batch:
        from .write import f_replace
        if batch and not top:
            return _guessed("f_replace", await f_replace(
                path=path, ctx=ctx, edits=edits, mode=kw.pop("mode", 1)))
        rkw = {k: kw.pop(k) for k in _REPLACE_KEYS if k in kw}
        rkw.update(path=path, ctx=ctx, mode=kw.pop("mode", 1))
        return _guessed("f_replace", await f_replace(**rkw))
    from .write import f_write
    return await f_write(path=path, ctx=ctx, edits=edits, **kw)


async def f_replace_entry(**kw):
    ctx = kw.pop("ctx")
    path = kw.pop("path", "")
    edits = kw.pop("edits", None)
    top = any(k in kw for k in _WRITE_KEYS)
    batch = _all_items(edits, _WRITE_KEYS, ("old", "new"))
    if top or batch:
        from .write import f_write
        if batch and not top:
            return _guessed("f_write", await f_write(
                path=path, ctx=ctx, edits=edits, mode=kw.pop("mode", 1)))
        wkw = {k: kw.pop(k) for k in _WRITE_KEYS if k in kw}
        wkw.update(path=path, ctx=ctx, mode=kw.pop("mode", 1))
        return _guessed("f_write", await f_write(**wkw))
    if isinstance(path, list):
        if len(path) == 1 and isinstance(path[0], str):
            path = path[0]
        elif len(path) > 1:
            return await _multi(path, edits, kw, ctx)
    from .write import f_replace
    return await f_replace(path=path, ctx=ctx, edits=edits, **kw)


async def _multi(paths: list, edits, kw: dict, ctx: "ToolContext") -> str:
    if not isinstance(edits, list) or len(edits) != len(paths):
        n = len(edits) if isinstance(edits, list) else "非数组"
        return err(f"path 给了 {len(paths)} 个文件，edits 必须同数量（当前 {n}），"
                   "数量严格匹配才按多文件执行")
    from .write import f_replace
    parts: list[str] = []
    for p, edit in zip(paths, edits):
        if not isinstance(edit, dict):
            return err(f"{p} 的 edits 项必须是对象，收到 {edit!r}")
        parts.append(await f_replace(
            path=p, ctx=ctx, mode=kw.get("mode", 1),
            old=edit.get("old", ""), new=edit.get("new", ""),
            replace_all=edit.get("replace_all", False),
            replace_count=edit.get("replace_count", 0)))
    return "\n\n".join(parts)
