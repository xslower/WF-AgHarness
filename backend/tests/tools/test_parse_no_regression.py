from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agent.loop_utils import parse_args
from app.agent.stream import execute_one
from app.provider.adapters.openai_sse import _repair_frame, delta_events
from app.util.jsonfix import (loads_lenient, parse_tool_args,
                              parse_tool_args_report, valid_tool_args)
from app.workflow.expr import json_value, yaml_value
from app.workflow.nodes.llm_parse import parse_output

pass
pass
LEGAL_ARGS: list[tuple[str, dict]] = [
    ('{"path": "a.txt", "url": "https://x/y"}',
     {"path": "a.txt", "url": "https://x/y"}),
    ('{"path": "a//b", "lines": "1,80"}',
     {"path": "a//b", "lines": "1,80"}),
    ('{"command": "echo /* hi */ ok", "timeout": 30}',
     {"command": "echo /* hi */ ok", "timeout": 30}),
    ('{"content": "他说 \\"你好\\"\\n第二行", "append": true}',
     {"content": '他说 "你好"\n第二行', "append": True}),
    ('{"path": "C:\\\\Users\\\\x", "note": "a：b"}',
     {"path": "C:\\Users\\x", "note": "a：b"}),
    ('{"text": "a,}", "items": [1, 2, 3]}',
     {"text": "a,}", "items": [1, 2, 3]}),
    ('{"cmd": "grep -n \\"x\\" f", "url": "http://x/y"}',
     {"cmd": 'grep -n "x" f', "url": "http://x/y"}),
]


@pytest.mark.parametrize("raw,want", LEGAL_ARGS)
def test_legal_args_never_error_in_any_scene(raw, want):
    for scene in ("raw", "args", "edits", "command"):
        v, detail, note = loads_lenient(raw, scene=scene)
        assert detail == "" and note == "" and v == want, (scene, detail, note)
    args, err = parse_tool_args(raw, scene="args")
    assert err == "" and args == want
    args2, err2, note2 = parse_tool_args_report(raw, scene="args")
    assert err2 == "" and args2 == want and note2 == ""
    assert valid_tool_args(raw) is True


@pytest.mark.parametrize("raw,want", LEGAL_ARGS)
def test_parse_args_by_tool_name_never_errors(raw, want):
    for tool in ("f_write", "f_replace", "run_command", "f_read", "grep",
                 "web", "mcp__x", None):
        tc = {"function": {"name": tool, "arguments": raw}}
        args, err, note = parse_args(tc)
        assert err == "" and note == "" and args == want, (tool, err, note)


@pytest.mark.parametrize("raw,want", LEGAL_ARGS)
def test_sse_frame_with_legal_args_never_errors(raw, want):
    frame = {"choices": [{"delta": {"tool_calls": [
        {"index": 0, "id": "c1",
         "function": {"name": "f_read", "arguments": raw}}]}}]}
    data = json.dumps(frame, ensure_ascii=False)
    obj = json.loads(data)
    evs = delta_events(obj["choices"][0]["delta"])
    assert any(e["type"] == "tool_args" for e in evs)
    pass
    repaired, note = _repair_frame(data)
    assert repaired == obj and note == "", "合法帧一个字节都不许改"


def test_broken_sse_frame_with_legal_url_still_repairs():
    data = ('{"choices":[{"delta":{"tool_calls":[{"index":0,"function":'
            '{"name":"f_read","arguments":"{\\"url\\":\\"http://x/y\\"}"}}]}}]')
    import pytest as _pytest
    with _pytest.raises(json.JSONDecodeError):
        json.loads(data)
    obj, note = _repair_frame(data)
    assert isinstance(obj, dict), f"补帧失败会炸会话：{data}"
    args = obj["choices"][0]["delta"]["tool_calls"][0]["function"]["arguments"]
    assert "http://x/y" in args, "URL 里的 // 不许被当成注释剥掉"
    assert note


def test_workflow_entries_with_legal_data_never_error():
    raw, want = LEGAL_ARGS[0]
    assert json_value(raw, None) == want
    out, err, fb = parse_output(f"```json\n{raw}\n```", "json", False)
    assert err == "" and json.loads(out) == want and fb is False
    pass
    assert yaml_value("items: [1, 2, 3]\n", None) == {"items": [1, 2, 3]}


def test_execute_one_runs_tool_on_legal_args():
    r = MagicMock()
    r.mcp = None
    r.registry = MagicMock()
    r.registry.execute = AsyncMock(return_value="done")
    r._check_plan_block = AsyncMock(return_value=False)
    r._check_escalation = AsyncMock(return_value=None)
    r._publish_tool_event = MagicMock()

    async def emit(ev):
        pass

    tc = {"id": "c1", "function": {"name": "f_read", "arguments": LEGAL_ARGS[0][0]}}
    args, err, note = parse_args(tc)
    assert err == "" and note == ""
    result = asyncio.run(execute_one(r, tc, args, "", None, [], 0, emit, ""))
    assert result == "done" and r.registry.execute.await_count == 1
