from __future__ import annotations

import asyncio
import time

import pytest


@pytest.fixture
def store(tmp_path, monkeypatch):
    from app import config as config_mod
    monkeypatch.setattr(config_mod, "DATA_DIR", tmp_path)
    from app.chat.sessions import SessionStore
    return SessionStore()


def test_save_async_persists_like_save(store):
    s = store.create(title="t", project="")
    s["messages"].append({"role": "user", "content": "hi"})
    s["title"] = "改过的标题"

    asyncio.run(store.save_async(s))

    back = store.get(s["id"])
    assert back is not None
    assert back["title"] == "改过的标题"
    assert back["messages"][-1]["content"] == "hi"


def test_save_async_keeps_incremental_semantics(store):
    s = store.create(title="t", project="")
    s["messages"].append({"role": "user", "content": "m1"})
    asyncio.run(store.save_async(s))

    s["messages"].append({"role": "assistant", "content": "m2"})
    asyncio.run(store.save_async(s))

    back = store.get(s["id"])
    assert [m["content"] for m in back["messages"]] == ["m1", "m2"]


def test_save_async_does_not_block_event_loop(store):
    s = store.create(title="t", project="")
    for i in range(300):
        s["messages"].append({"role": "user", "content": f"msg-{i}"})

    async def main() -> float:
        ticks: list[float] = []
        stop = False

        async def heartbeat() -> None:
            while not stop:
                ticks.append(time.monotonic())
                await asyncio.sleep(0.01)

        hb = asyncio.create_task(heartbeat())
        try:
            await store.save_async(s)
        finally:
            stop = True
            await hb
        gaps = [b - a for a, b in zip(ticks, ticks[1:])]
        return max(gaps) if gaps else 0.0

    worst = asyncio.run(main())
    pass
    assert worst < 0.3, f"save_async 阻塞了事件循环 {worst * 1000:.0f}ms"


def test_save_async_is_safe_to_await_repeatedly(store):
    s = store.create(title="t", project="")
    s["messages"].append({"role": "user", "content": "a"})

    async def main() -> None:
        await store.save_async(s)
        await store.save_async(s)
        s["messages"].append({"role": "assistant", "content": "b"})
        await store.save_async(s)

    asyncio.run(main())
    back = store.get(s["id"])
    assert [m["content"] for m in back["messages"]] == ["a", "b"]
