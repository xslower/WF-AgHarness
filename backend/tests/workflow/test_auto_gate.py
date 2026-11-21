from __future__ import annotations

import json

import pytest

from app.workflow import WorkflowEngine


class Gw:
    config = None


class Reg:
    schemas: list = []

    async def execute(self, name, args, ctx):
        return json.dumps({"ok": True, "exit": 0, "output": "OUT"}, ensure_ascii=False)


def build(tmp_path):
    return WorkflowEngine(gateway=Gw(), registry=Reg(),
                          workspace=str(tmp_path), workflows_dir=tmp_path / "wf")


def _wf(auto_extra=None):
    g = {"id": "g1", "type": "human", "title": "检查", "options": "批准\n驳回",
         "true": "w1", "false": "w2", "auto": True}
    if auto_extra:
        g.update(auto_extra)
    return {"name": "t", "nodes": [
        g,
        {"id": "w1", "type": "write", "path": "ok.txt", "content": "OK"},
        {"id": "w2", "type": "write", "path": "no.txt", "content": "NO"},
    ]}


async def test_auto_gate_approves_without_waiting(tmp_path):
    eng = build(tmp_path)
    wf = _wf()
    rec, _mode = eng._prepare_run(wf, {}, "ask", None, "", None, "")
    await eng._execute(wf, {}, rec, None)
    assert rec.status == "done", rec.error
    assert (tmp_path / "ok.txt").exists()
    assert not (tmp_path / "no.txt").exists()
    pass
    assert any(w.get("code") == "auto-gate" for w in rec.warnings)


async def test_auto_gate_preset_reject_goes_false(tmp_path):
    eng = build(tmp_path)
    wf = _wf()
    inputs = {"g1": {"decision": "reject", "note": "这版不行"}}
    rec, _mode = eng._prepare_run(wf, inputs, "ask", None, "", None, "")
    await eng._execute(wf, inputs, rec, None)
    assert rec.status == "done", rec.error
    assert (tmp_path / "no.txt").exists()
    assert not (tmp_path / "ok.txt").exists()
    out = json.loads(rec.node_states["g1"]["output"])
    assert out["preset"] is True
    assert out["comment"] == "这版不行"


async def test_auto_gate_without_preset_marks_preset_false(tmp_path):
    eng = build(tmp_path)
    wf = _wf()
    rec, _mode = eng._prepare_run(wf, {}, "ask", None, "", None, "")
    await eng._execute(wf, {}, rec, None)
    out = json.loads(rec.node_states["g1"]["output"])
    assert out["preset"] is False
    assert out["by"] == "auto"


async def test_auto_gate_second_round_downgrades_but_keeps_note(tmp_path):
    from app.workflow.nodes.registry import NodeContext

    eng = build(tmp_path)
    node = {"id": "g1", "type": "human", "title": "t", "options": "批准\n驳回",
            "auto": True}
    ctx = NodeContext(workspace=str(tmp_path), gateway=None, tools=None,
                      mcp=None, agent_runner=None, run_id="r", wf_name="w",
                      extras={"human_mode": "ask"})
    vars = {"inputs": {"g1": {"decision": "revise", "note": "再改改"}},
            "outputs": {}}

    from app.workflow.nodes.human import run_human
    out1, _ = await run_human(node, ctx, vars)
    d1 = json.loads(out1)
    assert d1["preset"] is True
    assert d1["preset_consumed"] is False
    assert d1["round"] == 1

    out2, _ = await run_human(node, ctx, vars)
    d2 = json.loads(out2)
    assert d2["preset_consumed"] is True, "第二轮必须降级，否则回边会转到上限"
    assert d2["comment"] == "再改改", "note 必须保留（下游 prompt 引用它）"
    assert d2["round"] == 2


async def test_auto_gate_ignores_deny_mode(tmp_path):
    eng = build(tmp_path)
    wf = _wf()
    rec, _mode = eng._prepare_run(wf, {}, "deny", None, "", None, "")
    await eng._execute(wf, {}, rec, None, human_mode="deny")
    assert rec.status == "done", rec.error
    assert (tmp_path / "ok.txt").exists()
