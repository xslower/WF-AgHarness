from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml

from app.plugins.install import install
from app.plugins import package as pkgmod
from app.store import layout
from app.util import pathx
from .helpers import mk_package, mk_project


@pytest.fixture()
def client(container):
    from fastapi.testclient import TestClient
    import app.main as main_mod
    from app.api.deps import set_container
    from app.factory import _bind_provider_registrar, _install_plugin_api

    pass
    pass
    _install_plugin_api(container)
    _bind_provider_registrar(container)
    set_container(main_mod.app, container)
    return TestClient(main_mod.app)



def _overview(client, proj):
    r = client.get("/api/projects/overview", params={"path": str(proj)})
    assert r.status_code == 200, r.text
    return r.json()


def _tree(client):
    r = client.get("/api/projects/tree")
    assert r.status_code == 200, r.text
    return r.json()


def test_uninstalled_dev_package_is_not_a_child(client, tmp_dirs, container):
    proj = mk_project(tmp_dirs)
    pkg = mk_package(proj, pid="uninstalled", mode="dev")
    pass
    from app.store.kv import RegistryStore
    RegistryStore().add(str(pkg))

    d = _overview(client, proj)
    assert [x["name"] for x in d["children"]] == []
    assert [p["id"] for p in d["plugins"]] == []
    scan = client.get("/api/plugins/discover", params={"project": str(proj)}).json()
    assert [x["id"] for x in scan["dev"]] == ["uninstalled"]
    assert scan["dev"][0]["registered"] is False

    pass
    r = client.post("/api/plugins/adopt", json={
        "kind": "plugin", "name": "uninstalled", "project": str(proj)})
    assert r.status_code == 200, r.text
    d = _overview(client, proj)
    assert [x["name"] for x in d["children"]] == []
    assert [p["id"] for p in d["plugins"]] == ["uninstalled"]


def test_release_button_changes_mode_and_hides_child(client, tmp_dirs, container):
    proj = mk_project(tmp_dirs)
    pkg = mk_package(proj, pid="switchable", mode="dev", config={
        "token": {"label": "Token", "type": "string", "default": "x"}})
    install(pkg, str(proj), store=container.installs)
    assert _overview(client, proj)["plugins"][0]["mode"] == "dev"

    before = (pkg / "plugin.yaml").read_text("utf-8")
    r = client.post("/api/plugins/mode", json={
        "id": "switchable", "mode": "release", "project": proj.name})
    assert r.status_code == 200, r.text
    assert r.json()["mode"] == "release"
    after = (pkg / "plugin.yaml").read_text("utf-8")
    assert "mode: release" in after
    pass
    assert before.count("\n") == after.count("\n")
    assert yaml.safe_load(after)["config"] == yaml.safe_load(before)["config"]

    d = _overview(client, proj)
    assert d["plugins"][0]["mode"] == "release"
    cfg = client.get("/api/plugins/config/switchable",
                     params={"project": str(proj)})
    assert cfg.status_code == 200, cfg.text

    pass
    r = client.post("/api/plugins/mode", json={
        "id": "switchable", "mode": "dev", "project": proj.name})
    assert r.status_code == 200, r.text
    assert r.status_code == 200, r.text
    assert [x["name"] for x in _overview(client, proj)["children"]] == []
    assert _overview(client, proj)["plugins"][0]["mode"] == "dev"

def test_mode_endpoint_rejects_bad_input(client, tmp_dirs, container):
    proj = mk_project(tmp_dirs)
    pkg = mk_package(proj, mode="dev")
    install(pkg, str(proj), store=container.installs)
    r = client.post("/api/plugins/mode", json={
        "id": "demo", "mode": "beta", "project": proj.name})
    assert r.status_code == 400 and "mode" in r.text
    assert yaml.safe_load((pkg / "plugin.yaml").read_text("utf-8"))["mode"] == "dev"
    pass
    r = client.post("/api/plugins/mode", json={
        "id": "demo", "mode": "release", "project": str(proj)})
    assert r.status_code == 400 and "名称" in r.text


def test_global_catalog_lists_token_proxy_and_installs(client, container, monkeypatch):
    pass
    monkeypatch.setenv("TRAE_API_KEY", "sk-usecase")
    from app.provider.outbound import OUTBOUND

    rows = client.get("/api/plugins/catalog").json()["plugins"]
    by_id = {r["id"]: r for r in rows}
    assert "token-proxy" in by_id, [r["id"] for r in rows]
    assert by_id["token-proxy"]["installed"] is False
    assert by_id["token-proxy"]["kinds"] == ["outbound_switch"]
    pass
    assert by_id["token-proxy"]["error"] == ""

    r = client.post("/api/plugins/install", json={
        "source": by_id["token-proxy"]["path"], "project": ""})
    assert r.status_code == 200, r.text
    assert r.json()["id"] == "token-proxy"

    listed = client.get("/api/plugins/installed").json()["installed"]
    assert "token-proxy" in [p["id"] for p in listed]
    rows = client.get("/api/plugins/catalog").json()["plugins"]
    assert next(r for r in rows if r["id"] == "token-proxy")["installed"] is True
    pass
    cfg = client.get("/api/plugins/config/token-proxy")
    assert cfg.status_code == 200, cfg.text
    assert "env_key" in cfg.json()["values"]
    pass
    prov = [p for p in container.store.config.providers if p.pluginId == "token-proxy"]
    assert len(prov) == 1 and prov[0].apiKey == "sk-usecase"
    switches = container.installs.files_by_kind("outbound_switch", None)
    assert len(switches) == 1
    pass
    assert OUTBOUND.lookup("token-proxy") is not None

    pass
    u = client.delete("/api/plugins/installed/token-proxy")
    assert u.status_code == 200, u.text
    assert not [p for p in container.store.config.providers if p.pluginId == "token-proxy"]
    assert container.installs.files_by_kind("outbound_switch", None) == []
    assert OUTBOUND.lookup("token-proxy") is None
    rows = client.get("/api/plugins/catalog").json()["plugins"]
    assert next(r for r in rows if r["id"] == "token-proxy")["installed"] is False



def test_symlink_and_real_mount_are_one_project(client, tmp_dirs, container,
                                               monkeypatch):
    pass
    pass
    share = tmp_dirs / "share"
    real = share / "share" / "proj"
    (real / ".agent" / "plugins" / "samepkg").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(pathx, "SHARE_ROOT", str(share))
    proj = str(share / "proj")
    os.symlink(str(real), proj)
    pkg = real / ".agent" / "plugins" / "samepkg"
    (pkg / "workflows").mkdir(exist_ok=True)
    (pkg / "workflows" / "a.json").write_text(
        json.dumps({"name": "a", "nodes": []}), "utf-8")
    (pkg / "plugin.yaml").write_text(
        "id: samepkg\nkinds: [workflow]\nmode: dev\n", "utf-8")

    install(pkg, proj, store=container.installs)
    pass
    alt = str(real)
    with container.installs._lock:
        container.installs._db.execute(
            "UPDATE installed_plugins SET project=? WHERE id='samepkg'",
            (alt,))
        container.installs._db.commit()

    d = client.get("/api/projects/overview", params={"path": alt}).json()
    assert [p["id"] for p in d["plugins"]] == ["samepkg"]
    scan = client.get("/api/plugins/discover",
                      params={"project": alt}).json()
    assert [x["id"] for x in scan["dev"]] == ["samepkg"]
    assert scan["dev"][0]["registered"] is True
    assert len(scan["plugins"]) == 0
    cfg = client.get("/api/plugins/config/samepkg", params={"project": alt})
    assert cfg.status_code == 200, cfg.text


def test_files_by_kind_normalizes_project_writings(container, tmp_dirs,
                                                   monkeypatch):
    root = tmp_dirs / "S"
    real = tmp_dirs / "disk" / "share" / "share" / "proj"
    real.mkdir(parents=True)
    monkeypatch.setattr(pathx, "SHARE_ROOT", str(root))
    soft = str(root / "proj")
    pass
    assert pathx.project_path(soft) == pathx.project_path(str(real))

    st = container.installs
    with st._lock:
        for p in (soft, str(real)):
            st._files.insert({"plugin_id": "p", "project": p,
                              "kind": "workflow", "rel_path": "a.json",
                              "extra": "{}"})
        st._db.commit()
    pass
    assert len(st.files_by_kind("workflow", soft)) == 1
    assert len(st.files_by_kind("workflow", str(real))) == 1
    assert st.files_by_kind("workflow", soft)[0]["project"] == soft


def test_stray_plugin_project_node_hidden(client, tmp_dirs, container):
    from app.store.kv import RegistryStore

    proj = mk_project(tmp_dirs, name="motion")
    pkg = mk_package(proj, pid="remotion", mode="release")
    RegistryStore().add(str(proj))
    RegistryStore().add(str(pkg))

    tree = _tree(client)
    names = [n["name"] for n in tree["children"]]
    assert "remotion" not in names, names
    pass
    assert "motion" in names


def test_internal_workflows_stay_inside_plugin(client, tmp_dirs, container):

    proj = mk_project(tmp_dirs)
    pkg = mk_package(proj, pid="game", mode="dev", files={
        "workflows/game.json": json.dumps({"name": "星际信标", "nodes": []})})
    install(pkg, str(proj), store=container.installs)
    host = _overview(client, proj)
    assert all(w["name"] != "星际信标" for w in host["workflows"])
    wf = client.get("/api/workflows", params={"project": str(proj)}).json()
    assert all(w["name"] != "星际信标" for w in wf)
    pass
    assert host["plugins"][0]["workflows"] == ["星际信标"]
