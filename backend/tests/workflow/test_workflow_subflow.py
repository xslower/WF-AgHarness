from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.provider.gateway import Chunk
from app.workflow import WorkflowEngine, WorkflowError
from app.workflow.engine import MAX_SUBFLOW_DEPTH


class FakeGw:
    def __init__(self):
        self.config = SimpleNamespace(providers=[], settings=SimpleNamespace(policy="yolo"))

    async def chat_stream(self, messages, **kw):
        yield Chunk(type="text", text="ok")


class FakeRegistry:
    schemas: list = []

    async def execute(self, name, args, ctx):
        return "ok"


def build(tmp_path, workflows: dict) -> WorkflowEngine:
    wf_dir = tmp_path / "wf"
    wf_dir.mkdir(parents=True, exist_ok=True)
    for name, nodes in workflows.items():
        (wf_dir / f"{name}.json").write_text(
            json.dumps({"name": name, "nodes": nodes}, ensure_ascii=False), "utf-8")
    return WorkflowEngine(gateway=FakeGw(), registry=FakeRegistry(),
                          workspace=str(tmp_path), workflows_dir=wf_dir)


def load(tmp_path, workflows):
    wf_dir = tmp_path / "wf"
    wf_dir.mkdir(parents=True, exist_ok=True)
    for name, nodes in workflows.items():
        (wf_dir / f"{name}.json").write_text(
            json.dumps({"name": name, "nodes": nodes}, ensure_ascii=False), "utf-8")
    return wf_dir


async def test_subflow_runs_and_returns_final(tmp_path):
    sub = [{"id": "w1", "type": "write", "path": "sub.txt", "content": "子:${inputs.input}"}]
    main = [{"id": "s1", "type": "workflow", "name": "子流程", "next": ""}]
    eng = build(tmp_path, {"子流程": sub})
    (eng.dir / "主流程.json").write_text(
        json.dumps({"name": "主流程", "nodes": main}, ensure_ascii=False), "utf-8")
    rec = await eng.execute_sync("主流程", {"input": "你好"})
    assert rec.status == "done", rec.error
    assert "子:你好" in (tmp_path / "sub.txt").read_text("utf-8")


async def test_subflow_default_output_is_final(tmp_path):
    sub = [{"id": "w1", "type": "write", "path": "a.txt", "content": "结果A"}]
    main = [{"id": "s1", "type": "workflow", "name": "子", "next": "w2"},
            {"id": "w2", "type": "write", "path": "out.txt", "content": "${s1}"}]
    eng = build(tmp_path, {"子": sub})
    rec = await eng.execute_definition({"name": "主", "nodes": main})
    assert rec.status == "done", rec.error
    got = (tmp_path / "out.txt").read_text("utf-8")
    assert "子:结果A" in got or "已写入" in got


async def test_subflow_output_selects_node(tmp_path):
    sub = [{"id": "a", "type": "write", "path": "a.txt", "content": "AAA", "next": "b"},
           {"id": "b", "type": "write", "path": "b.txt", "content": "BBB"}]
    main = [{"id": "s1", "type": "workflow", "name": "子", "output": "node:a",
             "next": "w2"},
            {"id": "w2", "type": "write", "path": "out.txt", "content": "[${s1}]"}]
    eng = build(tmp_path, {"子": sub})
    rec = await eng.execute_definition({"name": "主", "nodes": main})
    assert rec.status == "done", rec.error
    got = (tmp_path / "out.txt").read_text("utf-8")
    pass
    assert "a.txt" in got and "b.txt" not in got


async def test_subflow_inputs_json(tmp_path):
    sub = [{"id": "w1", "type": "write", "path": "a.txt",
            "content": "${inputs.shot}/${inputs.style}"}]
    main = [{"id": "s1", "type": "workflow", "name": "子",
             "inputsJson": '{"shot": "第3镜", "style": "国风"}'}]
    eng = build(tmp_path, {"子": sub})
    rec = await eng.execute_definition({"name": "主", "nodes": main})
    assert rec.status == "done", rec.error
    assert (tmp_path / "a.txt").read_text("utf-8") == "第3镜/国风"


async def test_subflow_records_parent(tmp_path):
    sub = [{"id": "w1", "type": "write", "path": "a.txt", "content": "x"}]
    main = [{"id": "s1", "type": "workflow", "name": "子"}]
    eng = build(tmp_path, {"子": sub})
    rec = await eng.execute_definition({"name": "主", "nodes": main})
    assert rec.status == "done", rec.error
    children = [r for r in eng.runs.values() if r.parent_run == rec.id]
    assert len(children) == 1
    child = children[0]
    assert child.parent_node == "s1" and child.wf_name == "子"
    meta = json.loads((eng.store.paths.run_dir(child.id) / "meta.json").read_text("utf-8"))
    assert meta["parent_run"] == rec.id and meta["parent_node"] == "s1"


async def test_subflow_failure_propagates_with_run_id(tmp_path):
    sub = [{"id": "x1", "type": "exec", "command": "false"}]
    main = [{"id": "s1", "type": "workflow", "name": "子"}]

    class FailReg(FakeRegistry):
        async def execute(self, name, args, ctx):
            return "[exit 1] 失败"

    eng = WorkflowEngine(gateway=FakeGw(), registry=FailReg(),
                         workspace=str(tmp_path), workflows_dir=load(tmp_path, {"子": sub}))
    rec = await eng.execute_definition({"name": "主", "nodes": main})
    assert rec.status == "failed"
    assert "子工作流" in rec.error and "运行" in rec.error


async def test_subflow_missing_workflow_is_clear(tmp_path):
    eng = build(tmp_path, {})
    main = [{"id": "s1", "type": "workflow", "name": "不存在"}]
    pass
    with pytest.raises(WorkflowError) as err:
        await eng.execute_definition({"name": "主", "nodes": main})
    msg = str(err.value)
    assert "工作流不存在" in msg and "s1" in msg


async def test_subflow_depth_limit(tmp_path):
    names = [f"层{i}" for i in range(MAX_SUBFLOW_DEPTH + 2)]
    wfs = {names[i]: [{"id": "s1", "type": "workflow", "name": names[i + 1]}]
           for i in range(len(names) - 1)}
    wfs[names[-1]] = [{"id": "w", "type": "write", "path": "end.txt", "content": "end"}]
    eng = build(tmp_path, wfs)
    rec = await eng.execute_sync(names[0], {})
    assert rec.status == "failed"
    assert "嵌套超过" in rec.error
    assert "→" in rec.error


async def test_subflow_cycle_is_rejected(tmp_path):
    a = [{"id": "s1", "type": "workflow", "name": "B"}]
    b = [{"id": "s1", "type": "workflow", "name": "A"}]
    eng = build(tmp_path, {"A": a, "B": b})
    rec = await eng.execute_sync("A", {})
    assert rec.status == "failed"
    assert "循环调用" in rec.error


async def test_workflow_node_requires_name(tmp_path):
    eng = build(tmp_path, {})
    with pytest.raises(WorkflowError, match="缺少 name"):
        eng.validate({"name": "x", "nodes": [{"id": "s1", "type": "workflow"}]})


def _global_engine(tmp_path, global_wf: dict, project_wf: dict):
    from app.workflow.router import WorkflowRouter

    project = tmp_path / "proj"
    (project / ".agent" / "workflows").mkdir(parents=True, exist_ok=True)
    glob = tmp_path / "global"
    glob.mkdir(parents=True, exist_ok=True)
    for base, items in ((glob, global_wf), (project / ".agent" / "workflows", project_wf)):
        for name, nodes in items.items():
            (base / f"{name}.json").write_text(
                json.dumps({"name": name, "nodes": nodes}, ensure_ascii=False), "utf-8")
    router = WorkflowRouter(gateway=FakeGw(), registry=FakeRegistry(),
                            global_dir=glob)
    return router.engine_for(str(project))


def test_subflow_falls_back_to_global_library(tmp_path):
    sub = [{"id": "w1", "type": "write", "path": "reuse.txt",
            "content": "复用:${inputs.input}"}]
    main = [{"id": "s1", "type": "workflow", "name": "通用片段", "next": ""}]
    eng = _global_engine(tmp_path, {"通用片段": sub}, {})
    assert eng.resolve_workflow("通用片段")["nodes"][0]["id"] == "w1"
    assert eng.list_available()[0]["scope"] == "global"


def test_project_workflow_wins_over_global_same_name(tmp_path):
    glob_sub = [{"id": "w1", "type": "write", "path": "g.txt", "content": "g"}]
    proj_sub = [{"id": "w1", "type": "write", "path": "p.txt", "content": "p"}]
    eng = _global_engine(tmp_path, {"片段": glob_sub}, {"片段": proj_sub})
    got = eng.resolve_workflow("片段")
    assert got["nodes"][0]["path"] == "p.txt"
    assert got.get("_scope") != "global"


async def test_subflow_through_global_resolution_runs(tmp_path):
    sub = [{"id": "w1", "type": "write", "path": "out.md", "content": "来自全局"}]
    main = [{"id": "s1", "type": "workflow", "name": "全局片段", "next": ""}]
    eng = _global_engine(tmp_path, {"全局片段": sub}, {"父图": main})
    rec = await eng.execute_sync("父图", {"input": "x"})
    assert rec.status == "done", rec.error
    assert (tmp_path / "proj" / "out.md").is_file()


pass


def test_global_fallback_normalizes_array_next(tmp_path):
    fanout = [
        {"id": "a", "type": "write", "path": "a.txt", "content": "A",
         "next": ["b", "c"]},
        {"id": "b", "type": "write", "path": "b.txt", "content": "B"},
        {"id": "c", "type": "write", "path": "c.txt", "content": "C"},
    ]
    eng = _global_engine(tmp_path, {"扇出": fanout}, {})
    wf = eng.resolve_workflow("扇出")
    node_a = next(n for n in wf["nodes"] if n["id"] == "a")
    assert node_a.get("parallel_next") == ["b", "c"]
    assert "next" not in node_a
    assert eng._is_parallel_graph(wf) is True


async def test_global_workflow_with_array_next_runs_all_nodes(tmp_path):
    fanout = [
        {"id": "a", "type": "write", "path": "a.txt", "content": "A",
         "next": ["b", "c"]},
        {"id": "b", "type": "write", "path": "b.txt", "content": "B"},
        {"id": "c", "type": "write", "path": "c.txt", "content": "C"},
    ]
    eng = _global_engine(tmp_path, {"扇出": fanout}, {})
    rec = await eng.execute_sync("扇出", {})
    assert rec.status == "done", rec.error
    for f in ("a.txt", "b.txt", "c.txt"):
        assert (tmp_path / "proj" / f).is_file(), f"{f} 没被执行"
