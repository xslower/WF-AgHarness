from __future__ import annotations

import json

import pytest

from app.agent.profile import AgentProfile
import app.tools.builtin.workflow_edit as we
from app.workflow import WorkflowRouter

PROFILE = AgentProfile(id="default", system_prompt="")


async def _noop(_ev):
    return None


@pytest.fixture
def fresh(tmp_dirs, monkeypatch):
    from app.factory import build_container

    return build_container()


def test_runner_has_wf_engine_right_after_assembly(fresh):
    assert isinstance(fresh.runner.wf_engine, WorkflowRouter)
    assert fresh.wf_router is fresh.runner.wf_engine


def test_context_gets_wf_edit_without_touching_api(fresh, tmp_path):
    ctx = fresh.runner._build_context(str(tmp_path), _noop, 0, "sid", PROFILE)
    assert ctx.wf_edit is not None
    assert ctx.workflow_start is not None


async def test_workflow_tool_works_immediately(fresh, tmp_path):
    ctx = fresh.runner._build_context(str(tmp_path), _noop, 0, "sid", PROFILE)
    wf = {"name": "接线验证", "desc": "",
          "nodes": [{"id": "s1", "type": "llm", "prompt": "hi"}]}
    saved = json.loads(await we.workflow_cmd(
        ctx, action="save", name="接线验证", workflow=wf))
    assert saved["ok"] is True and saved["nodes"] == 1

    listed = json.loads(await we.workflow_cmd(ctx, action="list"))
    assert [w["name"] for w in listed] == ["接线验证"]

    nodes = json.loads(await we.workflow_cmd(ctx, action="list_node", name="接线验证"))
    assert nodes[0]["id"] == "s1" and nodes[0]["type"] == "llm"


async def test_help_action_available_immediately(fresh, tmp_path):
    ctx = fresh.runner._build_context(str(tmp_path), _noop, 0, "sid", PROFILE)
    out = await we.workflow_cmd(ctx, action="help")
    assert out.startswith("# workflow 工具速查")


def test_container_and_runner_share_one_router(fresh, tmp_path):
    assert fresh.wf_engine(str(tmp_path)) is fresh.wf_router.engine_for(str(tmp_path))
    assert fresh.wf_engine("") is fresh.wf_router.engine_for("")


def test_subagent_depth_has_no_workflow_edit(fresh, tmp_path):
    ctx = fresh.runner._build_context(str(tmp_path), _noop, 1, "sid", PROFILE)
    assert ctx.wf_edit is None
