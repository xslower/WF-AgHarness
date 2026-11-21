from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

from app.agent.loop_utils import parse_args
from app.agent.stream import execute_one
from app.tools.builtin.fs.batch import _coerce_edits
from app.util.jsonx import json_error_detail, parse_tool_args


pass
def test_parse_tool_args_ok():
    args, err = parse_tool_args('{"path": "a.txt", "n": 2}')
    assert err == "" and args == {"path": "a.txt", "n": 2}


def test_parse_tool_args_empty_defaults():
    assert parse_tool_args("") == ({}, "")
    assert parse_tool_args(None) == ({}, "")


def test_parse_tool_args_bad_json_carries_position_and_snippet():
    bad = '{"path": "a.txt", "content": "unclosed}'
    args, err = parse_tool_args(bad)
    assert args == {}
    assert "列" in err and "字符" in err
    assert "出错处附近" in err
    assert "unclosed" in err
    assert "截断" in err


def test_parse_tool_args_long_args_not_echoed_whole():
    huge = '{"content": "' + "X" * 50_000
    args, err = parse_tool_args(huge)
    assert args == {}
    assert len(err) < 600
    assert "X" * 50_000 not in err
    assert "字符" in err


def test_parse_tool_args_non_object_rejected():
    for raw in ('[1, 2]', 'null', '"str"', '42'):
        args, err = parse_tool_args(raw)
        assert args == {}
        assert "JSON 对象" in err


def test_json_error_detail_without_jsondecodeerror():
    out = json_error_detail(RecursionError("嵌套过深"), "{}")
    assert "嵌套过深" in out and "位置未知" in out


def test_parse_args_delegates_and_returns_detail():
    tc = {"function": {"name": "f_read", "arguments": '{"path": '}}
    args, detail, note = parse_args(tc)
    assert args == {} and "出错处附近" in detail
    assert note == ""


pass
def _runner():
    r = MagicMock()
    r.mcp = None
    r.registry = MagicMock()
    r._check_plan_block = AsyncMock(return_value=False)
    r._check_escalation = AsyncMock(return_value=None)
    r._publish_tool_event = MagicMock()
    return r


def test_execute_one_returns_parse_error_detail_to_model():
    emitted = []

    async def emit(ev):
        emitted.append(ev)

    r = _runner()
    tc = {"id": "c1", "function": {"name": "f_read", "arguments": "{}"}}
    result = asyncio.run(execute_one(
        r, tc, {}, "Expecting ',' delimiter（第 1 行第 9 列）", None, [], 0, emit))
    obj = json.loads(result)
    assert "解析失败" in obj["error"]
    assert "Expecting" in obj["reason"]
    assert "第 1 行" in obj["reason"]
    r.registry.execute.assert_not_called()
    assert any(e.get("type") == "tool_end" for e in emitted)


pass
def test_coerce_edits_string_bad_json_has_detail():
    items, problem = _coerce_edits('[{"content": bad}]')
    assert items is None
    assert "JSON 数组" in problem
    assert "字符" in problem and "出错处附近" in problem
