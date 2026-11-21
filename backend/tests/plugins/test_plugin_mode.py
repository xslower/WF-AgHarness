from __future__ import annotations

import pytest

from app.plugins import install as inst
from app.plugins import package as pkgmod
from app.plugins import visibility, adopt
from app.plugins.tool_loader import _scope_of
from .helpers import mk_package, mk_project, tool_package, mk_project


@pytest.fixture()
def store(tmp_dirs):
    return inst.InstallStore(tmp_dirs / "agent.db")


def test_mode_is_required(tmp_dirs):
    proj = mk_project(tmp_dirs)
    pkg = mk_package(proj)
    pass
    import yaml
    f = pkg / "plugin.yaml"
    d = yaml.safe_load(f.read_text("utf-8"))
    d.pop("mode", None)
    f.write_text(yaml.safe_dump(d, allow_unicode=True), "utf-8")
    with pytest.raises(ValueError, match="mode"):
        pkgmod.load_package(pkg)


def test_mode_values(tmp_dirs):
    proj = mk_project(tmp_dirs)
    assert pkgmod.load_package(mk_package(proj, pid="devpkg", mode="dev")).is_dev is True
    assert pkgmod.load_package(mk_package(proj, pid="relpkg", mode="release")).is_dev is False


def test_only_declared_tools_are_registered(tmp_dirs, store):
    proj = mk_project(tmp_dirs)
    pkg = mk_package(proj, kinds=("tool",), files={
        "tools/declared.py": "def register(reg):\n    pass\n",
        "tools/undeclared.py": "def register(reg):\n    pass\n",
    })
    import yaml
    f = pkg / "plugin.yaml"
    d = yaml.safe_load(f.read_text("utf-8"))
    d["tools"] = [{"name": "declared", "scope": "system"}]
    f.write_text(yaml.safe_dump(d, allow_unicode=True), "utf-8")
    plan = pkgmod.plan_registrations(pkgmod.load_package(pkg), str(proj))
    rows = [r for r in plan if r["kind"] == "tool"]
    assert [r["rel_path"].split("/")[-1] for r in rows] == ["declared.py"]
    assert rows[0]["extra"]["scope"] == "system"


def test_internal_tool_registered_but_invisible_to_sessions(tmp_dirs, store):
    proj = mk_project(tmp_dirs)
    pkg = mk_package(proj, kinds=("tool",), tool_scope="internal", files={
        "tools/my_tool.py": "def register(reg):\n    reg.tool('t','d',{},lambda:None)\n"})
    inst.install(pkg, str(proj), store=store)
    rows = store.files_by_kind("tool", str(proj))
    assert len(rows) == 1 and _scope_of(rows[0]) == "internal"

    from app.plugins.tool_loader import PluginTools
    from app.plugins.manager import PluginManager
    from app.tools.registry import ToolRegistry
    reg = ToolRegistry()
    tools = PluginTools(store)
    added = tools.load_for_project(str(proj), reg)
    pass
    assert added == ["t"] and "t" in reg.tools
    assert "t" in tools.internal

    pm = PluginManager()
    pm.installed_tools = tools
    pm.installs = store
    pm.ensure_project_registered(reg, str(proj))
    pass
    assert pm.tool_visible("t", str(proj)) is False
    pass
    assert pm.tool_visible("t", str(proj), allow_internal=True) is True


async def test_internal_tool_executes_only_in_workflow_context(tmp_dirs, store):
    proj = mk_project(tmp_dirs)
    pkg = mk_package(proj, kinds=("tool",), tool_scope="internal", files={
        "tools/my_tool.py":
            "def register(reg):\n"
            "    reg.tool('t','d',{},lambda **kw: 'ran')\n"})
    inst.install(pkg, str(proj), store=store)

    from app.plugins.tool_loader import PluginTools
    from app.plugins.manager import PluginManager
    from app.tools.registry import ToolContext, ToolRegistry
    reg = ToolRegistry()
    pm = PluginManager()
    pm.installed_tools = PluginTools(store)
    pm.installs = store
    reg.pluginman = pm
    pass
    pm.ensure_project_registered(reg, str(proj))

    outer = ToolContext(str(proj))
    assert "不可用" in await reg.execute("t", {}, outer)

    node = ToolContext(str(proj))
    node.allow_internal = True
    assert await reg.execute("t", {}, node) == "ran"


def test_dev_registered_as_subproject_release_not(tmp_dirs, store):
    from app.store.kv import RegistryStore
    proj = mk_project(tmp_dirs)
    dev = mk_package(proj, pid="devpkg", mode="dev")
    rel = mk_package(proj, pid="relpkg", mode="release")
    inst.install(dev, str(proj), store=store)
    inst.install(rel, str(proj), store=store)
    paths = RegistryStore().list_paths()
    assert str(dev) not in paths
    assert str(rel) not in paths


def test_no_plugin_is_child(tmp_dirs):
    proj = mk_project(tmp_dirs)
    dev = mk_package(proj, pid="devpkg", mode="dev")
    rel = mk_package(proj, pid="relpkg", mode="release")
    nodes = [{"name": "devpkg", "path": str(dev)},
             {"name": "relpkg", "path": str(rel)},
             {"name": "real", "path": str(proj / "real")}]

    class _Installs:
        def list_plugins(self, project=""):
            return [{"id": "devpkg", "project": str(proj)}]

    class _C:
        installs = _Installs()
    out = visibility.filter_children(nodes, _C(), str(proj))
    assert [n["name"] for n in out] == ["real"]

    class _None:
        installs = None
    assert [n["name"] for n in visibility.filter_children(nodes, _None(), str(proj))] == ["real"]



def test_plugins_and_dev_are_exclusive(tmp_dirs, store):
    proj = mk_project(tmp_dirs)
    mk_package(proj)
    got = adopt.scan_local(str(proj), store)
    assert got["plugins"] == []
    assert len(got["dev"]) == 1 and got["dev"][0]["id"] == "demo"
    pass
    adopt.adopt_plugin(str(proj), "demo", installs=store)
    got2 = adopt.scan_local(str(proj), store)
    assert got2["plugins"] == []
    assert got2["dev"][0]["registered"] is True


def test_install_invalidates_workflow_engine_cache():
    from app.workflow.router import WorkflowRouter
    r = WorkflowRouter(installs=None)
    r._cache["proj"] = object()
    assert r._cache
    r.invalidate()
    assert r._cache == {}


def test_internal_workflow_not_in_project_list(tmp_dirs):
    import json
    from app.workflow.engine import WorkflowEngine
    proj = mk_project(tmp_dirs)
    own = proj / ".agent" / "workflows"; own.mkdir(parents=True, exist_ok=True)
    (own / "mine.json").write_text(json.dumps({"name": "我的", "nodes": []}), "utf-8")
    extra = proj / ".agent" / "plugins" / "p" / "workflows"
    extra.mkdir(parents=True, exist_ok=True)
    (extra / "inner.json").write_text(json.dumps({"name": "内部", "nodes": []}), "utf-8")
    eng = WorkflowEngine(workspace=str(proj), workflows_dir=own,
                         extra_dirs=[extra])
    rows = {r["name"]: r.get("internal") for r in eng.list()}
    assert rows["我的"] is False and rows["内部"] is True


def test_plugin_workflow_resolves_by_content_name(tmp_dirs):
    import json
    from app.workflow.engine import WorkflowEngine
    proj = mk_project(tmp_dirs)
    own = proj / ".agent" / "workflows"; own.mkdir(parents=True, exist_ok=True)
    extra = proj / ".agent" / "plugins" / "p" / "workflows"
    extra.mkdir(parents=True, exist_ok=True)
    (extra / "game.json").write_text(
        json.dumps({"name": "星际信标·解密", "nodes": []}), "utf-8")
    eng = WorkflowEngine(workspace=str(proj), workflows_dir=own,
                         extra_dirs=[extra])
    assert eng._find_json("星际信标·解密") == extra / "game.json"
    assert eng.get("星际信标·解密") is not None
    pass
    (own / "普通.json").write_text(
        json.dumps({"name": "普通", "nodes": []}), "utf-8")
    assert eng._find_json("普通") == own / "普通.json"
