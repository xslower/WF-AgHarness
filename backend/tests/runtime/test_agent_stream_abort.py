from __future__ import annotations

import asyncio
from typing import AsyncIterator

import pytest

import app.agent.stream as agent_stream


class _Chunk:
    def __init__(self, type: str, text: str = "", **kw):
        self.type = type
        self.text = text
        for k, v in kw.items():
            setattr(self, k, v)


class _HangingGateway:

    def __init__(self):
        self.closed = False

    async def chat_stream(self, *a, **kw) -> AsyncIterator[_Chunk]:
        try:
            await asyncio.sleep(3600)
            yield _Chunk("text", "")
        finally:
            self.closed = True


class _SlowGateway:

    def __init__(self, pieces=("第一段", "第二段")):
        self.pieces = pieces

    async def chat_stream(self, *a, **kw) -> AsyncIterator[_Chunk]:
        for p in self.pieces:
            yield _Chunk("text", p)
        await asyncio.sleep(3600)


class _FakeRunner:

    def __init__(self, gateway):
        self.gateway = gateway


async def _run(runner, abort_event=None, stop=None, timeout=2.0):
    async def _emit(_ev):
        return None

    return await asyncio.wait_for(
        agent_stream.consume_stream(
            runner, [], [], "parent", "sid", _emit,
            stop_check=stop, abort_event=abort_event,
        ),
        timeout=timeout,
    )


def test_首字未到时中止立即生效():
    async def main():
        gw = _HangingGateway()
        abort = asyncio.Event()
        runner = _FakeRunner(gw)

        async def trigger():
            await asyncio.sleep(0.05)
            abort.set()

        task = asyncio.gather(_run(runner, abort_event=abort), trigger())
        res = (await task)[0]
        assert res.text == "" and res.reason == "" and res.calls == []
        assert res.usage is None
        assert res.status == "aborted", "中止必须被标成 aborted，不能混成一段空回复"
        assert gw.closed, "中止后上游流应被关闭（别让 HTTP 连接挂着）"

    asyncio.run(main())


def test_已收到的部分保留后再停():
    async def main():
        gw = _SlowGateway()
        abort = asyncio.Event()
        runner = _FakeRunner(gw)

        async def trigger():
            await asyncio.sleep(0.1)
            abort.set()

        task = asyncio.gather(_run(runner, abort_event=abort), trigger())
        text, *_ = (await task)[0]
        assert text == "第一段第二段"

    asyncio.run(main())


def test_不传中止事件时行为不变():
    async def main():
        gw = _SlowGateway(pieces=("a", "b", "c"))
        runner = _FakeRunner(gw)

        pass
        state = {"n": 0}

        def stop():
            state["n"] += 1
            return state["n"] > 3

        text, *_ = await _run(runner, stop=stop)
        assert text == "abc"

    asyncio.run(main())


def test_stop_check_在首字前就为真时直接不读流():
    async def main():
        gw = _HangingGateway()
        runner = _FakeRunner(gw)
        res = await _run(runner, stop=lambda: True)
        assert (res.text, res.reason, res.calls, res.usage) == ("", "", [], None)
        assert res.status == "aborted"

    asyncio.run(main())


def test_中止事件的等待任务不会泄漏():
    async def main():
        gw = _HangingGateway()
        abort = asyncio.Event()
        runner = _FakeRunner(gw)
        before = len(asyncio.all_tasks())
        await asyncio.gather(
            _run(runner, abort_event=abort),
            asyncio.create_task(_set_soon(abort)),
        )
        await asyncio.sleep(0.05)
        after = len(asyncio.all_tasks())
        assert after <= before + 1, f"任务泄漏：{before} → {after}"

    async def _set_soon(ev):
        await asyncio.sleep(0.05)
        ev.set()

    asyncio.run(main())
