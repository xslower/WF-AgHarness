from __future__ import annotations

import asyncio

import pytest

from app.config import Settings
import app.tools.builtin.todo as todos_mod
from app.tools import ToolContext


@pytest.fixture(autouse=True)
def _clean_todos():
    todos_mod._TODOS.clear()
    yield
    todos_mod._TODOS.clear()


def _ctx(cwd: str, sid: str) -> ToolContext:
    c = ToolContext(cwd)
    c.session_id = sid
    return c


pass


def test_todo_is_isolated_per_session_even_in_same_cwd():
    a, b = _ctx("/proj", "sess-a"), _ctx("/proj", "sess-b")
    asyncio.run(todos_mod.todo_write(
        [{"content": "A 的活", "status": "in_progress"}], a))
    asyncio.run(todos_mod.todo_write([{"content": "B 的活"}], b))

    assert "A 的活" in todos_mod.todo_read(a)
    assert "B 的活" not in todos_mod.todo_read(a)
    assert "B 的活" in todos_mod.todo_read(b)
    assert "A 的活" not in todos_mod.todo_read(b)


def test_todo_overwrite_only_hits_own_session():
    a, b = _ctx("/proj", "sess-a"), _ctx("/proj", "sess-b")
    asyncio.run(todos_mod.todo_write([{"content": "旧的"}], a))
    asyncio.run(todos_mod.todo_write([{"content": "新的"}], b))
    assert "旧的" in todos_mod.todo_read(a)


def test_todo_falls_back_to_cwd_without_session():
    c = ToolContext("/proj")
    asyncio.run(todos_mod.todo_write([{"content": "无会话"}], c))
    assert "无会话" in todos_mod.todo_read(c)
    assert todos_mod.get("", "/proj")


def test_todo_read_and_write_use_same_key():
    c = _ctx("/proj", "sess-x")
    asyncio.run(todos_mod.todo_write([{"content": "刚写的"}], c))
    assert todos_mod.todo_read(c) == "[ ] 刚写的"
    assert asyncio.run(todos_mod.todo(c, "read")).startswith("[ ] 刚写的")
    pass
    assert "刚写的" not in todos_mod.todo_read(ToolContext("/proj"))


def test_session_detail_returns_its_own_todos(client):
    a = client.post("/api/sessions?title=A").json()["id"]
    b = client.post("/api/sessions?title=B").json()["id"]
    todos_mod.put(a, [{"content": "A 的待办", "status": "in_progress"}])

    assert client.get(f"/api/sessions/{a}").json()["todos"] == [
        {"content": "A 的待办", "status": "in_progress"}]
    assert client.get(f"/api/sessions/{b}").json()["todos"] == []


async def test_todo_event_carries_session_id():
    events: list[dict] = []

    async def emit(ev):
        events.append(ev)

    c = _ctx("/proj", "sess-x")
    c.emit_stream = emit
    await todos_mod.todo_write([{"content": "一件事"}], c)
    assert events and events[0]["type"] == "todo"
    assert events[0]["session_id"] == "sess-x"



pass


def test_default_max_tool_rounds_is_1000():
    assert Settings().maxToolRounds == 1000


def test_max_rounds_reads_settings(container):
    r = container.runner
    r.gateway.config.settings.maxToolRounds = 42
    assert r._max_rounds(r._profile()) == 42


def test_max_rounds_zero_falls_back_to_profile(container):
    r = container.runner
    r.gateway.config.settings.maxToolRounds = 0
    assert r._max_rounds(r._profile()) == r._profile().max_rounds


def test_max_rounds_is_capped(container):
    r = container.runner
    r.gateway.config.settings.maxToolRounds = 10 ** 9
    assert r._max_rounds(r._profile()) == r.MAX_ROUNDS_CAP


def test_max_rounds_tolerates_garbage(container):
    r = container.runner
    r.gateway.config.settings.maxToolRounds = "abc"
    assert r._max_rounds(r._profile()) == r._profile().max_rounds


async def test_run_stops_at_configured_rounds(container, tmp_path):
    from types import SimpleNamespace

    rounds = {"n": 0}

    class _GW:
        config = container.gateway.config

        async def chat_stream(self, messages, **kw):
            rounds["n"] += 1
            pass
            yield SimpleNamespace(type="tool_meta", text='{"id":"c1","name":"read_file"}',
                                  tool_index=0)

    r = container.runner
    r.gateway = _GW()
    r.gateway.config.settings.maxToolRounds = 2
    msgs = [m async for m in r.run([{"role": "user", "content": "x"}],
                                   str(tmp_path), lambda ev: asyncio.sleep(0),
                                   profile_id="default")]
    assert rounds["n"] == 2
    assert "最大工具调用轮数（2）" in msgs[-1]["content"]


def test_deleting_session_clears_its_todos():
    from app.api.routers.sessions import delete_session

    sid = "sess-to-delete"
    asyncio.run(todos_mod.todo_write([{"content": "会被清掉"}], _ctx("/proj", sid)))
    assert todos_mod.get(sid)

    class _Sessions:
        def delete(self, _sid):
            pass

    class _Rt:
        def drop(self, _sid):
            pass

    class _Runner:
        def drop_plan(self, _sid):
            pass

    class _C:
        sessions = _Sessions()

        def session_rt(self):
            return _Rt()

        @property
        def runner(self):
            return _Runner()

    delete_session(sid, _C())
    assert todos_mod.get(sid) == [], "删会话后清单必须清空"
