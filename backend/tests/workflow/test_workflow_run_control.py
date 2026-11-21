from __future__ import annotations

import asyncio
import json

import pytest

from app.workflow.nodes.registry import NodeRegistry, NodeSpec
from app.workflow import WorkflowEngine, WorkflowError


def slow_engine(tmp_path, sleep: float = 0.5):
    reg = NodeRegistry()
    done = []

    async def run_slow(node, ctx, vars):
        await asyncio.sleep(sleep)
        done.append(node["id"])
        return "慢节点完成", node.get("next")

    async def run_echo(node, ctx, vars):
        return ctx.sub(node.get("text", ""), vars), node.get("next")

    async def run_boom(node, ctx, vars):
        raise RuntimeError("故意失败")

    reg.register(NodeSpec(type="slow", label="slow", run=run_slow))
    reg.register(NodeSpec(type="echo", label="echo", run=run_echo))
    reg.register(NodeSpec(type="boom", label="boom", run=run_boom))
    eng = WorkflowEngine(workspace=str(tmp_path), workflows_dir=tmp_path / "wf",
                         nodes=reg)
    return eng, done


async def _wait_status(eng, rid, want=("done", "failed", "cancelled"), timeout=3.0):
    t0 = asyncio.get_running_loop().time()
    while asyncio.get_running_loop().time() - t0 < timeout:
        rec = eng.runs[rid]
        if rec.status in want:
            return rec
        await asyncio.sleep(0.02)
    return eng.runs[rid]


pass
async def test_cancel_running_workflow(tmp_path):
    eng, done = slow_engine(tmp_path, sleep=0.4)
    eng.save({"name": "c1", "nodes": [{"id": "s", "type": "slow"}]})
    rec = eng.start("c1")
    await asyncio.sleep(0.05)
    res = eng.cancel(rec.id)
    assert res == {"ok": True, "reason": "", "status": "cancelled"}
    assert rec.status == "cancelled" and rec.error == "用户中止"
    await asyncio.sleep(0.5)
    assert done == []


async def test_cancel_then_meta_on_disk_is_cancelled(tmp_path):
    eng, _ = slow_engine(tmp_path, sleep=0.4)
    eng.save({"name": "c2", "nodes": [{"id": "s", "type": "slow"}]})
    rec = eng.start("c2")
    await asyncio.sleep(0.05)
    eng.cancel(rec.id)
    meta = json.loads((eng.store.paths.run_dir(rec.id) / "meta.json").read_text("utf-8"))
    assert meta["status"] == "cancelled"


async def test_cancel_marks_running_nodes_cancelled(tmp_path):
    eng, _ = slow_engine(tmp_path, sleep=0.4)
    eng.save({"name": "c5", "nodes": [{"id": "s", "type": "slow"}]})
    rec = eng.start("c5")
    await asyncio.sleep(0.05)
    eng.cancel(rec.id)
    await asyncio.sleep(0.1)
    assert rec.node_states["s"]["status"] == "cancelled"


async def test_cancel_unknown_run_returns_error(tmp_path):
    eng, _ = slow_engine(tmp_path)
    res = eng.cancel("nope")
    assert res["ok"] is False and res["reason"] == "运行不存在"


async def test_cancel_finished_run_is_rejected(tmp_path):
    eng, _ = slow_engine(tmp_path, sleep=0)
    eng.save({"name": "c3", "nodes": [{"id": "e", "type": "echo", "text": "x"}]})
    rec = eng.start("c3")
    await _wait_status(eng, rec.id)
    res = eng.cancel(rec.id)
    assert res["ok"] is False and "已结束" in res["reason"]


async def test_cancel_does_not_touch_other_runs(tmp_path):
    eng, _ = slow_engine(tmp_path, sleep=0.3)
    eng.save({"name": "c4", "nodes": [{"id": "s", "type": "slow"}]})
    a = eng.start("c4")
    b = eng.start("c4")
    await asyncio.sleep(0.05)
    eng.cancel(a.id)
    await asyncio.sleep(0.4)
    assert a.status == "cancelled"
    assert b.status == "done", b.error


pass
async def test_resume_skips_successful_nodes(tmp_path):
    reg = NodeRegistry()
    calls: list[str] = []
    state = {"fail": True}

    async def run_a(node, ctx, vars):
        calls.append("a")
        return "A的输出", node.get("next")

    async def run_b(node, ctx, vars):
        calls.append("b")
        if state["fail"]:
            raise RuntimeError("第一次失败")
        return f"B收到={ctx.sub('${a}', vars)}", node.get("next")

    reg.register(NodeSpec(type="a", label="a", run=run_a))
    reg.register(NodeSpec(type="b", label="b", run=run_b))
    eng = WorkflowEngine(workspace=str(tmp_path), workflows_dir=tmp_path / "wf",
                         nodes=reg)
    eng.save({"name": "r1", "nodes": [
        {"id": "a", "type": "a", "next": "b"},
        {"id": "b", "type": "b", "next": ""}]})

    first = await eng.execute_sync("r1", {"x": 1})
    assert first.status == "failed" and calls == ["a", "b"]

    state["fail"] = False
    second = await eng.resume(first.id)
    assert second.status == "done", second.error
    assert calls == ["a", "b", "b"]
    assert second.node_states["b"]["output"] == "B收到=A的输出"


async def test_resume_keeps_original_inputs(tmp_path):
    reg = NodeRegistry()

    async def run_show(node, ctx, vars):
        return ctx.sub("${inputs.who}", vars), node.get("next")

    reg.register(NodeSpec(type="show", label="show", run=run_show))
    eng = WorkflowEngine(workspace=str(tmp_path), workflows_dir=tmp_path / "wf",
                         nodes=reg)
    eng.save({"name": "r2", "nodes": [{"id": "s", "type": "show"}]})
    first = await eng.execute_sync("r2", {"who": "用户A"})
    assert first.status == "done"
    second = await eng.resume(first.id)
    assert second.node_states["s"]["output"] == "用户A"


async def test_resume_unknown_run_or_workflow(tmp_path):
    eng, _ = slow_engine(tmp_path)
    with pytest.raises(WorkflowError, match="运行不存在"):
        await eng.resume("nope")


async def test_resume_can_start_from_given_node(tmp_path):
    eng, _ = slow_engine(tmp_path, sleep=0)
    eng.save({"name": "r3", "nodes": [
        {"id": "e", "type": "echo", "text": "E", "next": ""}]})
    base = await eng.execute_sync("r3", {})
    again = await eng.resume(base.id, start_node="e")
    assert again.node_states["e"]["output"] == "E"


pass
async def test_list_runs_newest_first_and_filter(tmp_path):
    eng, _ = slow_engine(tmp_path, sleep=0)
    eng.save({"name": "h1", "nodes": [{"id": "e", "type": "echo", "text": "1"}]})
    eng.save({"name": "h2", "nodes": [{"id": "e", "type": "echo", "text": "2"}]})
    await eng.execute_sync("h1", {})
    await asyncio.sleep(0.01)
    await eng.execute_sync("h2", {})

    items = eng.list_runs()
    assert [x["workflow"] for x in items] == ["h2", "h1"]
    assert items[0]["status"] == "done"
    assert "nodes" in items[0] and "e" in items[0]["nodes"]
    assert [x["workflow"] for x in eng.list_runs(workflow="h1")] == ["h1"]
    assert len(eng.list_runs(limit=1)) == 1


async def test_list_runs_reads_disk_after_restart(tmp_path):
    eng, _ = slow_engine(tmp_path, sleep=0)
    eng.save({"name": "h3", "nodes": [{"id": "e", "type": "echo", "text": "x"}]})
    rec = await eng.execute_sync("h3", {})

    fresh = WorkflowEngine(workspace=str(tmp_path), workflows_dir=tmp_path / "wf")
    items = fresh.list_runs()
    assert [x["id"] for x in items] == [rec.id]
    assert items[0]["status"] == "done"


pass
@pytest.fixture
def proj(tmp_path):
    p = tmp_path / "proj"
    p.mkdir()
    return str(p)


def test_run_history_endpoint(client, proj):
    wf = {"name": "hist", "nodes": [{"id": "a", "type": "write", "path": "o.txt",
                                     "content": "hi"}]}
    client.post("/api/workflows", params={"project": proj}, json=wf)
    r = client.post("/api/workflows/hist/run", json={"inputs": {}, "project": proj})
    rid = r.json()["run_id"]
    items = client.get("/api/workflows/runs", params={"project": proj}).json()["items"]
    assert any(x["id"] == rid for x in items)
    assert client.get("/api/workflows/runs", params={"project": proj,
                                                     "workflow": "hist"}).json()["items"]


def test_run_history_route_not_shadowed_by_name(client, proj):
    r = client.get("/api/workflows/runs", params={"project": proj})
    assert r.status_code == 200 and "items" in r.json()


def test_cancel_endpoint_unknown_404(client, proj):
    r = client.post("/api/workflows/runs/nope/cancel", json={"project": proj})
    assert r.status_code == 404


def test_resume_endpoint_unknown_404(client, proj):
    r = client.post("/api/workflows/runs/nope/resume", json={"project": proj})
    assert r.status_code == 404
