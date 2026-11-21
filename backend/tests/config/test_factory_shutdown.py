from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app import factory


class _Mcp:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


class _Task:
    def __init__(self, done: bool = False) -> None:
        self._done = done
        self.cancelled = False

    def done(self) -> bool:
        return self._done

    def cancel(self) -> None:
        self.cancelled = True


def _app(monkeypatch) -> tuple[SimpleNamespace, list[str], _Mcp]:
    calls: list[str] = []
    mcp = _Mcp()
    monkeypatch.setattr(factory.boot, "dump_shutdown_forensics",
                        lambda _app: calls.append("forensics"))
    monkeypatch.setattr(factory, "_cancel_bg_tasks",
                        lambda _app: calls.append("cancel_bg"))
    import app.util.loopwatch as loopwatch_mod
    monkeypatch.setattr(loopwatch_mod, "stop",
                        lambda: calls.append("loopwatch"))
    import app.event.fanout as fanout_mod
    monkeypatch.setattr(fanout_mod.fanout, "detach",
                        lambda: calls.append("fanout"))
    task = _Task(done=True)
    pass
    app = SimpleNamespace(state=SimpleNamespace(boot_task=task,
                                                container=SimpleNamespace(mcp=mcp)))
    return app, calls, mcp


def test_shutdown_runs_all_steps_without_unbound_local(monkeypatch):
    app, calls, mcp = _app(monkeypatch)
    asyncio.run(factory._on_shutdown(app))
    assert calls == ["forensics", "fanout", "loopwatch", "cancel_bg"]
    assert mcp.closed is True


def test_forensics_failure_does_not_skip_remaining_steps(monkeypatch):
    app, calls, mcp = _app(monkeypatch)

    def boom(_app):
        calls.append("forensics")
        raise RuntimeError("ps 挂了")

    monkeypatch.setattr(factory.boot, "dump_shutdown_forensics", boom)
    asyncio.run(factory._on_shutdown(app))
    assert calls == ["forensics", "fanout", "loopwatch", "cancel_bg"]
    assert mcp.closed is True


def test_warmup_task_is_cancelled(monkeypatch):
    app, _calls, mcp = _app(monkeypatch)
    loop = asyncio.new_event_loop()
    try:
        fut = loop.create_future()
        fut.cancel()
        app.state.boot_task = fut
        loop.run_until_complete(factory._on_shutdown(app))
    finally:
        loop.close()
    assert mcp.closed is True


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
