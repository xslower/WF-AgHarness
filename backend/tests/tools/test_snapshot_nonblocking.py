from __future__ import annotations

import asyncio
import time

import pytest

from app.tools import ToolContext


def test_auto_snapshot_is_a_coroutine():
    assert asyncio.iscoroutinefunction(ToolContext.auto_snapshot)


@pytest.mark.asyncio
async def test_slow_snapshot_does_not_block_loop():
    ctx = ToolContext(cwd="/tmp")

    def slow_snapshot(_message: str) -> None:
        time.sleep(0.3)

    ctx.snapshot = slow_snapshot

    beats = 0

    async def heartbeat() -> None:
        nonlocal beats
        while True:
            beats += 1
            await asyncio.sleep(0.01)

    hb = asyncio.create_task(heartbeat())
    await ctx.auto_snapshot("write x.py")
    hb.cancel()
    try:
        await hb
    except asyncio.CancelledError:
        pass

    pass
    assert beats > 5, f"快照阻塞了事件循环（心跳只跑了 {beats} 圈）"


@pytest.mark.asyncio
async def test_snapshot_failure_never_breaks_write():
    ctx = ToolContext(cwd="/tmp")

    def boom(_message: str) -> None:
        raise TimeoutExpired()

    ctx.snapshot = boom
    await ctx.auto_snapshot("write x.py")


@pytest.mark.asyncio
async def test_snapshot_runs_only_once_per_turn():
    ctx = ToolContext(cwd="/tmp")
    calls: list[str] = []

    def count(message: str) -> None:
        calls.append(message)

    ctx.snapshot = count
    await ctx.auto_snapshot("write a.py")
    await ctx.auto_snapshot("write b.py")
    assert calls == ["write a.py"]


class TimeoutExpired(Exception):
    pass
