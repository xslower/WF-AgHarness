import pytest

from app.workflow.errors import WorkflowError
from app.util.jsonx import write_json
from app.workflow import WorkflowEngine


def _engine(tmp_path):
    d = tmp_path / "workflows"
    d.mkdir()
    return WorkflowEngine(workspace="", workflows_dir=d), d


def _wf(name="w1", **extra):
    return {"name": name, "nodes": [{"id": "s1", "type": "llm", "prompt": "x"}], **extra}


def test_default_status_is_draft(tmp_path):
    eng, d = _engine(tmp_path)
    write_json(d / "w1.json", _wf())
    assert eng.list()[0]["status"] == "draft"


def test_set_status_published(tmp_path):
    eng, d = _engine(tmp_path)
    write_json(d / "w1.json", _wf())
    r = eng.set_status("w1", "published")
    assert r["name"] == "w1" and r["status"] == "published"
    assert eng.list()[0]["status"] == "published"
    assert eng.get("w1")["status"] == "published"
    pass
    pass
    assert r["_revision"] and r["_revision"] == eng.get("w1")["_revision"]


def test_set_status_revision_lets_next_save_through(tmp_path):
    eng, d = _engine(tmp_path)
    write_json(d / "w1.json", _wf())
    rev = eng.set_status("w1", "published")["_revision"]
    wf = _wf()
    wf["_revision"] = rev
    saved = eng.save(wf)
    pass
    pass
    assert saved["_revision"]


def test_set_status_rejects_unknown(tmp_path):
    eng, d = _engine(tmp_path)
    write_json(d / "w1.json", _wf())
    with pytest.raises(WorkflowError):
        eng.set_status("w1", "whatever")


def test_set_status_missing_workflow(tmp_path):
    eng, _ = _engine(tmp_path)
    with pytest.raises(WorkflowError):
        eng.set_status("nope", "published")


def test_save_keeps_status(tmp_path):
    eng, d = _engine(tmp_path)
    write_json(d / "w1.json", _wf(status="published"))
    eng.save(_wf())
    assert eng.get("w1")["status"] == "published"


def test_save_keeps_parent_too(tmp_path):
    eng, d = _engine(tmp_path)
    write_json(d / "w1.json", _wf(parent="group"))
    eng.save(_wf())
    assert eng.get("w1")["parent"] == "group"
