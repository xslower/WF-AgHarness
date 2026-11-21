from __future__ import annotations

import json

import pytest

from app.util.jsonfix import reset_stats
from app.workflow.errors import WorkflowError
from app.workflow.expr import json_value, parse_any, yaml_value
from app.workflow.nodes.llm_parse import parse_output
pass
from app.workflow.nodes.jsonargs import parse_args


pass

def test_parse_output_fenced_json_with_trailing_comma_repairs():
    raw = '分析如下\n```json\n{"a": 1, "b": [1, 2,],}\n```'
    out, err, fb = parse_output(raw, "json", allow_fallback=False)
    assert err == "" and fb is False
    assert json.loads(out) == {"a": 1, "b": [1, 2]}


def test_parse_output_fenced_json_python_literals_coerced():
    raw = '```json\n{"ok": True, "x": None}\n```'
    out, err, _ = parse_output(raw, "json", allow_fallback=False)
    assert err == ""
    assert json.loads(out) == {"ok": True, "x": None}


def test_parse_output_yaml_written_as_json_repairs():
    raw = '```yaml\n{"title": "报告", "n": 3,}\n```'
    out, err, _ = parse_output(raw, "yaml", allow_fallback=False)
    assert err == ""
    assert json.loads(out) == {"title": "报告", "n": 3}


def test_parse_output_bare_broken_json_repairs_without_retry():
    raw = '{"title": "月度报告", "items": [1, 2, 3]'
    out, err, _ = parse_output(raw, "json", allow_fallback=False)
    assert err == ""
    assert json.loads(out) == {"title": "月度报告", "items": [1, 2, 3]}


def test_parse_output_fallback_scans_after_repair():
    raw = '我的分析是……\n结论：{"pass": true, "score": 87,}'
    out, err, fb = parse_output(raw, "json", allow_fallback=True)
    assert err == ""
    assert fb is True
    assert json.loads(out) == {"pass": True, "score": 87}


def test_parse_output_unrepairable_still_errors():
    raw = "我就是不给你结构化结果"
    out, err, _ = parse_output(raw, "json", allow_fallback=False)
    assert out == "" and err != ""


def test_parse_output_repair_note_reaches_log_callback():
    notes: list[str] = []
    raw = '```json\n{"a": 1,}\n```'
    out, err, _ = parse_output(raw, "json", allow_fallback=False,
                               log_repair=notes.append)
    assert err == "" and json.loads(out) == {"a": 1}
    assert notes and "逗号" in notes[0]


pass

def test_json_value_repairs_broken_json():
    v = json_value('{"a": [1, 2,], "b": True}', None)
    assert v == {"a": [1, 2], "b": True}


def test_json_value_plain_text_still_default():
    assert json_value("这不是 JSON", None) is None


def test_yaml_value_repairs_jsonish_yaml():
    assert yaml_value('{"x": 1, "y": [1,],}', None) == {"x": 1, "y": [1]}


def test_parse_any_repairs_broken_json_for_raw_filter():
    assert parse_any('{"k": "v",}', None) == {"k": "v"}


pass

def test_tool_args_json_repaired():
    args = parse_args("t1", '{"path": "o.txt", "content": "hi",}')
    assert args == {"path": "o.txt", "content": "hi"}


def test_tool_args_json_unrepairable_raises():
    with pytest.raises(WorkflowError):
        parse_args("t1", "完全不是 JSON")


def test_tool_args_json_not_object_raises():
    with pytest.raises(WorkflowError):
        parse_args("t1", "[1, 2]")


def test_workflow_inputs_json_repaired():
    from app.workflow.nodes.workflow import run_workflow

    class Ctx:
        id = "wf1"
    pass
    pass
    text = '{"shot": "镜头1", "style": "国风",}'
    obj, detail, _ = __import__("app.util.jsonfix", fromlist=["loads_lenient"]) \
        .loads_lenient(text, scene="raw")
    assert detail == "" and obj == {"shot": "镜头1", "style": "国风"}
    del run_workflow, Ctx


pass

def test_repair_stats_increment():
    reset_stats()
    from app.util.jsonfix import stats
    parse_output('{"a": 1,}', "json", allow_fallback=False)
    assert stats().get("fixed:raw", 0) + stats().get("fixed:json5", 0) >= 1


pass

def test_parse_output_fenced_yaml_tab_indent_repairs():
    raw = '```yaml\ntitle: 报告\nitems:\n\t- 开场\n\t- 收尾\n```'
    out, err, _ = parse_output(raw, "yaml", allow_fallback=False)
    assert err == ""
    assert json.loads(out) == {"title": "报告", "items": ["开场", "收尾"]}


def test_parse_output_fenced_yaml_fullwidth_colon_repairs():
    raw = '```yaml\ntitle：报告\nn: 3\n```'
    out, err, _ = parse_output(raw, "yaml", allow_fallback=False)
    assert err == "" and json.loads(out) == {"title": "报告", "n": 3}


def test_parse_output_fenced_yaml_missing_space_after_colon_repairs():
    out, err, _ = parse_output('```yaml\na:1\nb: 2\n```', "yaml",
                               allow_fallback=False)
    assert err == "" and json.loads(out) == {"a": 1, "b": 2}


def test_parse_output_yaml_fallback_keeps_all_fields():
    raw = '前言\na: 1\nb:\n  - x\n  - y\n'
    out, err, fb = parse_output(raw, "yaml", allow_fallback=True)
    assert err == "" and fb is True
    assert json.loads(out) == {"a": 1, "b": ["x", "y"]}


def test_parse_output_yaml_fallback_accepts_repaired_candidates():
    raw = '分析如下\na：1\nb：2\n'
    out, err, fb = parse_output(raw, "yaml", allow_fallback=True)
    assert err == "" and fb is True
    assert json.loads(out) == {"a": 1, "b": 2}


def test_parse_output_yaml_repair_note_logged():
    notes: list[str] = []
    raw = '```yaml\ntitle：报告\nn: 3\n```'
    out, err, _ = parse_output(raw, "yaml", allow_fallback=False,
                               log_repair=notes.append)
    assert err == "" and json.loads(out)["title"] == "报告"
    assert notes and "中文冒号" in notes[0]


@pytest.mark.parametrize("fmt,body", [
    ("json", '```json\n42\n```'),
    ("json", '```json\n"一段文本"\n```'),
    ("yaml", '```yaml\n就是一段话\n```'),
])
def test_parse_output_rejects_scalar_top_level(fmt, body):
    out, err, _ = parse_output(body, fmt, allow_fallback=False)
    assert out == "" and "顶层" in err


def test_yaml_value_repairs_tab_and_fullwidth_colon():
    assert yaml_value('a:\n\tb: 1\n', None) == {"a": {"b": 1}}
    assert yaml_value('title：报告\nn: 3\n', None) == {"title": "报告", "n": 3}
    assert yaml_value('a:1\nb: 2\n', None) == {"a": 1, "b": 2}


def test_yaml_value_plain_text_still_default():
    assert yaml_value("就是一段话", "fallback") == "fallback"
