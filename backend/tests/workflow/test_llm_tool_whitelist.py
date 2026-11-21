from __future__ import annotations

import asyncio
import json

from app.workflow.nodes.llm import run_llm
from app.provider.gateway import Chunk
from app.workflow.nodes.registry import NodeContext


class _FakeTools:

    def __init__(self):
        self.executed: list[tuple[str, dict]] = []
        self.schemas = [
            {"type": "function", "function": {"name": "f_read", "description": "", "parameters": {}}},
            {"type": "function", "function": {"name": "run_command", "description": "", "parameters": {}}},
        ]

    async def execute(self, name, args, ctx):
        self.executed.append((name, args))
        return json.dumps({"ok": name})


class _Gw:

    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self.calls = 0
        self.tool_results: list[str] = []

    async def chat_stream(self, messages, tools=None, **kw):
        self.calls += 1
        if self.calls == 1:
            yield Chunk(type="tool_meta", tool_index=0,
                        text=json.dumps({"id": "c1", "name": self.tool_name}))
            yield Chunk(type="tool_args", tool_index=0, text="{}")
        else:
            self.tool_results = [m["content"] for m in messages
                                 if m.get("role") == "tool"]
            yield Chunk(type="text", text="完成")


def _run(node, gateway, tools):
    return asyncio.run(run_llm(node, NodeContext(tools=tools, gateway=gateway, workspace="."), {}))


def test_tool_in_whitelist_executes():
    tools = _FakeTools()
    node = {"id": "n", "type": "llm", "prompt": "x",
            "tools": "f_read,run_command", "next": ""}
    _run(node, _Gw("f_read"), tools)
    assert ("f_read", {}) in tools.executed


def test_tool_outside_whitelist_is_rejected():
    tools = _FakeTools()
    node = {"id": "n", "type": "llm", "prompt": "x", "tools": "f_read", "next": ""}
    out, _ = _run(node, _Gw("run_command"), tools)
    assert tools.executed == []
    assert out == "完成"


def test_out_of_whitelist_returns_error_to_model_and_continues():
    tools = _FakeTools()
    gw = _Gw("run_command")
    node = {"id": "n", "type": "llm", "prompt": "x", "tools": "f_read", "next": ""}
    _run(node, gw, tools)
    assert tools.executed == []
    assert any("不在本节点白名单内" in c for c in gw.tool_results)


def test_auto_mode_not_restricted():
    tools = _FakeTools()
    node = {"id": "n", "type": "llm", "prompt": "x", "tools": "auto", "next": ""}
    _run(node, _Gw("run_command"), tools)
    assert ("run_command", {}) in tools.executed


def test_off_mode_never_calls_tools():
    tools = _FakeTools()

    class _TextGw:
        async def chat_stream(self, messages, tools=None, **kw):
            yield Chunk(type="text", text="完成")

    node = {"id": "n", "type": "llm", "prompt": "x", "tools": "off", "next": ""}
    _run(node, _TextGw(), tools)
    assert tools.executed == []
