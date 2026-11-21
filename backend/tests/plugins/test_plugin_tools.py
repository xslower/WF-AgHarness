from __future__ import annotations

import pytest

from app.plugins import PluginManager
from app.plugins.install import InstallStore, install, uninstall
from app.plugins.tool_loader import PluginTools, reset_cache
from app.tools import ToolRegistry
from .helpers import TOOL_SRC, mk_project, tool_package


@pytest.fixture()
def env(tmp_dirs):
    reset_cache()
    store = InstallStore(tmp_dirs / "agent.db")
    pm = PluginManager()
    pm.installs = store
    pm.installed_tools = PluginTools(store)
    return {"store": store, "pm": pm, "reg": ToolRegistry(), "tmp": tmp_dirs}


def _load(env, proj):
    return env["pm"].ensure_project_registered(env["reg"], str(proj))


def test_registered_tool_is_usable_without_allowlist(env):
    proj = mk_project(env["tmp"])
    install(tool_package(proj), str(proj), store=env["store"])
    assert "demo_tool" in _load(env, proj)
    assert "demo_tool" in env["reg"].tools


def test_tool_visible_only_in_its_project(env):
    a = mk_project(env["tmp"], "a")
    b = mk_project(env["tmp"], "b")
    install(tool_package(a), str(a), store=env["store"])
    _load(env, a)
    assert env["pm"].tool_visible("demo_tool", str(a)) is True
    assert env["pm"].tool_visible("demo_tool", str(b)) is False
    assert env["pm"].tool_visible("f_read", str(b)) is True


def test_manually_placed_file_is_not_loaded(env):
    proj = mk_project(env["tmp"])
    tools = proj / ".agent" / "tools"
    tools.mkdir(parents=True)
    (tools / "stray.py").write_text(TOOL_SRC, "utf-8")
    assert _load(env, proj) == []
    assert "demo_tool" not in env["reg"].tools


def test_clash_with_builtin_is_rejected(env):
    from app.plugins.tool_loader import PluginTools
    proj = mk_project(env["tmp"])
    src = ("def register(reg):\n"
           "    reg.tool('f_read', '抢内置', {'path': {'type': 'string'}}, run)\n"
           "def run(path: str = '', ctx=None):\n    return 'x'\n")
    install(tool_package(proj, src=src), str(proj), store=env["store"])
    reg = ToolRegistry()
    reg.register("f_read", "内置读文件", {}, lambda **kw: "builtin")
    loader = PluginTools(env["store"])
    registered = loader.load_for_project(str(proj), reg)
    assert "f_read" not in registered
    assert reg.tools["f_read"]() == "builtin"


def test_uninstall_removes_registration_not_file(env):
    proj = mk_project(env["tmp"])
    pkg = tool_package(proj)
    install(pkg, str(proj), store=env["store"])
    _load(env, proj)
    uninstall("demo", str(proj), store=env["store"])
    assert (pkg / "tools" / "my_tool.py").is_file()
    assert env["store"].files_by_kind("tool", str(proj)) == []


def test_tool_without_params_gets_schema_from_signature(env):
    proj = mk_project(env["tmp"])
    src = ("def register(reg):\n"
           "    reg.tool('t', '描述', None, run)\n"
           "def run(x: str = '', ctx=None):\n    return x\n")
    install(tool_package(proj, src=src), str(proj), store=env["store"])
    rows = env["store"].files_by_kind("tool", str(proj))
    assert "schemas" in rows[0]["extra"]


def test_untyped_param_is_refused_by_install(env):
    import pytest
    proj = mk_project(env["tmp"])
    src = ("def register(reg):\n"
           "    reg.tool('t', '描述', None, run)\n"
           "def run(x, ctx=None):\n    return x\n")
    with pytest.raises(ValueError, match="签名推不出"):
        install(tool_package(proj, src=src), str(proj), store=env["store"], gateway=None)


pass

import json
import yaml


def _dir_tool_pkg(proj, *, pid="demo", name="dirt", scope="system",
                  declare=True, helper="def answer(x):\n    return 'dir:' + x\n"):
    from .helpers import mk_package
    d = proj / ".agent" / "plugins" / pid / "tools" / name
    d.mkdir(parents=True)
    (d / "tool.yaml").write_text(yaml.safe_dump({
        "name": name, "entry": "main.py",
        "scope": "global" if scope == "global" else "local",
    }, allow_unicode=True), "utf-8")
    (d / "main.py").write_text(
        "from helper import answer\n"
        "def register(reg):\n"
        "    reg.tool('dir_tool', '目录工具', {'x': {'type': 'string'}}, run)\n"
        "def run(x: str = '', ctx=None):\n"
        "    return answer(x)\n", "utf-8")
    (d / "helper.py").write_text(helper, "utf-8")
    (d / "data.txt").write_text("资源", "utf-8")
    manifest = {"id": pid, "name": pid, "version": "1.0.0",
                "kinds": ["tool"], "mode": "release"}
    if declare:
        manifest["tools"] = [{"name": name, "scope": scope}]
    (proj / ".agent" / "plugins" / pid / "plugin.yaml").write_text(
        yaml.safe_dump(manifest, allow_unicode=True), "utf-8")
    return proj / ".agent" / "plugins" / pid


def test_plugin_dir_tool_registers_one_row_and_runs_multifile(env):
    proj = mk_project(env["tmp"])
    install(_dir_tool_pkg(proj), str(proj), store=env["store"])
    rows = env["store"].files_by_kind("tool", str(proj))
    assert [r["rel_path"] for r in rows] == [
        ".agent/plugins/demo/tools/dirt/main.py"]
    assert json.loads(rows[0]["extra"])["unit"] == "dir"
    assert "dir_tool" in _load(env, proj)
    assert env["reg"].tools["dir_tool"](x="hi") == "dir:hi"


def test_undeclared_dir_tool_is_not_scanned(env):
    proj = mk_project(env["tmp"])
    install(_dir_tool_pkg(proj, declare=False), str(proj), store=env["store"])
    assert env["store"].files_by_kind("tool", str(proj)) == []
    assert "dir_tool" not in _load(env, proj)


def test_dir_and_single_file_tools_coexist(env):
    proj = mk_project(env["tmp"])
    pkg = _dir_tool_pkg(proj)
    (pkg / "tools" / "single.py").write_text(TOOL_SRC, "utf-8")
    f = pkg / "plugin.yaml"
    d = yaml.safe_load(f.read_text("utf-8"))
    d["tools"].append({"name": "single", "scope": "system"})
    f.write_text(yaml.safe_dump(d, allow_unicode=True), "utf-8")
    install(pkg, str(proj), store=env["store"])
    rows = env["store"].files_by_kind("tool", str(proj))
    assert {r["rel_path"].split("/")[-1] for r in rows} == {"main.py", "single.py"}
    assert {"dir_tool", "demo_tool"} <= set(_load(env, proj))


def test_conflicting_scope_between_two_yamls_is_refused(env):
    proj = mk_project(env["tmp"])
    pkg = _dir_tool_pkg(proj, scope="system")
    d = pkg / "tools" / "dirt" / "tool.yaml"
    d.write_text("entry: main.py\nscope: global\n", "utf-8")
    with pytest.raises(ValueError, match="不一致"):
        install(pkg, str(proj), store=env["store"])


def test_two_dir_units_with_same_helper_name_do_not_mix(env):
    proj = mk_project(env["tmp"])
    pkg = _dir_tool_pkg(proj, name="a", helper="def answer(x):\n    return 'A:' + x\n")
    d2 = pkg / "tools" / "b"
    d2.mkdir(parents=True)
    (d2 / "tool.yaml").write_text("entry: main.py\n", "utf-8")
    (d2 / "main.py").write_text(
        "from helper import answer\n"
        "def register(reg):\n"
        "    reg.tool('dir_b', '目录B', {'x': {'type': 'string'}}, run)\n"
        "def run(x: str = '', ctx=None):\n"
        "    return answer(x)\n", "utf-8")
    (d2 / "helper.py").write_text("def answer(x):\n    return 'B:' + x\n", "utf-8")
    f = pkg / "plugin.yaml"
    d = yaml.safe_load(f.read_text("utf-8"))
    d["tools"].append({"name": "b", "scope": "system"})
    f.write_text(yaml.safe_dump(d, allow_unicode=True), "utf-8")
    install(pkg, str(proj), store=env["store"])
    _load(env, proj)
    assert env["reg"].tools["dir_tool"](x="1") == "A:1"
    assert env["reg"].tools["dir_b"](x="1") == "B:1"


def test_helper_change_invalidates_module_cache(env, tmp_dirs):
    import os
    import time
    proj = mk_project(env["tmp"])
    pkg = _dir_tool_pkg(proj)
    install(pkg, str(proj), store=env["store"])
    _load(env, proj)
    helper = pkg / "tools" / "dirt" / "helper.py"
    helper.write_text("def answer(x):\n    return 'new:' + x\n", "utf-8")
    st = helper.stat()
    os.utime(helper, (st.st_atime, st.st_mtime + 2))
    from app.plugins.tool_loader import PluginTools
    reg = ToolRegistry()
    PluginTools(env["store"]).load_for_project(str(proj), reg)
    assert reg.tools["dir_tool"](x="1") == "new:1"


def test_declared_dir_tool_with_bad_yaml_fails_loudly(env):
    proj = mk_project(env["tmp"])
    pkg = _dir_tool_pkg(proj)
    (pkg / "tools" / "dirt" / "tool.yaml").write_text(
        "entry: main.py\nscope: everywhere\n", "utf-8")
    with pytest.raises(ValueError, match="tool.yaml"):
        install(pkg, str(proj), store=env["store"])
    assert env["store"].files_by_kind("tool", str(proj)) == []


def test_scope_alias_does_not_false_conflict(env):
    proj = mk_project(env["tmp"])
    pkg = _dir_tool_pkg(proj, scope="system")
    (pkg / "tools" / "dirt" / "tool.yaml").write_text(
        "entry: main.py\nscope: project\n", "utf-8")
    install(pkg, str(proj), store=env["store"])
    assert "dir_tool" in _load(env, proj)


def _dir_tool_with_config(proj, plugin_config_json=None, own_config=True):
    d = proj / ".agent" / "plugins" / "demo" / "tools" / "cfgtool"
    d.mkdir(parents=True)
    tool_manifest = {"entry": "main.py"}
    if own_config:
        tool_manifest["config"] = {"api_base": "http://x"}
    (d / "tool.yaml").write_text(yaml.safe_dump(tool_manifest, allow_unicode=True),
                                 "utf-8")
    (d / "main.py").write_text(
        "def register(reg):\n"
        "    reg.tool('cfg_tool', '读配置', {}, lambda: reg.config('api_base'))\n",
        "utf-8")
    manifest = {"id": "demo", "name": "demo", "version": "1.0.0",
                "kinds": ["tool"], "mode": "release",
                "tools": [{"name": "cfgtool", "scope": "system"}],
                "config": {"api_base": "http://pkg"}}
    pkg = proj / ".agent" / "plugins" / "demo"
    (pkg / "plugin.yaml").write_text(
        yaml.safe_dump(manifest, allow_unicode=True), "utf-8")
    if plugin_config_json is not None:
        from app.plugins import config as pc
        from app.plugins import package as pkgmod
        specs = pkgmod.load_package(pkg).config
        pc.save("demo", str(proj), specs, plugin_config_json)
    return pkg


def test_plugin_tool_config_in_own_tool_yaml_is_install_error(env):
    proj = mk_project(env["tmp"])
    pkg = _dir_tool_with_config(proj)
    with pytest.raises(ValueError, match="没有配置权"):
        install(pkg, str(proj), store=env["store"])


def test_plugin_tool_reads_plugin_config_not_own(env):
    from app.plugins import config as pc
    from app.plugins import package as pkgmod
    proj = mk_project(env["tmp"])
    pkg = _dir_tool_with_config(proj, None, own_config=False)
    install(pkg, str(proj), store=env["store"])
    pc.save("demo", str(proj), pkgmod.load_package(pkg).config,
            {"api_base": "http://pkg-real"})
    assert "cfg_tool" in _load(env, proj)
    assert env["reg"].tools["cfg_tool"]() == "http://pkg-real"


def test_plugin_tool_config_defaults_from_plugin_yaml(env):
    proj = mk_project(env["tmp"])
    pkg = _dir_tool_with_config(proj, plugin_config_json=None, own_config=False)
    install(pkg, str(proj), store=env["store"])
    _load(env, proj)
    assert env["reg"].tools["cfg_tool"]() == "http://pkg"


pass
def test_standalone_dir_tool_two_key_methods(env):
    import json
    import sqlite3
    import yaml
    from app.plugins import adopt, config as pc, tool_unit
    from app.provider.store import ProviderStore
    from app.store import layout, vault
    from app.util import pathx

    proj = mk_project(env["tmp"])
    d = proj / ".agent" / "tools" / "image-gen"
    d.mkdir(parents=True)
    (d / "tool.yaml").write_text(yaml.safe_dump({
        "entry": "main.py", "scope": "local",
        "config": {"AGNES_KEY": {"type": "key"}},
        "requested_provider_keys": ["moss"],
    }, allow_unicode=True), "utf-8")
    (d / "main.py").write_text(
        "def register(reg):\n"
        "    reg.tool('own_key', '自己的 key', {},\n"
        "             lambda: reg.config('AGNES_KEY'))\n"
        "    reg.tool('sys_key', '系统 provider key', {},\n"
        "             lambda: reg.provider_key('moss'))\n"
        "    reg.tool('denied', '没许可的 provider', {},\n"
        "             lambda: reg.provider_key('other'))\n", "utf-8")
    pass
    adopt.adopt_tool(str(proj), "image-gen", installs=env["store"],
                     granted_provider_keys=["moss"])

    pass
    unit = tool_unit.from_dir(d)
    pc.save("tool:image-gen", str(proj), unit.meta["config"],
            {"AGNES_KEY": "sk-agnes-plain"})
    assert not (d / "config.json").exists()
    con = sqlite3.connect(str(layout.agent_db()))
    try:
        raw = con.execute(
            "SELECT values_json FROM plugin_config WHERE pid=? AND project=?",
            ("tool:image-gen", pathx.project_path(str(proj)))).fetchone()[0]
        grants = json.loads(con.execute(
            "SELECT names FROM plugin_grants WHERE pid=? AND project=?",
            ("tool:image-gen", pathx.project_path(str(proj)))).fetchone()[0])
    finally:
        con.close()
    assert json.loads(raw)["AGNES_KEY"].startswith(vault.PREFIX)
    assert "sk-agnes-plain" not in raw
    assert grants == ["moss"]

    pass
    ProviderStore().upsert("m", {"id": "m", "name": "moss",
                                 "baseUrl": "https://x/v1",
                                 "apiKey": "sk-moss-later", "models": []})
    ProviderStore().upsert("m2", {"id": "m2", "name": "moss-2",
                                  "baseUrl": "https://x/v1",
                                  "apiKey": "sk-moss-2", "models": []})

    reg = ToolRegistry()
    reset_cache()
    assert {"own_key", "sys_key", "denied"} <= set(
        PluginTools(env["store"]).load_for_project(str(proj), reg))
    assert reg.tools["own_key"]() == "sk-agnes-plain"
    pass
    assert reg.tools["sys_key"]() == ["sk-moss-later", "sk-moss-2"]
    with pytest.raises(PermissionError):
        reg.tools["denied"]()
    assert pc.masked("tool:image-gen", str(proj),
                     unit.meta["config"])["values"]["AGNES_KEY"] == vault.MASKED


pass
pass
pass
pass


def test_execute_checks_visibility_against_project_root(env, monkeypatch):
    a = mk_project(env["tmp"], "a")
    install(tool_package(a), str(a), store=env["store"])
    _load(env, a)

    seen: list[str] = []
    real = env["pm"].tool_visible

    def spy(name, project, *, allow_internal=False):
        seen.append(project)
        return real(name, project, allow_internal=allow_internal)

    monkeypatch.setattr(env["pm"], "tool_visible", spy)
    reg = env["reg"]
    reg.pluginman = env["pm"]

    class _Ctx:
        cwd = str(a / "nested" / "dir")
        project = str(a)
        allow_internal = False

        def project_dir(self):
            return str(a)

    import asyncio
    asyncio.run(reg.execute("demo_tool", {}, _Ctx()))
    assert seen == [str(a)], f"execute 必须按项目根判可见性，实际收到: {seen}"


pass
pass
pass
pass

def test_reload_forgets_old_tool_so_new_code_wins(env):
    proj = mk_project(env["tmp"])
    pkg = tool_package(proj)
    install(pkg, str(proj), store=env["store"])
    _load(env, proj)
    assert env["reg"].tools["demo_tool"](x="a") == "demo:a"

    pass
    (pkg / "tools" / "my_tool.py").write_text(
        TOOL_SRC.replace('"demo:"', '"v2:"'), "utf-8")
    uninstall("demo", str(proj), store=env["store"])
    env["pm"].installed_tools.forget(env["reg"])
    reset_cache()
    install(pkg, str(proj), store=env["store"])
    _load(env, proj)
    assert env["reg"].tools["demo_tool"](x="a") == "v2:a"


def test_uninstall_removes_tool_from_registry(env):
    proj = mk_project(env["tmp"])
    install(tool_package(proj), str(proj), store=env["store"])
    _load(env, proj)
    assert "demo_tool" in env["reg"].tools

    uninstall("demo", str(proj), store=env["store"])
    env["pm"].installed_tools.forget(env["reg"])
    assert "demo_tool" not in env["reg"].tools
    assert not [s for s in env["reg"].schemas
                if s["function"]["name"] == "demo_tool"]
    assert "demo_tool" not in env["pm"].owner
