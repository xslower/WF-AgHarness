from __future__ import annotations

import asyncio
import time

import pytest

import app.util.loopwatch as loopwatch


@pytest.fixture(autouse=True)
def _reset():
    loopwatch.stats.update({"max_lag_ms": 0.0, "warn_count": 0, "samples": 0})
    loopwatch.stop()
    yield
    loopwatch.stop()


@pytest.mark.asyncio
async def test_probe_records_samples_and_is_idempotent():
    loopwatch.start()
    task = loopwatch._task
    loopwatch.start()
    assert loopwatch._task is task, "重复 start 不应再起一个任务"
    await asyncio.sleep(loopwatch.TICK_MS / 1000 * 3.5)
    assert loopwatch.stats["samples"] >= 2
    loopwatch.stop()
    assert loopwatch._task is None


@pytest.mark.asyncio
async def test_blocking_the_loop_is_detected(monkeypatch):
    monkeypatch.setattr(loopwatch, "TICK_MS", 20)
    monkeypatch.setattr(loopwatch, "WARN_MS", 60)
    loopwatch.start()
    await asyncio.sleep(0.05)
    time.sleep(0.15)
    await asyncio.sleep(0.1)
    assert loopwatch.stats["warn_count"] >= 1, "同步阻塞没被检测到"
    assert loopwatch.stats["max_lag_ms"] >= 60


@pytest.mark.asyncio
async def test_probe_is_cheap():
    loopwatch.start()
    t0 = loopwatch.stats["samples"]
    t_start = time.perf_counter()
    await asyncio.sleep(1.0)
    dt = time.perf_counter() - t_start
    assert dt < 1.5, f"监视本身拖慢了循环（1s 的 sleep 实际用了 {dt:.2f}s）"
    assert loopwatch.stats["samples"] > t0
