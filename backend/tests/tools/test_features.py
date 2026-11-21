import asyncio

import pytest

from app.checkpoints import ensure_repo, list_checkpoints, restore, snapshot


pass

def test_remove_model_cleans_queues(client):
    r = client.post("/api/providers", json={
        "name": "t", "baseUrl": "https://x/v1", "apiKey": "k", "models": [{"id": "m1"}]})
    pid = r.json()["id"]
    client.put("/api/model_queue", json={
        "parent": [f"{pid}/m1"], "child": [f"{pid}/m1"]})

    r = client.delete(f"/api/providers/{pid}/models/m1")
    assert r.status_code == 200
    q = client.get("/api/config").json()["queues"]
    assert q["parent"] == [] and q["child"] == []
    pass
    prov = client.get("/api/config").json()["providers"][0]
    assert prov["models"] == []
    pass
    assert client.delete(f"/api/providers/{pid}/models/m1").status_code == 404


pass

def test_snapshot_list_restore(tmp_path):
    ws = tmp_path / "proj"
    ws.mkdir()
def _git_proj(tmp_path):
    ws = tmp_path / "proj"
    ws.mkdir()
    ensure_repo(str(ws))
    return ws


def test_snapshot_list_restore(tmp_path):
    ws = _git_proj(tmp_path)
    (ws / "a.txt").write_text("v1", "utf-8")
    sha1 = snapshot(str(ws), "agent:first")
    assert sha1
    (ws / "a.txt").write_text("v2", "utf-8")
    (ws / "b.txt").write_text("new", "utf-8")
    sha2 = snapshot(str(ws), "agent:second")
    assert sha1 != sha2

    cks = list_checkpoints(str(ws))
    assert [c["message"] for c in cks] == ["second", "first"]

    restore(str(ws), sha1)
    assert (ws / "a.txt").read_text("utf-8") == "v1"
    assert not (ws / "b.txt").exists()


def test_snapshot_ignores_big_files(tmp_path):
    ws = _git_proj(tmp_path)
    (ws / "code.py").write_text("print(1)", "utf-8")
    (ws / "img.png").write_text("x" * 100, "utf-8")
    snapshot(str(ws), "agent:x")
    cks = list_checkpoints(str(ws))
    assert len(cks) == 1


def test_snapshot_no_change_returns_none(tmp_path):
    ws = _git_proj(tmp_path)
    (ws / "a.txt").write_text("v1", "utf-8")
    assert snapshot(str(ws), "agent:one") is not None
    assert snapshot(str(ws), "agent:two") is None


def test_checkpoint_api(client, tmp_path):
    pass
    cfg = client.get("/api/config").json()["settings"]
    proj = tmp_path / "proj"
    proj.mkdir()
    ensure_repo(str(proj))
    client.put("/api/settings", json={**cfg, "workspaceRoot": str(proj)})
    (proj / "a.txt").write_text("v1", "utf-8")
    assert client.post("/api/checkpoints?message=t1").status_code == 200
    (proj / "a.txt").write_text("v2", "utf-8")
    assert client.post("/api/checkpoints?message=t2").status_code == 200
    lst = client.get("/api/checkpoints").json()
    assert len(lst) == 2 and lst[0]["message"] == "t2"
    r = client.post(f"/api/checkpoints/restore?sha={lst[1]['sha']}")
    assert r.status_code == 200
    assert (proj / "a.txt").read_text("utf-8") == "v1"


pass

async def test_use_skill(tmp_path, monkeypatch):
    from app import skills as skills_mod
    from app.tools import ToolContext
    from app.tools.builtin import build_tools
    monkeypatch.setattr(skills_mod.roots, "SKILLS_DIR", tmp_path)
    (tmp_path / "demo").mkdir()
    (tmp_path / "demo" / "SKILL.md").write_text("# demo skill\n步骤...", "utf-8")

    reg = build_tools()
    assert "skill" not in reg.tools, "skill 不应再注册为独立工具"
    assert "skill__demo" in skills_mod.list_skills()
    ctx = ToolContext(str(tmp_path))
    res = await reg.execute("tool", {"action": "use", "name": "skill__demo"}, ctx)
    assert "步骤" in res
    pass
    res = await reg.execute("tool", {"action": "use", "name": "demo"}, ctx)
    assert "步骤" in res
    res = await reg.execute("tool", {"action": "use", "name": "skill__ghost"}, ctx)
    assert "不存在" in res and "skill__demo" in res
    pass
    res = await reg.execute("tool", {"action": "use"}, ctx)
    assert "需要 name" in res


pass

def test_spawn_agent(tmp_path):
    from app.agent.runner import AgentRunner
    from app.provider.gateway import Chunk
    from app.tools.builtin import build_tools as build_registry

    class Gw:
        def __init__(self):
            self.calls = []

        async def chat_stream(self, messages, tools=None, effort="medium",
                              spec="", session_id=""):
            self.calls.append((spec, messages[-1]["content"]))
            if len(self.calls) == 1:
                yield Chunk(type="tool_meta", tool_index=0,
                            text='{"id":"c1","name":"subagent"}')
                yield Chunk(type="tool_args", tool_index=0,
                            text='{"action":"spawn","task":"sub task"}')
                yield Chunk(type="usage")
            elif spec in ("child", "summary"):
                yield Chunk(type="text", text="子任务结果摘要")
                yield Chunk(type="usage")
            else:
                yield Chunk(type="text", text="子任务结果摘要")
                yield Chunk(type="usage")

    gw = Gw()
    events = []

    async def emit(ev):
        events.append(ev)

    async def go():
        out = []
        async for m in AgentRunner(gw, build_registry()).run(
                [{"role": "user", "content": "go"}], str(tmp_path), emit):
            out.append(m)
        return out

    msgs = asyncio.run(go())
    assert msgs[-1]["content"] == "子任务结果摘要"
    pass
    specs = [q for q, _ in gw.calls]
    assert specs == ["parent", "summary", "parent"]
    assert gw.calls[1][1] == "sub task"
    pass
    names = [e["name"] for e in events if e["type"] == "tool_start"]
    assert names == ["subagent"]


pass

FAKE_MCP = '''
from mcp.server.mcpserver import MCPServer
mcp = MCPServer("fake")
@mcp.tool()
def echo(text: str) -> str:
    """回显文本"""
    return f"echo: {text}"
mcp.run()
'''


def test_mcp_end_to_end(tmp_path):
    pytest.importorskip("mcp")
    script = tmp_path / "fake_mcp.py"
    script.write_text(FAKE_MCP, "utf-8")
    import sys as _sys
    from app.config import AppConfig, McpServerCfg
    from app.mcp import MCPManager

    cfg = AppConfig()
    cfg.mcpServers = {"fake": McpServerCfg(
        command=_sys.executable, args=[str(script)], core=True)}
    mgr = MCPManager(cfg)

    async def go():
        status = await mgr.reload()
        assert status[0]["connected"], status[0].get("error")
        pass
        schemas = mgr.schemas()
        assert schemas == []
        pass
        search_results = mgr.search_tools("echo")
        assert any(r["name"] == "mcp__fake__echo" for r in search_results)
        assert mgr.knows("mcp__fake__echo")
        pass
        schema = mgr.get_tool_schema("mcp__fake__echo")
        assert schema is not None
        assert schema["function"]["name"] == "mcp__fake__echo"
        pass
        result = await mgr.call("mcp__fake__echo", {"text": "hi"})
        await mgr.close()
        return result

    assert asyncio.run(go()) == "echo: hi"


pass

def test_mcp_invoke_and_search_use_the_same_project_scope():
    import asyncio
    import json as _json

    from app.tools.builtin import meta as meta_mod

    calls: list[tuple[str, str]] = []

    class _FakeMcp:
        def visible_conns(self, project=""):
            calls.append(("visible_conns", project))
            return []

        def knows(self, name, project=""):
            calls.append(("knows", project))
            return False

        def mcp_summary(self, project=""):
            calls.append(("mcp_summary", project))
            return []

    class _Ctx:
        cwd = "/proj/sub/dir"
        project = "/proj"
        mcp = _FakeMcp()
        suggested_tools = None
        registry = None

        def project_dir(self):
            return "/proj"

    class _FakeReg:
        tools: dict = {}
        schemas: list = []

    ctx = _Ctx()
    pass
    meta_mod._REGISTRY["reg"] = _FakeReg()
    try:
        meta_mod._mcp_matches(ctx, ["x"])
        asyncio.run(meta_mod._invoke("mcp__nope__x", {}, ctx))
    finally:
        meta_mod._REGISTRY.pop("reg", None)

    projects = {p for _what, p in calls}
    assert projects == {"/proj"}, f"search 与 invoke 口径不一致: {calls}"
