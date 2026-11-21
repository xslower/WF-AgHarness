from __future__ import annotations

import json

import pytest

from .helpers import api_package, mk_package, mk_project


@pytest.fixture()
def client(container):
    from fastapi.testclient import TestClient
    import app.main as main_mod
    from app.api.deps import set_container

    set_container(main_mod.app, container)
    return TestClient(main_mod.app)


def test_installed_list_starts_empty(client):
    r = client.get("/api/plugins/installed")
    assert r.status_code == 200 and r.json()["installed"] == []


def test_install_then_list_then_uninstall(client, tmp_dirs):
    proj = mk_project(tmp_dirs)
    pkg = mk_package(proj, kinds=("workflow",), files={
        "workflows/a.json": '{"name":"a","nodes":[]}'})
    r = client.post("/api/plugins/install",
                    json={"source": str(pkg), "project": str(proj)})
    assert r.status_code == 200
    assert "restartRequired" not in r.json() and "copied" not in r.json()
    listed = client.get("/api/plugins/installed",
                        params={"project": str(proj)}).json()["installed"]
    assert [x["id"] for x in listed] == ["demo"]
    assert not (proj / ".agent" / "workflows").exists()
    gone = client.delete("/api/plugins/installed/demo", params={"project": str(proj)})
    assert gone.status_code == 200
    assert "kept" not in gone.json()
    assert client.get("/api/plugins/installed",
                      params={"project": str(proj)}).json()["installed"] == []
    assert (pkg / "workflows" / "a.json").is_file()


def test_install_without_project_is_400(client, tmp_dirs):
    proj = mk_project(tmp_dirs)
    pkg = mk_package(proj)
    r = client.post("/api/plugins/install", json={"source": str(pkg)})
    assert r.status_code == 400


def test_install_outside_project_is_400(client, tmp_dirs):
    proj = mk_project(tmp_dirs)
    outside = tmp_dirs / "outside"
    outside.mkdir()
    import yaml
    (outside / "plugin.yaml").write_text(yaml.safe_dump(
        {"id": "out", "name": "out", "version": "1", "kinds": ["workflow"],
         "mode": "release"}), "utf-8")
    r = client.post("/api/plugins/install",
                    json={"source": str(outside), "project": str(proj)})
    assert r.status_code == 400


def test_install_internal_error_is_400_with_reason(client, tmp_dirs, monkeypatch):
    from app.plugins import install as inst_mod

    def boom(*a, **k):
        raise RuntimeError("磁盘炸了")

    monkeypatch.setattr(inst_mod, "install", boom)
    proj = mk_project(tmp_dirs)
    r = client.post("/api/plugins/install",
                    json={"source": str(proj), "project": str(proj)})
    assert r.status_code == 400
    assert "磁盘炸了" in r.json()["detail"]


def test_adopt_internal_error_is_400_with_reason(client, tmp_dirs, monkeypatch):
    from app.plugins import adopt as adopt_mod

    def boom(*a, **k):
        raise RuntimeError("schema 坏了")

    monkeypatch.setattr(adopt_mod, "adopt_plugin", boom)
    proj = mk_project(tmp_dirs)
    r = client.post("/api/plugins/adopt",
                    json={"kind": "plugin", "name": "x", "project": str(proj)})
    assert r.status_code == 400
    assert "schema 坏了" in r.json()["detail"]


def test_uninstall_unknown_is_404(client):
    assert client.delete("/api/plugins/installed/nope").status_code == 404


def test_install_exposes_config_fields(client, container, tmp_dirs):
    proj = mk_project(tmp_dirs)
    pkg = mk_package(proj, config={"k": 3})
    r = client.post("/api/plugins/install",
                    json={"source": str(pkg), "project": str(proj)})
    assert r.status_code == 200
    cfg = client.get("/api/plugins/config/demo", params={"project": str(proj)})
    assert cfg.status_code == 200
    assert [f["key"] for f in cfg.json()["fields"]] == ["k"]


def test_put_config_requires_field_and_masks_secret(client, tmp_dirs):
    proj = mk_project(tmp_dirs)
    pkg = mk_package(proj, config={"token": {"type": "secret"}})
    assert client.post("/api/plugins/install",
                       json={"source": str(pkg), "project": str(proj)}).status_code == 200
    r = client.put("/api/plugins/config/demo", params={"project": str(proj)},
                   json={"values": {"token": "sk-real"}})
    assert r.status_code == 200
    assert r.json()["values"]["token"] == "••••"


def test_system_scope_lists_only_global_plugins(client, tmp_dirs):
    proj = mk_project(tmp_dirs)
    pkg = mk_package(proj, kinds=("workflow",), files={
        "workflows/a.json": '{"name":"a","nodes":[]}'})
    assert client.post("/api/plugins/install", json={
        "source": str(pkg), "project": str(proj)}).status_code == 200

    pass
    assert client.get("/api/plugins/installed").json()["installed"] == []
    pass
    assert [x["id"] for x in client.get(
        "/api/plugins/installed", params={"scope": "all"}).json()["installed"]] == ["demo"]
    pass
    assert [x["id"] for x in client.get(
        "/api/plugins/installed", params={"project": str(proj)}).json()["installed"]] == ["demo"]
