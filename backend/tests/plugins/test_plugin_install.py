from __future__ import annotations

import json

import pytest
import yaml

from app.plugins import install as inst
from app.plugins import package as pkgmod
from app.plugins.location import resolve_registered
from app.store import layout
from .helpers import mk_package, mk_project, tool_package


@pytest.fixture()
def store(tmp_dirs):
    return inst.InstallStore(tmp_dirs / "agent.db")


pass

def test_package_requires_yaml(tmp_dirs):
    bad = tmp_dirs / "no-yaml"
    bad.mkdir()
    with pytest.raises(ValueError, match="plugin.yaml"):
        pkgmod.load_package(bad)


def test_package_rejects_unknown_kind(tmp_dirs):
    proj = mk_project(tmp_dirs)
    with pytest.raises(ValueError, match="未知 kind"):
        pkgmod.load_package(mk_package(proj, kinds=("nope",)))


def test_package_normalizes_config_and_providers(tmp_dirs):
    proj = mk_project(tmp_dirs)
    pkg = mk_package(proj, config={"k": 3},
                     providers=[{"id": "p1", "base_url": "http://x", "env_keys": ["X"]}])
    loaded = pkgmod.load_package(pkg)
    assert loaded.config[0]["type"] == "number"
    assert loaded.providers[0]["id"] == "p1"


def test_package_bad_config_keeps_identity(tmp_dirs):
    proj = mk_project(tmp_dirs)
    loaded = pkgmod.load_package(mk_package(proj, config={"k": {"type": "nope"}}))
    assert loaded.id == "demo" and loaded.mode == "release"
    assert loaded.kinds == ("workflow",)
    assert loaded.config == ()
    assert "type 不支持" in loaded.config_error


def test_global_kind_in_project_package_is_rejected(tmp_dirs, store):
    proj = mk_project(tmp_dirs)
    pkg = mk_package(proj, kinds=("workflow", "theme"),
                     files={"workflows/a.json": '{"name":"a","nodes":[]}'})
    with pytest.raises(ValueError, match="全局型"):
        inst.install(pkg, str(proj), store=store)


def test_source_outside_project_is_rejected(tmp_dirs, store):
    proj = mk_project(tmp_dirs)
    outside = tmp_dirs / "outside"
    outside.mkdir()
    (outside / "plugin.yaml").write_text(yaml.safe_dump(
        {"id": "out", "name": "out", "version": "1", "kinds": ["workflow"],
         "mode": "release"}), "utf-8")
    with pytest.raises(ValueError, match="必须先放进项目目录内"):
        inst.install(outside, str(proj), store=store)


pass

def test_install_registers_without_copying(tmp_dirs, store):
    proj = mk_project(tmp_dirs)
    pkg = mk_package(proj, kinds=("workflow", "api"), files={
        "workflows/a.json": '{"name":"a","nodes":[]}',
        "api/router.py": "async def handle(req, host):\n    return {}\n",
        "index.html": "<h1>hi</h1>",
    })
    before = sorted(str(f.relative_to(pkg)) for f in pkg.rglob("*") if f.is_file())
    r = inst.install(pkg, str(proj), store=store)
    assert r["files"] and "restartRequired" not in r and "copied" not in r
    after = sorted(str(f.relative_to(pkg)) for f in pkg.rglob("*") if f.is_file())
    assert before == after
    assert not (proj / ".agent" / "workflows").exists()
    assert not (proj / ".agent" / "api").exists()
    rows = store.files_of("demo", str(proj))
    assert {f["kind"] for f in rows} == {"workflow", "api"}
    pass
    assert all(f["rel_path"].endswith((".py", ".json")) for f in rows)
    for row in rows:
        assert resolve_registered(row, str(proj)).is_file()


def test_duplicate_registration_rejected(tmp_dirs, store):
    proj = mk_project(tmp_dirs)
    pkg = mk_package(proj)
    inst.install(pkg, str(proj), store=store)
    with pytest.raises(ValueError, match="已登记"):
        inst.install(pkg, str(proj), store=store)


def test_uninstall_removes_only_registration(tmp_dirs, store):
    proj = mk_project(tmp_dirs)
    pkg = mk_package(proj)
    inst.install(pkg, str(proj), store=store)
    wf = pkg / "workflows" / "a.json"
    assert wf.is_file()
    r = inst.uninstall("demo", str(proj), store=store)
    assert r["removed"] and "kept" not in r
    assert wf.is_file()
    assert store.files_of("demo", str(proj)) == []
    assert store.get_plugin("demo", str(proj)) is None


def test_uninstall_unknown_plugin(tmp_dirs, store):
    with pytest.raises(KeyError):
        inst.uninstall("nope", "", store=store)


def test_files_by_kind_is_the_load_manifest(tmp_dirs, store):
    proj = mk_project(tmp_dirs)
    pkg = mk_package(proj, kinds=("workflow",), files={
        "workflows/a.json": '{"name":"a","nodes":[]}'})
    inst.install(pkg, str(proj), store=store)
    rows = store.files_by_kind("workflow", str(proj))
    assert [f["rel_path"] for f in rows] == [".agent/plugins/demo/workflows/a.json"]
    assert store.files_by_kind("tool", str(proj)) == []


def test_tool_without_register_is_refused(tmp_dirs, store):
    proj = mk_project(tmp_dirs)
    pkg = tool_package(proj, src="x = 1\n")
    with pytest.raises(ValueError, match="register"):
        inst.install(pkg, str(proj), store=store)
    assert store.get_plugin("demo", str(proj)) is None


def test_mcp_only_registers_no_mcp_json(tmp_dirs, store):
    proj = mk_project(tmp_dirs)
    pkg = mk_package(proj, kinds=("mcp_server",), files={
        "mcp.json": json.dumps({"servers": {"s1": {"command": "x"}}})})
    inst.install(pkg, str(proj), store=store)
    assert not layout.project_mcp_json(proj).exists()
    rows = store.files_by_kind("mcp_server", str(proj))
    assert json.loads(rows[0]["extra"])["servers"] == {"s1": {"command": "x"}}


def test_provider_is_manifest_data(tmp_dirs, store):
    proj = mk_project(tmp_dirs)
    pass
    from app.plugins.provider_data import plugin_presets
    pkg = mk_package(proj, kinds=("provider",), providers=[
        {"id": "ext", "kind": "env_preset", "base_url": "http://x", "env_keys": ["K"]}])
    loaded = pkgmod.load_package(pkg)
    assert loaded.providers[0]["id"] == "ext"
    assert plugin_presets(store) == []


pass
def test_dirty_registration_row_raises_value_error(tmp_dirs):
    proj = mk_project(tmp_dirs)
    for row in (
        {"project": str(proj), "rel_path": None},
        {"project": str(proj)},
        {"project": str(proj), "rel_path": "  "},
        {"project": str(proj), "rel_path": 123},
    ):
        with pytest.raises(ValueError, match="登记行缺路"):
            resolve_registered(row, str(proj))


def test_bad_row_does_not_kill_the_batch(tmp_dirs, store):
    proj = mk_project(tmp_dirs)
    pkg = mk_package(proj)
    inst.install(pkg, str(proj), store=store)
    rows = store.files_of("demo", str(proj))
    rows.append({"plugin_id": "demo", "project": str(proj),
                 "kind": "workflow", "rel_path": None, "extra": ""})
    ok = []
    for r in rows:
        try:
            ok.append(resolve_registered(r, str(proj)))
        except ValueError:
            continue
    assert ok and all(p.is_file() for p in ok)


pass

def _move_under(proj, parent):
    dest = parent / proj.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    proj.rename(dest)
    return dest


def test_retarget_only_rewrites_project_column(tmp_dirs, store):
    parent = mk_project(tmp_dirs, "b")
    a = mk_project(tmp_dirs, "a")
    inst.install(mk_package(a), str(a), store=store)
    before = [r["rel_path"] for r in store.files_of("demo", str(a))]
    assert before and all(r.startswith(".agent/") for r in before)

    new_a = _move_under(a, parent)
    store.retarget(str(a), str(new_a))

    after = store.files_of("demo", str(new_a))
    assert after, "登记行没有跟着到新路径"
    pass
    assert sorted(r["rel_path"] for r in after) == sorted(before)
    for r in after:
        pass
        assert resolve_registered(r, str(new_a)).is_file()
    pass
    assert store.files_of("demo", str(a)) == []


def test_retarget_does_not_touch_sibling_projects(tmp_dirs, store):
    b = mk_project(tmp_dirs, "b")
    a = mk_project(b, "a")
    other = mk_project(b, "other")
    for d in (b, a, other):
        inst.install(mk_package(d), str(d), store=store)
    b_before = sorted(r["rel_path"] for r in store.files_of("demo", str(b)))
    o_before = sorted(r["rel_path"] for r in store.files_of("demo", str(other)))

    new_a = tmp_dirs / "a"
    a.rename(new_a)
    store.retarget(str(a), str(new_a))

    assert sorted(r["rel_path"] for r in store.files_of("demo", str(b))) == b_before
    assert sorted(r["rel_path"] for r in store.files_of("demo", str(other))) == o_before
    for r in store.files_of("demo", str(new_a)):
        assert resolve_registered(r, str(new_a)).is_file()


def test_rel_to_is_relative_to_the_project_itself(tmp_dirs):
    from app.plugins.location import base_of
    from app.plugins import location

    b = mk_project(tmp_dirs, "b")
    a = mk_project(b, "a")
    rel = location.rel_to(a / ".agent" / "plugins" / "x", str(a))
    assert rel == ".agent/plugins/x"
    pass
    assert base_of({"project": str(a)}) == a



def test_workflow_dirs_sees_child_but_not_sibling(tmp_dirs, store):
    from app.plugins.workflow_roots import workflow_dirs

    top = mk_project(tmp_dirs, "top")
    kid = mk_project(top, "kid")
    sib = mk_project(top, "sib")
    for d in (kid, sib):
        inst.install(mk_package(d), str(d), store=store)

    kid_dirs = workflow_dirs(store, str(kid))
    sib_dirs = workflow_dirs(store, str(sib))
    top_dirs = workflow_dirs(store, str(top))

    assert kid_dirs, "子项目自己的插件工作流没解析出来"
    assert all(str(kid) in str(d) for d in kid_dirs)
    assert sib_dirs, "兄弟项目自己的工作流也没有"
    assert all(str(sib) in str(d) for d in sib_dirs)
    pass
    assert set(top_dirs) == set(kid_dirs) | set(sib_dirs)
