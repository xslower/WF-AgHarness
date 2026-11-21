from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from app.provider.gateway import Chunk
import app.tools.builtin.exec.shell as shell
from app.tools.text_limit import MAX_OUTPUT, MAX_OUTPUT_HARD
from app.tools import ToolContext
from app.workflow import WorkflowEngine, WorkflowError


class FakeGw:
    def __init__(self):
        self.config = SimpleNamespace(providers=[], settings=SimpleNamespace(policy="yolo"))

    async def chat_stream(self, messages, **kw):
        yield Chunk(type="text", text="ok")


class Reg:
    schemas: list = []

    def __init__(self):
        self.calls: list[dict] = []

    async def execute(self, name, args, ctx):
        self.calls.append(dict(args))
        return "ok"


def build(tmp_path, reg=None):
    return WorkflowEngine(gateway=FakeGw(), registry=reg or Reg(),
                          workspace=str(tmp_path), workflows_dir=tmp_path / "wf")


pass
def _run_tool(args, timeout=60):
    ctx = ToolContext(".")
    from app.tools.builtin import build_tools
    reg = build_tools()
    return asyncio.run(reg.execute("run_command", args, ctx))


@pytest.mark.parametrize("n", [50000, 70000, 625000])
def test_single_huge_line_is_not_truncated(n):
    cmd = "head -c %d /dev/zero | tr '\\0' x" % n
    data = json.loads(_run_tool({"command": cmd, "meta": True, "max_output": 0,
                                 "split_stderr": True, "timeout": 60}))
    assert data.get("error") is None, data.get("error")
    assert len(data["output"]) == n
    assert data["truncated"] is False


def test_meta_truncation_is_structured_not_text_marker():
    cmd = "head -c 40000 /dev/zero | tr '\\0' x"
    data = json.loads(_run_tool({"command": cmd, "meta": True}))
    assert len(data["output"]) == MAX_OUTPUT
    assert "截断" not in data["output"] and "省略" not in data["output"]
    assert "[" not in data["output"]
    assert data["truncated"] is True and data["original_chars"] == 40000


def test_meta_truncation_keeps_tail_conclusion():
    cmd = "printf 'HEAD'; head -c 35000 /dev/zero | tr '\\0' x; printf 'FAILED tests/a.py::test_x'"
    data = json.loads(_run_tool({"command": cmd, "meta": True}))
    assert data["output"].startswith("HEAD")
    assert data["output"].endswith("FAILED tests/a.py::test_x")
    assert data["truncated"] is True


def test_hard_cap_errors_instead_of_eating_memory(monkeypatch):
    monkeypatch.setattr(shell, "MAX_OUTPUT_HARD", 1024)
    cmd = "head -c 200000 /dev/zero | tr '\\0' x"
    data = json.loads(_run_tool({"command": cmd, "meta": True, "max_output": 0}))
    assert "硬顶" in str(data.get("error"))


def test_chat_mode_keeps_visible_marker():
    cmd = "printf 'HEAD'; head -c 31000 /dev/zero | tr '\\0' x; printf 'FAILED tests/a.py::test_x'"
    out = _run_tool({"command": cmd})
    assert "中间省略" in out and len(out) < 31000
    assert out.startswith("[exit 0]\nHEAD")
    assert out.endswith("FAILED tests/a.py::test_x")


def test_stderr_does_not_pollute_output():
    data = json.loads(_run_tool({"command": "echo data; echo log >&2", "meta": True,
                                 "split_stderr": True}))
    assert data["output"].strip() == "data"
    assert "log" in data["stderr"]


def test_timeout_kills_process_group():
    data = json.loads(_run_tool({"command": "python3 -c 'import time; time.sleep(30)'",
                                 "timeout": 1, "meta": True}))
    assert "超时" in str(data.get("error"))


pass
def test_human_next_continues_chain(tmp_path):
    eng = build(tmp_path)
    nodes = [
        {"id": "w1", "type": "write", "path": "1-before.txt", "content": "b", "next": "h1"},
        {"id": "h1", "type": "human", "title": "确认", "options": "批准\n驳回", "next": "w2"},
        {"id": "w2", "type": "write", "path": "1-after.txt", "content": "a", "next": "w3"},
        {"id": "w3", "type": "write", "path": "1-last.txt", "content": "l"},
    ]
    eng.save({"name": "t", "nodes": nodes})
    rec = asyncio.run(eng.execute_sync("t", {}, human_mode="auto-approve"))
    assert rec.status == "done", rec.error
    for name in ("1-before.txt", "1-after.txt", "1-last.txt"):
        assert (tmp_path / name).exists(), name


def test_human_without_any_exit_is_rejected_before_run(tmp_path):
    eng = build(tmp_path)
    nodes = [{"id": "h1", "type": "human", "title": "确认", "options": "批准"}]
    eng.save({"name": "t", "nodes": nodes})
    with pytest.raises(WorkflowError) as err:
        asyncio.run(eng.execute_sync("t", {}, human_mode="auto-approve"))
    assert "h1" in str(err.value) and "出口" in str(err.value)


pass
def test_next_array_is_fanout(tmp_path):
    reg = Reg()
    eng = build(tmp_path, reg)
    eng.save({"name": "fan", "nodes": [
        {"id": "r", "type": "tool", "tool": "f_read", "argsJson": "{}",
         "next": ["a1", "b1"]},
        {"id": "a1", "type": "tool", "tool": "f_read", "argsJson": "{}"},
        {"id": "b1", "type": "tool", "tool": "f_read", "argsJson": "{}"},
    ]})
    rec = asyncio.run(eng.execute_sync("fan", {}, parallel_mode="agent"))
    assert rec.status == "done", rec.error
    assert len(reg.calls) == 3


def test_fanout_mixing_control_node_is_clear(tmp_path):
    eng = build(tmp_path)
    with pytest.raises(WorkflowError) as err:
        eng.save({"name": "mix", "nodes": [
            {"id": "r", "type": "tool", "tool": "f_read", "argsJson": "{}",
             "next": ["a1", "b1"]},
            {"id": "a1", "type": "tool", "tool": "f_read", "argsJson": "{}"},
            {"id": "b1", "type": "human", "title": "t", "options": "ok", "next": ""},
        ]})
    assert "map" in str(err.value)


pass
def test_max_visits_stops_normally_with_warning(tmp_path):
    eng = build(tmp_path)
    rec = asyncio.run(eng.execute_definition({"name": "t", "nodes": [
        {"id": "b1", "type": "write", "path": "o.txt", "content": "x", "next": "c1"},
        {"id": "c1", "type": "condition", "expr": "1 == 1",
         "true": "b1", "false": "", "maxVisits": 2},
    ]}))
    assert rec.status == "done", rec.error
    assert any(w["code"] == "max-visits" for w in rec.warnings)


def test_max_visits_takes_false_branch(tmp_path):
    eng = build(tmp_path)
    rec = asyncio.run(eng.execute_definition({"name": "t", "nodes": [
        {"id": "b1", "type": "write", "path": "loop.txt", "content": "x", "next": "c1"},
        {"id": "c1", "type": "condition", "expr": "True",
         "true": "b1", "false": "end", "maxVisits": 2},
        {"id": "end", "type": "write", "path": "done.txt", "content": "end"},
    ]}))
    assert rec.status == "done", rec.error
    assert (tmp_path / "done.txt").exists()


pass
def test_undefined_var_blocks_before_run(tmp_path):
    eng = build(tmp_path)
    eng.save({"name": "t", "nodes": [
        {"id": "w", "type": "write", "path": "o.txt", "content": "${not_exist_abc}"}]})
    with pytest.raises(WorkflowError) as err:
        asyncio.run(eng.execute_sync("t", {}))
    assert "not_exist_abc" in str(err.value)


def test_comment_lines_are_not_scanned(tmp_path):
    eng = build(tmp_path)
    eng.save({"name": "t", "nodes": [
        {"id": "c", "type": "code",
         "code": "# 用法：${inputs.x} 会被替换\nprint('ok')"}]})
    rec = asyncio.run(eng.execute_sync("t", {}, human_mode="auto-approve"))
    assert rec.status in ("done", "failed")
    assert "启动前检查未通过" not in (rec.error or "")


pass
def test_map_collect_default_keeps_text_output(tmp_path):
    eng = build(tmp_path)
    rec = asyncio.run(eng.execute_definition({"name": "t", "nodes": [
        {"id": "m1", "type": "map", "items": '["a","b"]', "body": "b1"},
        {"id": "b1", "type": "write", "path": "out-${__item__}.txt", "content": "x"},
    ]}))
    assert rec.status == "done", rec.error
    assert rec.node_states["m1"]["output"] == "a\n\nb"


def test_map_json_output_exposes_items_and_results(tmp_path):
    class JsonReg(Reg):
        async def execute(self, name, args, ctx):
            return json.dumps({"k": "a", "v": 1, "note": "第一段\n\n第二段"},
                              ensure_ascii=False)

    eng = build(tmp_path, JsonReg())
    nodes = [
        {"id": "m1", "type": "map", "items": '["a","b"]', "body": "t1",
         "collect": "t1", "output": "json", "next": "w"},
        {"id": "t1", "type": "tool", "tool": "fake", "argsJson": "{}"},
        {"id": "w", "type": "write", "path": "summary.txt",
         "content": "${m1.n} ${m1.results.1.v}"},
    ]
    rec = asyncio.run(eng.execute_definition({"name": "t", "nodes": nodes}))
    assert rec.status == "done", rec.error
    data = json.loads(rec.node_states["m1"]["output"])
    assert data["items"] == ["a", "b"] and len(data["results"]) == 2
    pass
    assert data["results"][1]["v"] == 1
    pass
    assert "\n\n" in data["results"][1]["note"]
    assert (tmp_path / "summary.txt").read_text("utf-8").strip() == "2 1"


def test_map_text_output_unchanged(tmp_path):
    eng = build(tmp_path)
    rec = asyncio.run(eng.execute_definition({"name": "t", "nodes": [
        {"id": "m1", "type": "map", "items": '["a","b"]', "body": "b1"},
        {"id": "b1", "type": "write", "path": "out-${__item__}.txt", "content": "x"},
    ]}))
    assert rec.status == "done", rec.error
    assert rec.node_states["m1"]["output"] == "a\n\nb"


pass
def test_warnings_reach_run_record(tmp_path):
    eng = build(tmp_path)
    rec = asyncio.run(eng.execute_definition({"name": "t", "nodes": [
        {"id": "b1", "type": "write", "path": "o.txt", "content": "x", "next": "c1"},
        {"id": "c1", "type": "condition", "expr": "True",
         "true": "b1", "false": "", "maxVisits": 2},
    ]}))
    assert rec.status == "done"
    assert rec.to_dict()["warnings"]
    assert rec.to_meta()["warnings"]
