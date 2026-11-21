from __future__ import annotations

import asyncio

import pytest

from app.workflow import WorkflowEngine


class Gw:
    config = None


class Reg:
    schemas: list = []

    async def execute(self, name, args, ctx):
        import json
        return json.dumps({"ok": True, "exit": 0, "output": "读到 OUT"})


def build(tmp_path):
    return WorkflowEngine(gateway=Gw(), registry=Reg(),
                          workspace=str(tmp_path),
                          workflows_dir=tmp_path / "wf")


def _wf():
    return {"name": "t", "nodes": [
        {"id": "s1", "type": "code", "code": "print('A')", "next": "s2"},
        {"id": "s2", "type": "code", "code": "print('${s1} ${inputs.q}')",
         "next": ""},
    ]}


def test_reads_extracted_from_template():
    from app.workflow.executor import _declared_reads
    node = {"id": "s2", "type": "write",
            "content": "x ${s1} y ${inputs.q} z ${s1.path}"}
    assert _declared_reads(node) == ["inputs.q", "s1"]


def test_reads_skip_escaped_and_comments():
    from app.workflow.executor import _declared_reads
    node = {"id": "c", "type": "code",
            "code": "# 用法 ${nope}\nprint('$${literal}')"}
    assert _declared_reads(node) == []


async def test_why_node_key_overview(tmp_path):
    eng = build(tmp_path)
    wf = _wf()
    rec, _mode = eng._prepare_run(wf, {"q": "Q"}, "ask", None, "", None, "")
    await eng._execute(wf, {"q": "Q"}, rec, None)
    assert rec.status == "done", rec.error

    pass
    d = eng.why(rec.id, node="s2")
    assert d["query"] == "node"
    assert "s1" in d["reads"] and "inputs.q" in d["reads"]
    assert d["writes"] == ["s2"]
    assert d["chars"] > 0

    pass
    d = eng.why(rec.id, key="s1")
    assert d["writers"] == ["s1"]
    assert d["readers"] == ["s2"]

    pass
    d = eng.why(rec.id, grep="读到")
    assert {h["node"] for h in d["hits"]} == {"s1", "s2"}
    assert all("snippet" in h for h in d["hits"])
    assert eng.why(rec.id, grep="根本不存在")["hits"] == []

    pass
    d = eng.why(rec.id)
    assert d["query"] == "overview"
    assert {n["node"] for n in d["nodes"]} == {"s1", "s2"}
    assert all(n["empty"] is False for n in d["nodes"])


async def test_why_marks_empty_output(tmp_path):
    from app.workflow.nodes.registry import NodeContext, NodeSpec

    eng = build(tmp_path)

    async def _empty(node, ctx, vars):
        return "", None

    eng.nodes.register(NodeSpec(type="_empty", label="空", run=_empty))
    wf = {"name": "t", "nodes": [
        {"id": "s1", "type": "write", "path": "a.txt", "content": "A", "next": "e1"},
        {"id": "e1", "type": "_empty"},
    ]}
    rec, _mode = eng._prepare_run(wf, {}, "ask", None, "", None, "")
    await eng._execute(wf, {}, rec, None)
    assert rec.status == "done", rec.error
    d = eng.why(rec.id)
    node = next(n for n in d["nodes"] if n["node"] == "e1")
    assert node["empty"] is True, node
    node2 = next(n for n in d["nodes"] if n["node"] == "s1")
    assert node2["empty"] is False


def test_why_unknown_run_raises(tmp_path):
    from app.workflow.errors import WorkflowError
    eng = build(tmp_path)
    with pytest.raises(WorkflowError):
        eng.why("nope")
