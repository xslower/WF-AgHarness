from __future__ import annotations

import asyncio
import json

import pytest

from app.workflow import ops as opmod
from app.workflow.errors import WorkflowError
from app.workflow.nodes.op import run_op
from app.workflow.nodes.registry import NodeContext
from app.workflow.ops import OpRegistry, ops_for


def _ctx(workspace="", subs=None):
    def _sub(text, v, long_ref=False, clean=False):
        if subs is not None:
            return subs(text)
        out = str(text)
        for k, val in (v.get("inputs") or {}).items():
            out = out.replace("${" + k + "}", str(val))
        return out

    return NodeContext(workspace=workspace, substitute=_sub,
                       node_id="n1", run_id="r1", wf_name="w")


pass


def test_op_registry_run_and_unknown_hint():
    reg = OpRegistry()
    reg.add("ec_leverage", lambda **kw: {"lev": 1.5, "kw": kw})
    value, err = reg.run("ec_leverage", {"codes": "sz300750"})
    assert err == ""
    assert value["lev"] == 1.5 and value["kw"] == {"codes": "sz300750"}

    _v, err = reg.run("ec_leveraage", {})
    assert "未知算子" in err and "ec_leverage" in err, "得给相近名，否则没法查"


def test_op_registry_missing_dependency_names_module_and_interpreter():
    def _needs_fitz():
        raise ModuleNotFoundError("No module named 'fitz'", name="fitz")

    reg = OpRegistry()
    reg.add("pdf_text", _needs_fitz)
    _v, err = reg.run("pdf_text", {})
    assert "fitz" in err and "sys.executable" not in err
    assert "缺少依赖模块" in err, "不能报成“算子执行失败: ModuleNotFoundError”"
    assert "exec 节点" in err, "要告诉人退路：把它留在装了依赖的解释器里跑"


def test_op_registry_type_error_shows_given_and_declared():
    reg = OpRegistry()
    reg.add("f", lambda a, b: a, params=("a", "b"))
    _v, err = reg.run("f", {"a": 1})
    assert "参数不匹配" in err
    assert "['a']" in err and "['a', 'b']" in err


pass


def test_ops_for_loads_project_files_and_isolates_failures(tmp_path, monkeypatch):
    d = tmp_path / ".agent" / "ops"
    d.mkdir(parents=True)
    (d / "good.py").write_text(
        "def register(reg):\n"
        "    reg.add('add1', lambda x: x + 1, desc='加一', params=('x',))\n",
        "utf-8")
    (d / "bad.py").write_text("raise RuntimeError('boom')\n", "utf-8")
    (d / "_helper.py").write_text("raise RuntimeError('不该被加载')\n", "utf-8")
    monkeypatch.setattr(opmod.layout, "project_chain", lambda p: [tmp_path])
    opmod.reset_cache()

    reg = ops_for(tmp_path)
    assert reg.names() == ["add1"], "坏的与 _ 开头的不能影响好文件"
    assert any("bad.py" in k for k in reg.errors())
    assert reg.run("add1", {"x": 1}) == (2, "")
    opmod.reset_cache()


def test_ops_for_caches_until_file_changes(tmp_path, monkeypatch):
    d = tmp_path / ".agent" / "ops"
    d.mkdir(parents=True)
    f = d / "v.py"
    f.write_text("def register(reg):\n    reg.add('v', lambda: 1)\n", "utf-8")
    monkeypatch.setattr(opmod.layout, "project_chain", lambda p: [tmp_path])
    opmod.reset_cache()
    assert ops_for(tmp_path).run("v", {}) == (1, "")
    assert ops_for(tmp_path) is ops_for(tmp_path), "同一份签名要走缓存"

    f.write_text("def register(reg):\n    reg.add('v', lambda: 2)\n", "utf-8")
    import os
    os.utime(f, (f.stat().st_atime, f.stat().st_mtime + 5))
    assert ops_for(tmp_path).run("v", {}) == (2, ""), "改了文件要重新加载"
    opmod.reset_cache()


pass

def _run(coro):
    return asyncio.run(coro)


def test_op_node_returns_object_as_json_not_through_stdout(tmp_path, monkeypatch):
    d = tmp_path / ".agent" / "ops"
    d.mkdir(parents=True)
    (d / "big.py").write_text(
        "def register(reg):\n"
        "    reg.add('big', lambda n: {'items': list(range(n)), 'zh': '中文'})\n",
        "utf-8")
    monkeypatch.setattr(opmod.layout, "project_chain", lambda p: [tmp_path])
    opmod.reset_cache()

    node = {"id": "n1", "type": "op", "op": "big", "argsJson": '{"n": 500}'}
    out, nxt = _run(run_op(node, _ctx(str(tmp_path)), {"inputs": {}, "outputs": {}}))
    assert nxt is None
    got = json.loads(out)
    assert got["items"] == list(range(500)) and got["zh"] == "中文", \
        "对象结果必须原样拿回来（不经 stdout 就没有截断与丢字节）"
    opmod.reset_cache()


def test_op_node_substitutes_args_before_calling(tmp_path, monkeypatch):
    d = tmp_path / ".agent" / "ops"
    d.mkdir(parents=True)
    (d / "echo.py").write_text(
        "def register(reg):\n    reg.add('echo', lambda **kw: kw)\n", "utf-8")
    monkeypatch.setattr(opmod.layout, "project_chain", lambda p: [tmp_path])
    opmod.reset_cache()

    node = {"id": "n1", "op": "echo",
            "argsJson": '{"codes": "${inputs.codes}", "asof": "2026-11-17", "n": 3}'}
    out, _ = _run(run_op(node, _ctx(str(tmp_path)),
                         {"inputs": {"codes": "sz300750"}, "outputs": {},
                          "_known": {"inputs", "asof"}}))
    got = json.loads(out)
    assert got == {"codes": "sz300750", "asof": "2026-11-17", "n": 3}, \
        "非字符串值（n=3）不能被替成字符串"
    opmod.reset_cache()


def test_op_node_unknown_op_raises_with_node_id(tmp_path, monkeypatch):
    monkeypatch.setattr(opmod.layout, "project_chain", lambda p: [])
    opmod.reset_cache()
    node = {"id": "calc2", "op": "nope"}
    with pytest.raises(WorkflowError) as e:
        _run(run_op(node, _ctx(), {"inputs": {}, "outputs": {}}))
    assert "calc2" in str(e.value) and "未知算子" in str(e.value)


def test_op_node_none_output_is_empty_string(tmp_path, monkeypatch):
    d = tmp_path / ".agent" / "ops"
    d.mkdir(parents=True)
    (d / "n.py").write_text(
        "def register(reg):\n    reg.add('nothing', lambda: None)\n", "utf-8")
    monkeypatch.setattr(opmod.layout, "project_chain", lambda p: [tmp_path])
    opmod.reset_cache()
    out, _ = _run(run_op({"id": "n1", "op": "nothing"}, _ctx(str(tmp_path)),
                         {"inputs": {}, "outputs": {}}))
    assert out == ""
    opmod.reset_cache()


pass


def test_preflight_reports_unknown_op_and_broken_file(tmp_path, monkeypatch):
    from app.workflow.preflight import check_ops
    d = tmp_path / ".agent" / "ops"
    d.mkdir(parents=True)
    (d / "good.py").write_text(
        "def register(reg):\n    reg.add('ec_leverage', lambda: 1)\n", "utf-8")
    (d / "bad.py").write_text("raise RuntimeError('boom')\n", "utf-8")
    monkeypatch.setattr(opmod.layout, "project_chain", lambda p: [tmp_path])
    opmod.reset_cache()

    issues: list[str] = []
    check_ops({"nodes": [{"id": "a", "type": "op", "op": "ec_leveraage"}]},
              str(tmp_path), issues)
    text = "\n".join(issues)
    assert "ec_leveraage" in text and "ec_leverage" in text, "要带相近名"
    assert "bad.py" in text, "算子文件加载失败也要报出来（否则像算子丢了）"
    opmod.reset_cache()


def test_preflight_op_ok_when_registered(tmp_path, monkeypatch):
    from app.workflow.preflight import check_ops
    d = tmp_path / ".agent" / "ops"
    d.mkdir(parents=True)
    (d / "g.py").write_text(
        "def register(reg):\n    reg.add('ec_leverage', lambda: 1)\n", "utf-8")
    monkeypatch.setattr(opmod.layout, "project_chain", lambda p: [tmp_path])
    opmod.reset_cache()
    issues: list[str] = []
    check_ops({"nodes": [{"id": "a", "type": "op", "op": "ec_leverage"}]},
              str(tmp_path), issues)
    assert issues == []
    opmod.reset_cache()


def test_preflight_skips_dynamic_op_name(tmp_path, monkeypatch):
    from app.workflow.preflight import check_ops
    monkeypatch.setattr(opmod.layout, "project_chain", lambda p: [])
    opmod.reset_cache()
    issues: list[str] = []
    check_ops({"nodes": [{"id": "a", "type": "op", "op": "${which}"}]},
              str(tmp_path), issues)
    assert issues == []


pass
pass
pass


def _engine(tmp_path):
    from types import SimpleNamespace
    from app.workflow import WorkflowEngine
    return WorkflowEngine(registry=SimpleNamespace(execute=None, schemas=[]),
                          workspace=str(tmp_path), workflows_dir=tmp_path / "wf")


def _write_op(tmp_path, body: str) -> None:
    d = tmp_path / ".agent" / "ops"
    d.mkdir(parents=True, exist_ok=True)
    (d / "t.py").write_text(body, "utf-8")
    opmod.reset_cache()


@pytest.fixture

def proj_chain(tmp_path, monkeypatch):
    monkeypatch.setattr(opmod.layout, "project_chain", lambda p: [tmp_path])
    opmod.reset_cache()
    yield tmp_path
    opmod.reset_cache()


async def test_engine_runs_op_node_and_feeds_downstream(proj_chain):
    tmp_path = proj_chain
    _write_op(tmp_path, (
        "def register(reg):\n"
        "    reg.add('leverage', lambda codes: {'codes': codes, 'lev': [1.2, 1.5]})\n"))
    eng = _engine(tmp_path)
    rec = await eng.execute_definition({"name": "o", "nodes": [
        {"id": "lev", "type": "op", "op": "leverage",
         "argsJson": '{"codes": "${inputs.c}"}', "next": "say"},
        {"id": "say", "type": "write", "path": "out.txt",
         "content": "${lev}"},
    ]}, {"c": "sz300750"})
    assert rec.status == "done", rec.error
    out = (tmp_path / "out.txt").read_text("utf-8")
    assert json.loads(out) == {"codes": "sz300750", "lev": [1.2, 1.5]}


async def test_engine_op_failure_stops_run_with_node_id(proj_chain):
    tmp_path = proj_chain
    _write_op(tmp_path, (
        "def register(reg):\n"
        "    def boom(**kw):\n"
        "        raise ValueError('估值模型无输入')\n"
        "    reg.add('boom', boom)\n"))
    eng = _engine(tmp_path)
    rec = await eng.execute_definition({"name": "f", "nodes": [
        {"id": "b1", "type": "op", "op": "boom"}]})
    assert rec.status == "failed"
    assert "b1" in (rec.error or "") and "估值模型无输入" in (rec.error or "")


async def test_engine_preflight_blocks_unknown_op_before_any_node(proj_chain):
    tmp_path = proj_chain
    _write_op(tmp_path, "def register(reg):\n    reg.add('known', lambda: 1)\n")
    eng = _engine(tmp_path)
    wf = {"name": "p", "nodes": [
        {"id": "a", "type": "op", "op": "unknown_one"}]}
    issues = eng.preflight(wf)
    assert any("unknown_one" in x for x in issues), issues
    assert any("known" in x for x in issues), "得给相近名"


async def test_engine_op_node_in_catalog_and_catalog_fields(tmp_path):
    eng = _engine(tmp_path)
    item = next((x for x in eng.nodes.catalog() if x["type"] == "op"), None)
    assert item is not None
    assert [f["key"] for f in item["fields"]] == ["op", "argsJson"]
    assert any(f["key"] == "op" and f["required"] for f in item["fields"])


pass
pass
pass


def _ctx_eval(outputs, inputs=None):
    from app.workflow.run_records import RunRecordsMixin
    vars = {"inputs": inputs or {}, "outputs": outputs}
    c = _ctx()
    c.extras = {"eval_value": lambda e, v: RunRecordsMixin.eval_value(e, v)}
    return c, vars


def test_whole_ref_keeps_native_list():
    from app.workflow.nodes.jsonargs import sub_values
    ctx, vars = _ctx_eval({"params": '{"codes": ["a", "b"]}'})
    vars["_known"] = {"params"}
    got = sub_values({"codes": "${params.codes}"}, ctx, vars)
    assert got["codes"] == ["a", "b"], "整值引用要拿到真 list，不是字符串"


def test_whole_ref_keeps_null_as_none():
    from app.workflow.nodes.jsonargs import sub_values
    ctx, vars = _ctx_eval({"params": '{"events": null}'})
    vars["_known"] = {"params"}
    got = sub_values({"events": "${params.events}"}, ctx, vars)
    assert got["events"] is None


def test_embedded_ref_still_text_substitution():
    from app.workflow.nodes.jsonargs import sub_values
    ctx, vars = _ctx_eval({}, {"s1": "s01"})
    got = sub_values({"path": "out/${s1}/r.md"}, ctx, vars)
    assert got["path"] == "out/s01/r.md"


def test_whole_ref_falls_back_without_eval_channel():
    from app.workflow.nodes.jsonargs import sub_values
    ctx = _ctx(subs=lambda t: "PLAIN")
    ctx.extras = {"native_refs": False}
    got = sub_values({"x": "${y}"}, ctx, {"inputs": {}, "outputs": {}})
    assert got["x"] == "PLAIN"


def test_non_string_values_untouched():
    from app.workflow.nodes.jsonargs import sub_values
    ctx, vars = _ctx_eval({})
    got = sub_values({"n": 3, "b": True, "d": {"k": 1}, "l": [1]}, ctx, vars)
    assert got == {"n": 3, "b": True, "d": {"k": 1}, "l": [1]}
