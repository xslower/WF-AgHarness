import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

from app.agent.loop_utils import parse_args
from app.agent.stream import execute_one
from app.util import jsonfix, jsonx
from app.util.jsonfix import (RepairResult, loads_lenient, parse_tool_args,
                              parse_tool_args_report, repair, scene_for_tool)


pass
def test_scene_for_tool():
    assert scene_for_tool("run_command") == "command"
    assert scene_for_tool("f_write") == "edits"
    assert scene_for_tool("f_replace") == "edits"
    assert scene_for_tool("f_read") == "args"
    assert scene_for_tool("mcp__whatever") == "args"
    assert scene_for_tool(None) == "args"


def test_jsonx_reexports_same_objects():
    assert jsonx.parse_tool_args is jsonfix.parse_tool_args
    assert jsonx.loads_lenient is jsonfix.loads_lenient
    assert jsonx.close_open_structs is jsonfix.close_open_structs
    assert jsonx.scene_for_tool is jsonfix.scene_for_tool


pass
def test_command_quotes_fixed_and_tail_params_kept():
    raw = '{"command": "grep -n "x", "y" file", "timeout": 120}'
    r = repair(raw, scene="command")
    assert r.level == "fixed"
    assert r.value == {"command": 'grep -n "x", "y" file', "timeout": 120}
    assert "command" in r.note


def test_command_truncated_refused():
    raw = '{"command": "echo "x" && ls -lt data/logs | tail -30'
    r = repair(raw, scene="command")
    assert r.level == "failed"
    assert r.value is None
    assert "字符" in r.detail


def test_command_not_first_key():
    raw = '{"timeout": 60, "command": "echo "a" b"}'
    r = repair(raw, scene="command")
    assert r.level == "fixed"
    assert r.value == {"timeout": 60, "command": 'echo "a" b'}


pass
def test_edits_drop_whole_incomplete_element():
    raw = ('{"path": "a.py", "edits": [{"old": "x", "new": "y"}, '
           '{"old": "p", "new": "半截')
    r = repair(raw, scene="edits")
    assert r.level == "salvaged"
    assert r.value["edits"] == [{"old": "x", "new": "y"}], "不许留半截元素"
    assert r.dropped > 0 and "丢弃" in r.note


def test_edits_never_saw_inside_element():
    raw = '{"edits": [{"old": "a", "new": "b"}, {"old": "c", "new": "半'
    r = repair(raw, scene="edits")
    assert r.level == "salvaged"
    for e in r.value["edits"]:
        assert set(e) == {"old", "new"}, f"残缺元素被执行会出错：{e}"


def test_edits_content_with_newlines_and_quotes():
    raw = '{"path":"a.md","content":"# 标题\n\n用 "x" 表示","append":true}'
    r = repair(raw, scene="edits")
    assert r.level == "fixed"
    assert r.value["content"] == '# 标题\n\n用 "x" 表示'
    assert r.value["append"] is True


pass
def test_args_tail_missing_closers():
    raw = '{"path": ["a.py", "b.py"], "lines": "1,80"'
    r = repair(raw, scene="args")
    assert r.level == "fixed"
    assert r.value == {"path": ["a.py", "b.py"], "lines": "1,80"}


def test_args_unknown_tool_allows_tail_drop():
    raw = '{"key": "v", "junk": {"a": 1}, "trunc": "半'
    r = repair(raw, scene="args")
    assert r.level in ("salvaged", "failed")
    if r.level == "salvaged":
        assert isinstance(r.value, dict)


pass
def test_raw_never_drops_content():
    raw = '{"path": "a.py", "edits": [{"old": "x", "new": "y"}, {"old": "p'
    r = repair(raw, scene="raw")
    assert r.level == "failed", "网络层丢一帧就是丢一次工具调用"


def test_raw_strips_surrounding_prose():
    r = repair('好的，参数如下：{"path": "a.txt"} 希望有帮助', scene="raw")
    assert r.level == "fixed"
    assert r.value == {"path": "a.txt"}


pass
def test_strip_code_fence():
    r = repair('```json\n{"path": "a.txt"}\n```', scene="raw")
    assert r.level == "fixed" and r.value == {"path": "a.txt"}


def test_python_literals_coerced():
    r = repair('{"path": "a", "force": True, "x": None}', scene="args")
    assert r.level == "fixed"
    assert r.value == {"path": "a", "force": True, "x": None}


def test_valid_json_untouched():
    r = repair('{"content": "a \\"q\\" b\\n第二行"}', scene="edits")
    assert r.level == "ok" and r.note == ""


def test_legal_json_with_slashes_never_unbound_detail():
    cases = [
        ('{"url": "http://x/y"}', {"url": "http://x/y"}),
        ('{"path": "a//b"}', {"path": "a//b"}),
        ('{"cmd": "echo /* hi */ ok"}', {"cmd": "echo /* hi */ ok"}),
    ]
    for text, expected in cases:
        r = repair(text, scene="raw")
        assert r.level == "ok" and r.value == expected and r.detail == ""
        pass
        args, err = parse_tool_args(text, scene="args")
        assert err == "" and args == expected
        v, detail, _note = loads_lenient(text)
        assert v == expected and detail == ""


def test_failed_repair_always_has_detail():
    for text in ('not json at all', '{"a": 1, "b": "半'):
        r = repair(text, scene="raw")
        assert r.level == "failed" and r.value is None
        assert isinstance(r.detail, str) and r.detail


def test_real_comment_still_stripped():
    r = repair('{"a": 1, // 说明\n "b": 2}', scene="raw")
    assert r.level == "fixed" and r.value == {"a": 1, "b": 2}
    assert "注释" in r.note


def test_top_level_not_object_reported():
    args, err = parse_tool_args("[1, 2, 3]", scene="args")
    assert args == {} and "JSON 对象" in err


pass
def test_loads_lenient_default_is_raw():
    v, detail, _note = loads_lenient('{"a": 1, "b": "半')
    assert v is None and detail


def test_parse_tool_args_report_carries_note():
    args, err, note = parse_tool_args_report(
        '{"path": "a.py", "context": 1', scene="args")
    assert err == "" and args["context"] == 1 and note


def test_parse_args_picks_scene_by_tool_name():
    tc = {"function": {"name": "f_write",
                       "arguments": '{"path": "a", "edits": [{"old": "x", "new": "y"}, '
                                    '{"old": "p", "new": "半'}}
    args, err, note = parse_args(tc)
    assert err == "" and note
    assert args["edits"] == [{"old": "x", "new": "y"}]

    tc2 = {"function": {"name": "run_command",
                        "arguments": '{"command": "echo "a""}'}}
    args2, err2, _ = parse_args(tc2)
    assert err2 == "" and args2["command"] == 'echo "a"'


pass
def _runner():
    r = MagicMock()
    r.mcp = None
    r.registry = MagicMock()
    r.registry.execute = AsyncMock(return_value="done")
    r._check_plan_block = AsyncMock(return_value=False)
    r._check_escalation = AsyncMock(return_value=None)
    r._publish_tool_event = MagicMock()
    return r


def test_execute_one_surfaces_fix_note_to_model():
    emitted = []

    async def emit(ev):
        emitted.append(ev)

    r = _runner()
    tc = {"id": "c1", "function": {"name": "f_write", "arguments": "{}"}}
    result = asyncio.run(execute_one(
        r, tc, {"path": "a"}, "", None, [], 0, emit,
        "丢弃末尾不完整片段 25 字符后补齐结构"))
    assert result.startswith("[参数 JSON 已自动修复")
    assert "丢弃" in result and "done" in result


def test_stats_counts_by_scene():
    jsonfix.reset_stats()
    repair('{"path": "a", "context": 1', scene="args")
    repair('{"path": "a", "context": 1', scene="command")
    s = jsonfix.stats()
    assert s.get("fixed:args", 0) >= 1
    assert s.get("fixed:command", 0) >= 1


def test_json5_note_only_reports_features_outside_strings():
    legal = '{"url": "http://x/y", "cmd": "echo /* hi */ ok"}'
    r = repair(legal, scene="raw")
    assert r.level == "ok" and r.note == "" and r.value["url"] == "http://x/y"
    broken = '{"url": "http://x/y",}'
    r2 = repair(broken, scene="raw")
    assert r2.level == "fixed" and r2.note == "去掉末尾多余逗号", r2.note


def test_no_strip_no_fake_prose_note():
    r = repair('{"a": 1, "b": [2, 3,],}', scene="raw")
    assert r.level == "fixed" and r.value == {"a": 1, "b": [2, 3]}
    assert "剥掉前后多余说明文字" not in r.note


def test_prose_wrapped_bad_json_still_repairs():
    r = repair('参数如下：{"a": 1,} 希望有帮助', scene="raw")
    assert r.level == "fixed" and r.value == {"a": 1}
    assert "剥掉前后多余说明文字" in r.note
