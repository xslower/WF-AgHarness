from __future__ import annotations

import json

import pytest

import app.tools.builtin.workflow_edit as we
from app.tools import ToolContext
from app.workflow import WorkflowEngine


@pytest.fixture(autouse=True)
def _clean_drafts():
    we._DRAFTS.clear()
    yield
    we._DRAFTS.clear()


@pytest.fixture
def eng(tmp_path):
    d = tmp_path / "workflows"
    d.mkdir(parents=True)
    return WorkflowEngine(workflows_dir=d)


@pytest.fixture
def ctx(tmp_path, eng):
    c = ToolContext(str(tmp_path))
    c.wf_edit = eng
    return c


@pytest.fixture
def demo(tmp_path, eng):
    eng.save({"name": "demo", "desc": "示例",
              "nodes": [{"id": "n1", "type": "llm", "next": "n2"},
                        {"id": "n2", "type": "write", "path": "out.md"}]})
    return "demo"


def j(s: str):
    return json.loads(s)


def node_ids(wf: dict) -> list[str]:
    return [n["id"] for n in wf["nodes"]]


pass
async def test_list_empty(ctx):
    assert j(await we.workflow_cmd(ctx, "list")) == []


async def test_list_reports_name_desc_nodes(ctx, demo):
    out = j(await we.workflow_cmd(ctx, "list"))
    pass
    assert len(out) == 1
    assert {k: out[0][k] for k in ("name", "desc", "nodes")} == {
        "name": "demo", "desc": "示例", "nodes": 2}


async def test_list_tolerates_broken_file(ctx, eng, tmp_path):
    (eng.dir / "bad.json").write_text("{ not json", "utf-8")
    names = {x["name"]: x for x in j(await we.workflow_cmd(ctx, "list"))}
    assert names["bad"]["desc"] == "(解析失败)" and names["bad"]["nodes"] == 0


async def test_get_returns_definition_with_revision(ctx, demo):
    wf = j(await we.workflow_cmd(ctx, "get", name="demo"))
    assert node_ids(wf) == ["n1", "n2"]
    assert wf["_revision"]


async def test_get_missing_workflow_reports_error(ctx):
    assert "工作流不存在: nope" in j(await we.workflow_cmd(ctx, "get", name="nope"))["error"]


pass
async def test_list_node_summary_excludes_routing_keys(ctx, demo):
    out = j(await we.workflow_cmd(ctx, "list_node", name="demo"))
    assert [x["id"] for x in out] == ["n1", "n2"]
    assert out[0]["next"] == "n2"
    pass
    assert set(out[0]["fields"]) == set()
    assert out[1]["fields"] == {"path": "out.md"}


async def test_list_node_missing_workflow(ctx):
    assert "工作流不存在" in j(await we.workflow_cmd(ctx, "list_node", name="nope"))["error"]


pass
async def test_add_node_is_visible_before_save(ctx, demo):
    r = j(await we.workflow_cmd(ctx, "add_node", name="demo",
                                node={"id": "n3", "type": "write"}))
    assert r["ok"] is True and r["nodes"] == 3
    assert node_ids(j(await we.workflow_cmd(ctx, "get", name="demo"))) == ["n1", "n2", "n3"]
    assert [x["id"] for x in j(await we.workflow_cmd(ctx, "list_node", name="demo"))] == \
        ["n1", "n2", "n3"]


async def test_add_node_then_save_hits_disk(ctx, eng, demo):
    await we.workflow_cmd(ctx, "add_node", name="demo", node={"id": "n3", "type": "write"})
    r = j(await we.workflow_cmd(ctx, "save", name="demo"))
    assert r == {"ok": True, "name": "demo", "nodes": 3}
    assert node_ids(eng.get("demo")) == ["n1", "n2", "n3"]


async def test_add_node_rejects_duplicate_id(ctx, demo):
    r = j(await we.workflow_cmd(ctx, "add_node", name="demo", node={"id": "n1", "type": "llm"}))
    assert "节点 id 已存在" in r["error"]


async def test_add_node_requires_id_and_type(ctx, demo):
    assert "需要 id 和 type" in j(await we.workflow_cmd(
        ctx, "add_node", name="demo", node={"id": "x"}))["error"]
    assert "需要 id 和 type" in j(await we.workflow_cmd(
        ctx, "add_node", name="demo", node={"type": "llm"}))["error"]


async def test_add_node_missing_workflow(ctx):
    assert "工作流不存在" in j(await we.workflow_cmd(
        ctx, "add_node", name="nope", node={"id": "a", "type": "llm"}))["error"]


pass
async def test_edit_node_merges_fields_and_persists(ctx, eng, demo):
    r = j(await we.workflow_cmd(ctx, "edit_node", name="demo", node_id="n2",
                                fields={"prompt": "写摘要", "path": "sum.md"}))
    assert r["ok"] and r["node"]["prompt"] == "写摘要"
    await we.workflow_cmd(ctx, "save", name="demo")
    on_disk = {n["id"]: n for n in eng.get("demo")["nodes"]}
    assert on_disk["n2"]["prompt"] == "写摘要" and on_disk["n2"]["path"] == "sum.md"
    assert on_disk["n2"]["type"] == "write"


async def test_edit_node_null_deletes_key(ctx, eng, demo):
    await we.workflow_cmd(ctx, "edit_node", name="demo", node_id="n2", fields={"path": None})
    assert "path" in {n["id"]: n for n in eng.get("demo")["nodes"]}["n2"]
    await we.workflow_cmd(ctx, "save", name="demo")
    assert "path" not in {n["id"]: n for n in eng.get("demo")["nodes"]}["n2"]


async def test_edit_node_missing_node(ctx, demo):
    assert "节点不存在" in j(await we.workflow_cmd(
        ctx, "edit_node", name="demo", node_id="zzz", fields={"a": 1}))["error"]


async def test_edit_node_missing_workflow(ctx):
    assert "工作流不存在" in j(await we.workflow_cmd(
        ctx, "edit_node", name="nope", node_id="n1", fields={"a": 1}))["error"]


pass
async def test_del_node_removes_and_cleans_references(ctx, demo):
    await we.workflow_cmd(ctx, "add_node", name="demo",
                          node={"id": "n3", "type": "condition", "true": "n3", "false": "n2"})
    r = j(await we.workflow_cmd(ctx, "del_node", name="demo", node_id="n3"))
    assert r == {"ok": True, "nodes": 2}
    wf = j(await we.workflow_cmd(ctx, "get", name="demo"))
    assert {n["id"]: n for n in wf["nodes"]}["n1"]["next"] == "n2"


async def test_del_node_clears_next_pointing_to_it(ctx, eng, demo):
    await we.workflow_cmd(ctx, "del_node", name="demo", node_id="n2")
    r = j(await we.workflow_cmd(ctx, "save", name="demo"))
    assert r["ok"] is True, r
    assert node_ids(eng.get("demo")) == ["n1"]
    assert "next" not in eng.get("demo")["nodes"][0]


async def test_del_node_missing(ctx, demo):
    assert "节点不存在" in j(await we.workflow_cmd(ctx, "del_node", name="demo",
                                                  node_id="zzz"))["error"]


async def test_del_node_missing_workflow(ctx):
    assert "工作流不存在" in j(await we.workflow_cmd(ctx, "del_node", name="nope",
                                                    node_id="n1"))["error"]


pass
async def test_save_full_definition_creates_new(ctx, eng):
    r = j(await we.workflow_cmd(ctx, "save", name="fresh", workflow={
        "name": "fresh", "nodes": [{"id": "a", "type": "llm"}]}))
    assert r == {"ok": True, "name": "fresh", "nodes": 1}
    assert node_ids(eng.get("fresh")) == ["a"]


async def test_save_does_not_mutate_caller_dict(ctx):
    payload = {"name": "keep", "nodes": [{"id": "a", "type": "llm"}],
               "_revision": "fake"}
    await we.workflow_cmd(ctx, "save", name="keep", workflow=payload)
    assert payload["_revision"] == "fake"


async def test_save_invalid_structure_reports_error(ctx):
    r = j(await we.workflow_cmd(ctx, "save", name="bad", workflow={"nodes": []}))
    assert "缺少 name" in r["error"]


async def test_save_conflict_when_disk_changed(ctx, eng, demo):
    await we.workflow_cmd(ctx, "edit_node", name="demo", node_id="n1", fields={"prompt": "agent"})
    pass
    fresh = eng.get("demo")
    fresh["nodes"].append({"id": "ui", "type": "write"})
    eng.save(fresh)
    r = j(await we.workflow_cmd(ctx, "save", name="demo"))
    pass
    assert r["ok"] is True
    assert "ui" in node_ids(eng.get("demo"))


async def test_save_missing_workflow(ctx):
    assert "工作流不存在" in j(await we.workflow_cmd(ctx, "save", name="nope"))["error"]


pass
async def test_dispatch_rejects_unknown_action(ctx):
    r = j(await we.workflow_cmd(ctx, "explode"))
    assert "action 必须是" in r["error"] and "explode" in r["error"]


@pytest.mark.parametrize("action,kwargs,expect", [
    ("get", {}, "需要 name"),
    ("list_node", {}, "需要 name"),
    ("add_node", {}, "需要 name"),
    ("save", {}, "需要 name"),
    ("add_node", {"name": "demo"}, "需要 node"),
    ("edit_node", {"name": "demo"}, "需要 node_id 与 fields"),
    ("edit_node", {"name": "demo", "node_id": "n1"}, "需要 node_id 与 fields"),
    ("del_node", {"name": "demo"}, "需要 node_id"),
])
async def test_dispatch_required_params(ctx, demo, action, kwargs, expect):
    assert expect in j(await we.workflow_cmd(ctx, action, **kwargs))["error"]


async def test_run_requires_name(ctx):
    assert "action=run 需要 name" in j(await we.workflow_cmd(ctx, "run"))["error"]


async def test_run_without_callback(ctx, demo):
    assert "工作流执行不可用" in j(await we.workflow_cmd(ctx, "run", name="demo"))["error"]


async def test_run_delegates_to_injected_callback(ctx, demo):
    seen = {}

    async def fake_start(name, inp, human, start_node="", parallel=""):
        seen["name"], seen["input"], seen["human"] = name, inp, human
        seen["start_node"] = start_node
        seen["parallel"] = parallel
        return '{"run_id": "r1"}'

    ctx.workflow_start = fake_start
    out = await we.workflow_cmd(ctx, "run", name="demo", input="你好")
    assert json.loads(out)["run_id"] == "r1"
    pass
    assert seen == {"name": "demo", "input": "你好", "human": "deny",
                    "start_node": "", "parallel": ""}
    pass
    await we.workflow_cmd(ctx, "run", name="demo", input="你好", start_node="s3")
    assert seen["start_node"] == "s3"


async def test_engine_not_injected(ctx):
    bare = ToolContext(str(ctx.cwd))
    for action, kw in (("list", {}), ("get", {"name": "demo"}),
                       ("list_node", {"name": "demo"}),
                       ("add_node", {"name": "demo", "node": {"id": "x", "type": "llm"}}),
                       ("del_node", {"name": "demo", "node_id": "n1"}),
                       ("save", {"name": "demo"}),
                       ("edit_node", {"name": "demo", "node_id": "n1", "fields": {}})):
        assert "工作流功能不可用" in j(await we.workflow_cmd(bare, action, **kw))["error"]


async def test_tool_registered_with_all_actions():
    from app.tools.builtin import build_tools as build_registry
    reg = build_registry()
    spec = reg.tools["workflow"]
    assert spec is not None
    assert list(we.WORKFLOW_ACTIONS) == ["list", "help", "run", "wait", "get",
                                         "list_node", "add_node", "edit_node",
                                         "del_node", "save"]
