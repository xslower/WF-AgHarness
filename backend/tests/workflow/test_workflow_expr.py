from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.provider.gateway import Chunk
from app.workflow import WorkflowEngine, WorkflowError
from app.workflow.expr import boolv, get_path, num
from app.workflow.vars import substitute_expr


class FakeGw:
    def __init__(self):
        self.config = SimpleNamespace(providers=[], settings=SimpleNamespace(policy="yolo"))

    async def chat_stream(self, messages, **kw):
        yield Chunk(type="text", text="ok")


class FakeRegistry:
    schemas: list = []

    async def execute(self, name, args, ctx):
        return "ok"


@pytest.fixture
def run(tmp_path):
    async def _run(nodes, inputs=None):
        eng = WorkflowEngine(gateway=FakeGw(), registry=FakeRegistry(),
                             workspace=str(tmp_path), workflows_dir=tmp_path / "wf")
        return await eng.execute_definition({"name": "t", "nodes": nodes},
                                            inputs or {})
    return _run


def vars_of(**outputs):
    return {"inputs": {}, "outputs": dict(outputs), "output_paths": {}}


pass
def test_plain_substitution_stays_string():
    assert substitute_expr("len(${s1}) > 3", vars_of(s1="abcdef")) == "len('abcdef') > 3"
    assert substitute_expr("'错' in ${s1}", vars_of(s1="有错")) == "'错' in '有错'"


def test_raw_substitution_keeps_native_types():
    v = vars_of(n="12", b='{"pass": true}', s2='{"scenes": [{"shot": "开场"}]}')
    assert substitute_expr("${n!raw} > 3", v) == "12 > 3"
    assert substitute_expr("${b!raw}['pass'] == True", v) == "{'pass': True}['pass'] == True"
    assert substitute_expr("${s2!raw}['scenes'][0]['shot']", v) == \
        "{'scenes': [{'shot': '开场'}]}['scenes'][0]['shot']"


def test_raw_missing_variable_raises():
    with pytest.raises(WorkflowError) as err:
        substitute_expr("${nope!raw} is None", vars_of())
    assert "nope" in str(err.value)


def test_raw_known_but_not_run_yet_is_none():
    v = vars_of()
    v["_known"] = {"b2"}
    assert substitute_expr("${b2!raw} is None", v) == "None is None"


pass
async def test_bool_compare_with_raw(run):
    with pytest.raises(WorkflowError) as err:
        await run([{"id": "c1", "type": "condition", "expr": "${rev.pass!raw} == True",
                    "true": "w1", "false": "w2"},
                   {"id": "w1", "type": "write", "path": "yes.txt", "content": "1"},
                   {"id": "w2", "type": "write", "path": "no.txt", "content": "0"}],
                  inputs={})
    assert "rev" in str(err.value)


async def test_bool_compare_with_raw_and_value(run):
    nodes = [
        {"id": "rev", "type": "llm", "prompt": "评分", "tools": "off",
         "next": "c1"},
        {"id": "c1", "type": "condition", "expr": "${rev.pass!raw} == True",
         "true": "w1", "false": "w2"},
        {"id": "w1", "type": "write", "path": "yes.txt", "content": "1"},
        {"id": "w2", "type": "write", "path": "no.txt", "content": "0"},
    ]
    pass
    rec = await run(nodes)
    assert rec.status == "done", rec.error
    assert "condition=false" in rec.node_states["c1"]["output"]


async def test_json_helper_parses_string_output(run, tmp_path):
    nodes = [
        {"id": "s1", "type": "code", "code": "pass",
         "next": "c1"},
        {"id": "c1", "type": "condition",
         "expr": "get(json(${s1}), 'scenes.1.shot') == '结尾'",
         "true": "w1", "false": "w2"},
        {"id": "w1", "type": "write", "path": "ok.txt", "content": "ok"},
        {"id": "w2", "type": "write", "path": "bad.txt", "content": "bad"},
    ]
    pass
    class Reg(FakeRegistry):
        async def execute(self, name, args, ctx):
            return '{"scenes": [{"shot": "开场"}, {"shot": "结尾"}]}'

    eng = WorkflowEngine(gateway=FakeGw(), registry=Reg(),
                         workspace=str(tmp_path), workflows_dir=tmp_path / "wf")
    rec = await eng.execute_definition({"name": "t", "nodes": nodes})
    assert rec.status == "done", rec.error
    assert (tmp_path / "ok.txt").exists()


async def test_boolv_num_and_match_helpers(run, tmp_path):
    nodes = [
        {"id": "s1", "type": "code", "code": "pass", "next": "c1"},
        {"id": "c1", "type": "condition",
         "expr": "boolv(${s1}) and num('3 镜') > 2 and match('[0-9]+', ${s1})",
         "true": "w1", "false": "w2"},
        {"id": "w1", "type": "write", "path": "ok.txt", "content": "ok"},
        {"id": "w2", "type": "write", "path": "bad.txt", "content": "bad"},
    ]

    class Reg(FakeRegistry):
        async def execute(self, name, args, ctx):
            return "通过 3 镜"

    eng = WorkflowEngine(gateway=FakeGw(), registry=Reg(),
                         workspace=str(tmp_path), workflows_dir=tmp_path / "wf")
    rec = await eng.execute_definition({"name": "t", "nodes": nodes})
    assert rec.status == "done", rec.error
    assert (tmp_path / "ok.txt").exists()


async def test_bad_expr_surfaces_error_instead_of_silent_false(run):
    nodes = [
        {"id": "c1", "type": "condition", "expr": "len(", "true": "w1", "false": "w2"},
        {"id": "w1", "type": "write", "path": "a.txt", "content": "1"},
        {"id": "w2", "type": "write", "path": "b.txt", "content": "0"},
    ]
    rec = await run(nodes)
    assert rec.status == "done", rec.error
    out = json.loads(rec.node_states["c1"]["output"])
    assert out["pass"] is False
    assert "SyntaxError" in out["error"]


async def test_condition_pass_field_is_real_bool(run):
    nodes = [
        {"id": "c1", "type": "condition", "expr": "1 == 1",
         "true": "w1", "false": "w2"},
        {"id": "w1", "type": "write", "path": "a.txt", "content": "${c1.pass}"},
        {"id": "w2", "type": "write", "path": "b.txt", "content": "x"},
    ]
    rec = await run(nodes)
    assert rec.status == "done", rec.error
    assert json.loads(rec.node_states["c1"]["output"])["pass"] is True


def test_helpers_unit():
    assert boolv("TRUE") and boolv("通过") and not boolv("")
    assert num("3 镜") == 3 and num("abc", 7) == 7
    assert get_path({"a": {"b": [1, {"c": 9}]}}, "a.b.1.c") == 9
    assert get_path({"a": 1}, "a.b", "缺省") == "缺省"


def test_no_builtins_leak():
    from app.workflow.expr import evaluate, safe_env
    ok, err = evaluate("__import__('os').getcwd()", safe_env(), {})
    assert ok is False and err
    ok, err = evaluate("open('/etc/passwd').read()", safe_env(), {})
    assert ok is False and err
