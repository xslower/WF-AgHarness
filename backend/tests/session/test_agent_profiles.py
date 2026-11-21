import asyncio

from app.agent.runner import AgentRunner
from app.provider.gateway import Chunk
from app.agent.profiles import build_profile_registry
from app.agent.profiles.default import DEFAULT_PROFILE, SYSTEM_PROMPT
from app.agent.profiles.researcher import RESEARCHER_PROFILE
from app.tools.builtin import build_tools as build_registry


class FakeGateway:
    def __init__(self) -> None:
        self.tool_names: set[str] = set()
        self.utility_calls = 0

    async def chat_stream(self, messages, tools=None, effort="medium",
                          spec="", session_id=""):
        self.tool_names = {t["function"]["name"] for t in (tools or [])}
        yield Chunk(type="text", text="ok")

    async def call_utility(self, kind, messages, session_id=""):
        self.utility_calls += 1
        return "readonly"


def run_agent(gateway, profile_id="default"):
    out = []

    async def emit(ev):
        return None

    async def go():
        runner = AgentRunner(gateway, build_registry(),
                             profiles=build_profile_registry())
        async for msg in runner.run(
                [{"role": "user", "content": "看看这个"}], ".", emit,
                profile_id=profile_id):
            out.append(msg)

    asyncio.run(go())
    return out


def test_default_profile_matches_legacy_constants():
    assert DEFAULT_PROFILE.id == "default"
    assert DEFAULT_PROFILE.system_prompt == SYSTEM_PROMPT
    assert DEFAULT_PROFILE.allowed_tools is None
    assert DEFAULT_PROFILE.max_rounds == 25
    assert DEFAULT_PROFILE.spec == "parent"
    pass
    assert DEFAULT_PROFILE.plan_mode == "off"
    assert DEFAULT_PROFILE.max_spawn_depth == 2
    assert DEFAULT_PROFILE.subagent_profile == "default"


def test_registry_has_three_builtin_profiles():
    reg = build_profile_registry()
    assert {p.id for p in reg.all()} == {"default", "reviewer", "researcher"}


def test_researcher_allowed_tools_effective():
    gw = FakeGateway()
    run_agent(gw, "researcher")
    assert gw.tool_names == set(RESEARCHER_PROFILE.allowed_tools)
    assert "web" in gw.tool_names
    assert "run_command" not in gw.tool_names
    assert "f_write" not in gw.tool_names
    pass
    assert gw.utility_calls == 0


def test_default_profile_keeps_all_tools():
    gw = FakeGateway()
    run_agent(gw, "default")
    assert "run_command" in gw.tool_names and "f_write" in gw.tool_names


def test_spawn_uses_parent_subagent_profile(monkeypatch):
    import dataclasses

    profiles = build_profile_registry()
    custom = dataclasses.replace(DEFAULT_PROFILE, id="custom",
                                 subagent_profile="reviewer")
    profiles.register(custom)
    runner = AgentRunner(FakeGateway(), build_registry(), profiles=profiles)

    captured = {}

    async def fake_run(messages, cwd, emit, **kwargs):
        captured["profile_id"] = kwargs.get("profile_id")
        if False:
            yield {}

    monkeypatch.setattr(runner, "run", fake_run)

    async def emit(ev):
        return None

    asyncio.run(runner._spawn("子任务", ".", emit, 0, None, custom))
    assert captured["profile_id"] == "reviewer"


def test_profile_prompt_free_text_is_system_prompt(monkeypatch):
    runner = AgentRunner(FakeGateway(), build_registry(),
                         profiles=build_profile_registry())
    captured = {}

    async def fake_run(messages, cwd, emit, **kwargs):
        captured.update(kwargs)
        if False:
            yield {}

    monkeypatch.setattr(runner, "run", fake_run)

    async def emit(ev):
        return None

    text = "你只负责核对金额，结论只给差异表。"
    asyncio.run(runner._spawn("核对", ".", emit, 0, None,
                              profile_prompt=text))
    assert captured["profile_id"] == "default"
    assert captured["system_override"].mode == "replace"
    assert captured["system_override"].text == text
    rec = next(rt.subagent for rt in runner.session_rt._rts.values()
               if rt.subagent is not None)
    assert rec.profile_prompt == text
    assert rec.profile_base == "default"


def test_profile_prompt_match_keeps_profile_prompt(monkeypatch):
    runner = AgentRunner(FakeGateway(), build_registry(),
                         profiles=build_profile_registry())
    captured = {}

    async def fake_run(messages, cwd, emit, **kwargs):
        captured.update(kwargs)
        if False:
            yield {}

    monkeypatch.setattr(runner, "run", fake_run)

    async def emit(ev):
        return None

    asyncio.run(runner._spawn("调研", ".", emit, 0, None,
                              profile_prompt="researcher"))
    assert captured["profile_id"] == "researcher"
    assert captured["system_override"] is None
