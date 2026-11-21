from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import TYPE_CHECKING

from ....util.fsx import ensure_parent
from ....util.jsonx import err
from . import revert
from .common import _emit_file
from .lines import split_lines

if TYPE_CHECKING:
    from ... import ToolContext

pass
_WRITE_LOCKS: dict[str, asyncio.Lock] = {}


def lock_for(p: Path) -> asyncio.Lock:
    key = str(p)
    lock = _WRITE_LOCKS.get(key)
    if lock is None:
        lock = _WRITE_LOCKS[key] = asyncio.Lock()
    return lock


def atomic_write(p: Path, text: str) -> None:
    ensure_parent(p)
    tmp = p.with_name(f".{p.name}.tmp-write")
    try:
        pass
        tmp.write_bytes(text.encode("utf-8"))
        if p.exists():
            try:
                os.chmod(tmp, p.stat().st_mode)
            except OSError:
                pass
        os.replace(tmp, p)
    finally:
        if tmp.exists():
            tmp.unlink()


def count_lines(text: str) -> int:
    return len(split_lines(text)[0])


async def revert_last(p: Path, ctx: "ToolContext", old_text: str,
                      existed: bool) -> str:
    prev = revert.pop(ctx, p)
    if prev is None:
        return err(f"没有可回退的写入记录：{p}（本会话内该文件没被写过）")
    revert.push(ctx, p, old_text)
    await ctx.auto_snapshot(f"revert {p.name}", [p])
    atomic_write(p, prev)
    _emit_file(ctx, p, "modified" if existed else "created")
    return f"已回退 {p}（恢复为上一次写入前的内容，{count_lines(prev)} 行）"


async def read_baseline(p: Path, ctx: "ToolContext", mode: int
                        ) -> tuple[str, bool, str | None, str | None]:
    pass
    old_text = p.read_bytes().decode("utf-8", "replace") if p.is_file() else ""
    existed = p.is_file()
    if mode == 2:
        return old_text, existed, None, await revert_last(p, ctx, old_text, existed)
    if mode == 3:
        prev = revert.peek(ctx, p)
        if prev is None:
            return old_text, existed, err(
                f"没有可回退的写入记录：{p}（本会话内该文件没被写过），"
                "mode=3 需要先有一次写入才有回滚点"), None
        return prev, True, None, None
    if mode != 1:
        return old_text, existed, err(
            "mode 只能是 1(执行) / 2(撤销上一次写入) / 3(回滚后重写)，"
            f"收到: {mode}"), None
    return old_text, existed, None, None
