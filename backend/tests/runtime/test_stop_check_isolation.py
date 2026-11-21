from __future__ import annotations

import asyncio

from app.agent.runner import AgentRunner
from app.tools import ToolRegistry


def _runner() -> AgentRunner:
    return AgentRunner(gateway=None, registry=ToolRegistry())


async def _prepare(runner: AgentRunner, sid: str, stop):
    async def emit(_ev):
        return None

    ctx, _messages, _schemas = await runner._prepare_turn(
        [], "/tmp", emit, 1, sid, runner._profile(), "", "off", [], stop)
    await asyncio.sleep(0)
    return ctx.stop_check


def test_并发会话各拿自己的中止信号():
    async def main():
        runner = _runner()
        stop_a = lambda: False
        stop_b = lambda: True

        got_a, got_b = await asyncio.gather(
            _prepare(runner, "sid-a", stop_a),
            _prepare(runner, "sid-b", stop_b),
        )
        assert got_a is stop_a
        assert got_b is stop_b
        assert got_a is not got_b

    asyncio.run(main())


def test_实例上不再挂着_stop_check():
    runner = _runner()
    assert not hasattr(runner, "_stop_check")

    async def main():
        async def emit(_ev):
            return None

        await runner._prepare_turn([], "/tmp", emit, 1, "sid", runner._profile(),
                                   "", "off", [], lambda: False)
        assert not hasattr(runner, "_stop_check")

    asyncio.run(main())


def test_没传中止信号时为_None():
    async def main():
        runner = _runner()
        assert await _prepare(runner, "sid", None) is None

    asyncio.run(main())
