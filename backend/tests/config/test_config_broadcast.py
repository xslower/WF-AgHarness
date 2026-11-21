from __future__ import annotations

import pytest

from app.event.bus import HUB


@pytest.fixture
def caught():
    got: list[dict] = []
    off = HUB.on("config.changed", lambda ev: got.append(ev))
    yield got
    off()


def _new(client, **kw) -> str:
    body = {"name": "p", "baseUrl": "https://api.test.com/v1", "apiKey": "k",
            "models": []}
    body.update(kw)
    return client.post("/api/providers", json=body).json()["id"]


@pytest.mark.parametrize("action", [
    "add_provider", "update_provider", "fetch_models", "remove_model",
    "delete_provider", "set_queue", "set_utility", "set_settings",
])
def test_every_config_write_broadcasts(client, caught, monkeypatch, action):
    pid = _new(client, models=[{"id": "m-a", "kind": "lm"},
                               {"id": "m-b", "kind": "lm"}])
    pname = "p"

    async def fake(p):
        return [("m-a", ""), ("m-b", "")]

    import app.main as main_mod
    monkeypatch.setattr(main_mod.app.state.container.gateway,
                        "fetch_models_with_wire", fake)
    caught.clear()

    if action == "add_provider":
        _new(client, name="另一个")
    elif action == "update_provider":
        client.put(f"/api/providers/{pid}", json={
            "name": "改名", "baseUrl": "https://x/v1", "apiKey": "k", "models": []})
    elif action == "fetch_models":
        client.post(f"/api/providers/{pid}/fetch_models")
    elif action == "remove_model":
        client.delete(f"/api/providers/{pid}/models/m-a")
    elif action == "delete_provider":
        client.delete(f"/api/providers/{pid}")
    elif action == "set_queue":
        client.put("/api/model_queue", json={"parent": [f"{pname}/m-a"], "child": []})
    elif action == "set_utility":
        client.put("/api/utility", json={"completion": [], "classify": [],
                                         "review": [], "suggest": []})
    elif action == "set_settings":
        client.put("/api/settings", json={"defaultEffort": "low"})

    assert caught, f"{action} 没有广播 config.changed"
    assert caught[-1]["payload"]["reason"], "事件要带非空 reason，方便排查是谁改的"


def test_event_carries_payload_and_stays_small(caught):
    from app.event.bus import HUB
    HUB.publish("config.changed", {"reason": "x"})
    assert set(caught[-1]["payload"]) == {"reason"}


def test_sync_config_without_hub_does_not_raise(tmp_path):
    from app.api.deps import Container
    c = Container.__new__(Container)
    c.hub = object()
    c.gateway = type("G", (), {"config": None})()
    c.envs = type("E", (), {"bindings": {}})()
    c.projects = type("P", (), {"root": ""})()
    c.store = type("St", (), {"config": type("C", (), {
        "settings": type("Se", (), {"envPython": "", "envNode": "",
                                    "projectsRoot": ""})()})()})()
    c.sync_config()
