from __future__ import annotations

import json

import pytest

from app.mcp.query import MCPQueryMixin


class _Conn:
    def __init__(self, name, owner="", ready=True, tools=None):
        self.name = name
        self.owner = owner
        self.ready = ready
        self.tools = tools or {}
        self.started = True


def _schema(desc="描述"):
    return {"function": {"name": "x", "description": desc, "parameters": {}}}


class _Mgr(MCPQueryMixin):

    def __init__(self, conns, top_map=None):
        self._conns = {c.name: c for c in conns}
        self._tool_call_counts: dict[str, int] = {}
        self._top_map = top_map or {}
        self.calls: list = []
        self.fail_with: Exception | None = None

    def status(self):
        return [{"name": c.name, "ready": c.ready} for c in self._conns.values()]

    def _visible_conns(self, project=""):
        if not project:
            return [c for c in self._conns.values() if not c.owner]
        return [c for c in self._conns.values()
                if not c.owner or c.owner == project]

    async def _ensure_connected(self, c):
        self.calls.append(("ensure", c.name))

    async def _request(self, c, op, payload):
        self.calls.append((op, c.name))
        if self.fail_with:
            raise self.fail_with
        return json.dumps({"ok": True, "name": payload.get("name")})


def _mgr_with_tools():
    return _Mgr([
        _Conn("global", tools={"mcp__global__a": _schema("读文件")}),
        _Conn("projA", owner="/p/a", tools={"mcp__projA__b": _schema("写库")}),
        _Conn("lazy", owner="/p/a", ready=False, tools={}),
    ])


pass
def test_global_visible_to_everyone():
    m = _mgr_with_tools()
    assert {c.name for c in m.visible_conns("/p/b")} == {"global"}
    assert {c.name for c in m.visible_conns("/p/a")} == {"global", "projA", "lazy"}


def test_project_tool_not_visible_to_other_project():
    m = _mgr_with_tools()
    assert "mcp__projA__b" not in [t["name"] for t in m.search_tools("", "/p/b")]


def test_no_project_sees_only_global():
    m = _mgr_with_tools()
    assert [c.name for c in m.visible_conns("")] == ["global"]


def test_visible_status_filtered_by_project():
    m = _mgr_with_tools()
    assert [s["name"] for s in m.visible_status("/p/b")] == ["global"]


pass
def test_search_matches_name_and_description():
    m = _mgr_with_tools()
    assert m.search_tools("global", "/p/a")
    assert m.search_tools("读文件", "/p/a")
    assert m.search_tools("读文件", "/p/b")


def test_search_empty_returns_all_visible_and_ready():
    m = _mgr_with_tools()
    names = [t["name"] for t in m.search_tools("", "/p/a")]
    assert "mcp__global__a" in names and "mcp__projA__b" in names


def test_search_skips_not_ready_conn():
    m = _Mgr([_Conn("x", ready=False, tools={"mcp__x__t": _schema()})])
    assert m.search_tools("", "") == []


def test_knows_respects_project_scope():
    m = _mgr_with_tools()
    assert m.knows("mcp__projA__b", "/p/a") is True
    assert m.knows("mcp__projA__b", "/p/b") is False


def test_get_tool_schema_by_name():
    m = _mgr_with_tools()
    assert m.get_tool_schema("mcp__global__a", "") is not None
    assert m.get_tool_schema("nope", "") is None


def test_schemas_never_injects_mcp_tools():
    assert _mgr_with_tools().schemas() == []


pass
def test_popular_empty_when_no_counts():
    assert _mgr_with_tools().popular_mcp_tools() == []


def test_popular_sorted_by_count_and_scoped():
    m = _mgr_with_tools()
    m._tool_call_counts = {"mcp__global__a": 2, "mcp__projA__b": 9}
    top = m.popular_mcp_tools(limit=10, project="/p/b")
    assert [r["name"] for r in top] == ["mcp__global__a"]


def test_popular_respects_limit():
    conn = _Conn("g", tools={f"mcp__g__t{i}": _schema() for i in range(5)})
    m = _Mgr([conn])
    m._tool_call_counts = {f"mcp__g__t{i}": i for i in range(5)}
    assert len(m.popular_mcp_tools(limit=3)) == 3


pass
def test_mcp_summary_lists_short_names():
    m = _mgr_with_tools()
    out = {x["server"]: x for x in m.mcp_summary("/p/a")}
    assert out["global"]["tools"] == ["a"]
    assert out["global"]["tool_count"] == 1


def test_mcp_summary_skips_servers_without_tools():
    m = _mgr_with_tools()
    assert [x["server"] for x in m.mcp_summary("")] == ["global"]


pass
@pytest.mark.asyncio
async def test_call_ensures_connection_first():
    m = _mgr_with_tools()
    await m.call("mcp__global__a", {}, "")
    assert m.calls[0] == ("ensure", "global")


@pytest.mark.asyncio
async def test_call_success_increments_count():
    m = _mgr_with_tools()
    await m.call("mcp__global__a", {}, "")
    assert m._tool_call_counts["mcp__global__a"] == 1


@pytest.mark.asyncio
async def test_call_failure_does_not_increment_count():
    m = _mgr_with_tools()
    m.fail_with = RuntimeError("boom")
    out = json.loads(await m.call("mcp__global__a", {}, ""))
    assert "MCP 调用失败" in out["error"]
    assert "mcp__global__a" not in m._tool_call_counts


@pytest.mark.asyncio
async def test_call_unknown_tool_reports_error():
    m = _mgr_with_tools()
    out = json.loads(await m.call("nope", {}, ""))
    assert "不存在" in out["error"]


@pytest.mark.asyncio
async def test_call_cannot_reach_other_projects_tool():
    m = _mgr_with_tools()
    out = json.loads(await m.call("mcp__projA__b", {}, "/p/b"))
    assert "不存在" in out["error"]


@pytest.mark.asyncio
async def test_refresh_tools_on_unknown_server():
    m = _mgr_with_tools()
    assert "未连接" in (await m.refresh_tools("nope"))["error"]
