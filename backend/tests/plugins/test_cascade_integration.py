from __future__ import annotations

import asyncio
import json

import pytest

from app.plugins.install import InstallStore, install
from app.plugins.tool_loader import PluginTools, reset_cache
from app.tools import ToolRegistry, cascade
from .helpers import mk_project


@pytest.fixture()
def global_env(tmp_dirs, monkeypatch):
    from app.store import layout
    plugins = tmp_dirs / "plugins"
    plugins.mkdir()
    monkeypatch.setattr(layout, "SOURCE_ROOT", tmp_dirs)
    reset_cache()
    cascade.reset()
    store = InstallStore(tmp_dirs / "agent.db")
    yield {"store": store, "reg": ToolRegistry(), "plugins": plugins,
           "tmp": tmp_dirs}
    cascade.reset()


def _package(root, pid, src, scope="global"):
    pkg = root / pid
    pkg.mkdir(parents=True)
    (pkg / "plugin.yaml").write_text(
        f"id: {pid}\nname: {pid}\nversion: 1.0.0\n"
        f"kinds: [tool]\nmode: release\n"
        f"tools:\n  - name: demo\n    scope: {scope}\n",
        "utf-8")
    (pkg / "tools").mkdir()
    (pkg / "tools" / "demo.py").write_text(src, "utf-8")
    return pkg


CASCADE_SRC = '''
def register(reg):
    async def paid(query: str = "", limit: int = 5, ctx=None):
        return "PAID:" + query
    reg.cascade("web", paid, order="after")
'''


def test_global_plugin_cascade_registers_and_merges(global_env):
    pkg = _package(global_env["plugins"], "paid", CASCADE_SRC)
    install(pkg, project="", store=global_env["store"])
    tools = PluginTools(global_env["store"])
    tools.load_global(global_env["reg"])

    pass
    assert "web" not in global_env["reg"].tools
    providers = cascade.providers("web")
    assert len(providers) == 1 and providers[0]["plugin_id"] == "paid"

    async def system():
        return json.dumps({"error": "免费失败"})

    out = asyncio.run(cascade.run("web", {"query": "abc"}, None, system))
    assert out == "PAID:abc"


def test_cascade_ignored_for_non_global_scope(global_env):
    proj = mk_project(global_env["tmp"])
    pkg = _package(proj / ".agent" / "plugins", "paid", CASCADE_SRC, scope="system")
    pass
    install(pkg, str(proj), store=global_env["store"])
    tools = PluginTools(global_env["store"])
    tools.load_for_project(str(proj), global_env["reg"])
    assert cascade.providers("web") == []


DIR_SRC = '''
def register(reg):
    reg.tool("dir_alpha", "演示", {"x": {"type": "string"}}, run)

def run(x: str = "", ctx=None):
    return "dir:" + x
'''


def test_tool_yaml_cascade_declaration_is_consumed(global_env):
    pkg = global_env["plugins"] / "dirt"
    (pkg / "tools" / "dirt").mkdir(parents=True)
    (pkg / "plugin.yaml").write_text(
        "id: dirt\nname: dirt\nversion: 1.0.0\nkinds: [tool]\nmode: release\n"
        "tools:\n  - name: dirt\n    scope: global\n", "utf-8")
    (pkg / "tools" / "dirt" / "tool.yaml").write_text(
        "entry: main.py\nscope: global\ncascade:\n  mode: system_first\n  target: web\n",
        "utf-8")
    (pkg / "tools" / "dirt" / "main.py").write_text(DIR_SRC, "utf-8")
    install(pkg, project="", store=global_env["store"])
    tools = PluginTools(global_env["store"])
    tools.load_global(global_env["reg"])

    assert "dir_alpha" not in global_env["reg"].tools
    assert [p["plugin_id"] for p in cascade.providers("web")] == ["dirt"]
