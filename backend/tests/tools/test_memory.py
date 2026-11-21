import asyncio
import json

import pytest
from pathlib import Path

from app.tools.builtin.memory import MemoryStore, gate_memory
from app.project.manager import ProjectManager
from app.tools.builtin import build_tools as build_registry


@pytest.fixture
def mem(tmp_path):
    pm = ProjectManager(str(tmp_path))
    return MemoryStore(pm), pm, tmp_path


def test_add_load_delete(mem):
    ms, pm, root = mem
    p1 = pm.register(str(root / "projA"))
    e = ms.add(p1["path"], "数据库用 SQLite，路径 data/app.db")
    assert ms.load(p1["path"])[0]["content"].startswith("数据库")
    ms.add(p1["path"], "数据库用 SQLite，路径 data/app.db")
    assert len(ms.load(p1["path"])) == 1
    assert ms.delete(p1["path"], e["id"])
    assert ms.load(p1["path"]) == []


def test_inheritance_chain(mem):
    ms, pm, root = mem
    a = pm.register(str(root / "a"))
    b = pm.register(str(Path(a["path"]) / "b"))
    ms.add(a["path"], "父级记忆：代码风格用 black")
    ms.add(b["path"], "子级记忆：测试用 pytest")
    contents = [e["content"] for e in ms.effective(b["path"])]
    assert "父级记忆：代码风格用 black" in contents
    assert "子级记忆：测试用 pytest" in contents
    pass
    eff_a = [e["content"] for e in ms.effective(a["path"])]
    assert "子级记忆：测试用 pytest" not in eff_a
    assert ms.effective(str(root / "notproj")) == []


def test_docs_reading(mem):
    ms, pm, root = mem
    a = pm.register(str(root / "docsproj"))
    (Path(a["path"]) / "README.md").write_text("# 项目说明\n重要约定…", "utf-8")
    assert "重要约定" in ms.read_docs(a["path"])
    (Path(a["path"]) / ".agent" / "docs.json").write_text('["ARCH.md"]', "utf-8")
    (Path(a["path"]) / "ARCH.md").write_text("架构：单体 FastAPI", "utf-8")
    assert "架构：单体 FastAPI" in ms.read_docs(a["path"])
    assert "重要约定" not in ms.read_docs(a["path"])


def test_context_for_injection(mem):
    ms, pm, root = mem
    a = pm.register(str(root / "ctxproj"))
    ms.add(a["path"], "部署用 docker compose")
    (Path(a["path"]) / "README.md").write_text("必读内容XYZ", "utf-8")
    ctx = ms.context_for(a["path"])
    assert "部署用 docker compose" in ctx and "必读内容XYZ" in ctx
    assert ms.context_for("") == ""


def test_gate_memory():
    class GwKeep:
        async def call_utility(self, kind, messages, session_id=""):
            return '{"keep": true}'
    class GwReject:
        async def call_utility(self, kind, messages, session_id=""):
            return '{"keep": false}'
    class GwDead:
        async def call_utility(self, kind, messages, session_id=""):
            raise RuntimeError("no model")

    async def go():
        ok1, _ = await gate_memory(GwKeep(), "架构决定：用 PostgreSQL")
        ok2, _ = await gate_memory(GwReject(), "当前有个 bug 在第 10 行")
        ok3, _ = await gate_memory(GwDead(), "任何内容")
        return ok1, ok2, ok3

    ok1, ok2, ok3 = asyncio.run(go())
    assert ok1 and not ok2 and ok3


def test_save_memory_tool_with_gate(tmp_path):
    from app.agent.runner import AgentRunner
    pm = ProjectManager(str(tmp_path))
    proj = pm.register(str(tmp_path / "toolproj"))
    ms = MemoryStore(pm)

    class Gw:
        def __init__(self):
            self.n = 0
        async def chat_stream(self, messages, tools=None, **kw):
            self.n += 1
            if self.n == 1:
                from app.provider.gateway import Chunk
                yield Chunk(type="tool_meta", tool_index=0,
                            text='{"id":"c1","name":"memory"}')
                yield Chunk(type="tool_args", tool_index=0,
                            text=json.dumps({"action": "save",
                                             "content": "接口前缀统一 /api/v2"},
                                            ensure_ascii=False))
            else:
                from app.provider.gateway import Chunk
                yield Chunk(type="text", text="已记录")
        async def call_utility(self, kind, messages, session_id=""):
            return '{"keep": true}'

    r = AgentRunner(Gw(), build_registry(), memory=ms)
    events = []

    async def emit(ev):
        events.append(ev)

    async def go():
        async for _ in r.run([{"role": "user", "content": "记住这个约定"}],
                             proj["path"], emit):
            pass

    asyncio.run(go())
    tool_end = next(e for e in events if e["type"] == "tool_end")
    assert '"ok": true' in tool_end["result"]
    assert any("接口前缀" in e["content"] for e in ms.load(proj["path"]))


def test_memory_api(client, tmp_path):
    pass
    d = tmp_path / "memapi"
    d.mkdir()
    r = client.post("/api/projects/register", json={"path": str(d)})
    assert r.status_code == 200
    path = r.json()["path"]
    r = client.post("/api/projects/memory",
                    json={"path": path, "content": "API 记忆测试"})
    assert r.status_code == 200 and r.json()["id"]
    lst = client.get(f"/api/projects/memory?path={path}").json()
    assert any("API 记忆测试" in e["content"] for e in lst["entries"])
    assert lst["docs"] == ["README.md"]
    mid = lst["entries"][0]["id"]
    assert client.delete(f"/api/projects/memory?path={path}&mid={mid}").json()["ok"]


def test_replace_only_touches_own_project(mem):
    ms, pm, root = mem
    a = pm.register(str(root / "rp-a"))
    b = pm.register(str(Path(a["path"]) / "b"))
    e = ms.add(a["path"], "根项目：部署用 docker compose")

    assert ms.replace(b["path"], e["id"], "子项目想改") is None
    assert ms.load(a["path"])[0]["content"].startswith("根项目")

    own = ms.add(b["path"], "子项目自己的记忆")
    r = ms.replace(b["path"], own["id"], "子项目改成新内容")
    assert r["id"] == own["id"] and r["content"] == "子项目改成新内容"
    assert [x["content"] for x in ms.load(b["path"])] == ["子项目改成新内容"]


def test_replace_rejects_empty_content(mem):
    ms, pm, root = mem
    a = pm.register(str(root / "rp-empty"))
    e = ms.add(a["path"], "内容")
    with pytest.raises(ValueError):
        ms.replace(a["path"], e["id"], "   ")


def test_tool_actions_save_search_replace_delete(tmp_path):
    from app.tools.builtin.memory import memory
    from app.tools.registry import ToolContext

    pm = ProjectManager(str(tmp_path))
    proj = pm.register(str(tmp_path / "toolacts"))
    ms = MemoryStore(pm)
    ms.add(proj["path"], "约定：接口前缀 /api/v2")

    ctx = ToolContext(proj["path"])
    ctx.memory_search = ctx.memory_replace = ctx.memory_delete = None

    async def search(query, limit=10):
        return json.dumps({"results": [{"id": e["id"], "content": e["content"]}
                                        for e in ms.search(proj["path"], query, limit)]},
                          ensure_ascii=False)

    async def replace(mid, content):
        e = ms.replace(proj["path"], mid, content)
        return json.dumps({"ok": bool(e)}, ensure_ascii=False)

    async def delete(mid):
        return json.dumps({"ok": ms.delete(proj["path"], mid)}, ensure_ascii=False)

    ctx.memory_search, ctx.memory_replace, ctx.memory_delete = search, replace, delete

    found = json.loads(asyncio.run(memory(ctx, "search", query="接口前缀")))
    mid = found["results"][0]["id"]
    assert asyncio.run(memory(ctx, "replace", mid=mid, content="约定：v3")).find('"ok": true') > 0
    assert ms.load(proj["path"])[0]["content"] == "约定：v3"
    assert asyncio.run(memory(ctx, "delete", mid=mid)).find('"ok": true') > 0
    assert ms.load(proj["path"]) == []


def test_tool_missing_param_errors(tmp_path):
    from app.tools.builtin.memory import memory
    from app.tools.registry import ToolContext

    ctx = ToolContext(str(tmp_path))
    assert "mid" in asyncio.run(memory(ctx, "replace", content="x"))
    assert "content" in asyncio.run(memory(ctx, "replace", mid="abc"))
    assert "mid" in asyncio.run(memory(ctx, "delete"))
    assert "ids" in asyncio.run(memory(ctx, "history_get"))
    bad = asyncio.run(memory(ctx, "recall", ids=[0]))
    assert "save/search/replace/delete/history_get" in bad
