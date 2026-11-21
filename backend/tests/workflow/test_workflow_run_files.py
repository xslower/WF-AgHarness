from __future__ import annotations

import pytest

from app.workflow.nodes.registry import NodeContext
from app.workflow import WorkflowEngine


class NoopRegistry:

    async def execute(self, name, args, ctx):
        return "ok"


@pytest.fixture
def engine(tmp_path):
    return WorkflowEngine(gateway=None, registry=NoopRegistry(),
                          workspace=str(tmp_path), workflows_dir=tmp_path / "wf")


async def test_write_node_reports_file(engine, tmp_path):
    rec = await engine.execute_definition({"name": "t", "nodes": [
        {"id": "w1", "type": "write", "path": "out/report.md", "content": "正文"},
    ]}, {})
    assert rec.status == "done", rec.error
    files = rec.to_dict()["files"]
    assert [f["rel"] for f in files] == ["out/report.md"]
    assert files[0]["node"] == "w1"
    assert files[0]["size"] == len("正文".encode())
    assert files[0]["path"] == str(tmp_path / "out" / "report.md")


async def test_same_path_reported_once(engine):
    rec = await engine.execute_definition({"name": "t", "nodes": [
        {"id": "a", "type": "write", "path": "log.md", "content": "短", "next": "b"},
        {"id": "b", "type": "write", "path": "log.md", "content": "长一些的内容"},
    ]}, {})
    files = rec.to_dict()["files"]
    assert len(files) == 1
    assert files[0]["node"] == "b"
    assert files[0]["size"] == len("长一些的内容".encode())


async def test_missing_file_not_listed(engine):
    rec = engine.runs
    from app.workflow.record import RunRecord
    r = RunRecord("rid", "t", str(engine.workspace))
    r.add_file(str(engine.workspace) + "/nope.md")
    assert r.files == []
    assert isinstance(rec, dict)


async def test_rel_falls_back_outside_workspace(engine, tmp_path):
    from app.workflow.record import RunRecord
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir(exist_ok=True)
    p = outside / "x.md"
    p.write_text("hi", "utf-8")
    r = RunRecord("rid", "t", str(tmp_path))
    r.add_file(str(p))
    assert r.files[0]["rel"] == "x.md"


def test_report_file_hook_reaches_tool_ctx():
    seen: list[tuple[str, str]] = []
    ctx = NodeContext(workspace="/tmp", report_file=lambda p, n: seen.append((p, n)),
                      node_id="n1")
    tctx = ctx.tool_ctx()
    assert tctx.report_file is not None
    tctx.report_file("/tmp/a.md")
    assert seen == [("/tmp/a.md", "n1")]

    pass
    plain = NodeContext(workspace="/tmp")
    assert plain.tool_ctx().report_file is None


def test_report_swallow_exceptions():
    def boom(path, node):
        raise RuntimeError("disk gone")

    ctx = NodeContext(workspace="/tmp", report_file=boom, node_id="n1")
    ctx.report("/tmp/a.md")


async def test_tool_node_write_lands_in_files(tmp_path):
    from app.tools.builtin import build_tools as build_registry

    eng = WorkflowEngine(gateway=None, registry=build_registry(),
                         workspace=str(tmp_path), workflows_dir=tmp_path / "wf")
    rec = await eng.execute_definition({"name": "t", "nodes": [
        {"id": "t1", "type": "tool", "tool": "f_write",
         "argsJson": '{"path":"out/a.md","content":"hello"}', "next": "t2"},
        {"id": "t2", "type": "write", "path": "out/b.md", "content": "world"},
    ]}, {})
    assert rec.status == "done", rec.error
    got = [(f["node"], f["rel"]) for f in rec.to_dict()["files"]]
    assert got == [("t1", "out/a.md"), ("t2", "out/b.md")]
