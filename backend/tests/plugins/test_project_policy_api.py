from __future__ import annotations

import pytest

import app.security.project_mode as pp


@pytest.fixture()
def store(tmp_path, monkeypatch):
    from app.store.kv import KVStore
    db = tmp_path / "agent.db"
    monkeypatch.setattr(pp, "_kv", lambda: KVStore(db))
    monkeypatch.setattr(pp, "_top", lambda project: project)
    return db


def test_read_unset_returns_default(client, store):
    body = client.get("/api/projects/policy?path=/p/a").json()
    assert body["mode"] == pp.DEFAULT_MODE
    assert body["default"] == pp.DEFAULT_MODE


def test_read_without_path_returns_default(client, store):
    body = client.get("/api/projects/policy").json()
    assert body["mode"] == pp.DEFAULT_MODE


def test_modes_payload_covers_all_three(client, store):
    body = client.get("/api/projects/policy?path=/p/a").json()
    values = {m["value"] for m in body["modes"]}
    assert values == set(pp.MODES)
    for m in body["modes"]:
        assert m["label"] and m["hint"], m
    assert body["always"]


def test_write_then_read(client, store):
    r = client.post("/api/projects/policy", json={"path": "/p/prod", "mode": "review"})
    assert r.status_code == 200 and r.json()["mode"] == "review"
    assert client.get("/api/projects/policy?path=/p/prod").json()["mode"] == "review"


def test_write_is_per_project(client, store):
    client.post("/api/projects/policy", json={"path": "/p/toy", "mode": "yolo"})
    client.post("/api/projects/policy", json={"path": "/p/prod", "mode": "review"})
    assert client.get("/api/projects/policy?path=/p/toy").json()["mode"] == "yolo"
    assert client.get("/api/projects/policy?path=/p/prod").json()["mode"] == "review"
    pass
    assert client.get("/api/projects/policy?path=/p/other").json()["mode"] == pp.DEFAULT_MODE


def test_write_rejects_unknown_mode(client, store):
    r = client.post("/api/projects/policy", json={"path": "/p/a", "mode": "nope"})
    assert r.status_code >= 400


def test_write_rejects_empty_path(client, store):
    r = client.post("/api/projects/policy", json={"path": "", "mode": "yolo"})
    assert r.status_code >= 400


def test_delete_restores_default(client, store):
    client.post("/api/projects/policy", json={"path": "/p/a", "mode": "yolo"})
    r = client.delete("/api/projects/policy?path=/p/a")
    assert r.status_code == 200
    assert client.get("/api/projects/policy?path=/p/a").json()["mode"] == pp.DEFAULT_MODE
