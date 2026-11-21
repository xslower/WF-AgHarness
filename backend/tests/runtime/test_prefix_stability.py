from __future__ import annotations

import asyncio

from app.agent.runner import AgentRunner
from app.agent.plan import PLAN_MODE_SYSTEM_PROMPT
from app.tools import ToolRegistry


def _runner() -> AgentRunner:
    return AgentRunner(gateway=None, registry=ToolRegistry())


async def _prepare(runner: AgentRunner, messages: list[dict], project_context: str,
                   plan_mode: str):
    async def emit(_ev):
        return None

    return await runner._prepare_turn(
        messages, "/tmp", emit, 0, "sid", runner._profile(),
        project_context, plan_mode, [], lambda: False)


def test_计划状态切换不改前缀():
    async def main():
        runner = _runner()
        history = [{"role": "user", "content": "原始问题"}]
        systems = []
        for mode in ("on", "executing", "off", "on"):
            _ctx, msgs, _schemas = await _prepare(
                runner, list(history), "[项目记忆] 固定内容", mode)
            systems.append(msgs[0]["content"])
        assert len(set(systems)) == 1
        assert "计划" in systems[0]

    asyncio.run(main())


def test_项目记忆变化只影响尾部():
    async def main():
        runner = _runner()
        history = [{"role": "user", "content": "原始问题"}]

        _c1, first, _s1 = await _prepare(
            runner, list(history), "[项目记忆] 版本 A", "on")
        _c2, second, _s2 = await _prepare(
            runner, list(history), "[项目记忆] 版本 B（新增一条）", "on")

        pass
        assert first[:-1] == second[:-1]
        pass
        assert first[-1] == {"role": "system", "content": "[项目记忆] 版本 A"}
        assert second[-1]["role"] == "system"
        assert "版本 B" in second[-1]["content"]
        pass
        assert "[项目记忆]" not in first[0]["content"]

    asyncio.run(main())


def test_没有项目上下文时不追加尾部消息():
    async def main():
        runner = _runner()
        history = [{"role": "user", "content": "原始问题"}]
        _ctx, msgs, _schemas = await _prepare(runner, list(history), "", "off")
        assert len(msgs) == 2
        assert msgs[0]["role"] == "system"
        assert msgs[1] == history[0]

    asyncio.run(main())


def test_恒定文本不声称本轮只读():
    assert "本轮你处于只读模式" not in PLAN_MODE_SYSTEM_PROMPT
    assert "plan_blocked" in PLAN_MODE_SYSTEM_PROMPT
    assert "不要从这段话推断本轮是否被拦" in PLAN_MODE_SYSTEM_PROMPT
