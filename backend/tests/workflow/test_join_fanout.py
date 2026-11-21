from __future__ import annotations

import asyncio
import json

import pytest

from app.workflow import WorkflowEngine


class Gw:
    config = None


def build(tmp_path):
    return WorkflowEngine(gateway=Gw(), workspace=str(tmp_path),
                          workflows_dir=tmp_path / "wf")


def _wf(nodes, edges=None):
    wf = {"name": "t", "nodes": nodes}
    if edges:
        wf["edges"] = edges
    return wf


async def test_fanout_to_join_runs_join_once(tmp_path):
    eng = build(tmp_path)
    nodes = [
        {"id": "a", "type": "write", "path": "a.txt", "content": "A",
         "next": ["b1", "b2"]},
        {"id": "b1", "type": "write", "path": "b1.txt", "content": "B1",
         "next": "j"},
        {"id": "b2", "type": "write", "path": "b2.txt", "content": "B2",
         "next": "j"},
        {"id": "j", "type": "join", "next": "c"},
        {"id": "c", "type": "write", "path": "c.txt", "content": "C"},
    ]
    wf = _wf(nodes)
    wf["nodes"][0]["parallel_next"] = ["b1", "b2"]
    wf["nodes"][0].pop("next")
    rec, mode = eng._prepare_run(wf, {}, "ask", None, "", None, "")
    await eng._execute(wf, {}, rec, None)
    assert rec.status == "done", rec.error
    for f in ("a.txt", "b1.txt", "b2.txt", "c.txt"):
        assert (tmp_path / f).exists(), f
    pass
    assert "j" in rec.node_states


async def test_join_after_condition_branches(tmp_path):
    eng = build(tmp_path)
    nodes = [
        {"id": "c1", "type": "condition", "expr": "len('x') > 0",
         "true": "w1", "false": "w2"},
        {"id": "w1", "type": "write", "path": "t.txt", "content": "T", "next": "j"},
        {"id": "w2", "type": "write", "path": "f.txt", "content": "F", "next": "j"},
        {"id": "j", "type": "join", "next": "end"},
        {"id": "end", "type": "write", "path": "end.txt", "content": "E"},
    ]
    wf = _wf(nodes)
    rec, _mode = eng._prepare_run(wf, {}, "ask", None, "", None, "")
    await eng._execute(wf, {}, rec, None)
    assert rec.status == "done", rec.error
    assert (tmp_path / "t.txt").exists()
    assert not (tmp_path / "f.txt").exists()
    assert (tmp_path / "end.txt").exists()


async def test_fanout_without_join_rejected():
    from app.workflow import WorkflowError
    from app.workflow.validate import ValidateMixin

    wf = {"name": "t", "nodes": [
        {"id": "c1", "type": "condition", "expr": "1", "true": "b1", "false": "b2"},
        {"id": "b1", "type": "write", "parallel_next": ["x", "y"]},
        {"id": "b2", "type": "write"},
        {"id": "x", "type": "write", "next": "z"},
        {"id": "y", "type": "write", "next": "z"},
        {"id": "z", "type": "write"},
    ]}
    with pytest.raises(WorkflowError, match="join"):
        ValidateMixin.validate_structure(wf)


async def test_fanout_with_join_passes_validation():
    from app.workflow.validate import ValidateMixin

    wf = {"name": "t", "nodes": [
        {"id": "c1", "type": "condition", "expr": "1", "true": "b1", "false": "b2"},
        {"id": "b1", "type": "write", "parallel_next": ["x", "y"]},
        {"id": "b2", "type": "write"},
        {"id": "x", "type": "write", "next": "j"},
        {"id": "y", "type": "write", "next": "j"},
        {"id": "j", "type": "join", "next": ""},
    ]}
    ValidateMixin.validate_structure(wf)


async def test_join_is_registered_type(tmp_path):
    from app.workflow.constants import default_nodes
    spec = default_nodes().get("join")
    assert spec is not None
    out, nxt = await spec.run({"id": "j", "next": "x"},
                              _ctx(), {"outputs": {"prev": "UP"}})
    assert out == "UP"
    assert nxt == "x"


def _ctx():
    from app.workflow.nodes.registry import NodeContext
    return NodeContext(workspace="", gateway=None, tools=None, mcp=None,
                       agent_runner=None, run_id="r", wf_name="w")
