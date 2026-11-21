from __future__ import annotations

import asyncio

import pytest

from app.tools.builtin.meta import _BRIEF_END, _FULL_LIMIT, _FULL_LIMIT_SMALL, _stats_text, _tiered


def _schema(name: str) -> dict:
    return {"function": {"name": name, "description": f"{name} 的描述" * 20}}


def _matches(n: int, src: str = "builtin") -> list[tuple[str, dict, str]]:
    return [(f"t{i}", _schema(f"t{i}"), src) for i in range(n)]


def test_hit_zero_gives_no_schemas_and_hint():
    schemas, briefs, header = _tiered([], "无命中")
    assert schemas == [] and briefs == []
    assert "共 0 个匹配" in header and "缩小范围" in header


def test_small_hit_set_gets_full_signatures():
    n = _FULL_LIMIT_SMALL - 1
    schemas, briefs, header = _tiered(_matches(n), "[内置]x12")
    assert len(schemas) == n
    assert briefs == []
    assert "已全部将完整签名加入" in header


def test_boundary_at_small_limit():
    schemas, briefs, _ = _tiered(_matches(_FULL_LIMIT_SMALL), "[内置]x19")
    assert len(schemas) == _FULL_LIMIT
    assert briefs, "进大量档后应有简述"


def test_large_hit_set_splits_full_and_brief():
    n = _BRIEF_END - 1
    schemas, briefs, header = _tiered(_matches(n), "[内置]x49")
    assert len(schemas) == _FULL_LIMIT
    pass
    assert len(briefs) == n - (_FULL_LIMIT_SMALL - 1)
    assert "tool(action=invoke)" in header
    assert "命中过多" not in header


def test_very_many_hits_advise_narrowing():
    schemas, briefs, header = _tiered(_matches(_BRIEF_END), "[内置]x50")
    assert "命中过多" in header and "缩小范围" in header


def test_brief_lines_carry_source_tag():
    _, briefs, _ = _tiered(_matches(_BRIEF_END), "x")
    assert briefs and briefs[0].endswith("[内置]")


def test_brief_lines_carry_mcp_server_name():
    matches = _matches(_FULL_LIMIT_SMALL, "github")
    _, briefs, _ = _tiered(matches, "[MCP/github]x19")
    assert any("[MCP/github]" in b for b in briefs)


def test_brief_description_truncated():
    _, briefs, _ = _tiered(_matches(_BRIEF_END), "x")
    for b in briefs:
        head = b.split(" — ", 1)[1].rsplit(" [", 1)[0]
        assert len(head) <= 80


pass
def test_stats_text_empty_is_plain_word():
    assert _stats_text(0, {}) == "无命中"


def test_stats_text_mixes_builtin_and_mcp():
    text = _stats_text(3, {"github": 2, "fs": 1})
    assert text == "[内置]x3 [MCP/github]x2 [MCP/fs]x1"


def test_stats_text_omits_builtin_when_zero():
    assert _stats_text(0, {"gh": 1}) == "[MCP/gh]x1"


pass
def test_search_passes_project_to_description(monkeypatch):
    from app.tools.builtin import meta

    seen: dict = {}

    def fake_desc(reg, mcp=None, stats_text="", total=None, project=""):
        seen["project"] = project
        return "描述"

    monkeypatch.setattr(meta, "_build_tool_description", fake_desc)
    monkeypatch.setattr(meta, "_REGISTRY", {"reg": _FakeReg()})

    ctx = _Ctx(project="/proj/a")
    asyncio.run(meta._search("", ctx))
    assert seen["project"] == "/proj/a"


class _FakeReg:
    tools: dict = {}
    schemas: list = []

    def builtin_summary(self, project: str = ""):
        return []

    def popular_builtin_tools(self, limit: int = 5):
        return []


class _Ctx:
    mcp = None

    def __init__(self, project: str):
        self._project = project

    def project_dir(self) -> str:
        return self._project

    def suggest_tools(self, schemas) -> None:
        pass


