from __future__ import annotations

import json
import re

import pytest

import app.tools.builtin.workflow_edit as we
from app.tools.builtin.workflow_help import _RECIPES, build_help
from app.workflow.nodes import build_default_nodes
from app.tools import ToolContext
from app.tools.builtin import build_tools as build_registry

pass
NODE_META_KEYS = {"id", "type", "next", "true", "false", "body", "edges", "edgesIn",
                  "pos", "position", "note", "group"}


@pytest.fixture(scope="module")
def reg():
    return build_default_nodes()


def calls_of(text: str) -> list[dict]:
    out = []
    for m in re.finditer(r'\{"action"', text):
        try:
            obj, _ = json.JSONDecoder().raw_decode(text[m.start():])
        except ValueError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


pass

def test_overview_lists_every_action_and_node(reg):
    text = build_help(reg)
    for act in we.WORKFLOW_ACTIONS:
        assert f"- {act}：" in text, f"速查表漏了动作 {act}"
    for spec in reg.all():
        assert f"- {spec.type}（{spec.label}）" in text, f"速查表漏了节点 {spec.type}"
    pass
    assert "必须再 save 才落盘" in text
    assert "nodes[0] 开始" in text


def test_overview_required_fields_match_registry(reg):
    text = build_help(reg)
    lines = {ln.split("（")[0].strip()[2:]: ln for ln in text.splitlines()
             if ln.startswith("  - ")}
    assert "必填 path, content" in lines["write"]
    assert "必填 prompt" in lines["llm"]
    assert "必填 expr, true" in lines["condition"]
    assert "必填 body, items" in lines["map"]
    pass
    pass
    for spec in reg.all():
        for f in spec.fields:
            if not f.options or f.required:
                continue
            want = f"{f.key}({'|'.join(f.options)})"
            assert want in lines[spec.type], f"{spec.type} 的 {want} 没出现在速查表"


pass

def test_overview_has_copyable_minimal_template(reg):
    from app.workflow import WorkflowEngine

    text = build_help(reg)
    assert "最小可运行模板" in text
    calls = calls_of(text)
    save = next(c for c in calls if c["action"] == "save")
    wf = save["workflow"]
    assert wf["name"] == save["name"]
    assert [n["type"] for n in wf["nodes"]] == ["llm", "write"]
    assert wf["nodes"][0]["next"] == wf["nodes"][1]["id"]
    WorkflowEngine.validate_structure(json.loads(json.dumps(wf)))
    run = next(c for c in calls if c["action"] == "run")
    assert run["name"] == save["name"]


def test_overview_warns_against_faking_it(reg):
    assert "必须真的 save 落盘" in build_help(reg)


def test_overview_lists_recipe_titles(reg):
    text = build_help(reg)
    for r in _RECIPES:
        assert r["title"].split("：")[-1] in text


def test_node_detail_has_fields_options_and_example(reg):
    text = build_help(reg, "llm")
    assert "## 节点 llm" in text
    assert "prompt" in text and "必填" in text
    pass
    fmt = next(f for f in reg.get("llm").fields if f.key == "format")
    assert f"select={'|'.join(fmt.options)}" in text
    pass
    assert not [f for f in reg.get("llm").fields if f.key == "queue"]
    model = next(f for f in reg.get("llm").fields if f.key == "model")
    assert model.kind == "model" and "model" in text
    line = next(ln for ln in text.splitlines() if ln.startswith("最小示例："))
    node = json.loads(line.split("：", 1)[1])
    assert node["type"] == "llm" and node["prompt"]


def test_condition_detail_mentions_branch_keys_once(reg):
    text = build_help(reg, "condition")
    pass
    for k in reg.get("condition").branch_keys:
        assert k in text, k
    assert text.count("必填字段") == 1
    pass
    assert "  - true" not in text


def test_human_detail_lists_all_exits(reg):
    text = build_help(reg, "human")
    for k in ("true", "false", "next"):
        assert f"  - {k}  " in text, k
    assert "走 next" in text


def test_action_detail_includes_tip_and_recipe_pointer(reg):
    text = build_help(reg, "add_node")
    assert "## action=add_node" in text
    assert "必填：name, node" in text
    assert "edit_node 接上游 next" in text
    assert "相关案例" in text


def test_topic_is_case_insensitive_and_fuzzy(reg):
    assert build_help(reg, "COND") == build_help(reg, "condition")
    assert build_help(reg, " add_node ") == build_help(reg, "add_node")
    assert "## 节点 write" in build_help(reg, "writ")


def test_ambiguous_topic_asks_for_full_name(reg):
    text = build_help(reg, "l")
    assert "匹配到多个" in text and "llm" in text


def test_overview_aliases(reg):
    for alias in ("用法", "帮助", "help", "总表", ""):
        assert build_help(reg, alias).startswith("# workflow 工具速查")


def test_unknown_topic_lists_available(reg):
    text = build_help(reg, "nope")
    assert "没有 topic" in text
    assert "llm" in text and "recipe" in text


pass

def test_recipes_present_and_indexed(reg):
    text = build_help(reg, "recipe")
    assert len(_RECIPES) >= 6
    for r in _RECIPES:
        assert r["title"] in text
        assert r["types"] and r["actions"]


def test_recipe_calls_are_valid_actions_with_known_params():
    allowed = {"action", "topic", "name", "node", "node_id", "fields", "workflow",
               "input", "ctx"}
    for r in _RECIPES:
        got = calls_of(r["body"])
        assert got, f"{r['id']} 里没有可解析的调用"
        for call in got:
            assert call["action"] in we.WORKFLOW_ACTIONS, f"{r['id']}: {call['action']}"
            assert set(call) <= allowed, f"{r['id']}: 多余参数 {set(call) - allowed}"


def test_recipe_workflow_definitions_pass_structure_validation(reg):
    from app.workflow import WorkflowEngine

    checked = 0
    for r in _RECIPES:
        for call in calls_of(r["body"]):
            wf = call.get("workflow")
            if not isinstance(wf, dict):
                continue
            WorkflowEngine.validate_structure(json.loads(json.dumps(wf)))
            checked += 1
    assert checked >= 3, "至少要有 3 个可直接照抄的完整工作流案例"


def test_recipe_node_fields_are_declared(reg):
    for r in _RECIPES:
        for call in calls_of(r["body"]):
            wf = call.get("workflow") or {}
            for node in wf.get("nodes") or []:
                spec = reg.get(node["type"])
                assert spec is not None, f"{r['id']}: 未知节点类型 {node['type']}"
                allowed = {f.key for f in spec.fields} | NODE_META_KEYS
                unknown = set(node) - allowed
                assert not unknown, f"{r['id']} 的 {node['type']} 节点用了未声明字段 {unknown}"
                missing = set(spec.required) - set(node) - {"true", "false"}
                assert not missing, f"{r['id']} 的 {node['id']} 缺必填 {missing}"


def test_recipe_variables_reference_defined_ids(reg):
    for r in _RECIPES:
        ids: set[str] = set()
        for call in calls_of(r["body"]):
            wf = call.get("workflow")
            if isinstance(wf, dict):
                ids |= {n["id"] for n in wf.get("nodes") or [] if n.get("id")}
        if not ids:
            continue
        for ref in set(re.findall(r'\$\{([A-Za-z_][\w]*(?:\.[\w]+)?)\}', r["body"])):
            head = ref.split(".")[0]
            assert head in ids or head in {"inputs", "prev", "__item__", "__i__"}, \
                f"{r['id']}: ${{{ref}}} 引用了未定义的 {head}"


pass

async def test_help_action_runs_without_name(tmp_path):
    ctx = ToolContext(str(tmp_path))
    out = await we.workflow_cmd(ctx, action="help")
    assert out.startswith("# workflow 工具速查")


async def test_help_action_accepts_topic_via_input(tmp_path):
    ctx = ToolContext(str(tmp_path))
    out = await we.workflow_cmd(ctx, action="help", input="llm")
    assert "## 节点 llm" in out


async def test_help_works_without_engine(tmp_path):
    ctx = ToolContext(str(tmp_path))
    assert ctx.wf_edit is None
    assert "## 一、动作" in await we.workflow_cmd(ctx, action="help")


async def test_help_prefers_topic_over_input(tmp_path):
    ctx = ToolContext(str(tmp_path))
    out = await we.workflow_cmd(ctx, action="help", topic="write", input="llm")
    assert "## 节点 write" in out


def _wf_schema() -> dict:
    reg = build_registry()
    spec = next(s for s in reg.schemas if s["function"]["name"] == "workflow")
    return spec["function"]


def test_schema_mentions_help_and_topic():
    params = _wf_schema()["parameters"]
    assert "help" in params["properties"]["action"]["enum"]
    assert "topic" in params["properties"]
    assert params["required"] == ["action"]


def test_schema_descriptions_are_action_specific():
    props = _wf_schema()["parameters"]["properties"]
    assert "add_node 必填" in props["node"]["description"]
    assert "edit_node 必填" in props["fields"]["description"]
    assert "edit_node / del_node 必填" in props["node_id"]["description"]
    assert "save 可选" in props["workflow"]["description"]
    assert "除 list/help 外都必填" in props["name"]["description"]
