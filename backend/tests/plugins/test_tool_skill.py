import asyncio
import json

import pytest

from app import skills as skills_mod
from app.tools import ToolContext
from app.tools.builtin import build_tools
import app.tools.builtin.meta as meta_mod


def run(reg, ctx, name, args):
    return asyncio.run(reg.execute(name, args, ctx))


@pytest.fixture
def skill_reg(tmp_path, monkeypatch):
    monkeypatch.setattr(skills_mod.roots, "SKILLS_DIR", tmp_path)
    (tmp_path / "demo").mkdir()
    (tmp_path / "demo" / "SKILL.md").write_text(
        "# 部署指南\ntags: 部署, docker\n用 docker compose 起服务。", "utf-8")
    (tmp_path / "report").mkdir()
    (tmp_path / "report" / "SKILL.md").write_text(
        "# 报表生成\ntags: 报表\n用 pandas 汇总后导出 xlsx。", "utf-8")
    reg = build_tools()
    return reg, ToolContext(str(tmp_path))


def test_skill_not_registered_as_tool(skill_reg):
    reg, _ = skill_reg
    assert "skill" not in reg.tools
    assert "tool" in reg.tools


def test_skill_names_are_prefixed(skill_reg):
    reg, _ = skill_reg
    names = skills_mod.list_skills()
    assert "skill__demo" in names and "skill__report" in names
    assert "demo" not in names


def test_use_loads_skill_body(skill_reg):
    reg, ctx = skill_reg
    out = run(reg, ctx, "tool", {"action": "use", "name": "skill__demo"})
    assert "docker compose" in out


def test_use_prefix_is_optional(skill_reg):
    reg, ctx = skill_reg
    assert "docker compose" in run(reg, ctx, "tool",
                                   {"action": "use", "name": "demo"})


def test_use_missing_name_is_clear_error(skill_reg):
    reg, ctx = skill_reg
    data = json.loads(run(reg, ctx, "tool", {"action": "use"}))
    assert "error" in data and "name" in data["error"]


def test_use_unknown_skill_lists_available(skill_reg):
    reg, ctx = skill_reg
    data = json.loads(run(reg, ctx, "tool",
                          {"action": "use", "name": "skill__ghost"}))
    assert "不存在" in data["error"]
    assert "skill__demo" in data["error"]


def test_search_hits_skill_and_points_to_use(skill_reg):
    reg, ctx = skill_reg
    out = run(reg, ctx, "tool", {"action": "search", "query": "报表"})
    assert "技能库命中" in out
    assert "skill__report" in out
    assert "action=use" in out


def test_search_hits_by_tag(skill_reg):
    reg, ctx = skill_reg
    out = run(reg, ctx, "tool", {"action": "search", "query": "docker"})
    assert "skill__demo" in out


def test_invoke_routes_skill_to_use(skill_reg):
    reg, ctx = skill_reg
    out = run(reg, ctx, "tool", {"action": "invoke", "name": "skill__demo"})
    assert "docker compose" in out
    assert "等价 tool(action=use)" in out


def test_skill_catalog_is_always_in_description(skill_reg):
    reg, _ = skill_reg
    meta_mod.update_dynamic_schemas(reg)
    tool = next(s["function"] for s in reg.schemas
                if s["function"]["name"] == "tool")
    desc = tool["description"]
    assert "技能库" in desc
    assert "skill__demo" in desc and "skill__report" in desc
    assert "部署指南" in desc
