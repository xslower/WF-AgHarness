from __future__ import annotations

import json

import pytest

from app.tools.builtin.workflow_edit import _NEEDS_NODE_ID, WORKFLOW_ACTIONS, workflow_cmd


class Ctx:

    def __init__(self, start=None, wait=None):
        self.workflow_start = start
        self.workflow_wait = wait
        self.cwd = "/tmp"
        self.suggested: list = []

    def suggest_tools(self, schemas):
        self.suggested.extend(schemas)


async def call(ctx, **kw):
    return await workflow_cmd(ctx, **kw)


async def _dummy(*a):
    return "unused"


def _is_err(text: str) -> bool:
    return '"error"' in text or "error" in text[:40]


pass
@pytest.mark.asyncio
async def test_unknown_action_lists_choices():
    msg = await call(Ctx(), action="explode")
    assert "action 必须是" in msg
    for act in WORKFLOW_ACTIONS:
        assert act in msg


@pytest.mark.asyncio
async def test_run_without_name():
    msg = await call(Ctx(), action="run")
    assert "需要 name" in msg


@pytest.mark.asyncio
async def test_run_without_callback():
    msg = await call(Ctx(), action="run", name="g")
    assert "执行不可用" in msg


@pytest.mark.asyncio
async def test_run_rejects_bad_human_mode():
    msg = await call(Ctx(_dummy), action="run", name="g", human="maybe")
    assert "human 只能是" in msg


@pytest.mark.asyncio
async def test_run_rejects_bad_parallel():
    msg = await call(Ctx(_dummy), action="run", name="g", parallel="turbo")
    assert "parallel 只能是" in msg


@pytest.mark.asyncio
@pytest.mark.parametrize("act", ["get", "list_node", "add_node", "edit_node",
                                 "del_node", "save"])
async def test_actions_need_name(act):
    msg = await call(Ctx(), action=act)
    assert "需要 name" in msg


@pytest.mark.asyncio
async def test_add_node_needs_node_body():
    msg = await call(Ctx(), action="add_node", name="g")
    assert "需要 node" in msg


@pytest.mark.asyncio
async def test_edit_node_needs_id_and_fields():
    assert "需要 node_id" in await call(Ctx(), action="edit_node", name="g")
    assert "需要 node_id" in await call(Ctx(), action="edit_node", name="g",
                                       node_id="n1")


@pytest.mark.asyncio
async def test_del_node_needs_id():
    msg = await call(Ctx(), action="del_node", name="g")
    assert "需要 node_id" in msg


def test_needs_node_id_messages_are_specific():
    assert "fields" in _NEEDS_NODE_ID["edit_node"]


pass
@pytest.mark.asyncio
async def test_run_calls_full_signature_first():
    seen = {}

    async def start(name, inp, mode, start_node, par):
        seen.update(name=name, mode=mode, start_node=start_node, par=par)
        return "ok"

    out = await call(Ctx(start), action="run", name="g", input="x",
                     human="auto-approve", start_node="n2", parallel="agent")
    assert out == "ok"
    assert seen == {"name": "g", "mode": "auto-approve", "start_node": "n2",
                    "par": "agent"}


@pytest.mark.asyncio
async def test_run_requires_full_signature_no_fallback():
    async def short_start(name, inp, mode, par):
        return "ok"

    out = await call(Ctx(short_start), action="run", name="g", start_node="s3")
    assert "工作流执行失败" in json.loads(out)["error"]


@pytest.mark.asyncio
async def test_run_exception_becomes_readable_error():
    async def start(*a):
        raise ValueError("节点 s1 的 docs 路径不存在")

    msg = await call(Ctx(start), action="run", name="g")
    assert "工作流执行失败" in msg and "docs 路径不存在" in msg


@pytest.mark.asyncio
async def test_run_normalizes_case_and_whitespace():
    seen = {}

    async def start(name, inp, mode, start_node, par):
        seen["mode"] = mode
        return "ok"

    await call(Ctx(start), action="run", name="g", human="  AUTO-APPROVE  ")
    assert seen["mode"] == "auto-approve"


@pytest.mark.asyncio
async def test_action_case_insensitive():
    msg = await call(Ctx(), action="  RUN  ")
    assert "需要 name" in msg


pass
@pytest.mark.asyncio
async def test_wait_needs_id():
    msg = await call(Ctx(_dummy, _dummy), action="wait")
    assert "需要 id" in msg


@pytest.mark.asyncio
async def test_wait_without_callback_is_readable():
    msg = await call(Ctx(_dummy), action="wait", id="r1")
    assert "等待运行不可用" in msg


@pytest.mark.asyncio
async def test_wait_forwards_id_timeout_and_detail():
    seen = {}

    async def wait(rid, t, detail=False):
        seen.update(rid=rid, t=t, detail=detail)
        return "结果"

    out = await call(Ctx(_dummy, wait), action="wait", id="r1",
                     timeout=42, detail=True)
    assert out == "结果"
    assert seen == {"rid": "r1", "t": 42, "detail": True}


@pytest.mark.asyncio
async def test_wait_caps_timeout_and_defaults_non_positive():
    from app.provider.spec import (SUBAGENT_WAIT_TIMEOUT_MAX_SEC,
                                   SUBAGENT_WAIT_TIMEOUT_SEC)
    got = []

    async def wait(rid, t, detail=False):
        got.append(t)
        return "ok"

    ctx = Ctx(_dummy, wait)
    await call(ctx, action="wait", id="r1")
    await call(ctx, action="wait", id="r1", timeout=0)
    await call(ctx, action="wait", id="r1", timeout=999999)
    assert got[0] == SUBAGENT_WAIT_TIMEOUT_SEC
    assert got[1] == SUBAGENT_WAIT_TIMEOUT_SEC
    assert got[2] == SUBAGENT_WAIT_TIMEOUT_MAX_SEC
