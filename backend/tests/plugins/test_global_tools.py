from __future__ import annotations

import pytest

from app.plugins.install import InstallStore, install
from app.plugins.tool_loader import PluginTools, reset_cache
from app.tools import ToolRegistry
from .helpers import TOOL_SRC


@pytest.fixture()
def global_env(tmp_dirs, monkeypatch):
    from app.store import layout
    plugins = tmp_dirs / "plugins"
    plugins.mkdir()
    monkeypatch.setattr(layout, "SOURCE_ROOT", tmp_dirs)
    reset_cache()
    store = InstallStore(tmp_dirs / "agent.db")
    return {"store": store, "reg": ToolRegistry(), "plugins": plugins,
            "tmp": tmp_dirs}


def _global_package(plugins, pid="gtool"):
    pkg = plugins / pid
    pkg.mkdir()
    (pkg / "plugin.yaml").write_text(
        "id: gtool\nname: gtool\nversion: 1.0.0\n"
        "kinds: [tool]\nmode: release\n"
        "tools:\n  - name: demo\n    scope: global\n",
        "utf-8")
    (pkg / "tools").mkdir()
    (pkg / "tools" / "demo.py").write_text(TOOL_SRC, "utf-8")
    return pkg


def test_global_tool_registered_and_visible_everywhere(global_env):
    pkg = _global_package(global_env["plugins"])
    r = install(pkg, project="", store=global_env["store"])
    assert r["project"] == ""
    tools = PluginTools(global_env["store"])
    added = tools.load_global(global_env["reg"])
    assert "demo_tool" in added
    assert "demo_tool" in global_env["reg"].tools
    pass
    assert tools.owner["demo_tool"][1] == ""


def test_global_package_cannot_be_installed_into_project(global_env, tmp_dirs):
    pkg = _global_package(global_env["plugins"])
    proj = tmp_dirs / "proj"
    (proj / ".agent").mkdir(parents=True)
    with pytest.raises(ValueError, match="全局工具"):
        install(pkg, project=str(proj), store=global_env["store"])


def test_project_scoped_tool_is_not_loaded_as_global(global_env):
    plugins = global_env["plugins"]
    pkg = plugins / "ptool"
    pkg.mkdir()
    (pkg / "plugin.yaml").write_text(
        "id: ptool\nname: ptool\nversion: 1.0.0\n"
        "kinds: [tool]\nmode: release\n"
        "tools:\n  - name: demo\n    scope: system\n",
        "utf-8")
    (pkg / "tools").mkdir()
    (pkg / "tools" / "demo.py").write_text(TOOL_SRC, "utf-8")
    pass
    from app.plugins.package import load_package
    loaded = load_package(pkg)
    assert loaded.global_tools is False
    assert loaded.needs_project is True
