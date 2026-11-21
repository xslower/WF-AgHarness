from __future__ import annotations

from app.event.bus import HUB
from app.store.runs import RunStore
from app.workflow.engine import WorkflowEngine
from app.workflow.record import RunRecord

WF = {
    "name": "demo",
    "desc": "",
    "parallel_mode": "sequential",
    "inputs": [{"name": "input", "desc": "输入", "type": "string"}],
    "nodes": [
        {"id": "s1", "type": "llm", "prompt": "处理：${inputs.input}", "next": "h1"},
        {"id": "h1", "type": "handoff"},
    ],
    "edges": [{"source": "s1", "target": "h1", "sourceHandle": "out"}],
}


def _engine(tmp_path) -> WorkflowEngine:
    return WorkflowEngine(workspace=str(tmp_path), workflows_dir=tmp_path / "wfs")


def _collect(topic: str):
    got: list[dict] = []
    off = HUB.on(topic, got.append, key="test-wf-events")
    return got, off


def test_save_broadcasts_changed(tmp_path):
    eng = _engine(tmp_path)
    got, off = _collect("workflow.changed")
    try:
        eng.save(dict(WF))
    finally:
        off()
    assert got, "保存必须广播 workflow.changed，否则 AI 改完画布不同步"
    p = got[-1]["payload"]
    assert p["name"] == "demo"
    assert p["action"] == "save"
    assert p["project"] == str(tmp_path)
    assert p["revision"], "带上 revision，前端可据此判断该不该重载"


def test_delete_broadcasts_changed(tmp_path):
    eng = _engine(tmp_path)
    eng.save(dict(WF))
    got, off = _collect("workflow.changed")
    try:
        assert eng.delete("demo") is True
    finally:
        off()
    assert [e["payload"]["action"] for e in got] == ["delete"]


def test_rename_broadcasts_both_names(tmp_path):
    eng = _engine(tmp_path)
    eng.save(dict(WF))
    got, off = _collect("workflow.changed")
    try:
        eng.rename("demo", "demo2")
    finally:
        off()
    p = got[-1]["payload"]
    assert p["action"] == "rename" and p["name"] == "demo2" and p["old"] == "demo"


def test_delete_missing_workflow_does_not_broadcast(tmp_path):
    eng = _engine(tmp_path)
    got, off = _collect("workflow.changed")
    try:
        assert eng.delete("nope") is False
    finally:
        off()
    assert got == []


def test_run_meta_broadcasts_status(tmp_path):
    eng = _engine(tmp_path)
    eng.save(dict(WF))
    rec = RunRecord("r-meta-1", "demo", str(tmp_path))
    got, off = _collect("workflow.run")
    try:
        eng._save_run_meta(rec)
    finally:
        off()
    assert len(got) >= 1
    p = got[-1]["payload"]
    assert p["run"] == rec.id and p["workflow"] == "demo"
    pass
    assert "project" in p and "status" in p


def test_run_store_write_meta_does_not_broadcast(tmp_path):
    store = RunStore(str(tmp_path))
    got, off = _collect("workflow.run")
    try:
        store.prepare("r9", "demo")
        store.write_meta("r9", {"id": "r9", "workflow": "demo", "status": "done"})
    finally:
        off()
    assert got == []


def test_broadcast_failure_does_not_break_save(tmp_path, monkeypatch):
    eng = _engine(tmp_path)

    def _boom(_ev):
        raise RuntimeError("订阅者炸了")

    HUB.on("workflow.changed", _boom, key="test-wf-boom")
    try:
        saved = eng.save(dict(WF))
        assert saved["name"] == "demo"
        assert (tmp_path / "wfs" / "demo.json").is_file()
    finally:
        HUB.off("workflow.changed", key="test-wf-boom")
