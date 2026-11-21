from __future__ import annotations

import asyncio
import inspect
import json

from app.agent.subagents import SubAgentRecord
from app.tools.builtin.fs import read as fs_read


def test_grep_is_async_and_offloads_slow_work():
    assert inspect.iscoroutinefunction(fs_read.grep)
    assert inspect.isfunction(fs_read.grep_sync)


def test_grep_no_longer_blocks_event_loop(tmp_path):
    (tmp_path / "a.txt").write_text("NEEDLE\n", encoding="utf-8")
    calls = {}

    def slow_run(*args, **kwargs):
        import time
        time.sleep(0.15)
        class R:
            returncode = 0
            stdout = "a.txt:1:NEEDLE"
            stderr = ""
        return R()

    class _Ctx:
        cwd = str(tmp_path)

    orig_which, orig_run = fs_read.shutil.which, fs_read.subprocess.run
    fs_read.shutil.which = lambda _n: "/usr/bin/rg"
    fs_read.subprocess.run = slow_run

    async def go():
        ticks = [0]
        async def beat():
            for _ in range(20):
                await asyncio.sleep(0.01)
                ticks[0] += 1
        t = asyncio.create_task(beat())
        out = await fs_read.grep(["NEEDLE"], _Ctx(), path=".", context=0)
        await t
        calls["ticks"] = ticks[0]
        return out

    try:
        out = asyncio.run(go())
    finally:
        fs_read.shutil.which, fs_read.subprocess.run = orig_which, orig_run
    assert "NEEDLE" in out
    assert calls["ticks"] >= 10, "事件循环被 grep 卡住了"


def test_transcript_writes_are_off_loop(tmp_path):
    rec = SubAgentRecord(
        id="sa_noblock", parent_id="p", project=str(tmp_path),
        task="任务", child_session_id="sub_noblock")
    for i in range(50):
        rec.append_event({"type": "tool_output", "text": f"line {i}"})
    rec.finish("done", "结论")
    lines = rec.transcript_path.read_text("utf-8").splitlines()
    assert len(lines) == 50
    assert json.loads(lines[0])["event"]["text"] == "line 0"


def test_transcript_dir_is_resolved_once(tmp_path):
    rec = SubAgentRecord(
        id="sa_cached", parent_id="p", project=str(tmp_path),
        task="任务", child_session_id="sub_cached")
    first = rec.dir
    for _ in range(20):
        rec.append_event({"type": "tool_output", "text": "x"})
    assert rec.dir is first


pass
pass
pass
pass
pass
pass
pass
pass
pass

import asyncio as _aio
import inspect as _inspect
import threading as _threading
import time as _time

from app.tools.registry import ToolContext as _ToolContext, ToolRegistry as _Reg


def _fresh_registry() -> _Reg:
    return _Reg()


def test_sync_tool_runs_off_event_loop_thread(tmp_path):
    reg = _fresh_registry()
    seen = {}

    def slow(ctx=None):
        seen["tid"] = _threading.get_ident()
        return "done"

    reg.register("slow", "d", {}, slow, [])

    async def go():
        seen["loop"] = _threading.get_ident()
        return await reg.execute("slow", {}, _ToolContext(str(tmp_path)))

    assert _aio.run(go()) == "done"
    assert seen["tid"] != seen["loop"], "同步工具仍在事件循环线程上跑"


def test_slow_sync_tool_does_not_stall_the_loop(tmp_path):
    reg = _fresh_registry()

    def slow(ctx=None):
        _time.sleep(0.3)
        return "done"

    reg.register("slow", "d", {}, slow, [])

    async def go():
        ticks = 0

        async def beat():
            nonlocal ticks
            while True:
                await _aio.sleep(0.01)
                ticks += 1

        t = _aio.create_task(beat())
        try:
            await reg.execute("slow", {}, _ToolContext(str(tmp_path)))
        finally:
            t.cancel()
        return ticks

    ticks = _aio.run(go())
    pass
    assert ticks >= 15, f"事件循环被同步工具阻塞：只推进了 {ticks} 次"


def test_async_tool_stays_on_event_loop_thread(tmp_path):
    reg = _fresh_registry()
    seen = {}

    async def atool(ctx=None):
        seen["tid"] = _threading.get_ident()
        await _aio.sleep(0)
        return {"ok": True}

    reg.register("atool", "d", {}, atool, [])

    async def go():
        seen["loop"] = _threading.get_ident()
        return await reg.execute("atool", {}, _ToolContext(str(tmp_path)))

    out = _aio.run(go())
    assert out == '{"ok": true}'
    assert seen["tid"] == seen["loop"]


def test_sync_tool_returning_awaitable_is_awaited(tmp_path):
    reg = _fresh_registry()

    def weird(ctx=None):
        async def inner():
            return {"late": True}
        return inner()

    reg.register("weird", "d", {}, weird, [])

    async def go():
        return await reg.execute("weird", {}, _ToolContext(str(tmp_path)))

    assert _aio.run(go()) == '{"late": true}'


def test_tool_contextvars_reach_the_worker_thread(tmp_path):
    from app.project import scope as _scope

    reg = _fresh_registry()
    seen = {}

    def read_cvar(ctx=None):
        seen["cur"] = _scope.current_project()
        return "ok"

    reg.register("cvar", "d", {}, read_cvar, [])

    async def go():
        _scope.set_current_project(str(tmp_path))
        return await reg.execute("cvar", {}, _ToolContext(str(tmp_path)))

    assert _aio.run(go()) == "ok"
    assert seen["cur"] == str(tmp_path), "contextvar 没被复制进线程池（应使用 asyncio.to_thread）"


def test_sync_tool_exception_still_becomes_tool_error(tmp_path):
    reg = _fresh_registry()

    def boom(ctx=None):
        raise ValueError("炸了")

    reg.register("boom", "d", {}, boom, [])

    async def go():
        return await reg.execute("boom", {}, _ToolContext(str(tmp_path)))

    out = _aio.run(go())
    assert "ValueError" in out and "炸了" in out


def test_todo_tool_is_async_so_it_can_push_stream_frames():
    from app.tools.builtin import todo as todo_mod

    assert _inspect.iscoroutinefunction(todo_mod.todo)
    assert _inspect.iscoroutinefunction(todo_mod.todo_write)


async def test_todo_write_emits_stream_frame(tmp_path):
    from app.tools.builtin import todo as todo_mod

    frames = []

    async def emit(ev):
        frames.append(ev)

    ctx = _ToolContext(str(tmp_path))
    ctx.session_id = "s_test_todo"
    ctx.emit_stream = emit
    try:
        out = await todo_mod.todo(ctx, action="write",
                                  todos=[{"content": "写测试", "status": "done"}])
    finally:
        todo_mod.clear("s_test_todo")
    assert "写测试" in out
    assert frames and frames[0]["type"] == "todo"
    assert frames[0]["todos"][0]["content"] == "写测试"
