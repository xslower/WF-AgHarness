from __future__ import annotations

import pytest


@pytest.fixture()
def client(container):
    from fastapi.testclient import TestClient
    import app.main as main_mod
    from app.api.deps import set_container

    set_container(main_mod.app, container)
    return TestClient(main_mod.app)


def _body(**kw):
    base = {
        "name": "t1", "owner": "frontend", "action": "session",
        "kind": "every", "spec": "3600",
        "payload": {"project": "content/foo", "prompt": "写昨天的日报"},
    }
    base.update(kw)
    return base


def test_create_list_delete(client):
    r = client.post("/api/timers", json=_body())
    assert r.status_code == 200, r.text
    got = r.json()
    assert got["name"] == "t1" and got["action"] == "session"
    assert got["nextRunAt"] and got["nextRunAt"] > 0

    rows = client.get("/api/timers", params={"owner": "frontend"}).json()
    assert [x["name"] for x in rows] == ["t1"]
    assert client.get("/api/timers", params={"owner": "backend"}).json() == []

    assert client.delete("/api/timers/t1").json() == {"ok": True}
    assert client.get("/api/timers").json() == []
    assert client.delete("/api/timers/t1").status_code == 404


def test_filter_by_project(client):
    client.post("/api/timers", json=_body(name="a"))
    client.post("/api/timers", json=_body(name="b", payload={
        "project": "content/bar", "prompt": "x"}))
    rows = client.get("/api/timers", params={"project": "content/foo"}).json()
    assert [x["name"] for x in rows] == ["a"]


def test_rejects_unknown_action_and_owner(client):
    r = client.post("/api/timers", json=_body(action="callback"))
    assert r.status_code == 400
    r = client.post("/api/timers", json=_body(owner="worker"))
    assert r.status_code == 400
    assert client.get("/api/timers").json() == []


def test_rejects_bad_cron_and_missing_fields(client):
    assert client.post("/api/timers", json=_body(
        kind="cron", spec="nope")).status_code == 400
    assert client.post("/api/timers", json=_body(
        payload={"project": "p"})).status_code == 400
    assert client.post("/api/timers", json=_body(
        action="workflow", payload={"project": "p"})).status_code == 400


def test_cron_next_run_is_computed(client):
    r = client.post("/api/timers", json=_body(kind="cron", spec="0 9 * * mon"))
    assert r.status_code == 200, r.text
    assert r.json()["nextRunAt"] > 0


def test_patch_toggles_and_edits(client):
    client.post("/api/timers", json=_body())
    r = client.patch("/api/timers/t1", json={"enabled": False})
    assert r.status_code == 200, r.text
    assert r.json()["enabled"] is False
    r = client.patch("/api/timers/t1", json={"spec": "600"})
    assert r.json()["spec"] == "600"
    assert client.patch("/api/timers/nope", json={"enabled": True}).status_code == 404


def test_patch_rejects_bad_spec(client):
    client.post("/api/timers", json=_body())
    r = client.patch("/api/timers/t1", json={"spec": "0"})
    assert r.status_code == 400


def test_backend_task_enters_scheduler(client):
    from app.event.schedule import TIMERS

    client.post("/api/timers", json=_body(name="be", owner="backend"))
    client.post("/api/timers", json=_body(name="fe"))
    try:
        assert "be" in [j["name"] for j in TIMERS.jobs()]
        assert "fe" not in [j["name"] for j in TIMERS.jobs()]
    finally:
        TIMERS.detach("be")
        TIMERS.remove("be")
        TIMERS.remove("fe")


def test_no_fire_endpoint(client):
    client.post("/api/timers", json=_body())
    assert client.post("/api/timers/t1/fire").status_code in (404, 405)
    client.delete("/api/timers/t1")
