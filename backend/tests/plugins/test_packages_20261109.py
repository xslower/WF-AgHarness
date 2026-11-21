from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.plugins import location, package as pkgmod
from app.workflow import preflight

REPO = Path(__file__).resolve().parents[3]
PROXY = REPO / "plugins" / "token-proxy"
pass
pass
pass
pass
AGENT_ROOT = Path("~/agent").expanduser()
BEACON = AGENT_ROOT / "bot" / "beacon"
BEACON_PKG = BEACON / ".agent" / "plugins" / "star-beacon"


pass

def test_token_proxy_is_global_outbound_switch_package():
    pkg = pkgmod.load_package(PROXY)
    assert pkg.id == "token-proxy"
    assert pkg.kinds == ("outbound_switch",)
    assert pkg.needs_project is False
    assert len(pkg.outbound_switches) == 1
    d = pkg.outbound_switches[0]
    assert d["provider"] == "trae-proxy"
    assert (d["handler"], d["setup"]) == ("handle", "switch")
    pass
    assert not hasattr(pkg, "env")


def test_token_proxy_registration_rows_have_table_metadata():
    pkg = pkgmod.load_package(PROXY)
    plan = pkgmod.plan_registrations(pkg, "")
    switches = [x for x in plan if x["kind"] == "outbound_switch"]
    setups = [x for x in plan if x["kind"] == "provider_setup"]
    assert len(switches) == 1 and len(setups) == 1
    e = switches[0]["extra"]
    assert e["provider"] == "trae-proxy" and e["handler"] == "handle"
    pass
    assert "module" not in e and "declarations" not in e
    pass
    for x in plan:
        row = {"project": "", "rel_path": x["rel_path"]}
        assert location.resolve_registered(row, "").is_file()


def test_global_plugins_dir_is_source_root():
    from app.store import layout
    assert layout.plugins_dir() == layout.SOURCE_ROOT / "plugins"
    assert layout.plugins_dir().is_dir()
    assert (layout.plugins_dir() / "token-proxy").is_dir()


pass

def test_beacon_project_is_independent(tmp_dirs):
    from app import config as config_mod
    from app.store import layout
    config_mod.DATA_DIR = tmp_dirs
    pass
    proj = tmp_dirs / "beacon"
    (proj / ".agent").mkdir(parents=True)
    pkg = proj / ".agent" / "plugins" / "star-beacon"
    pkg.mkdir(parents=True)
    assert layout.is_project(proj)
    assert layout.top_project(proj) == proj
    top, name = layout.plugin_package_of(pkg)
    assert top == proj and name == "star-beacon"


def test_beacon_package_structure():
    pkg = pkgmod.load_package(BEACON_PKG)
    assert pkg.id == "star-beacon"
    assert set(pkg.kinds) == {"workflow", "tool", "api"}
    assert pkg.needs_project is True
    assert pkg.entry == "index.html"
    assert (BEACON_PKG / "index.html").is_file()
    assert (BEACON_PKG / "static" / "art.svg").is_file()
    assert (BEACON_PKG / "static" / "app.js").is_file()
    plan = pkgmod.plan_registrations(pkg, str(BEACON))
    kinds = [x["kind"] for x in plan]
    pass
    assert kinds.count("workflow") == 3
    assert "tool" in kinds and "api" in kinds
    assert (BEACON_PKG / "workflows" / "trial.json").is_file()


@pytest.mark.parametrize("name", ["game.json", "round.json", "trial.json"])
def test_beacon_workflows_pass_engine_preflight(name):
    wf = json.loads((BEACON_PKG / "workflows" / name).read_text("utf-8"))
    issues: list[str] = []
    runtime = {"player": "测试员", "beacon": "B-7", "guess": "信标在说谎",
               "action": "explore", "target": "日志终端"}
    preflight.check_vars(wf, issues, runtime_inputs=runtime)
    preflight.check_code_imports(wf, str(BEACON), issues)
    assert issues == [], f"{name} 体检失败: {issues}"
    ids = {n["id"] for n in wf["nodes"]}
    for n in wf["nodes"]:
        for key in ("next", "true", "false"):
            if n.get(key):
                assert n[key] in ids, f"{name}: {n['id']}.{key} 悬空"
    assert wf["start_node"] in ids


def test_beacon_game_has_enough_llm_and_code_nodes():
    types = []
    for name in ("game.json", "round.json", "trial.json"):
        wf = json.loads((BEACON_PKG / "workflows" / name).read_text("utf-8"))
        types += [n["type"] for n in wf["nodes"]]
    assert types.count("llm") >= 6, types
    assert types.count("code") >= 8, types
    assert "condition" in types
    all_nodes = [n for name in ("game.json", "round.json", "trial.json")
                 for n in json.loads((BEACON_PKG / "workflows" / name).read_text("utf-8"))["nodes"]]
    assert any(n.get("mode") == "llm" for n in all_nodes
               if n["type"] == "condition")


def test_beacon_explore_rules_are_code_not_llm():
    wfs = {name: json.loads((BEACON_PKG / "workflows" / name).read_text("utf-8"))
           for name in ("game.json", "round.json", "trial.json")}
    explore_code = "\n".join(n.get("code", "") for n in wfs["round.json"]["nodes"]
                              if n["type"] == "code")
    assert "locked" in explore_code and "energy" in explore_code
    assert "evidence" in explore_code
    guard = next(n for n in wfs["trial.json"]["nodes"] if n["id"] == "guard")
    assert guard["type"] == "code" and "len(ev) < 3" in guard["code"]


pass

def _setup_pkg(tmp_dirs) -> tuple[Path, list[dict]]:
    pkg_root = tmp_dirs / "data" / "plugins" / "sw"
    pkg_root.mkdir(parents=True)
    (pkg_root / "provider.py").write_text(
        "def provide(host):\n"
        "    return {'name': 'sw-prov', 'baseUrl': 'http://x',\n"
        "            'apiKey': 'k', 'models': [], 'adapter': 'openai_compatible'}\n",
        encoding="utf-8")
    (pkg_root / "plugin.yaml").write_text(
        "id: sw\nname: sw\nversion: 1.0.0\nmode: release\n"
        "kinds: [outbound_switch]\noutbound_switches:\n"
        "  - provider: sw-prov\n    handler: handle\n    setup: switch\n",
        encoding="utf-8")
    (pkg_root / "outbound" / "switch.py").parent.mkdir()
    (pkg_root / "outbound" / "switch.py").write_text(
        "def handle(req):\n    return None\n", encoding="utf-8")
    return pkg_root, pkgmod.plan_registrations(
        pkgmod.load_package(pkg_root), "")


def test_setup_provider_returns_single_dict(tmp_dirs):
    from app.plugins import provider_setup as ph

    root, plan = _setup_pkg(tmp_dirs)
    assert len([x for x in plan if x["kind"] == "provider_setup"]) == 1
    data = ph.setup_provider(plan, "", "sw")
    assert isinstance(data, dict) and data["name"] == "sw-prov"
    assert "id" not in data and "pluginId" not in data


def test_setup_provider_without_row_returns_none(tmp_dirs):
    from app.plugins import provider_setup as ph

    assert ph.setup_provider([], "", "sw") is None


def test_create_provider_cleans_up_after_failure(tmp_dirs):
    from app.plugins import provider_setup as ph

    calls: list[str] = []

    def boom(action, plugin_id, payload):
        calls.append(action)
        if action == "create":
            raise ValueError("名称已存在")
        return []

    ph.bind_provider_registrar(boom)
    try:
        with pytest.raises(ValueError, match="名称已存在"):
            ph.create_provider("sw", {"name": "sw-prov"})
        assert calls == ["create", "delete"]
    finally:
        ph.bind_provider_registrar(None)


def test_create_provider_none_is_noop(tmp_dirs):
    from app.plugins import provider_setup as ph

    ph.bind_provider_registrar(None)
    assert ph.create_provider("sw", None) is None
