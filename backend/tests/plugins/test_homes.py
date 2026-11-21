from __future__ import annotations

import yaml

from app.plugins import config as pc
from app.plugins import homes, install as inst, package as pkgmod
from app.plugins.plugin_sdk import PluginHost
from app.store import project_crypto


def _mk(tmp, *, pid="demo", config=None):
    proj = tmp / "proj"
    (proj / ".agent").mkdir(parents=True, exist_ok=True)
    pkg = proj / ".agent" / "plugins" / pid
    (pkg / "workflows").mkdir(parents=True, exist_ok=True)
    data = {"id": pid, "name": pid, "version": "1",
            "kinds": ["workflow"], "mode": "release"}
    if config is not None:
        data["config"] = config
    (pkg / "plugin.yaml").write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), "utf-8")
    (pkg / "workflows" / "a.json").write_text("{}", "utf-8")
    return proj, pkg


SPECS = {"api_base": {"label": "地址", "type": "string"},
         "token": {"label": "令牌", "type": "secret"}}


def test_config_lives_in_plugin_dir_with_project_key(tmp_dirs):
    proj, pkg = _mk(tmp_dirs, config=SPECS)
    store = inst.InstallStore(tmp_dirs / "agent.db")
    inst.install(pkg, str(proj), store=store)
    view = pkgmod.load_package(pkg)
    pc.save("demo", str(proj), view.config,
            {"api_base": "http://x", "token": "sk-real"})

    cfg_file = pkg / "config.json"
    assert cfg_file.is_file()
    raw = cfg_file.read_text("utf-8")
    assert "sk-real" not in raw
    assert project_crypto.PREFIX in raw
    assert pc.load("demo", str(proj), view.config)["token"] == "sk-real"


def test_data_lives_in_plugin_dir(tmp_dirs):
    proj, pkg = _mk(tmp_dirs)
    store = inst.InstallStore(tmp_dirs / "agent.db")
    inst.install(pkg, str(proj), store=store)
    h = PluginHost.for_plugin("demo", str(proj))
    h.data.set("progress", 7)
    assert (pkg / "data.json").is_file()
    assert PluginHost.for_plugin("demo", str(proj)).data.get("progress") == 7


def test_kb_lives_in_plugin_dir(tmp_dirs):
    proj, pkg = _mk(tmp_dirs)
    store = inst.InstallStore(tmp_dirs / "agent.db")
    inst.install(pkg, str(proj), store=store)
    h = PluginHost.for_plugin("demo", str(proj))
    h.kb.add("faq", [{"key": "1", "title": "标题", "body": "正文内容"}])
    assert (pkg / "store.db").is_file()


def test_no_central_plugin_data_dir_created(tmp_dirs):
    proj, pkg = _mk(tmp_dirs)
    store = inst.InstallStore(tmp_dirs / "agent.db")
    inst.install(pkg, str(proj), store=store)
    PluginHost.for_plugin("demo", str(proj)).data.set("k", 1)
    assert not (proj / ".agent" / "plugin_data").exists()


def test_project_workflow_kv_goes_to_project_kv(tmp_dirs):
    proj = tmp_dirs / "proj"
    (proj / ".agent").mkdir(parents=True, exist_ok=True)
    h = PluginHost.for_cwd(str(proj))
    h.data.set("x", 1)
    assert (proj / ".agent" / "kv.json").is_file()


def test_home_of_returns_none_for_unregistered(tmp_dirs):
    assert homes.home_of("ghost", str(tmp_dirs / "proj")) is None


def test_home_of_returns_none_for_standalone_unit(tmp_dirs):
    assert homes.home_of("tool:fs_read", "") is None
