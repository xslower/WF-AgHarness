from __future__ import annotations

import json

import pytest



def _db(pid: str) -> dict | None:
    from app.provider.store import ProviderStore
    return next((x for x in ProviderStore().list_all() if x["id"] == pid), None)


def _after_restart(pid: str):
    from app.config import ConfigStore
    cfg = ConfigStore().config
    return next((p for p in cfg.providers if p.id == pid), None)


def _new(client, **kw) -> str:
    body = {"name": "p1", "baseUrl": "https://api.test.com/v1", "apiKey": "sk-1",
            "models": []}
    body.update(kw)
    r = client.post("/api/providers", json=body)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_new_provider_persisted(client):
    pid = _new(client, name="我的中转站")
    row = _db(pid)
    assert row and row["name"] == "我的中转站" and row["apiKey"] == "sk-1"
    assert _after_restart(pid).name == "我的中转站"


def test_update_provider_persisted_and_survives_restart(client):
    pid = _new(client, name="旧名", baseUrl="https://old/v1")
    r = client.put(f"/api/providers/{pid}", json={
        "name": "新名", "baseUrl": "https://new/v1", "apiKey": "sk-2",
        "models": [{"id": "m1"}, {"id": "m2"}],
    })
    assert r.status_code == 200
    assert r.json()["name"] == "新名"

    row = _db(pid)
    assert row["name"] == "新名" and row["baseUrl"] == "https://new/v1"
    assert [m["id"] for m in row["models"]] == ["m1", "m2"]

    after = _after_restart(pid)
    assert after.baseUrl == "https://new/v1"
    assert [m.id for m in after.models] == ["m1", "m2"]


def test_fetch_models_persisted(client, monkeypatch):
    pid = _new(client)

    async def fake(p):
        return [("m-a", ""), ("m-b", "")]

    import app.main as main_mod
    monkeypatch.setattr(main_mod.app.state.container.gateway,
                        "fetch_models_with_wire", fake)
    r = client.post(f"/api/providers/{pid}/fetch_models")
    assert r.status_code == 200
    assert [m["id"] for m in r.json()["models"]] == ["m-a", "m-b"]

    assert [m["id"] for m in _db(pid)["models"]] == ["m-a", "m-b"]
    assert [m.id for m in _after_restart(pid).models] == ["m-a", "m-b"]


def test_fetch_models_is_idempotent(client, monkeypatch):
    pid = _new(client, models=[{"id": "m-a", "supportsThinking": True,
                                "contextLength": 32000}])

    async def fake(p):
        return [("m-a", ""), ("m-b", "")]

    import app.main as main_mod
    monkeypatch.setattr(main_mod.app.state.container.gateway,
                        "fetch_models_with_wire", fake)
    client.post(f"/api/providers/{pid}/fetch_models")
    client.post(f"/api/providers/{pid}/fetch_models")
    models = {m["id"]: m for m in _db(pid)["models"]}
    assert set(models) == {"m-a", "m-b"}
    assert models["m-a"]["supportsThinking"] is True
    assert models["m-a"]["contextLength"] == 32000


def test_remove_model_persisted(client, monkeypatch):
    pid = _new(client, models=[{"id": "m-a"}, {"id": "m-b"}])
    assert client.delete(f"/api/providers/{pid}/models/m-a").status_code == 200
    assert [m["id"] for m in _db(pid)["models"]] == ["m-b"]
    assert [m.id for m in _after_restart(pid).models] == ["m-b"]


def test_remove_model_cleans_queues(client):
    pid = _new(client, models=[{"id": "m-a"}, {"id": "m-b"}])
    client.put("/api/model_queue", json={"parent": ["p1/m-a"], "child": []})
    client.delete(f"/api/providers/{pid}/models/m-a")
    cfg = client.get("/api/config").json()
    assert "p1/m-a" not in cfg["queues"]["parent"]


def test_delete_provider_persisted(client):
    pid = _new(client, name="要删的")
    assert client.delete(f"/api/providers/{pid}").status_code == 200
    assert _db(pid) is None
    assert _after_restart(pid) is None


def test_provider_kind_and_adapter_survive(client):
    pid = _new(client, kind="web_session", adapter="web-session")
    row = _db(pid)
    assert row["kind"] == "web_session" and row["adapter"] == "web-session"
    after = _after_restart(pid)
    assert (after.kind, after.adapter) == ("web_session", "web-session")


def test_config_endpoint_provider_shape(client):
    pid = _new(client, name="契约", kind="openai_compatible",
               models=[{"id": "m1", "kind": "lm", "contextLength": 128000}])
    cfg = client.get("/api/config").json()
    p = next(x for x in cfg["providers"] if x["id"] == pid)
    pass
    for k in ("id", "name", "baseUrl", "apiKey", "kind", "adapter", "models",
              "note", "imported", "dailyFreeQuota"):
        assert k in p, f"契约字段缺失: {k}"
    assert isinstance(p["dailyFreeQuota"], int)
    assert isinstance(p["models"], list)
    assert p["models"][0]["contextLength"] == 128000
