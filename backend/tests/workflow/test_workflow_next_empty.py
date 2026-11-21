import asyncio

import pytest

from app.tools.builtin import build_tools as build_registry
from app.workflow import RunRecord, WorkflowEngine, WorkflowError


def _engine(tmp_path):
    return WorkflowEngine(registry=build_registry(), workspace=str(tmp_path),
                          workflows_dir=tmp_path / "wf")


def _run(eng, wf, inputs):
    rec = RunRecord("r1", wf.get("name", "t"))
    eng.runs[rec.id] = rec
    asyncio.run(eng._execute(wf, inputs, rec, lambda r: None))
    return rec


def test_empty_next_ends_chain(tmp_path):
    wf = {"name": "t", "inputs": [{"name": "task", "type": "string"}],
          "nodes": [{"id": "s1", "type": "write", "path": "o.txt",
                     "content": "${inputs.task}", "next": ""}],
          "edges": []}
    rec = _run(_engine(tmp_path), wf, {"task": "hi"})
    assert rec.status == "done", rec.error
    assert (tmp_path / "o.txt").read_text("utf-8") == "hi"


def test_empty_next_on_last_of_chain(tmp_path):
    wf = {"name": "t", "inputs": [{"name": "task", "type": "string"}],
          "nodes": [
              {"id": "a", "type": "write", "path": "a.txt",
               "content": "A:${inputs.task}", "next": "b"},
              {"id": "b", "type": "write", "path": "b.txt",
               "content": "B", "next": ""},
          ],
          "edges": []}
    rec = _run(_engine(tmp_path), wf, {"task": "x"})
    assert rec.status == "done", rec.error
    assert (tmp_path / "a.txt").is_file() and (tmp_path / "b.txt").is_file()


def test_missing_next_still_rejected(tmp_path):
    wf = {"name": "t", "inputs": [],
          "nodes": [{"id": "s1", "type": "write", "path": "o.txt",
                     "content": "x", "next": "ghost"}],
          "edges": []}
    with pytest.raises(WorkflowError):
        WorkflowEngine.validate_structure(wf)
