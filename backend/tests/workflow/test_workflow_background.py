from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from app.tools.builtin.workflow_edit import WORKFLOW_ACTIONS, workflow_cmd
from app.workflow import WorkflowEngine


class Ctx:

    def __init__(self, wait=None, start=None):
        self.workflow_start = start
        self.workflow_wait = wait
        self.cwd = "/tmp"
        self.suggested: list = []

    def suggest_tools(self, schemas):
        self.suggested.extend(schemas)


async def call(ctx, **kw):
    return await workflow_cmd(ctx, **kw)


pass

def test_wait_is_a_first_class_action():
    assert "wait" in WORKFLOW_ACTIONS
    pass
    assert list(WORKFLOW_ACTIONS).count("wait") == 1


def test_wait_needs_id():
    async def go():
        return await call(Ctx(), action="wait")
    assert "action=wait 需要 id" in asyncio.run(go())


def test_wait_without_callback_is_readable():
    async def go():
        return await call(Ctx(), action="wait", id="r1")
    assert "等待运行不可用" in asyncio.run(go())


def test_wait_forwards_timeout_and_caps_it():
    seen = []

    async def wait(rid, t, detail=False):
        seen.append((rid, t))
        return json.dumps({"run_id": rid, "status": "running"})

    ctx = Ctx(wait=wait)

    async def go(**kw):
        return await call(ctx, action="wait", id="r1", **kw)

    asyncio.run(go())
    asyncio.run(go(timeout=0))
    asyncio.run(go(timeout=-5))
    asyncio.run(go(timeout=99999))
    asyncio.run(go(timeout=7))
    from app.provider.spec import (SUBAGENT_WAIT_TIMEOUT_SEC,
                                   SUBAGENT_WAIT_TIMEOUT_MAX_SEC)
    assert [t for _, t in seen] == [SUBAGENT_WAIT_TIMEOUT_SEC,
                                    SUBAGENT_WAIT_TIMEOUT_SEC,
                                    SUBAGENT_WAIT_TIMEOUT_SEC,
                                    SUBAGENT_WAIT_TIMEOUT_MAX_SEC, 7.0]
    assert {r for r, _ in seen} == {"r1"}


pass

def test_run_is_always_background():
    seen = {}

    async def start(name, inp, mode, start_node, par):
        seen.update(name=name, mode=mode, start_node=start_node, par=par)
        return json.dumps({"run_id": "r9", "status": "running"})

    ctx = Ctx(start=start)
    out = asyncio.run(call(ctx, action="run", name="g"))
    assert json.loads(out)["run_id"] == "r9"
    assert seen == {"name": "g", "mode": "deny",
                    "start_node": "", "par": ""}


pass

class _Gw:

    config = SimpleNamespace(providers=[], settings=SimpleNamespace(policy="yolo"))

    async def chat_stream(self, messages, **kw):
        from app.provider.gateway import Chunk
        yield Chunk(type="text", text="ok")


class _Registry:
    schemas: list = []

    async def execute(self, name, args, ctx):
        return f"{name} 结果"


def _engine(tmp_path):
    e = WorkflowEngine(gateway=_Gw(), registry=_Registry(),
                       workspace=str(tmp_path), workflows_dir=tmp_path / "wf")
    return e


@pytest.fixture
def eng(tmp_path):
    e = _engine(tmp_path)
    e.save({"name": "g", "nodes": [
        {"id": "s1", "type": "llm", "prompt": "说句话", "next": "w1"},
        {"id": "w1", "type": "write", "path": "out/r.md", "content": "${s1}"}]})
    return e


def test_start_for_returns_before_finishing(eng):
    ctx = Ctx()

    async def start(name, inp, mode, start, par):
        rec = eng.start_definition(eng.get(name), inp, human_mode=mode)
        return json.dumps({"run_id": rec.id, "status": rec.status})

    async def wait(rid, t, detail=False):
        data = await eng.wait_run(rid, t)
        return json.dumps(data)

    ctx.workflow_start = start
    ctx.workflow_wait = wait

    async def go():
        started = json.loads(await call(ctx, action="run", name="g"))
        done = json.loads(await call(ctx, action="wait", id=started["run_id"]))
        return started, done

    started, done = asyncio.run(go())
    assert started["status"] in ("running", "done")
    assert done["status"] == "done" and done["timed_out"] is False
    pass
    assert [n["id"] for n in done["nodes"]] == ["s1", "w1"]
    assert done["final_chars"] > 0


def test_wait_timeout_does_not_stop_the_run(eng):

    async def go():
        rec = eng.start_definition(eng.get("g"), {})
        first = await eng.wait_run(rec.id, 0.001)
        second = await eng.wait_run(rec.id, 30)
        return first, second

    first, second = asyncio.run(go())
    assert second["status"] == "done"
    pass
    assert first["timed_out"] in (True, False)
    assert second["nodes"], "运行被 wait 超时取消了"


def test_start_for_reports_bad_graph_immediately(eng):
    eng.save({"name": "bad", "nodes": [
        {"id": "s1", "type": "llm", "prompt": "${不存在的变量}"}]})

    async def start(name, inp, mode, start, par):
        try:
            rec = eng.start_definition(eng.get(name), inp, human_mode=mode)
        except Exception as e:
            return json.dumps({"error": f"工作流启动失败: {e}"}, ensure_ascii=False)
        return json.dumps({"run_id": rec.id})

    ctx = Ctx()
    ctx.workflow_start = start
    out = asyncio.run(call(ctx, action="run", name="bad"))
    assert "启动失败" in json.loads(out)["error"]


def test_wait_unknown_run_is_readable(eng):
    async def go():
        return await eng.wait_run("nope", 1)
    with pytest.raises(Exception) as ei:
        asyncio.run(go())
    assert "运行不存在" in str(ei.value)


def test_router_wait_for_resolves_run_across_projects(tmp_path):
    from app.workflow import WorkflowRouter

    a = _engine(tmp_path / "a")
    a.save({"name": "g", "nodes": [{"id": "s1", "type": "llm", "prompt": "hi"}]})
    r = WorkflowRouter(nodes=None)
    r._cache["/proj"] = a

    async def go():
        rec = await r.start_for("g", {}, "/proj")
        return await r.wait_for(rec.id, 30)

    data = asyncio.run(go())
    assert data["status"] == "done" and data["run_id"]


def test_router_wait_for_unknown_run_is_readable(tmp_path):
    from app.workflow import WorkflowRouter

    r = WorkflowRouter(nodes=None)
    with pytest.raises(Exception) as ei:
        asyncio.run(r.wait_for("nope", 1))
    assert "运行不存在" in str(ei.value)
