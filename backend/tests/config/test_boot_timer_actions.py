from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app import boot


class _FakeTurn:

    made: list[dict] = []

    def __init__(self, c, s, sid, rt, emit):
        self.emit = emit
        _FakeTurn.made.append({"c": c, "s": s, "sid": sid, "rt": rt})

    async def handle(self, req: dict) -> None:
        _FakeTurn.made[-1]["req"] = req
        await self.emit({"type": "done", "model": "", "usage": None})


@pytest.fixture()
def fake_turn(monkeypatch):
    import app.api.routers.chat_session as cs
    _FakeTurn.made = []
    monkeypatch.setattr(cs, "SessionTurn", _FakeTurn)
    return _FakeTurn


def _container(**kw):
    created: list[dict] = []
    sessions = SimpleNamespace(
        create=lambda title, project="": (created.append(
            {"id": str(len(created) + 1), "title": title, "project": project})
            or created[-1]))
    rt = SimpleNamespace(emit=None, push_stream=lambda *_a: None, touch=lambda: None)
    return SimpleNamespace(
        sessions=sessions,
        session_rt=lambda: SimpleNamespace(get=lambda _sid: rt),
        **kw), created


def test_timer_run_session_creates_real_session(fake_turn):
    c, created = _container()
    task = {"name": "daily", "action": "session", "payload": {
        "project": "content/foo", "prompt": "写日报", "title": "每日日报"}}
    asyncio.run(boot.timer_run_session(c, task))

    assert created == [{"id": "1", "title": "每日日报", "project": "content/foo"}]
    req = fake_turn.made[0]["req"]
    assert req["content"] == "写日报"
    assert req["plan"] is False


def test_timer_run_session_skips_without_prompt(fake_turn):
    c, created = _container()
    asyncio.run(boot.timer_run_session(c, {"name": "x", "payload": {"project": "p"}}))
    assert created == [] and fake_turn.made == []


def test_timer_run_workflow_uses_auto_approve():
    calls: list[dict] = []
    engine = SimpleNamespace(start=lambda *a, **kw: (calls.append({"a": a, **kw})
                                                     or SimpleNamespace(id="r1")))
    c = SimpleNamespace(wf_engine=lambda _p: engine)
    asyncio.run(boot.timer_run_workflow(c, {"name": "wf", "payload": {
        "project": "content/foo", "workflow": "日报", "inputs": {"d": 1}}}))
    assert calls == [{"a": ("日报", {"d": 1}), "human_mode": "auto-approve"}]


def test_timer_run_workflow_skips_without_name():
    calls: list[dict] = []
    c = SimpleNamespace(wf_engine=lambda _p: SimpleNamespace(start=lambda *a, **k: calls.append(1)))
    asyncio.run(boot.timer_run_workflow(c, {"name": "x", "payload": {"project": "p"}}))
    assert calls == []


def test_wire_timers_registers_both_actions(tmp_path):
    from app.event.schedule import Timers

    c = SimpleNamespace()
    t = Timers()
    boot.wire_timers(c, t)
    assert t._actions.keys() == {"session", "workflow"}
