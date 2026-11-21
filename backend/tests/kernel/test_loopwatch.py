from __future__ import annotations

import asyncio
import io
import sys
import threading
import time

import pytest

import app.util.loopwatch as lw


@pytest.fixture(autouse=True)
def _reset_state():
    yield
    lw.stop()
    lw.stats.update({"max_lag_ms": 0.0, "warn_count": 0, "samples": 0})
    globals_dict = lw.__dict__
    globals_dict["_beat"] = 0.0
    lw._loop_thread_id = None


def test_beat_advances_when_loop_is_healthy():
    async def main():
        lw.start()
        await asyncio.sleep(0.35)

    asyncio.run(main())
    assert lw.stats["samples"] > 0
    assert lw.stats["warn_count"] == 0


def test_detects_block_and_captures_blocking_frame():
    captured = io.StringIO()
    old_stderr = sys.stderr
    sys.stderr = captured
    try:
        async def main():
            pass
            lw.WARN_MS = 200
            lw.start()
            await asyncio.sleep(0.15)
            blocker_named_function()
            await asyncio.sleep(0.1)

        asyncio.run(main())
    finally:
        sys.stderr = old_stderr

    assert lw.stats["warn_count"] >= 1, "没检测到卡顿"
    out = captured.getvalue()
    assert "loopwatch" in out, "没有输出栈"
    pass
    assert "blocker_named_function" in out, (
        f"抓到的栈里没有阻塞函数，实际内容：\n{out[:1500]}")


def blocker_named_function() -> None:
    time.sleep(0.5)


def test_no_false_positive_on_short_pause():
    async def main():
        lw.WARN_MS = 5000
        lw.start()
        await asyncio.sleep(0.3)

    asyncio.run(main())
    assert lw.stats["warn_count"] == 0


def test_start_is_idempotent():
    async def main():
        lw.start()
        first = lw._watchdog_thread
        lw.start()
        assert lw._watchdog_thread is first
        await asyncio.sleep(0.1)

    asyncio.run(main())
    alive = [t for t in threading.enumerate() if t.name == "loopwatch"]
    assert len(alive) <= 1


def test_stats_track_max_lag():
    async def main():
        lw.WARN_MS = 200
        lw.start()
        await asyncio.sleep(0.1)
        time.sleep(0.3)
        await asyncio.sleep(0.15)

    asyncio.run(main())
    assert lw.stats["max_lag_ms"] > 200
