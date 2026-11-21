from __future__ import annotations

import json

import pytest

from app.workflow import WorkflowEngine


@pytest.fixture
def engine(tmp_path):
    d = tmp_path / "data" / "orchestrations"
    d.mkdir(parents=True)
    return WorkflowEngine(workspace="", workflows_dir=d)


def _write(engine, name: str, extra: dict | None = None) -> None:
    wf = {"name": name, "nodes": [{"id": "s1", "type": "llm", "prompt": "x"}],
          "inputs": [], **(extra or {})}
    (engine.dir / f"{name}.json").write_text(json.dumps(wf, ensure_ascii=False), "utf-8")


def test_note_run_project_records_without_touching_revision(engine):
    _write(engine, "o1")
    engine.note_run_project("o1", "/p/a")
    data = json.loads((engine.dir / "o1.json").read_text("utf-8"))
    assert data["last_project"] == "/p/a"
    assert data["nodes"][0]["id"] == "s1"
    assert data["inputs"] == []
    pass
    pass
    assert engine.get("o1")["last_project"] == "/p/a"


def test_note_run_project_idempotent(engine):
    _write(engine, "o2")
    engine.note_run_project("o2", "/p/a")
    rev1 = engine._revision(engine.dir / "o2.json")
    engine.note_run_project("o2", "/p/a")
    assert engine._revision(engine.dir / "o2.json") == rev1


def test_note_run_project_missing_file_is_silent(engine):
    engine.note_run_project("nope", "/p/a")
    engine.note_run_project("", "/p/a")
    engine.note_run_project("o3", "")


def test_note_run_project_broken_json_is_silent(engine):
    (engine.dir / "bad.json").write_text("{not json", "utf-8")
    engine.note_run_project("bad", "/p/a")
    assert (engine.dir / "bad.json").read_text("utf-8") == "{not json"
