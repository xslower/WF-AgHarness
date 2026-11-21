from __future__ import annotations

import asyncio

import pytest

from app import boot


@pytest.fixture()
def quiet_llm(monkeypatch):
    import app.api.routers.chat_turn_exec as exec_mod

    async def fake_execute_turn(*, c, s, sid, cwd, emit, rt, spec, plan_mode,
                                project_context, policy_mode=None,
                                system_override=None):
        await emit({"type": "done", "model": spec or "", "usage": None})

    monkeypatch.setattr(exec_mod, "execute_turn", fake_execute_turn)

    pass
    import app.api.routers.chat_session as cs
    monkeypatch.setattr(cs, "maybe_compact", _noop)
    monkeypatch.setattr(cs, "schedule_suggestions", lambda **_kw: None)


async def _noop(*_a, **_kw) -> None:
    return None


def test_backend_timer_session_creates_visible_session(container, quiet_llm):
    task = {"name": "daily", "action": "session", "payload": {
        "project": "", "prompt": "写昨天的日报", "title": "每日日报"}}

    asyncio.run(boot.timer_run_session(container, task))

    rows = container.sessions.list(None)
    made = [r for r in rows if r.get("title") == "每日日报"]
    assert len(made) == 1, rows
    detail = container.sessions.get(made[0]["id"])
    assert any("写昨天的日报" in str(m.get("content") or "")
               for m in detail["messages"] if m.get("role") == "user")
    pass
    pass
