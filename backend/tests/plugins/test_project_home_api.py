from __future__ import annotations

import json

import pytest

from app.plugins.install import install
from .helpers import mk_package, mk_project, tool_package


@pytest.fixture()
def client(container):
    from fastapi.testclient import TestClient
    import app.main as main_mod
    from app.api.deps import set_container

    set_container(main_mod.app, container)
    return TestClient(main_mod.app)


def _overview(client, proj):
    r = client.get("/api/projects/overview", params={"path": str(proj)})
    assert r.status_code == 200
    return r.json()


def test_overview_returns_all_sections(client, tmp_dirs):
    proj = mk_project(tmp_dirs)
    d = _overview(client, proj)
    for key in ("children", "sessions", "workflows", "plugins", "tools",
                "skills", "ui"):
        assert key in d
    assert "pending" not in d, "扫描结果是 discover 的唯一真源，overview 不该再带一份"
    assert d["is_top"] is True and d["parent"] is None


def test_overview_lists_registered_plugins(client, tmp_dirs, container):
    proj = mk_project(tmp_dirs)
    install(mk_package(proj), str(proj), store=container.installs)
    d = _overview(client, proj)
    assert [p["id"] for p in d["plugins"]] == ["demo"]


def test_plugin_mode_reads_live_yaml_not_stale_manifest(client, tmp_dirs, container):
    import yaml
    proj = mk_project(tmp_dirs)
    pkg = mk_package(proj, mode="release")
    install(pkg, str(proj), store=container.installs)
    assert _overview(client, proj)["plugins"][0]["mode"] == "release"
    f = pkg / "plugin.yaml"
    d = yaml.safe_load(f.read_text("utf-8"))
    d["mode"] = "dev"
    f.write_text(yaml.safe_dump(d, allow_unicode=True), "utf-8")
    assert _overview(client, proj)["plugins"][0]["mode"] == "dev"


def test_overview_does_not_scan_automatically(client, tmp_dirs, monkeypatch):
    proj = mk_project(tmp_dirs)
    calls = []
    import app.plugins.adopt as adopt
    orig = adopt.scan_local
    def spy(project, installs):
        calls.append(project)
        return orig(project, installs)
    monkeypatch.setattr(adopt, "scan_local", spy)

    d = _overview(client, proj)
    assert "pending" not in d
    assert calls == [], "overview 偷偷调了 scan_local"

    pass
    r = client.get("/api/plugins/discover", params={"project": str(proj)})
    assert r.status_code == 200 and calls == [str(proj)]


def test_ui_prefs_get_put_and_hide(client, tmp_dirs, container):
    proj = mk_project(tmp_dirs)
    install(mk_package(proj, mode="dev"), str(proj), store=container.installs)
    kid = mk_project(proj, "kid")
    pass
    from app.store.kv import RegistryStore
    RegistryStore().add(str(kid), str(proj))
    child = mk_project(proj, "kid")
    before = [x["name"] for x in _overview(client, proj)["children"]]
    assert "demo" not in before, "插件包不许当子项目"
    assert "kid" in before
    r = client.put("/api/projects/ui-prefs", params={"path": str(proj)},
                   json={"hiddenPluginProjects": True, "hiddenWorkflows": True})
    assert r.status_code == 200 and r.json()["ui"]["hiddenPluginProjects"] is True
    after = _overview(client, proj)
    assert after["workflows"] == []
    assert after["ui"]["hiddenWorkflows"] is True
    assert "kid" in [x["name"] for x in after["children"]], "普通子项目不受影响"


def test_dev_mode_package_is_visible_with_errors(client, tmp_dirs):
    proj = mk_project(tmp_dirs)
    tool_package(proj, src="x = 1\n")
    pass
    assert "pending" not in _overview(client, proj)
    pass
    r = client.get("/api/plugins/discover", params={"project": str(proj)})
    assert r.status_code == 200
    dev = r.json()["dev"]
    assert dev and dev[0]["registered"] is False
    assert any("register" in e for e in dev[0]["errors"])


def test_project_subproject_shows_its_workflows(client, tmp_dirs, container):
    proj = mk_project(tmp_dirs)
    pkg = mk_package(proj, kinds=("workflow",), files={
        "workflows/daily.json": json.dumps({"name": "daily", "nodes": []})})
    install(pkg, str(proj), store=container.installs)
    child = _overview(client, pkg)
    assert [w["name"] for w in child["workflows"]] == ["daily"]


def test_wf_list_hides_internal_plugin_workflows(client, tmp_dirs, container):
    proj = mk_project(tmp_dirs)
    pkg = mk_package(proj, kinds=("workflow",), files={
        "workflows/game.json": json.dumps({"name": "星际信标·解密", "nodes": []})})
    install(pkg, str(proj), store=container.installs)
    parent = client.get("/api/workflows", params={"project": str(proj)}).json()
    assert "星际信标·解密" not in [w["name"] for w in parent]
    child = client.get("/api/workflows", params={"project": str(pkg)}).json()
    assert [w["name"] for w in child] == ["星际信标·解密"]


def test_overview_plugin_detail_has_no_disk_path(client, tmp_dirs, container):
    proj = mk_project(tmp_dirs)
    pkg = mk_package(proj, mode="dev")
    install(pkg, str(proj), store=container.installs)
    d = _overview(client, proj)
    assert "path" not in d["plugins"][0]
    assert d["plugins"][0]["project"] == proj.name
    assert d["children"] == []


def test_config_reads_live_yaml_not_stale_manifest(client, tmp_dirs, container):
    import yaml
    proj = mk_project(tmp_dirs)
    pkg = mk_package(proj, mode="dev")
    install(pkg, str(proj), store=container.installs)
    f = pkg / "plugin.yaml"
    d = yaml.safe_load(f.read_text("utf-8"))
    d["config"] = {"player": {"label": "玩家", "type": "string",
                          "default": "领航员"}}
    f.write_text(yaml.safe_dump(d, allow_unicode=True), "utf-8")
    r = client.get("/api/plugins/config/demo", params={"project": str(proj)})
    assert r.status_code == 200, r.text
    assert [x["key"] for x in r.json()["fields"]] == ["player"]
    pass
    r2 = client.put("/api/plugins/config/demo", params={"project": str(proj)},
                    json={"values": {"player": "测试员"}})
    assert r2.status_code == 200 and r2.json()["values"]["player"] == "测试员"

    pass
    pass
    import json
    conn = container.installs._db
    conn.execute(
        "UPDATE installed_plugins SET manifest=? WHERE id=? AND project=?",
        (json.dumps({"id": "demo", "name": "demo", "version": "1.0.0",
                     "kinds": ["workflow"], "config": {}},
                    ensure_ascii=False), "demo", str(proj)))
    conn.commit()
    r3 = client.get("/api/plugins/config/demo", params={"project": str(proj)})
    assert r3.status_code == 200, r3.text
    assert [x["key"] for x in r3.json()["fields"]] == ["player"]


pass


def test_overview_tools_lists_standalone_dir_tool(client, tmp_dirs, container):
    import yaml
    from app.plugins import adopt
    proj = mk_project(tmp_dirs)
    d = proj / ".agent" / "tools" / "dirtool"
    d.mkdir(parents=True)
    (d / "tool.yaml").write_text(yaml.safe_dump({
        "entry": "main.py", "scope": "local", "name": "目录工具",
        "desc": "说明",
        "config": {"k": "v"},
    }, allow_unicode=True), "utf-8")
    (d / "main.py").write_text(
        "def register(reg):\n    reg.tool('t', 'd', {}, lambda: None)\n", "utf-8")
    adopt.adopt_tool(str(proj), "dirtool", installs=container.installs)

    o = _overview(client, proj)
    assert [t["id"] for t in o["tools"]] == ["tool:dirtool"]
    t = o["tools"][0]
    assert t["name"] == "目录工具" and t["desc"] == "说明"
    assert t["has_config"] is True
    assert o["plugins"] == []


def test_overview_plugin_tool_not_in_tools(client, tmp_dirs, container):
    import yaml
    proj = mk_project(tmp_dirs)
    pkg = mk_package(proj, kinds=("tool",))
    (pkg / "tools").mkdir()
    (pkg / "tools" / "x.py").write_text(
        "def register(reg):\n    reg.tool('x', 'd', {}, lambda: None)\n", "utf-8")
    d = yaml.safe_load((pkg / "plugin.yaml").read_text("utf-8"))
    d["tools"] = [{"name": "x", "scope": "system"}]
    (pkg / "plugin.yaml").write_text(yaml.safe_dump(d, allow_unicode=True), "utf-8")
    install(pkg, str(proj), store=container.installs)

    o = _overview(client, proj)
    assert [p["id"] for p in o["plugins"]] == ["demo"]
    assert o["tools"] == []


def test_overview_tools_mapping_config_gives_config_button(client, tmp_dirs, container):
    import yaml
    from app.plugins import adopt
    proj = mk_project(tmp_dirs)
    d = proj / ".agent" / "tools" / "maptool"
    d.mkdir(parents=True)
    (d / "tool.yaml").write_text(yaml.safe_dump({
        "entry": "main.py", "scope": "local", "name": "映射配置工具",
        "config": {"out_dir": "runs", "retries": 2, "enabled": True},
    }, allow_unicode=True), "utf-8")
    (d / "main.py").write_text(
        "def register(reg):\n    reg.tool('t', 'd', {}, lambda: None)\n", "utf-8")
    adopt.adopt_tool(str(proj), "maptool", installs=container.installs)

    t = _overview(client, proj)["tools"][0]
    assert t["has_config"] is True
    assert "error" not in t

def test_adopt_tool_with_nested_config_flattens_keys(client, tmp_dirs, container):
    import yaml
    from app.plugins import adopt
    proj = mk_project(tmp_dirs)
    d = proj / ".agent" / "tools" / "dirtool"
    d.mkdir(parents=True)
    (d / "tool.yaml").write_text(yaml.safe_dump({
        "entry": "main.py", "scope": "local", "name": "嵌套配置工具",
        "config": {"slots": {"agnes": "CHANGE_ME", "ms": "CHANGE_ME"}},
    }, allow_unicode=True), "utf-8")
    (d / "main.py").write_text(
        "def register(reg):\n    reg.tool('t', 'd', {}, lambda: None)\n", "utf-8")
    adopt.adopt_tool(str(proj), "dirtool", installs=container.installs)

    t = _overview(client, proj)["tools"][0]
    assert t["name"] == "嵌套配置工具"
    assert t["has_config"] is True
    assert "config_error" not in t

    pass
    r = client.get("/api/plugins/config/tool:dirtool",
                   params={"project": str(proj)})
    assert r.status_code == 200, r.text
    assert [f["key"] for f in r.json()["fields"]] == ["slots.agnes", "slots.ms"]
