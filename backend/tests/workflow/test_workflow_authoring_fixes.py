from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.provider.gateway import Chunk
from app.workflow import WorkflowEngine, WorkflowError
from app.workflow.expr import yaml_value
from app.workflow.vars import substitute_expr


class FakeGw:
    def __init__(self):
        self.config = SimpleNamespace(providers=[], settings=SimpleNamespace(policy="yolo"))

    async def chat_stream(self, messages, **kw):
        yield Chunk(type="text", text="ok")


class FakeRegistry:
    schemas: list = []

    def __init__(self, results=None):
        self.results = results or {}
        self.calls: list[tuple[str, dict]] = []

    async def execute(self, name, args, ctx):
        self.calls.append((name, args))
        if name in self.results:
            return self.results[name]
        return "ok"


def build(tmp_path, reg=None):
    return WorkflowEngine(gateway=FakeGw(), registry=reg or FakeRegistry(),
                          workspace=str(tmp_path), workflows_dir=tmp_path / "wf")


pass
def test_raw_parses_yaml_text():
    v = {"inputs": {}, "output_paths": {},
         "outputs": {"rev": "pass: true\nscore: 85\nnotes:\n  - 光线硬\n"}}
    expr = substitute_expr("${rev!raw}['pass'] == True", v)
    assert expr == "{'pass': True, 'score': 85, 'notes': ['光线硬']}['pass'] == True"


def test_raw_plain_text_stays_string():
    v = {"inputs": {}, "output_paths": {},
         "outputs": {"rep": "第一段说明\n第二段说明\n"}}
    expr = substitute_expr("len(${rep!raw}) > 0", v)
    assert "第一段说明" in expr and expr.startswith("len('")


def test_yaml_helper_and_yaml_value():
    assert yaml_value("a: 1\nb:\n  - x\n") == {"a": 1, "b": ["x"]}
    assert yaml_value('{"a": 1}') == {"a": 1}
    assert yaml_value("就是一段话") == None


pass
async def test_map_items_from_raw_expression(tmp_path):
    scenes = {"scenes": [{"shot": "开场"}, {"shot": "结尾"}]}
    nodes = [
        {"id": "s1", "type": "code", "code": "pass", "next": "m1"},
        {"id": "m1", "type": "map", "items": "${s1!raw}['scenes']", "body": "b1",
         "collect": "b1", "next": ""},
        {"id": "b1", "type": "code", "code": "pass"},
    ]
    reg = FakeRegistry({"run_command": json.dumps(scenes, ensure_ascii=False)})
    pass
    eng = build(tmp_path, reg=reg)
    rec = await eng.execute_definition({"name": "t", "nodes": nodes})
    assert rec.status == "done", rec.error
    pass
    assert rec.node_states["m1"]["status"] == "done"
    assert rec.node_states["m1"]["output"]


async def test_map_items_plain_text_still_splits(tmp_path):
    nodes = [{"id": "m1", "type": "map", "items": "a, b, c", "body": "b1",
              "collect": "b1", "next": ""},
             {"id": "b1", "type": "write", "path": "${__item__}.txt",
              "content": "${__i__}"}]
    eng = build(tmp_path)
    rec = await eng.execute_definition({"name": "t", "nodes": nodes})
    assert rec.status == "done", rec.error
    for name in ("a", "b", "c"):
        assert (tmp_path / f"{name}.txt").exists()


pass
async def test_exec_nonzero_fails_by_default(tmp_path):
    reg = FakeRegistry({"run_command": "[exit 2] boom"})
    nodes = [{"id": "e1", "type": "exec", "command": "run"}]
    rec = await build(tmp_path, reg=reg).execute_definition({"name": "t", "nodes": nodes})
    assert rec.status == "failed"
    assert "exec 节点失败" in rec.error


async def test_exec_allow_fail_continues(tmp_path):
    reg = FakeRegistry({"run_command": "[exit 2] gate_failed"})
    nodes = [{"id": "e1", "type": "exec", "command": "run", "allowFail": True,
              "next": "w1"},
             {"id": "w1", "type": "write", "path": "after.txt", "content": "${e1}"}]
    rec = await build(tmp_path, reg=reg).execute_definition({"name": "t", "nodes": nodes})
    assert rec.status == "done", rec.error
    body = (tmp_path / "after.txt").read_text("utf-8")
    assert "[exit 2]" in body


async def test_exec_allow_fail_accepts_string_true(tmp_path):
    reg = FakeRegistry({"run_command": "[exit 1] x"})
    nodes = [{"id": "e1", "type": "exec", "command": "run", "allowFail": "true"}]
    rec = await build(tmp_path, reg=reg).execute_definition({"name": "t", "nodes": nodes})
    assert rec.status == "done", rec.error


pass
async def test_max_visits_reaches_limit_and_stops_normally(tmp_path):
    nodes = [{"id": "b1", "type": "write", "path": "o.txt", "content": "x", "next": "c1"},
             {"id": "c1", "type": "condition", "expr": "1 == 1",
              "true": "b1", "false": "", "maxVisits": 2}]
    rec = await build(tmp_path).execute_definition({"name": "t", "nodes": nodes})
    assert rec.status == "done", rec.error
    warn = [w for w in rec.warnings if w["code"] == "max-visits"]
    assert warn and warn[0]["node"] == "c1"
    assert "上限 2" in warn[0]["message"]


pass
async def test_human_inside_map_body_keeps_loop_vars(tmp_path):
    import asyncio

    nodes = [
        {"id": "m1", "type": "map", "items": "镜1, 镜2", "body": "h1",
         "collect": "w1", "next": ""},
        {"id": "h1", "type": "human", "title": "确认第 ${__i__} 镜：${__item__}",
         "options": "批准\n驳回", "true": "w1", "false": "w2"},
        {"id": "w1", "type": "write", "path": "${__item__}.txt",
         "content": "index=${__i__}"},
        {"id": "w2", "type": "write", "path": "skip-${__i__}.txt", "content": "skip"},
    ]
    eng = build(tmp_path)
    rec = eng.start_definition({"name": "t", "nodes": nodes}, parallel_mode="sequential")
    pass
    seen_titles = []
    for expected in ("镜1", "镜2"):
        for _ in range(100):
            gate = eng.human.pending(rec.id)
            if gate:
                break
            await asyncio.sleep(0.02)
        assert gate, "闸门没有挂起"
        seen_titles.append(gate["title"])
        assert eng.human.decide(rec.id, gate["node_id"], "批准")
        pass
        for _ in range(100):
            if rec.status != "running":
                break
            pending = eng.human.pending(rec.id)
            if pending and expected == "镜1":
                break
            await asyncio.sleep(0.02)
    for _ in range(100):
        if rec.status != "running":
            break
        await asyncio.sleep(0.02)
    assert rec.status == "done", rec.error
    assert seen_titles == ["确认第 0 镜：镜1", "确认第 1 镜：镜2"]
    assert (tmp_path / "镜1.txt").read_text("utf-8") == "index=0"
    assert (tmp_path / "镜2.txt").read_text("utf-8") == "index=1"


pass
async def test_map_items_dict_raises_clear_error(tmp_path):
    nodes = [
        {"id": "s0", "type": "code", "code": "pass", "next": "m1"},
        {"id": "m1", "type": "map", "items": "${s0!raw}", "body": "b1",
         "next": ""},
        {"id": "b1", "type": "code", "code": "pass"},
    ]
    reg = FakeRegistry({"run_command": '{"scenes": [{"id": 1}]}'})


async def test_map_items_raw_field_selection_works(tmp_path):
    nodes = [
        {"id": "s0", "type": "code", "code": "pass", "next": "m1"},
        {"id": "m1", "type": "map", "items": "${s0!raw}['scenes']", "body": "b1",
         "collect": "b1", "next": ""},
        {"id": "b1", "type": "write", "path": "s-${__i__}.txt",
         "content": "${__item__}"},
    ]
    reg = FakeRegistry({"run_command": '{"scenes": [{"id": 1}, {"id": 2}]}'})
    rec = await build(tmp_path, reg=reg).execute_definition({"name": "t", "nodes": nodes})
    assert rec.status == "done", rec.error
    assert (tmp_path / "s-0.txt").read_text("utf-8") == '{"id": 1}'
    assert (tmp_path / "s-1.txt").read_text("utf-8") == '{"id": 2}'


def test_substitute_supports_raw_suffix():
    from app.workflow.vars import substitute
    v = {"inputs": {}, "output_paths": {},
         "outputs": {"s0": "shot: 开场\nid: 1\n"}}
    assert substitute("第 ${s0!raw} 镜", v).startswith('第 {"shot"')
    pass
    assert substitute("第 ${s0} 镜", v) == "第 shot: 开场\nid: 1\n 镜"


async def test_read_file_node_has_no_line_numbers(tmp_path):
    from app.tools.builtin.fs import f_read

    class RealFs(FakeRegistry):
        async def execute(self, name, args, ctx):
            if name == "f_read":
                from app.tools import ToolContext
                return f_read(args["path"], ToolContext(str(tmp_path)),
                                 raw=args.get("raw", False))
            return "ok"

    (tmp_path / "a.json").write_text('{"a": 1}', "utf-8")
    nodes = [{"id": "r1", "type": "read_file", "path": "a.json", "next": "w1"},
             {"id": "w1", "type": "write", "path": "copy.json", "content": "${r1}"}]
    rec = await build(tmp_path, reg=RealFs()).execute_definition(
        {"name": "t", "nodes": nodes})
    assert rec.status == "done", rec.error
    assert json.loads(rec.node_states["r1"]["output"]) == {"a": 1}
    assert (tmp_path / "copy.json").read_text("utf-8") == '{"a": 1}'


async def test_read_file_tool_no_line_numbers_by_default(tmp_path):
    from app.tools import ToolContext
    from app.tools.builtin.fs import f_read
    (tmp_path / "b.txt").write_text("x\ny\n", "utf-8")
    ctx = ToolContext(str(tmp_path))
    assert f_read("b.txt", ctx) == "x\ny"
    assert f_read("b.txt", ctx, linenos=True).startswith("1\tx")


async def test_exec_output_has_no_exit_prefix(tmp_path):
    class Real(FakeRegistry):
        async def execute(self, name, args, ctx):
            return json.dumps({"ok": True, "exit": 0,
                               "output": '{"pass": true}\n'})

    nodes = [{"id": "e1", "type": "exec", "command": "echo", "next": "c1"},
             {"id": "c1", "type": "condition", "expr": "${e1!raw}['pass'] == True",
              "true": "w1", "false": "w2"},
             {"id": "w1", "type": "write", "path": "ok.txt", "content": "ok"},
             {"id": "w2", "type": "write", "path": "no.txt", "content": "no"}]
    rec = await build(tmp_path, reg=Real()).execute_definition({"name": "t", "nodes": nodes})
    assert rec.status == "done", rec.error
    assert rec.node_states["e1"]["output"].startswith('{"pass"')
    assert (tmp_path / "ok.txt").exists()


async def test_allow_fail_from_real_tool_meta(tmp_path):
    class Gate(FakeRegistry):
        async def execute(self, name, args, ctx):
            return json.dumps({"ok": False, "exit": 1, "output": "gate: fail"})

    nodes = [{"id": "e1", "type": "exec", "command": "x", "allowFail": True,
              "next": "w1"},
             {"id": "w1", "type": "write", "path": "out.txt", "content": "${e1}"}]
    rec = await build(tmp_path, reg=Gate()).execute_definition({"name": "t", "nodes": nodes})
    assert rec.status == "done", rec.error
    body = (tmp_path / "out.txt").read_text("utf-8")
    assert body.startswith("[exit 1]")
    assert "gate: fail" in body


async def test_json_helper_tolerates_exit_prefix():
    from app.workflow.expr import json_value, parse_any
    assert json_value('[exit 0]\n{"a": 1}') == {"a": 1}
    assert parse_any('[exit 2]\npass: true\n') == {"pass": True}


pass
async def test_workflow_tool_run_accepts_human_mode(tmp_path):
    from app.tools.builtin.workflow_edit import workflow_cmd

    nodes = [{"id": "h1", "type": "human", "title": "确认", "options": "批准\n驳回",
              "true": "w1", "false": "w1"},
             {"id": "w1", "type": "write", "path": "ok.txt", "content": "ok"}]
    eng = build(tmp_path)
    eng.dir.mkdir(parents=True, exist_ok=True)
    (eng.dir / "g.json").write_text(json.dumps({"name": "g", "nodes": nodes}), "utf-8")

    async def start(name, text, human, start_node="", parallel=""):
        try:
            rec = eng.start_definition(eng.get(name), {"input": text},
                                       human_mode=human, start_node=start_node,
                                       parallel_mode=parallel)
        except Exception as e:
            return json.dumps({"error": f"工作流启动失败: {e}"}, ensure_ascii=False)
        return json.dumps({"run_id": rec.id, "status": rec.status})

    async def wait(rid, t, detail=False):
        data = await eng.wait_run(rid, t)
        if data.get("status") == "failed":
            return json.dumps({"error": f"工作流失败: {data.get('error') or ''}"})
        return data.get("final") or ""

    ctx = SimpleNamespace(workflow_start=start, workflow_wait=wait)
    started = json.loads(await workflow_cmd(ctx, action="run", name="g", input="x",
                                           human="auto-approve"))
    ok = await workflow_cmd(ctx, action="wait", id=started["run_id"])
    assert "error" not in ok
    bad = await workflow_cmd(ctx, action="run", name="g", input="x", human="deny")
    assert "人工闸门" in json.loads(bad)["error"]


async def test_workflow_tool_rejects_bad_human_mode(tmp_path):
    from app.tools.builtin.workflow_edit import workflow_cmd

    ctx = SimpleNamespace(workflow_start=lambda *a: None)
    msg = await workflow_cmd(ctx, action="run", name="g", input="x", human="maybe")
    assert "human 只能是" in msg


pass
def test_parse_any_strips_exit_prefix():
    from app.workflow.expr import parse_any

    assert parse_any('[exit 0]\n{"pass": true}') == {"pass": True}
    assert parse_any("[exit 2]\nnot json") == "not json"


def test_substitute_raw_in_plain_text():
    from app.workflow.vars import substitute

    v = {"inputs": {}, "output_paths": {},
         "outputs": {"s0": '{"scenes": [{"shot": "开场"}]}'}}
    out = substitute("确认分镜：${s0!raw}", v)
    assert out == '确认分镜：{"scenes": [{"shot": "开场"}]}'


async def test_map_items_dict_raises_clear_error_via_llm(tmp_path):
    nodes = [{"id": "s0", "type": "llm", "prompt": "p", "format": "json",
              "tools": "off", "next": "m1"},
             {"id": "m1", "type": "map", "items": "${s0!raw}", "body": "b1",
              "collect": "b1", "next": ""},
             {"id": "b1", "type": "write", "path": "o.txt", "content": "x"}]

    class JsonGw(FakeGw):
        async def chat_stream(self, messages, **kw):
            yield Chunk(type="text", text='{"scenes": [{"id": 1}]}')

    eng = WorkflowEngine(gateway=JsonGw(), registry=FakeRegistry(),
                         workspace=str(tmp_path), workflows_dir=tmp_path / "wf")
    rec = await eng.execute_definition({"name": "t", "nodes": nodes})
    assert rec.status == "failed"
    assert "不是列表" in rec.error


async def test_map_items_yaml_and_index_work(tmp_path):
    nodes = [{"id": "s0", "type": "llm", "prompt": "p", "format": "json",
              "tools": "off", "next": "m1"},
             {"id": "m1", "type": "map", "items": '${s0!raw}["scenes"]',
              "body": "b1", "collect": "b1", "next": ""},
             {"id": "b1", "type": "write", "path": "out_${__i__}.txt",
              "content": "${__item__}"}]

    class JsonGw(FakeGw):
        async def chat_stream(self, messages, **kw):
            yield Chunk(type="text",
                        text='{"scenes": [{"id": 1}, {"id": 2}, {"id": 3}]}')

    eng = WorkflowEngine(gateway=JsonGw(), registry=FakeRegistry(),
                         workspace=str(tmp_path), workflows_dir=tmp_path / "wf")
    rec = await eng.execute_definition({"name": "t", "nodes": nodes})
    assert rec.status == "done", rec.error
    for i in range(3):
        assert (tmp_path / f"out_{i}.txt").exists()


def test_read_file_node_uses_raw_channel(tmp_path):
    from app.tools.builtin.fs import f_read
    from app.tools import ToolContext

    f = tmp_path / "a.txt"
    f.write_text("1\n2\n3\n", "utf-8")
    ctx = ToolContext(str(tmp_path))
    assert f_read(str(f), ctx) == "1\n2\n3"
    assert f_read(str(f), ctx, raw=True) == "1\n2\n3"
    assert f_read(str(f), ctx, linenos=True) == "1\t1\n2\t2\n3\t3"


async def test_exec_output_has_no_exit_prefix(tmp_path):
    class ShellReg(FakeRegistry):
        async def execute(self, name, args, ctx):
            self.calls.append((name, args))
            assert args.get("meta") is True, "exec 节点必须传 meta=true"
            return json.dumps({"ok": True, "exit": 0, "output": '{"pass": true}'})

    reg = ShellReg()
    nodes = [{"id": "e1", "type": "exec", "command": "run", "next": "w1"},
             {"id": "w1", "type": "write", "path": "o.txt", "content": "${e1}"}]
    rec = await build(tmp_path, reg=reg).execute_definition({"name": "t", "nodes": nodes})
    assert rec.status == "done", rec.error
    assert (tmp_path / "o.txt").read_text("utf-8") == '{"pass": true}'
