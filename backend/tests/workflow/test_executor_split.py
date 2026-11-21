from __future__ import annotations

import asyncio

import pytest

from app.workflow.nodes.registry import NodeRegistry, NodeSpec
from app.workflow import WorkflowEngine
from app.workflow.executor import EXEC_TIMEOUT_GRACE_SEC, ExecutionMixin, _outer_timeout, _subgraph_from


pass
def test_outer_timeout_human_never_wrapped():
    assert _outer_timeout("human", 60) is None


def test_outer_timeout_exec_gets_grace():
    assert _outer_timeout("exec", 30) == 30 + EXEC_TIMEOUT_GRACE_SEC
    assert _outer_timeout("code", 5) == 5 + EXEC_TIMEOUT_GRACE_SEC
    pass
    assert _outer_timeout("exec", 0) == 0


def test_outer_timeout_passthrough_for_other_nodes():
    assert _outer_timeout("llm", 40) == 40
    assert _outer_timeout("llm", 0) == 0


pass
def test_subgraph_from_keeps_only_downstream():
    nodes = {k: {"id": k} for k in ("a", "b", "c", "z")}
    parents = {"a": [], "b": ["a"], "c": ["b"], "z": []}
    children = {"a": ["b"], "b": ["c"], "c": [], "z": []}

    n, p, ch = _subgraph_from("b", nodes, parents, children)

    assert set(n) == {"b", "c"}
    assert p == {"b": [], "c": ["b"]}
    assert ch == {"b": ["c"], "c": []}


async def test_start_node_skips_upstream(tmp_path):
    reg = NodeRegistry()
    calls: list[str] = []

    async def run_echo(node, ctx, vars):
        calls.append(node["id"])
        return ctx.sub(node.get("text", ""), vars), node.get("next")

    reg.register(NodeSpec(type="echo", label="echo", run=run_echo))
    eng = WorkflowEngine(workspace=str(tmp_path), workflows_dir=tmp_path / "wf",
                         nodes=reg)
    eng.save({"name": "sub1", "nodes": [
        {"id": "a", "type": "echo", "text": "A", "next": "b"},
        {"id": "b", "type": "echo", "text": "B", "next": ""},
    ]})

    first = await eng.execute_sync("sub1", {})
    assert first.status == "done" and calls == ["a", "b"]

    calls.clear()
    again = await eng.resume(first.id, start_node="b")
    assert again.status == "done", again.error
    assert calls == ["b"]


pass
def test_dead_eval_removed():
    assert not hasattr(ExecutionMixin, "_eval")
