from __future__ import annotations

import asyncio

import pytest

from app.provider.gateway import Chunk
from app.workflow.nodes.registry import NodeContext
from app.workflow.nodes.llm_prompt import resolve_docs as _resolve_docs
from app.tools.builtin import build_tools as build_registry
from app.workflow import WorkflowError


class Gw:
    def __init__(self):
        self.calls: list[dict] = []

    async def chat_stream(self, messages, tools=None, effort="medium",
                          spec="", session_id=""):
        self.calls.append({"messages": [dict(m) for m in messages]})
        yield Chunk(type="text", text="ok")


def engine(tmp_path, gw):
    from app.workflow import WorkflowEngine
    return WorkflowEngine(gateway=gw, registry=build_registry(),
                          agent_runner=None, workspace=str(tmp_path),
                          workflows_dir=tmp_path / "wf")


def run_wf(tmp_path, gw, node):
    (tmp_path / "wf").mkdir(exist_ok=True)
    eng = engine(tmp_path, gw)
    eng.save({"name": "t", "nodes": [dict(node, prompt=node.get("prompt", "总结"),
                                          next="")]})
    return asyncio.run(eng.execute_sync("t", {}))


def prompt_of(gw) -> str:
    return gw.calls[0]["messages"][-1]["content"]


pass
def test_resolve_relative_against_workspace(tmp_path):
    (tmp_path / "prompts").mkdir()
    f = tmp_path / "prompts" / "a.md"
    f.write_text("正文", "utf-8")
    hits, resolved = _resolve_docs("prompts/a.md", str(tmp_path))
    assert hits == [f]
    assert resolved == f


def test_resolve_absolute_path_unchanged(tmp_path):
    f = tmp_path / "abs.md"
    f.write_text("x", "utf-8")
    hits, resolved = _resolve_docs(str(f), "/nonexistent/workspace")
    assert hits == [f] and resolved == f


def test_resolve_glob_and_dir(tmp_path):
    d = tmp_path / "prompts"
    d.mkdir()
    for n in ("b.md", "a.md", "c.txt", "skip.png"):
        (d / n).write_text(n, "utf-8")
    globbed, _ = _resolve_docs("prompts/*.md", str(tmp_path))
    assert [p.name for p in globbed] == ["a.md", "b.md"]
    as_dir, _ = _resolve_docs("prompts", str(tmp_path))
    assert [p.name for p in as_dir] == ["a.md", "b.md", "c.txt"]


def test_resolve_recursive_glob(tmp_path):
    (tmp_path / "p" / "sub").mkdir(parents=True)
    (tmp_path / "p" / "a.md").write_text("1", "utf-8")
    (tmp_path / "p" / "sub" / "b.md").write_text("2", "utf-8")
    hits, _ = _resolve_docs("p/**/*.md", str(tmp_path))
    assert [p.name for p in hits] == ["a.md", "b.md"]


def test_resolve_missing_returns_no_hits(tmp_path):
    hits, resolved = _resolve_docs("prompts/none.md", str(tmp_path))
    assert hits == [] and resolved == tmp_path / "prompts" / "none.md"


pass
def test_llm_docs_relative_path_resolved(tmp_path):
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "seg.md").write_text("分镜规则正文", "utf-8")
    gw = Gw()
    rec = run_wf(tmp_path, gw, {"id": "l", "type": "llm",
                                "docs": "prompts/seg.md"})
    assert rec.status == "done", rec.error
    p = prompt_of(gw)
    assert "[文档: seg.md]" in p and "分镜规则正文" in p
    assert "不存在" not in p


def test_llm_docs_missing_blocks_before_run(tmp_path):
    (tmp_path / "prompts").mkdir()
    f = tmp_path / "prompts" / "gone.md"
    f.write_text("临时", "utf-8")
    (tmp_path / "wf").mkdir(exist_ok=True)
    gw = Gw()
    eng = engine(tmp_path, gw)
    eng.save({"name": "t", "nodes": [{"id": "l", "type": "llm",
                                      "docs": "prompts/gone.md",
                                      "prompt": "总结", "next": ""}]})
    f.unlink()
    with pytest.raises(WorkflowError) as err:
        asyncio.run(eng.execute_sync("t", {}))
    msg = str(err.value)
    pass
    assert str(tmp_path / "prompts" / "gone.md") in msg
    assert not gw.calls
    assert "docs" in msg


pass
def test_save_rejects_missing_docs(tmp_path):
    from app.workflow import WorkflowError
    (tmp_path / "wf").mkdir(exist_ok=True)
    eng = engine(tmp_path, Gw())
    with pytest.raises(WorkflowError) as ei:
        eng.save({"name": "t", "nodes": [{"id": "l", "type": "llm",
                                          "docs": "prompts/none.md",
                                          "prompt": "x", "next": ""}]})
    msg = str(ei.value)
    assert "docs" in msg and "none.md" in msg and "节点 l" in msg


def test_save_accepts_existing_docs_and_glob(tmp_path):
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "a.md").write_text("x", "utf-8")
    (tmp_path / "wf").mkdir(exist_ok=True)
    eng = engine(tmp_path, Gw())
    for docs in ("prompts/a.md", "prompts", "prompts/*.md", "prompts/**/*.md"):
        eng.save({"name": f"t-{abs(hash(docs))}", "nodes": [
            {"id": "l", "type": "llm", "docs": docs, "prompt": "x", "next": ""}]})


def test_save_skips_runtime_expressions_in_docs(tmp_path):
    (tmp_path / "wf").mkdir(exist_ok=True)
    eng = engine(tmp_path, Gw())
    eng.save({"name": "t", "nodes": [
        {"id": "l", "type": "llm", "docs": "${inputs.doc}", "prompt": "x", "next": ""}]})


def test_llm_docs_glob_injects_all(tmp_path):
    (tmp_path / "prompts").mkdir()
    for n in ("1-role.md", "2-style.md"):
        (tmp_path / "prompts" / n).write_text(f"{n} 内容", "utf-8")
    gw = Gw()
    rec = run_wf(tmp_path, gw, {"id": "l", "type": "llm", "docs": "prompts/*.md"})
    assert rec.status == "done", rec.error
    p = prompt_of(gw)
    assert "1-role.md 内容" in p and "2-style.md 内容" in p


def test_llm_docs_multiple_lines(tmp_path):
    (tmp_path / "a.md").write_text("AAA", "utf-8")
    (tmp_path / "b.txt").write_text("BBB", "utf-8")
    gw = Gw()
    rec = run_wf(tmp_path, gw, {"id": "l", "type": "llm", "docs": "a.md\nb.txt"})
    assert rec.status == "done", rec.error
    p = prompt_of(gw)
    assert "AAA" in p and "BBB" in p
