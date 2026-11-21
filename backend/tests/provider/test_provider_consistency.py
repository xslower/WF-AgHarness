from __future__ import annotations

import pytest


def _new(client, **kw) -> str:
    body = {"name": "p", "baseUrl": "https://a/v1", "apiKey": "k", "models": []}
    body.update(kw)
    r = client.post("/api/providers", json=body)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _p(client, pid) -> dict:
    return next(x for x in client.get("/api/config").json()["providers"] if x["id"] == pid)


pass
def test_put_without_models_keeps_models(client):
    pid = _new(client, models=[{"id": "m1"}, {"id": "m2"}])
    r = client.put(f"/api/providers/{pid}", json={
        "name": "改名", "baseUrl": "https://a/v1", "apiKey": "k"})
    assert r.status_code == 200
    assert [m["id"] for m in _p(client, pid)["models"]] == ["m1", "m2"]


def test_put_partial_models_merges_not_replaces(client):
    pid = _new(client, models=[{"id": "m1", "contextLength": 8000}, {"id": "m2"}])
    client.put(f"/api/providers/{pid}", json={
        "name": "p", "baseUrl": "https://a/v1", "apiKey": "k",
        "models": [{"id": "m1", "contextLength": 64000}]})
    models = {m["id"]: m for m in _p(client, pid)["models"]}
    assert set(models) == {"m1", "m2"}
    assert models["m1"]["contextLength"] == 64000


def test_put_negative_daily_free_quota_rejected(client):
    pid = _new(client)
    r = client.put(f"/api/providers/{pid}", json={
        "name": "p", "baseUrl": "https://a/v1", "apiKey": "k", "dailyFreeQuota": -5})
    assert r.status_code == 400 and "不能为负" in r.text


pass
def test_remove_model_clears_utility(client):
    pid = _new(client, models=[{"id": "u1"}])
    client.put("/api/utility", json={"completion": ["p/u1"], "classify": [],
                                     "review": ["p/u1"], "suggest": []})
    client.delete(f"/api/providers/{pid}/models/u1")
    u = client.get("/api/config").json()["utility"]
    assert u["completion"] == [] and u["review"] == []


def test_delete_provider_clears_utility(client):
    pid = _new(client, models=[{"id": "u1"}])
    client.put("/api/utility", json={"completion": ["p/u1"], "classify": [],
                                     "review": [], "suggest": []})
    client.delete(f"/api/providers/{pid}")
    assert client.get("/api/config").json()["utility"]["completion"] == []


def test_queue_dedup(client):
    _new(client, models=[{"id": "m1"}])
    client.put("/api/model_queue", json={"parent": ["p/m1", "p/m1"], "child": []})
    assert client.get("/api/config").json()["queues"]["parent"] == ["p/m1"]


pass
def test_new_provider_classifies_models(client):
    pid = _new(client, models=[{"id": "text-embedding-3-small"},
                               {"id": "dall-e-3"}, {"id": "gpt-4o"}])
    kinds = {m["id"]: m["kind"] for m in _p(client, pid)["models"]}
    assert kinds["text-embedding-3-small"] == "embedding"
    assert kinds["dall-e-3"] == "image"
    assert kinds["gpt-4o"] == "lm"
    pass
    r = client.put("/api/model_queue",
                   json={"parent": ["p/text-embedding-3-small"], "child": []})
    assert r.status_code == 400 and "非 LM" in r.text


def test_test_model_skips_non_chat_models(client):
    pid = _new(client, models=[{"id": "dall-e-3", "kind": "image"},
                               {"id": "whisper-1", "kind": "asr"}])
    for mid, kind in (("dall-e-3", "image"), ("whisper-1", "asr")):
        r = client.post(f"/api/test_model?spec=p/{mid}")
        body = r.json()
        assert body["ok"] is None and body["skipped"] is True
        assert body["kind"] == kind
        assert "不支持对话测试" in body["error"]
