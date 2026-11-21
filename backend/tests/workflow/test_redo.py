from __future__ import annotations

import json

import pytest

from app.workflow import WorkflowEngine


class Gw:
    config = None


class Reg:
    schemas: list = []
    calls: list = []

    async def execute(self, name, args, ctx):
        Reg.calls.append(args)
        return json.dumps({"ok": True, "exit": 0, "output": "OUT"}, ensure_ascii=False)


def build(tmp_path):
    Reg.calls = []
    return WorkflowEngine(gateway=Gw(), registry=Reg(),
                          workspace=str(tmp_path), workflows_dir=tmp_path / "wf")


def _wf():
    return {"name": "t", "nodes": [
        {"id": "a", "type": "code", "code": "print('a')", "next": "b"},
        {"id": "b", "type": "code", "code": "print('${a}')", "next": "c"},
        {"id": "c", "type": "code", "code": "print('${b}')", "next": ""},
    ]}


async def test_descendants():
    from app.workflow.run_records import RunRecordsMixin
    wf = _wf()
    assert RunRecordsMixin._descendants(wf, "a") == {"b", "c"}
    assert RunRecordsMixin._descendants(wf, "b") == {"c"}
    assert RunRecordsMixin._descendants(wf, "c") == set()


async def test_redo_from_middle_skips_upstream(tmp_path):
    eng = build(tmp_path)
    wf = eng.save(_wf())
    rec, _mode = eng._prepare_run(wf, {}, "ask", None, "", None, "")
    await eng._execute(wf, {}, rec, None)
    assert rec.status == "done", rec.error
    first_calls = len(Reg.calls)
    assert first_calls == 3

    Reg.calls = []
    rec2 = await eng.redo(rec.id, from_node="b", note="第2步不满意")
    assert rec2.status == "done", rec2.error
    pass
    assert len(Reg.calls) == 2, Reg.calls
    assert any(w.get("code") == "redo" for w in rec2.warnings)


async def test_redo_stashes_old_outputs(tmp_path):
    eng = build(tmp_path)
    wf = eng.save(_wf())
    rec, _mode = eng._prepare_run(wf, {}, "ask", None, "", None, "")
    await eng._execute(wf, {}, rec, None)
    before = eng.store.read_node(rec.id, "b")["content"]

    rec2 = await eng.redo(rec.id, from_node="b")
    stale_dir = eng.store.paths.run_dir(rec.id) / "stale"
    files = list(stale_dir.glob("b.*.md"))
    assert files, "作废范围里节点的旧输出必须挪到 stale/"
    assert files[0].read_text("utf-8") == before


async def test_redo_unknown_node(tmp_path):
    from app.workflow.errors import WorkflowError
    eng = build(tmp_path)
    wf = eng.save(_wf())
    rec, _mode = eng._prepare_run(wf, {}, "ask", None, "", None, "")
    await eng._execute(wf, {}, rec, None)
    with pytest.raises(WorkflowError):
        await eng.redo(rec.id, from_node="nope")


async def test_redo_without_from_uses_first_undone(tmp_path):
    eng = build(tmp_path)
    wf = eng.save(_wf())
    rec, _mode = eng._prepare_run(wf, {}, "ask", None, "", None, "")
    await eng._execute(wf, {}, rec, None)
    Reg.calls = []
    rec2 = await eng.redo(rec.id)
    assert rec2.status == "done", rec2.error
    assert len(Reg.calls) == 3
