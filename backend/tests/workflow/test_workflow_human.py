from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from app.provider.gateway import Chunk
from app.workflow import WorkflowEngine, WorkflowError


class FakeGw:
    def __init__(self):
        self.config = SimpleNamespace(providers=[], settings=SimpleNamespace(policy="yolo"))

    async def chat_stream(self, messages, **kw):
        for c in [Chunk(type="text", text="ok")]:
            yield c


class FakeRegistry:
    schemas: list = []

    async def execute(self, name, args, ctx):
        return f"{name} 结果"


def build(tmp_path, nodes):
    return WorkflowEngine(gateway=FakeGw(), registry=FakeRegistry(),
                          workspace=str(tmp_path), workflows_dir=tmp_path / "wf")


A_APPROVE_WORKFLOW = [
    {"id": "h1", "type": "human", "title": "确认烧图", "ask": "要花积分了",
     "options": "批准\n驳回", "true": "w1", "false": "w2"},
    {"id": "w1", "type": "write", "path": "go.txt", "content": "go"},
    {"id": "w2", "type": "write", "path": "stop.txt", "content": "stop"},
]


async def _wait(rec, rounds=100):
    for _ in range(rounds):
        if rec.status != "running":
            return
        await asyncio.sleep(0.02)


async def test_approve_goes_true_branch(tmp_path):
    eng = build(tmp_path, A_APPROVE_WORKFLOW)
    rec = eng.start_definition({"name": "t", "nodes": A_APPROVE_WORKFLOW})
    await asyncio.sleep(0.05)
    pending = eng.human.pending(rec.id)
    assert pending and pending["node_id"] == "h1"
    assert pending["options"] == ["批准", "驳回"]

    assert eng.human.decide(rec.id, "h1", "批准", "开工")
    await _wait(rec)
    assert rec.status == "done", rec.error
    assert (tmp_path / "go.txt").read_text("utf-8") == "go"
    out = json.loads(rec.node_states["h1"]["output"])
    assert out["choice"] == "批准" and out["comment"] == "开工"


async def test_reject_goes_false_branch(tmp_path):
    eng = build(tmp_path, A_APPROVE_WORKFLOW)
    rec = eng.start_definition({"name": "t", "nodes": A_APPROVE_WORKFLOW})
    await asyncio.sleep(0.05)
    assert eng.human.decide(rec.id, "h1", "驳回")
    await _wait(rec)
    assert rec.status == "done", rec.error
    assert (tmp_path / "stop.txt").read_text("utf-8") == "stop"
    assert not (tmp_path / "go.txt").exists()


async def test_option_can_target_node_directly(tmp_path):
    nodes = [
        {"id": "h1", "type": "human", "title": "选", "options": "批准\n回炉=w3",
         "true": "w1", "false": "w2"},
        {"id": "w1", "type": "write", "path": "a.txt", "content": "a"},
        {"id": "w2", "type": "write", "path": "b.txt", "content": "b"},
        {"id": "w3", "type": "write", "path": "c.txt", "content": "c"},
    ]
    eng = build(tmp_path, nodes)
    rec = eng.start_definition({"name": "t", "nodes": nodes})
    await asyncio.sleep(0.05)
    assert eng.human.decide(rec.id, "h1", "回炉")
    await _wait(rec)
    assert rec.status == "done", rec.error
    assert (tmp_path / "c.txt").exists()


async def test_timeout_fail_is_default(tmp_path):
    nodes = [{"id": "h1", "type": "human", "title": "t", "options": "批准\n驳回",
              "timeout": 1, "true": "w1", "false": "w1"},
             {"id": "w1", "type": "write", "path": "x.txt", "content": "x"}]
    eng = build(tmp_path, nodes)
    rec = await eng.execute_definition({"name": "t", "nodes": nodes})
    assert rec.status == "failed"
    assert "超时" in rec.error


async def test_timeout_approve_honours_node_setting(tmp_path):
    nodes = [{"id": "h1", "type": "human", "title": "t", "options": "批准\n驳回",
              "timeout": 1, "onTimeout": "approve", "true": "w1", "false": "w2"},
             {"id": "w1", "type": "write", "path": "go.txt", "content": "go"},
             {"id": "w2", "type": "write", "path": "stop.txt", "content": "stop"}]
    eng = build(tmp_path, nodes)
    rec = await eng.execute_definition({"name": "t", "nodes": nodes})
    assert rec.status == "done", rec.error
    assert (tmp_path / "go.txt").exists()


async def test_unattended_run_fails_fast(tmp_path):
    eng = build(tmp_path, A_APPROVE_WORKFLOW)
    eng.dir.mkdir(parents=True, exist_ok=True)
    (eng.dir / "t.json").write_text(json.dumps({"name": "t", "nodes": A_APPROVE_WORKFLOW}),
                                    "utf-8")
    with pytest.raises(WorkflowError) as err:
        await eng.execute_sync("t")
    pass
    assert "人工闸门" in str(err.value) and "auto-approve" in str(err.value)
    assert not eng.runs


async def test_explicit_auto_approve_works(tmp_path):
    eng = build(tmp_path, A_APPROVE_WORKFLOW)
    eng.dir.mkdir(parents=True, exist_ok=True)
    (eng.dir / "t.json").write_text(json.dumps({"name": "t", "nodes": A_APPROVE_WORKFLOW}),
                                    "utf-8")
    rec = await eng.execute_sync("t", human_mode="auto-approve")
    assert rec.status == "done", rec.error
    assert (tmp_path / "go.txt").exists()


async def test_cancel_releases_gate(tmp_path):
    eng = build(tmp_path, A_APPROVE_WORKFLOW)
    rec = eng.start_definition({"name": "t", "nodes": A_APPROVE_WORKFLOW})
    await asyncio.sleep(0.05)
    assert eng.human.pending(rec.id) is not None
    res = eng.cancel(rec.id)
    assert res["ok"], res
    await _wait(rec)
    assert rec.status == "cancelled"
    assert eng.human.pending(rec.id) is None
    assert rec.pending_human is None


async def test_decide_on_unknown_gate_returns_false(tmp_path):
    eng = build(tmp_path, A_APPROVE_WORKFLOW)
    assert eng.human.decide("nope", "h1", "批准") is False


async def test_human_requires_title_and_options(tmp_path):
    eng = build(tmp_path, A_APPROVE_WORKFLOW)
    wf = {"name": "t", "nodes": [{"id": "h1", "type": "human"}]}
    with pytest.raises(WorkflowError, match="缺少 title"):
        eng.validate(wf)


async def test_human_is_control_type_not_parallel(tmp_path):
    from app.workflow.engine import CONTROL_TYPES
    assert "human" in CONTROL_TYPES
    assert "while" not in CONTROL_TYPES
