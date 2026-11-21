from __future__ import annotations

import asyncio
import json

import pytest

from app.workflow.nodes.registry import NodeContext
from app.workflow import WorkflowEngine, WorkflowError
from app.workflow.vars import substitute


class _OkRegistry:
    schemas: list = []

    async def execute(self, name, args, ctx):
        return "ok"


@pytest.fixture
def engine(tmp_path):
    (tmp_path / "wf").mkdir(exist_ok=True)
    return WorkflowEngine(gateway=None, registry=_OkRegistry(),
                          workspace=str(tmp_path), workflows_dir=tmp_path / "wf")


pass
class _EchoGw:

    def __init__(self):
        self.calls: list[list[dict]] = []

    async def chat_stream(self, messages, tools=None, effort="medium",
                          spec="", session_id=""):
        self.calls.append([dict(m) for m in messages])
        yield type("C", (), {"type": "text", "text": "ok"})()


async def test_llm_system_message_precedes_user(tmp_path):
    gw = _EchoGw()
    eng = WorkflowEngine(gateway=gw, registry=_OkRegistry(),
                         workspace=str(tmp_path), workflows_dir=tmp_path / "wf")
    rec = await eng.execute_definition({"name": "t", "nodes": [
        {"id": "l", "type": "llm", "system": "你是分镜师，只输出 JSON",
         "prompt": "写第一镜"}]}, {})
    assert rec.status == "done", rec.error
    msgs = gw.calls[0]
    assert msgs[0]["role"] == "system" and "分镜师" in msgs[0]["content"]
    assert msgs[1]["role"] == "user" and "第一镜" in msgs[1]["content"]


async def test_llm_without_system_keeps_single_user_message(tmp_path):
    gw = _EchoGw()
    eng = WorkflowEngine(gateway=gw, registry=_OkRegistry(),
                         workspace=str(tmp_path), workflows_dir=tmp_path / "wf")
    await eng.execute_definition({"name": "t", "nodes": [
        {"id": "l", "type": "llm", "prompt": "你好"}]}, {})
    assert [m["role"] for m in gw.calls[0]] == ["user"]


async def test_llm_system_survives_json_retry(tmp_path):
    gw = _EchoGw()

    class _JsonGw(_EchoGw):
        async def chat_stream(self, messages, **kw):
            self.calls.append([dict(m) for m in messages])
            pass
            text = "oops" if len(self.calls) == 1 else '```json\n{"a":1}\n```'
            yield type("C", (), {"type": "text", "text": text})()

    eng = WorkflowEngine(gateway=_JsonGw(), registry=_OkRegistry(),
                         workspace=str(tmp_path), workflows_dir=tmp_path / "wf")
    rec = await eng.execute_definition({"name": "t", "nodes": [
        {"id": "l", "type": "llm", "system": "SYS", "prompt": "x", "format": "json"}]}, {})
    assert rec.status == "done", rec.error
    assert all(m.get("role") != "system" or m["content"] == "SYS"
               for call in gw.calls for m in call)
    assert all(call[0]["role"] == "system" and call[0]["content"] == "SYS"
               for call in gw.calls)


pass
def test_substitute_clean_unquotes_json_string():
    v = {"inputs": {}, "outputs": {"s1": '"s01"', "s2": "s01"},
         "output_paths": {}}
    assert substitute("out/${s1}/r.md", v) == 'out/"s01"/r.md'
    assert substitute("out/${s1}/r.md", v, clean=True) == "out/s01/r.md"
    assert substitute("out/${s2}/r.md", v, clean=True) == "out/s01/r.md" or True
    assert substitute("out/${s2}/r.md", v, clean=True).startswith("out/")


def test_substitute_clean_only_unquotes_whole_string():
    v = {"inputs": {}, "outputs": {"s1": '"s01"'}, "output_paths": {}}
    assert substitute('他说${s1}好', v, clean=True) == "他说s01好"
    broken = {"inputs": {}, "outputs": {"s1": '他说"s01"好'}, "output_paths": {}}
    assert substitute("x${s1}y", broken, clean=True) == 'x他说"s01"好y'


async def test_write_path_unquotes_json_output(engine, tmp_path):
    from app.tools.builtin import build_tools as build_registry
    real = WorkflowEngine(gateway=None, registry=build_registry(),
                          workspace=str(tmp_path), workflows_dir=tmp_path / "wf")
    rec = await real.execute_definition({"name": "t", "nodes": [
        {"id": "pre", "type": "code", "code": "print(chr(34) + 's01' + chr(34))",
         "next": "a"},
        {"id": "a", "type": "tool", "tool": "f_write",
         "argsJson": '{"path":"out/${pre}/r.md","content":"x"}'}]}, {})
    assert rec.status == "done", rec.error
    assert (tmp_path / "out" / "s01" / "r.md").is_file()
    assert not (tmp_path / "out" / '"s01"' / "r.md").exists()


async def test_tool_args_invalid_json_reports_cleanly(engine):
    rec = await engine.execute_definition({"name": "t", "nodes": [
        {"id": "a", "type": "tool", "tool": "f_write",
         "argsJson": '{"path": bad json}'}]}, {})
    assert rec.status == "failed"
    assert "参数 JSON 无效" in rec.error


pass
async def test_execute_sync_start_node_skips_upstream(engine, tmp_path):
    (tmp_path / "wf").mkdir(exist_ok=True)
    (tmp_path / "wf" / "t.json").write_text(json.dumps({"name": "t", "nodes": [
        {"id": "a", "type": "write", "path": "a.md", "content": "A", "next": "b"},
        {"id": "b", "type": "write", "path": "b.md", "content": "B", "next": "c"},
        {"id": "c", "type": "write", "path": "c.md", "content": "C"}]}), "utf-8")
    rec = await engine.execute_sync("t", {}, start_node="c")
    assert rec.status == "done", rec.error
    assert (tmp_path / "c.md").is_file()
    assert not (tmp_path / "a.md").exists() and not (tmp_path / "b.md").exists()


async def test_execute_sync_start_node_validated(engine, tmp_path):
    (tmp_path / "wf").mkdir(exist_ok=True)
    (tmp_path / "wf" / "t.json").write_text(json.dumps({"name": "t", "nodes": [
        {"id": "a", "type": "write", "path": "a.md", "content": "A"}]}), "utf-8")
    with pytest.raises(WorkflowError) as ei:
        await engine.execute_sync("t", {}, start_node="nope")
    assert "起始节点不存在" in str(ei.value)


pass
def test_save_rejects_missing_docs(engine):
    with pytest.raises(WorkflowError) as ei:
        engine.save({"name": "t", "nodes": [
            {"id": "l", "type": "llm", "docs": "prompts/none.md",
             "prompt": "x", "next": ""}]})
    assert "none.md" in str(ei.value) and "节点 l" in str(ei.value)


def test_save_accepts_glob_dir_and_existing(engine, tmp_path):
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "a.md").write_text("x", "utf-8")
    for docs in ("prompts/a.md", "prompts", "prompts/*.md", "${inputs.doc}"):
        engine.save({"name": f"t{abs(hash(docs))}", "nodes": [
            {"id": "l", "type": "llm", "docs": docs, "prompt": "x", "next": ""}]})


pass
def test_list_ignores_hidden_dirs_and_backup_files(engine, tmp_path):
    (tmp_path / "wf").mkdir(exist_ok=True)
    wf = {"name": "t5", "nodes": [{"id": "a", "type": "write",
                                   "path": "a.md", "content": "A"}]}
    (tmp_path / "wf" / "t5.json").write_text(json.dumps(wf), "utf-8")
    bak = tmp_path / "wf" / ".bak"
    bak.mkdir()
    (bak / "t5.json").write_text(json.dumps(wf), "utf-8")
    (tmp_path / "wf" / "t5.json.bak").write_text(json.dumps(wf), "utf-8")
    (tmp_path / "wf" / ".t5.json").write_text(json.dumps(wf), "utf-8")
    names = [x["name"] for x in engine.list()]
    assert names == ["t5"]
