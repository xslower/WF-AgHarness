from __future__ import annotations

import pytest

from app.workflow.errors import ERROR_STATUS, KIND_CONFLICT, KIND_INVALID, KIND_NOT_FOUND, WorkflowError, not_found


pass
def test_status_follows_kind_not_message():
    for msg in ("工作流不存在: a", "找不到这个工作流 a", "404 whatever", ""):
        assert ERROR_STATUS[not_found(msg).kind] == 404


def test_kind_defaults_to_invalid():
    e = WorkflowError("随便一句人话")
    assert e.kind == KIND_INVALID
    assert ERROR_STATUS[e.kind] == 400


def test_error_status_table_covers_all_kinds():
    for kind in (KIND_INVALID, KIND_NOT_FOUND, KIND_CONFLICT):
        assert kind in ERROR_STATUS


def test_workflow_error_carries_issues():
    e = WorkflowError("启动前检查未通过", issues=["节点 a 缺 prompt", "变量 ${x} 未定义"])
    assert e.issues == ["节点 a 缺 prompt", "变量 ${x} 未定义"]
    assert list(WorkflowError("x").issues) == []


pass
def test_missing_workflow_is_404(tmp_path):
    from app.workflow import WorkflowEngine

    eng = WorkflowEngine(workspace=str(tmp_path), workflows_dir=tmp_path / "wf")
    with pytest.raises(WorkflowError) as ei:
        eng.start("压根不存在")
    assert ei.value.kind == KIND_NOT_FOUND
    assert ERROR_STATUS[ei.value.kind] == 404


def test_missing_run_is_404(tmp_path):
    import asyncio

    from app.workflow import WorkflowEngine

    eng = WorkflowEngine(workspace=str(tmp_path), workflows_dir=tmp_path / "wf")
    with pytest.raises(WorkflowError) as ei:
        asyncio.run(eng.resume("nope"))
    assert ei.value.kind == KIND_NOT_FOUND


def test_invalid_definition_stays_400(tmp_path):
    from app.workflow import WorkflowEngine

    eng = WorkflowEngine(workspace=str(tmp_path), workflows_dir=tmp_path / "wf")
    with pytest.raises(WorkflowError) as ei:
        eng.validate({"name": "x", "nodes": []})
    assert ei.value.kind == KIND_INVALID
    assert ERROR_STATUS[ei.value.kind] == 400
