from __future__ import annotations

import asyncio
import json

import pytest

from app.provider.gateway import Chunk
from app.workflow.errors import WorkflowError
from app.workflow.nodes.llm import run_llm
from app.workflow.nodes.mcp import run_mcp
from app.workflow.nodes.registry import NodeContext


class _FakeTools:
    def __init__(self):
        self.executed: list[tuple[str, dict]] = []
        self.schemas = [
            {"type": "function", "function": {
                "name": "f_read", "description": "", "parameters": {}}},
        ]

    async def execute(self, name, args, ctx):
        self.executed.append((name, args))
        return json.dumps({"ok": name})


class _BadArgsGw:

    def __init__(self, fragments):
        self.fragments = fragments
        self.calls = 0
        self.tool_results: list[str] = []

    async def chat_stream(self, messages, tools=None, **kw):
        self.calls += 1
        if self.calls == 1:
            yield Chunk(type="tool_meta", tool_index=0,
                        text=json.dumps({"id": "c1", "name": "f_read"}))
            for part in self.fragments:
                yield Chunk(type="tool_args", tool_index=0, text=part)
        else:
            self.tool_results = [m["content"] for m in messages
                                 if m.get("role") == "tool"]
            yield Chunk(type="text", text="完成")


def _run(node, gateway, tools):
    return asyncio.run(run_llm(
        node, NodeContext(tools=tools, gateway=gateway, workspace="."), {}))


def test_llm_node_bad_args_feeds_diagnostic_back_to_model():
    tools = _FakeTools()
    pass
    frags = ['{"path": "a.txt", "content": "', "X" * 200, "（截断）"]
    gw = _BadArgsGw(frags)
    node = {"id": "n", "type": "llm", "prompt": "x", "tools": "f_read", "next": ""}
    _run(node, gw, tools)
    assert tools.executed == []
    assert gw.tool_results
    payload = json.loads(gw.tool_results[0])
    assert "解析失败" in payload["error"]
    assert "字符" in payload["reason"] and "出错处附近" in payload["reason"]


def test_mcp_node_bad_args_error_has_detail():
    class _Ctx:
        mcp = object()

        def sub(self, text, _vars):
            return text

    with pytest.raises(WorkflowError) as ei:
        asyncio.run(run_mcp(
            {"id": "m", "type": "mcp", "tool": "t", "argsJson": "{不是json"},
            _Ctx(), {}))
    msg = str(ei.value)
    assert "参数 JSON 无效" in msg
    assert "字符" in msg and "出错处附近" in msg
