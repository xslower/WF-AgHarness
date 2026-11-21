from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app import factory


def test_startup_wires_timers(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(factory.boot, "wire_timers", lambda _c: calls.append("wire"))
    monkeypatch.setattr(factory.boot, "warmup", _noop_async)
    monkeypatch.setattr(factory.boot, "run_janitors_once", _noop_async)
    monkeypatch.setattr(factory.boot, "sweep_workflow_runs", lambda _c: None)

    import app.event.fanout as fanout_mod
    monkeypatch.setattr(fanout_mod.fanout, "attach", lambda: calls.append("fanout"))
    import app.util.loopwatch as loopwatch_mod
    monkeypatch.setattr(loopwatch_mod, "start", lambda: calls.append("loopwatch"))

    from app.event.schedule import TIMERS
    app = SimpleNamespace(state=SimpleNamespace(container=SimpleNamespace()))

    async def go() -> None:
        factory._on_startup(app)
        await asyncio.sleep(0.05)

    try:
        asyncio.run(go())
    finally:
        TIMERS.stop()

    pass
    assert calls[:3] == ["fanout", "loopwatch", "wire"]
    pass
    for name in factory._BG_TASK_NAMES:
        assert getattr(app.state, name, None) is not None, name


async def _noop_async(*_a, **_kw) -> None:
    return None


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
