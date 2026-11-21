from __future__ import annotations

import json

import pytest
import yaml

from app.plugins import config as cfg
from app.plugins import install as inst
from app.plugins import package as pkgmod


def _mk_project(root):
    p = root / "proj"
    (p / ".agent").mkdir(parents=True, exist_ok=True)
    return p


@pytest.fixture()
def store(tmp_dirs):
    return inst.InstallStore(tmp_dirs / "agent.db")


def _mk_pkg(root, *, pid="demo", kinds=("workflow",), config=None, files=None):
    proj = root / "proj"
    (proj / ".agent").mkdir(parents=True, exist_ok=True)
    pkg = proj / ".agent" / "plugins" / pid
    pkg.mkdir(parents=True, exist_ok=True)
    data = {"id": pid, "name": pid, "version": "1",
            "kinds": list(kinds), "mode": "release"}
    if config is not None:
        data["config"] = config
    (pkg / "plugin.yaml").write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), "utf-8")
    for rel, content in (files or {"workflows/a.json": "{}"}).items():
        f = pkg / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content, "utf-8")
    return pkg

def _parts(host):
    if hasattr(host, "id"):
        return host.id, host.config
    return f"tool:{host.name}", (host.meta or {}).get("config") or ()


def _save(host, values, project=""):
    pid, specs = _parts(host)
    return cfg.save(pid, project, specs, values)


def _load(host, project=""):
    pid, specs = _parts(host)
    return cfg.load(pid, project, specs)


def _masked(host, project=""):
    pid, specs = _parts(host)
    return cfg.masked(pid, project, specs)


def _db_row(pid, project=""):
    import sqlite3
    from app.store import layout
    from app.util import pathx
    con = sqlite3.connect(str(layout.agent_db()))
    try:
        row = con.execute(
            "SELECT values_json FROM plugin_config WHERE pid=? AND project=?",
            (pid, pathx.project_path(project))).fetchone()
    finally:
        con.close()
    assert row, f"plugin_config 里没有 {pid} @ {project}"
    return json.loads(row[0])


pass
SPECS_MAP = {
    "api_base": {"label": "地址", "type": "string", "required": True},
    "mode": {"label": "模式", "type": "select", "options": ["fast", "precise"],
             "default": "fast"},
    "token": {"label": "令牌", "type": "secret"},
    "max_items": {"label": "上限", "type": "number", "default": 20,
                  "min": 1, "max": 200},
    "verbose": {"label": "详细", "type": "boolean", "default": False},
}
SPECS = cfg.normalize_config(SPECS_MAP)


pass


def test_required_field_is_named():
    with pytest.raises(cfg.ConfigError, match="api_base"):
        cfg.validate(SPECS, {})


def test_defaults_filled():
    got = cfg.validate(SPECS, {"api_base": "http://x"})
    assert got == {"api_base": "http://x", "mode": "fast", "token": None,
                   "max_items": 20, "verbose": False}


def test_number_coercion_and_range():
    got = cfg.validate(SPECS, {"api_base": "u", "max_items": "50"})
    assert got["max_items"] == 50
    with pytest.raises(cfg.ConfigError, match="max_items"):
        cfg.validate(SPECS, {"api_base": "u", "max_items": 500})
    with pytest.raises(cfg.ConfigError, match="max_items"):
        cfg.validate(SPECS, {"api_base": "u", "max_items": "abc"})


def test_select_rejects_unknown_option():
    with pytest.raises(cfg.ConfigError, match="mode"):
        cfg.validate(SPECS, {"api_base": "u", "mode": "turbo"})


def test_boolean_accepts_strings():
    assert cfg.validate(SPECS, {"api_base": "u", "verbose": "true"})["verbose"] is True
    assert cfg.validate(SPECS, {"api_base": "u", "verbose": "0"})["verbose"] is False


def test_undeclared_keys_dropped():
    got = cfg.validate(SPECS, {"api_base": "u", "evil": "x"})
    assert "evil" not in got


def test_secret_is_masked_outward():
    specs = [{"key": "token", "type": "secret"}]
    assert cfg.mask(specs, {"token": "abc"}) == {"token": cfg.MASKED}
    pass
    assert cfg.mask(specs, {"token": ""}) == {"token": ""}
pass

def test_save_and_load_writes_agent_db(tmp_dirs, store):
    proj = _mk_project(tmp_dirs)
    pkg = _mk_pkg(tmp_dirs, config=SPECS_MAP, kinds=("workflow",))
    inst.install(pkg, str(proj), store=store)

    view = pkgmod.load_package(pkg)
    _save(view, {"api_base": "http://real", "token": "t0k"})

    pass
    saved = _db_row(view.id)
    assert saved["api_base"] == "http://real"
    assert saved["token"].startswith("enc:v1:")
    assert not (pkg / "config.json").exists()
    assert not (proj / ".agent" / "config.json").exists()

    loaded = _load(view)
    assert loaded["api_base"] == "http://real"
    assert loaded["token"] == "t0k"
    assert _masked(view)["values"]["token"] == cfg.MASKED


def test_load_bad_config_raises_named_error(tmp_dirs):
    from app.store.plugin_config import PluginConfigStore
    pkg = _mk_pkg(tmp_dirs, config=SPECS_MAP, kinds=("workflow",))
    PluginConfigStore().put("demo", "", {"api_base": "u", "mode": "turbo"})
    view = pkgmod.load_package(pkg)
    with pytest.raises(cfg.ConfigError, match="mode"):
        _load(view)


def test_load_missing_config_uses_defaults(tmp_dirs):
    pass
    specs = {k: v for k, v in SPECS_MAP.items() if not v.get("required")}
    pkg = _mk_pkg(tmp_dirs, config=specs, kinds=("workflow",))
    got = _load(pkgmod.load_package(pkg))
    assert got["mode"] == "fast" and got["max_items"] == 20


def test_save_masked_secret_keeps_original(tmp_dirs):
    pkg = _mk_pkg(tmp_dirs, config=SPECS_MAP, kinds=("workflow",))
    view = pkgmod.load_package(pkg)
    _save(view, {"api_base": "u", "token": "sk-real"})

    view2 = _masked(view)
    assert view2["values"]["token"] == cfg.MASKED

    _save(view, dict(view2["values"]))
    assert _load(view)["token"] == "sk-real"


def test_save_empty_secret_keeps_original(tmp_dirs):
    pkg = _mk_pkg(tmp_dirs, config=SPECS_MAP, kinds=("workflow",))
    view = pkgmod.load_package(pkg)
    _save(view, {"api_base": "u", "token": "sk-real"})
    _save(view, {"api_base": "u", "token": ""})
    assert _load(view)["token"] == "sk-real"


def test_save_new_secret_overwrites(tmp_dirs):
    pkg = _mk_pkg(tmp_dirs, config=SPECS_MAP, kinds=("workflow",))
    view = pkgmod.load_package(pkg)
    _save(view, {"api_base": "u", "token": "old"})
    _save(view, {"api_base": "u", "token": "new"})
    assert _load(view)["token"] == "new"


def test_view_without_dir_can_save(tmp_dirs):
    view = pkgmod.load_package_from_text(
        yaml.safe_dump({"id": "demo", "kinds": ["workflow"], "mode": "release",
                        "config": SPECS_MAP}, allow_unicode=True), "demo")
    _save(view, {"api_base": "u"})
    assert _load(view)["api_base"] == "u"


pass

def _mk_dir_tool(proj, name="dirt", config=None):
    d = proj / ".agent" / "tools" / name
    d.mkdir(parents=True)
    data = {"entry": "main.py", "scope": "local"}
    if config is not None:
        data["config"] = config
    (d / "tool.yaml").write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), "utf-8")
    (d / "main.py").write_text(
        "def register(reg):\n"
        "    reg.tool('t', 'd', {}, lambda: None)\n", "utf-8")
    return d


def test_dir_tool_config_roundtrip(tmp_dirs):
    from app.plugins import tool_unit
    proj = _mk_project(tmp_dirs)
    d = _mk_dir_tool(proj, config=SPECS_MAP)
    unit = tool_unit.from_dir(d)
    assert [s["key"] for s in unit.meta["config"]] == [s["key"] for s in SPECS]

    _save(unit, {"api_base": "http://tool", "token": "tk"})
    assert not (d / "config.json").exists()
    assert _db_row("tool:dirt")["api_base"] == "http://tool"
    assert _load(unit)["token"] == "tk"
    assert _masked(unit)["values"]["token"] == cfg.MASKED


def test_runtime_reads_by_name_without_manifest_snapshot(tmp_dirs):
    from app.plugins import tool_unit
    proj = _mk_project(tmp_dirs)
    d = _mk_dir_tool(proj, config=SPECS_MAP)
    unit = tool_unit.from_dir(d)
    extra = unit.extra()
    assert "config" not in extra
    rebuilt = tool_unit.from_row(unit.entry, extra)
    assert rebuilt.meta == {}
    _save(unit, {"api_base": "u", "token": "tk"})
    pass
    assert cfg.load("tool:dirt", "")["api_base"] == "u"


pass


def test_standalone_tool_declared_default_reaches_runtime(tmp_dirs):
    from app.plugins import adopt, tool_unit
    from app.plugins.install import InstallStore
    from app.plugins.plugin_sdk import PluginHost
    from app.plugins.tool_loader import PluginTools
    from app.tools import ToolRegistry

    proj = _mk_project(tmp_dirs)
    d = _mk_dir_tool(proj, config=SPECS_MAP)
    store = InstallStore(tmp_dirs / "agent.db")
    adopt.adopt_tool(str(proj), "dirt", installs=store)

    specs = tool_unit.from_dir(d).meta["config"]
    PluginTools(store).load_for_project(str(proj), ToolRegistry())

    pass
    host = PluginHost.for_tool("tool:dirt", str(proj), tools=None,
                               registry=None, specs=specs)
    assert host.config("mode") == "fast"
pass
pass
pass
pass

def test_plain_mapping_infers_types():
    rows = cfg.normalize_config({"models": "models.yaml", "retries": 3,
                                 "enabled": True})
    assert [(r["key"], r["type"], r.get("default")) for r in rows] == [
        ("models", "string", "models.yaml"),
        ("retries", "number", 3),
        ("enabled", "boolean", True),
    ]


def test_mapping_value_can_be_full_declaration():
    rows = cfg.normalize_config({
        "level": {"type": "select", "options": ["low", "high"], "default": "low"},
        "note": {"label": "备注", "default": "hi"},
    })
    assert rows[0] == {"key": "level", "label": "level", "type": "select",
                       "options": ["low", "high"], "default": "low"}
    assert rows[1]["label"] == "备注" and rows[1]["type"] == "string"


def test_list_form_is_rejected():
    with pytest.raises(cfg.ConfigError, match="必须是映射"):
        cfg.normalize_config([{"key": "a", "type": "string"}])


def test_nested_mapping_is_flattened_to_dotted_keys():
    rows = cfg.normalize_config({
        "slots": {"agnes": "CHANGE_ME", "silicon": "CHANGE_ME"},
        "paths": {"out": "runs", "cache": {"dir": "c"}},
    })
    assert [r["key"] for r in rows] == [
        "slots.agnes", "slots.silicon", "paths.out", "paths.cache.dir"]
    assert rows[0]["default"] == "CHANGE_ME" and rows[0]["type"] == "string"


def test_nested_leaf_can_be_full_declaration():
    rows = cfg.normalize_config({
        "slots": {"agnes": {"default": "CHANGE_ME", "env": "AGNES_KEY"}},
    })
    assert rows[0]["key"] == "slots.agnes"
    assert rows[0]["default"] == "CHANGE_ME"
    assert rows[0]["type"] == "string"


def test_nesting_deeper_than_three_levels_is_an_error():
    with pytest.raises(cfg.ConfigError, match="嵌套超过 3 层"):
        cfg.normalize_config({"a": {"b": {"c": {"d": 1}}}})


def test_inferred_type_inside_nesting():
    rows = cfg.normalize_config({"g": {"n": 3, "b": True}})
    assert [(r["key"], r["type"]) for r in rows] == [
        ("g.n", "number"), ("g.b", "boolean")]


def test_list_value_is_an_error():
    with pytest.raises(cfg.ConfigError, match="列表"):
        cfg.normalize_config({"tags": ["a", "b"]})


def test_empty_config_is_no_config():
    assert cfg.normalize_config(None) == []


def test_mapping_form_roundtrips_through_save(tmp_dirs, store):
    pkg = _mk_pkg(tmp_dirs, kinds=("tool",),
                  config={"out_dir": "runs", "retries": 2},
                  files={"tools/t.py": ""})
    p = pkgmod.load_package(pkg)
    assert [f["key"] for f in p.config] == ["out_dir", "retries"]
    _save(p, {"out_dir": "output", "retries": 5})
    assert _load(p) == {"out_dir": "output", "retries": 5}
    assert not (pkg / "config.json").exists()


def test_nested_config_keys_are_flat_everywhere(tmp_dirs):
    from app.plugins import tool_unit
    proj = _mk_project(tmp_dirs)
    d = _mk_dir_tool(proj, config={"slots": {"agnes": "A", "ms": "M"},
                                  "out_dir": "runs"})
    unit = tool_unit.from_dir(d)
    assert [s["key"] for s in unit.meta["config"]] == [
        "slots.agnes", "slots.ms", "out_dir"]

    _save(unit, {"slots.agnes": "KEY1", "slots.ms": "KEY2",
                 "out_dir": "output"})
    assert _db_row("tool:dirt") == {
        "slots.agnes": "KEY1", "slots.ms": "KEY2", "out_dir": "output"}
    got = cfg.load("tool:dirt", "")
    assert got["slots.agnes"] == "KEY1" and got["out_dir"] == "output"
