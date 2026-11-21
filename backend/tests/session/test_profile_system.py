from __future__ import annotations

import asyncio

from app.agent.profiles import build_profile_registry
from app.agent.profiles.default import SYSTEM_PROMPT
from app.agent.runner import AgentRunner
from app.provider.gateway import Chunk
from app.tools.builtin import build_tools as build_registry


class _GW:
    def __init__(self) -> None:
        self.messages: list[dict] = []

    async def chat_stream(self, messages, tools=None, effort="medium",
                          spec="", session_id=""):
        self.messages = list(messages)
        yield Chunk(type="text", text="ok")


def _run(**kwargs) -> list[dict]:
    gw = _GW()

    async def go():
        runner = AgentRunner(gw, build_registry(),
                             profiles=build_profile_registry())
        async for _msg in runner.run([{"role": "user", "content": "问"}], ".",
                                     _emit, **kwargs):
            pass

    asyncio.run(go())
    return gw.messages


async def _emit(ev):
    return None


def _system_of(messages: list[dict]) -> str:
    return next(m["content"] for m in messages if m["role"] == "system")


def test_run_applies_append_override():
    from app.agent.profile import SystemOverride

    msgs = _run(system_override=SystemOverride(mode="append", text="只引用条款号。"))
    system = _system_of(msgs)
    assert system.startswith(SYSTEM_PROMPT[:50])
    assert "只引用条款号。" in system
    assert SYSTEM_PROMPT.strip() in system


def test_run_applies_replace_override():
    from app.agent.profile import SystemOverride

    msgs = _run(system_override=SystemOverride(mode="replace", text="你只做检索。"))
    assert _system_of(msgs).startswith("你只做检索。")


def test_run_without_override_keeps_profile_prompt():
    assert _system_of(_run()).startswith(SYSTEM_PROMPT[:50])


def test_subagent_closing_rule_survives_replace():
    from app.agent.profile import SystemOverride
    from app.agent.prompt import SUBAGENT_CLOSING_RULE

    msgs = _run(depth=1, session_id="sub_x",
                system_override=SystemOverride(mode="replace", text="只查错别字。"))
    system = _system_of(msgs)
    assert system.startswith("只查错别字。")
    assert SUBAGENT_CLOSING_RULE in system
