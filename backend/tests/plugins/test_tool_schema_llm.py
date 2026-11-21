from __future__ import annotations

import json

import pytest

from app.plugins import schema_llm as tsl


class _Chunk:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class FakeGateway:

    def __init__(self, reply: str, *, boom: bool = False) -> None:
        self.reply = reply
        self.boom = boom
        self.calls: list[tuple[str, str]] = []

    async def chat_stream(self, messages, spec="", **_kw):
        self.calls.append((spec, messages[0]["content"]))
        if self.boom:
            raise RuntimeError("模型不可用")
        for i in range(0, len(self.reply), 8):
            yield _Chunk(self.reply[i:i + 8])


def _demo(query: str, limit: int = 5, ctx=None) -> str:
    return query


def test_infer_uses_child_queue_and_reads_source():
    gw = FakeGateway(json.dumps({
        "desc": "按关键词搜索仓库文件",
        "params": {
            "query": {"type": "string", "description": "关键词"},
            "limit": {"type": "integer", "description": "返回条数，默认 5"},
        },
        "required": ["query"],
    }, ensure_ascii=False))
    got = tsl.run_sync(tsl.infer_tool_schema(gw, name="search", desc="", fn=_demo))
    assert got["params"]["query"]["description"] == "关键词"
    assert got["required"] == ["query"]
    spec, prompt = gw.calls[0]
    assert spec == "child"
    assert "def _demo" in prompt
    assert "ctx" in prompt or "不要写进去" in prompt


def test_infer_drops_invented_params():
    gw = FakeGateway(json.dumps({
        "desc": "搜索",
        "params": {"query": {"type": "string", "description": "关键词"},
                   "nonexistent": {"type": "string", "description": "编的"}},
        "required": ["query", "nonexistent"],
    }, ensure_ascii=False))
    got = tsl.run_sync(tsl.infer_tool_schema(gw, name="search", desc="", fn=_demo))
    assert set(got["params"]) == {"query"}
    assert got["required"] == ["query"]


def test_infer_tolerates_fenced_json_and_chatter():
    gw = FakeGateway("好的，这是 schema：\n```json\n" + json.dumps({
        "desc": "搜索", "params": {"query": {"type": "string",
                                            "description": "关键词"}},
        "required": ["query"]}, ensure_ascii=False) + "\n```\n希望有用！")
    got = tsl.run_sync(tsl.infer_tool_schema(gw, name="search", desc="", fn=_demo))
    assert got and got["params"]["query"]["type"] == "string"


def test_infer_returns_none_when_model_down():
    gw = FakeGateway("", boom=True)
    assert tsl.run_sync(tsl.infer_tool_schema(
        gw, name="s", desc="", fn=_demo)) is None


def test_infer_returns_none_on_garbage():
    gw = FakeGateway("我不太确定这个函数在干什么")
    assert tsl.run_sync(tsl.infer_tool_schema(
        gw, name="s", desc="", fn=_demo)) is None


def test_illegal_type_is_normalized_to_string():
    gw = FakeGateway(json.dumps({
        "desc": "搜索",
        "params": {"query": {"type": "text", "description": "关键词"}},
        "required": ["query"],
    }, ensure_ascii=False))
    got = tsl.run_sync(tsl.infer_tool_schema(gw, name="s", desc="", fn=_demo))
    assert got["params"]["query"]["type"] == "string"


pass

def test_needs_llm_when_declaration_incomplete():
    assert tsl.needs_llm(None, "有描述", _demo)
    assert tsl.needs_llm({"query": {"type": "string"}}, "", _demo)
    assert tsl.needs_llm({"query": {"type": "string"}}, "d", _demo)
    assert tsl.needs_llm({"query": {"type": "string"},
                          "limit": {"type": "integer"}}, "d", _demo)


def test_no_llm_when_declaration_is_complete():
    params = {"query": {"type": "string", "description": "关键词"},
              "limit": {"type": "integer", "description": "条数"}}
    assert not tsl.needs_llm(params, "按关键词搜", _demo)
