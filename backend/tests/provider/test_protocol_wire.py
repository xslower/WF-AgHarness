from __future__ import annotations

import json

from app.provider.adapters.openai_compatible import OpenAICompatibleAdapter
from app.provider.adapters.protocol_wire import wire_messages


def test_internal_keys_are_stripped():
    src = [{"role": "user", "content": "hi", "_bg_job": "x", "_seq": 3}]
    assert wire_messages(src) == [{"role": "user", "content": "hi"}]


def test_valid_tool_calls_are_untouched():
    calls = [{"id": "c1", "type": "function",
              "function": {"name": "f_read", "arguments": '{"path":"a.py"}'}}]
    assert wire_messages([{"role": "assistant", "tool_calls": calls}])[0][
        "tool_calls"] == calls


def test_truncated_arguments_become_empty_object():
    msgs = [
        {"role": "assistant", "content": None,
         "tool_calls": [{"id": "c1", "type": "function",
                         "function": {"name": "f_write",
                                      "arguments": '{"path":"a.py","content":"半截'}}]},
        {"role": "tool", "tool_call_id": "c1", "content": "参数解析失败"},
    ]
    out = wire_messages(msgs)
    assert len(out) == 2
    fn = out[0]["tool_calls"][0]["function"]
    assert json.loads(fn["arguments"]) == {}
    assert fn["name"] == "f_write" and out[0]["tool_calls"][0]["id"] == "c1"
    assert out[1]["tool_call_id"] == "c1"


def test_missing_name_and_id_are_filled():
    out = wire_messages([{"role": "assistant",
                          "tool_calls": [{"function": {"arguments": "{}"}}]}])
    call = out[0]["tool_calls"][0]
    assert call["type"] == "function" and call["function"]["name"] == "unknown"
    assert call["id"] == "call_invalid"


def test_absent_or_null_tool_calls_are_safe():
    assert wire_messages([{"role": "user", "content": "x"}])[0] == {
        "role": "user", "content": "x"}
    assert wire_messages([{"role": "assistant", "tool_calls": None}])[0][
        "tool_calls"] is None


def test_request_body_wires_clean_messages():
    body = OpenAICompatibleAdapter._request_body(
        type("M", (), {"wireId": "", "id": "m1", "supportsThinking": False})(),
        {"messages": [{"role": "assistant", "content": None,
                       "tool_calls": [{"id": "c1", "type": "function",
                                       "function": {"name": "grep",
                                                    "arguments": '{"key":'}}],
                       "_seq": 95},
                      {"role": "tool", "tool_call_id": "c1", "content": "err"}],
         "tools": None, "effort": "medium"})
    assert body["model"] == "m1" and body["stream"] is True
    assert "_seq" not in body["messages"][0]
    assert json.loads(body["messages"][0]["tool_calls"][0][
        "function"]["arguments"]) == {}
