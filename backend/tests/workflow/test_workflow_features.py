from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from app.provider.gateway import Chunk
from app.workflow.nodes.registry import NodeField, NodeRegistry, NodeSpec
from app.workflow import WorkflowEngine, WorkflowError


pass
def flaky_nodes(fails: int = 2, sleep: float = 0.0):
    reg = NodeRegistry()
    state = {"calls": 0}

    async def run_flaky(node, ctx, vars):
        state["calls"] += 1
        if state["calls"] <= fails:
            raise RuntimeError(f"第 {state['calls']} 次失败")
        return f"第 {state['calls']} 次成功", node.get("next")

    async def run_slow(node, ctx, vars):
        await asyncio.sleep(sleep)
        return "太慢了", node.get("next")

    async def run_echo(node, ctx, vars):
        return ctx.sub(node.get("text", ""), vars), node.get("next")

    reg.register(NodeSpec(type="flaky", label="flaky", run=run_flaky))
    reg.register(NodeSpec(type="slow", label="slow", run=run_slow))
    reg.register(NodeSpec(type="echo", label="echo", run=run_echo,
                          fields=(NodeField("text", "文本"),)))
    return reg, state


def make_engine(tmp_path, nodes=None):
    return WorkflowEngine(registry=SimpleNamespace(execute=None, schemas=[]),
                          workspace=str(tmp_path), workflows_dir=tmp_path / "wf",
                          nodes=nodes)


pass
async def test_node_retry_until_success(tmp_path):
    nodes, state = flaky_nodes(fails=2)
    eng = make_engine(tmp_path, nodes)
    rec = await eng.execute_definition({"name": "t", "nodes": [
        {"id": "f", "type": "flaky", "retry": 2}]})
    assert rec.status == "done", rec.error
    assert state["calls"] == 3
    assert rec.node_states["f"]["output"] == "第 3 次成功"


async def test_node_retry_exhausted_fails_with_attempts(tmp_path):
    nodes, state = flaky_nodes(fails=5)
    eng = make_engine(tmp_path, nodes)
    rec = await eng.execute_definition({"name": "t", "nodes": [
        {"id": "f", "type": "flaky", "retry": 1}]})
    assert rec.status == "failed"
    assert state["calls"] == 2
    assert rec.node_states["f"]["status"] == "failed"
    assert rec.node_states["f"]["attempts"] == 2
    assert "第 2 次失败" in rec.node_states["f"]["error"]


async def test_node_timeout_marks_failed(tmp_path):
    nodes, _ = flaky_nodes(sleep=0.3)
    eng = make_engine(tmp_path, nodes)
    rec = await eng.execute_definition({"name": "t", "nodes": [
        {"id": "s", "type": "slow", "timeout": 0.05}]}, {"x": 1})
    assert rec.status == "failed"
    assert "TimeoutError" in rec.error


async def test_node_timeout_not_hit_when_fast(tmp_path):
    nodes, _ = flaky_nodes()
    pass
    eng = make_engine(tmp_path, nodes)
    rec = await eng.execute_definition({"name": "t", "nodes": [
        {"id": "s", "type": "slow", "timeout": 5}]})
    assert rec.status == "done", rec.error
    assert rec.node_states["s"]["output"] == "太慢了"


async def test_bad_retry_and_timeout_values_are_ignored(tmp_path):
    nodes, _ = flaky_nodes()
    eng = make_engine(tmp_path, nodes)
    rec = await eng.execute_definition({"name": "t", "nodes": [
        {"id": "e", "type": "echo", "text": "ok", "retry": "abc", "timeout": ""}]})
    assert rec.status == "done", rec.error
    assert rec.node_states["e"]["output"] == "ok"


pass
async def test_start_node_skips_upstream_and_uses_preset(tmp_path):
    nodes, _ = flaky_nodes()
    eng = make_engine(tmp_path, nodes)
    rec = await eng.execute_definition({"name": "t", "nodes": [
        {"id": "a", "type": "echo", "text": "A", "next": "b"},
        {"id": "b", "type": "echo", "text": "拿到=${a}", "next": "c"},
        {"id": "c", "type": "echo", "text": "C", "next": ""},
    ]}, start_node="b", preset_outputs={"a": "上次的结果"})
    assert rec.status == "done", rec.error
    assert "a" not in rec.node_states
    assert rec.node_states["b"]["output"] == "拿到=上次的结果"
    assert rec.node_states["c"]["output"] == "C"


async def test_start_node_unknown_raises(tmp_path):
    nodes, _ = flaky_nodes()
    eng = make_engine(tmp_path, nodes)
    with pytest.raises(WorkflowError) as e:
        await eng.execute_definition({"name": "t", "nodes": [
            {"id": "a", "type": "echo", "text": "x"}]}, start_node="zzz")
    assert "起始节点不存在" in str(e.value)


async def test_preset_outputs_feed_variables(tmp_path):
    nodes, _ = flaky_nodes()
    eng = make_engine(tmp_path, nodes)
    rec = await eng.execute_definition({"name": "t", "nodes": [
        {"id": "b", "type": "echo", "text": "${seed}"}]},
        preset_outputs={"seed": "预置值"})
    assert rec.node_states["b"]["output"] == "预置值"


pass
async def test_run_single_only_runs_target_node(tmp_path):
    nodes, _ = flaky_nodes()
    eng = make_engine(tmp_path, nodes)
    eng.save({"name": "t", "nodes": [
        {"id": "a", "type": "echo", "text": "A", "next": "b"},
        # b 故意缺字段（草稿态）：单节点试运行不该被其它节点拖累
        {"id": "b", "type": "echo", "next": ""},
    ]})
    rec = await eng.run_single("t", "a", preset_outputs={"up": "U"})
    assert rec.status == "done", rec.error
    assert list(rec.node_states) == ["a"]
    assert rec.node_states["a"]["output"] == "A"


async def test_run_single_unknown_node_or_type(tmp_path):
    nodes, _ = flaky_nodes()
    eng = make_engine(tmp_path, nodes)
    eng.save({"name": "t", "nodes": [{"id": "a", "type": "echo", "text": "A"}]})
    with pytest.raises(WorkflowError, match="节点不存在"):
        await eng.run_single("t", "zzz")
    eng.save({"name": "t2", "nodes": [{"id": "a", "type": "nope"}]})
    with pytest.raises(WorkflowError, match="未知节点类型"):
        await eng.run_single("t2", "a")


async def test_run_single_missing_required_field(tmp_path):
    eng = WorkflowEngine(workspace=str(tmp_path), workflows_dir=tmp_path / "wf")
    eng.save({"name": "t", "nodes": [{"id": "a", "type": "llm"}]})
    with pytest.raises(WorkflowError, match="缺少 prompt"):
        await eng.run_single("t", "a")


async def test_run_single_missing_workflow(tmp_path):
    eng = make_engine(tmp_path)
    with pytest.raises(WorkflowError, match="工作流不存在"):
        await eng.run_single("nope", "a")


pass
async def test_execute_definition_writes_run_meta(tmp_path):
    nodes, _ = flaky_nodes()
    eng = make_engine(tmp_path, nodes)
    rec = await eng.execute_definition({"name": "rec", "nodes": [
        {"id": "e", "type": "echo", "text": "hello"}]})
    assert rec.status == "done"
    meta_path = eng.store.paths.run_dir(rec.id) / "meta.json"
    meta = json.loads(meta_path.read_text("utf-8"))
    assert meta["status"] == "done" and meta["workflow"] == "rec"
    pass
    out_file = eng.store.paths.run_dir(rec.id) / "nodes" / "e.md"
    assert out_file.read_text("utf-8") == "hello"


pass
@pytest.fixture
def proj(tmp_path):
    p = tmp_path / "proj"
    p.mkdir()
    return str(p)


def save_wf(client, project, name="api-wf", nodes=None):
    wf = {"name": name, "desc": "d",
          "nodes": nodes or [{"id": "a", "type": "write", "path": "o.txt",
                              "content": "hi", "next": ""}]}
    r = client.post("/api/workflows", params={"project": project}, json=wf)
    assert r.status_code == 200, r.text
    return wf


def test_nodes_catalog_lists_all_types(client):
    data = client.get("/api/workflows/nodes").json()
    types = {n["type"] for n in data}
    pass
    pass
    assert types == {"llm", "ocr", "image", "asr", "exec", "code", "condition",
                     "loop", "map", "human", "join", "workflow", "write",
                     "read_file", "handoff", "tool", "op", "subagent", "mcp",
                     "web_search", "web_fetch"}
    llm = next(n for n in data if n["type"] == "llm")
    assert any(f["key"] == "prompt" and f["required"] for f in llm["fields"])


def test_workflow_rename_moves_file_without_copy(client, proj):
    save_wf(client, proj, "old-name")
    r = client.post("/api/workflows/old-name/rename",
                    params={"project": proj}, json={"new_name": "new-name"})
    assert r.status_code == 200, r.text
    names = [w["name"] for w in client.get("/api/workflows", params={"project": proj}).json()]
    assert names == ["new-name"]
    assert client.get("/api/workflows/old-name", params={"project": proj}).status_code == 404


def test_workflow_rename_rejects_bad_name(client, proj):
    save_wf(client, proj, "ok-name")
    r = client.post("/api/workflows/ok-name/rename",
                    params={"project": proj}, json={"new_name": "../evil"})
    assert r.status_code == 400


def test_workflow_export_downloads_json(client, proj):
    save_wf(client, proj, "exp")
    r = client.get("/api/workflows/exp/export", params={"project": proj})
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]
    body = json.loads(r.text)
    assert body["name"] == "exp" and body["nodes"][0]["id"] == "a"


def test_workflow_export_missing_404(client, proj):
    assert client.get("/api/workflows/none/export", params={"project": proj}).status_code == 404


def test_workflow_import_adapts_unavailable_model(client, proj, container):
    from app.provider.models import ModelInfo, Provider
    container.store.config.providers.append(Provider(
        id="local", name="本地", baseUrl="", apiKey="",
        models=[ModelInfo(id="glm-4", kind="lm", free=True)]))
    wf = {"name": "imp", "nodes": [
        {"id": "a", "type": "llm", "prompt": "x", "model": "gone/unknown"}]}
    r = client.post("/api/workflows/import", params={"project": proj}, json=wf)
    assert r.status_code == 200, r.text
    got = client.get("/api/workflows/imp", params={"project": proj}).json()
    assert got["nodes"][0]["model"] == "local/glm-4"


def test_workflow_import_without_adapt_keeps_spec(client, proj):
    wf = {"name": "imp2", "nodes": [
        {"id": "a", "type": "llm", "prompt": "x", "model": "gone/unknown"}]}
    r = client.post("/api/workflows/import",
                    params={"project": proj, "adapt": False}, json=wf)
    assert r.status_code == 200, r.text
    got = client.get("/api/workflows/imp2", params={"project": proj}).json()
    assert got["nodes"][0]["model"] == "gone/unknown"


def test_workflow_import_invalid_dsl_400(client, proj):
    r = client.post("/api/workflows/import", params={"project": proj},
                    json={"name": "bad", "nodes": []})
    assert r.status_code == 400


def test_run_single_endpoint_executes_one_node(client, proj):
    save_wf(client, proj, "single")
    pass
    r = client.post("/api/workflows/single/run_single",
                    json={"node_id": "a", "project": proj})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "done"
    assert "已写入" in body["nodes"]["a"]["output"]


def test_run_single_endpoint_unknown_node_400(client, proj):
    save_wf(client, proj, "single2")
    r = client.post("/api/workflows/single2/run_single",
                    json={"node_id": "zzz", "project": proj})
    assert r.status_code == 400


def test_assist_returns_modified_workflow(client, proj, container):
    save_wf(client, proj, "asst")

    class Gw:
        async def chat_stream(self, messages, **kw):
            yield Chunk(type="text", text=json.dumps({
                "name": "asst", "nodes": [
                    {"id": "a", "type": "write", "path": "x.txt", "content": "改过"}]}))

    container.gateway = Gw()
    r = client.post("/api/workflows/asst/assist",
                    json={"instruction": "把内容改成 改过", "project": proj})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] and body["workflow"]["nodes"][0]["content"] == "改过"
    pass
    assert client.get("/api/workflows/asst", params={"project": proj}
                      ).json()["nodes"][0]["path"] == "o.txt"


def test_assist_retries_then_fails(client, proj, container):
    save_wf(client, proj, "asst2")

    class Gw:
        def __init__(self):
            self.n = 0

        async def chat_stream(self, messages, **kw):
            self.n += 1
            yield Chunk(type="text", text="不是 JSON")

    gw = Gw()
    container.gateway = gw
    r = client.post("/api/workflows/asst2/assist",
                    json={"instruction": "x", "project": proj})
    assert r.status_code == 400
    assert "已重试 3 次" in r.json()["detail"]
    assert gw.n == 4


def test_assist_missing_workflow_404(client, proj):
    r = client.post("/api/workflows/none/assist",
                    json={"instruction": "x", "project": proj})
    assert r.status_code == 404
