from __future__ import annotations

import pytest


@pytest.fixture()
def client(container):
    from fastapi.testclient import TestClient
    import app.main as main_mod
    from app.api.deps import set_container

    set_container(main_mod.app, container)
    return TestClient(main_mod.app)


def _wf():
    return {"name": "demo", "nodes": [
        {"id": "s1", "type": "write", "path": "a.txt", "content": "A",
         "next": "s2"},
        {"id": "s2", "type": "write", "path": "b.txt", "content": "读到 ${s1}",
         "next": ""},
    ]}


async def _run_once(container, project: str):
    eng = container.wf_engine(project)
    eng.save(_wf())
    rec = await eng.execute_definition(_wf(), {})
    assert rec.status == "done", rec.error
    return rec


def test_why_route_returns_json(client, container, tmp_path):
    import asyncio
    rec = asyncio.run(_run_once(container, str(tmp_path / "p")))

    r = client.get(f"/api/workflows/runs/{rec.id}/why",
                   params={"project": str(tmp_path / "p")})
    assert r.status_code == 200, r.text[:200]
    body = r.json()
    assert body["query"] == "overview"
    assert {n["node"] for n in body["nodes"]} == {"s1", "s2"}


def test_why_route_node_and_key(client, container, tmp_path):
    import asyncio
    proj = str(tmp_path / "p")
    rec = asyncio.run(_run_once(container, proj))

    d = client.get(f"/api/workflows/runs/{rec.id}/why",
                   params={"project": proj, "node": "s2"}).json()
    assert d["query"] == "node" and "s1" in d["reads"]

    k = client.get(f"/api/workflows/runs/{rec.id}/why",
                   params={"project": proj, "key": "s1"}).json()
    assert k["query"] == "key" and k["readers"] == ["s2"]


def test_why_route_unknown_run_is_404_not_html(client, container, tmp_path):
    r = client.get("/api/workflows/runs/nope/why", params={"project": str(tmp_path)})
    assert r.status_code == 404, r.text[:200]


def test_redo_route_returns_new_run_id(client, container, tmp_path):
    import asyncio
    proj = str(tmp_path / "p")
    rec = asyncio.run(_run_once(container, proj))

    r = client.post(f"/api/workflows/runs/{rec.id}/redo",
                    json={"project": proj, "start_node": "s2", "note": "不满意"})
    assert r.status_code == 200, r.text[:300]
    new_id = r.json()["run_id"]
    pass
    assert new_id and new_id != rec.id

    back = client.get(f"/api/workflows/runs/{new_id}", params={"project": proj}).json()
    assert back["status"] == "done"
    assert any(w.get("code") == "redo" for w in back.get("warnings") or [])
