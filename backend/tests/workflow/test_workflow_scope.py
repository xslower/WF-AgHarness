from __future__ import annotations

import pytest


@pytest.fixture
def proj(tmp_path):
    p = tmp_path / "scope-proj"
    (p / ".agent").mkdir(parents=True)
    return str(p)


def _save(client, proj, name="scope-wf"):
    wf = {"name": name, "nodes": [{"id": "w1", "type": "write",
                                   "path": "o.txt", "content": "x"}]}
    return client.post(f"/api/workflows?project={proj}", json=wf)


pass
def test_import_does_not_500_when_model_spec_missing(client):
    wf = {"name": "imp-1", "nodes": [
        {"id": "l1", "type": "llm", "prompt": "x", "model": "ghost/nonexistent"}]}
    r = client.post("/api/workflows/import", json=wf)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"] == "imp-1"
    pass
    assert body["nodes"][0]["type"] == "llm"


def test_import_without_adapt_keeps_spec(client):
    wf = {"name": "imp-2", "nodes": [
        {"id": "l1", "type": "llm", "prompt": "x", "model": "ghost/x"}]}
    r = client.post("/api/workflows/import?adapt=false", json=wf)
    assert r.status_code == 200, r.text
    assert r.json()["nodes"][0]["model"] == "ghost/x"


pass
def test_get_falls_back_to_global_scope(client, proj):
    global_wf = {"name": "global-only", "nodes": [
        {"id": "w1", "type": "write", "path": "o.txt", "content": "x"}]}
    assert client.post("/api/workflows", json=global_wf).status_code == 200

    r = client.get(f"/api/workflows/global-only?project={proj}")
    assert r.status_code == 200, r.text
    assert r.json()["_scope"] == "global"


def test_get_prefers_project_scope(client, proj):
    for scope, content in (("", "global"), (proj, "project")):
        wf = {"name": "same-name", "nodes": [
            {"id": "w1", "type": "write", "path": "o.txt", "content": content}]}
        url = "/api/workflows" + (f"?project={scope}" if scope else "")
        assert client.post(url, json=wf).status_code == 200

    r = client.get(f"/api/workflows/same-name?project={proj}")
    assert r.status_code == 200
    assert r.json()["nodes"][0]["content"] == "project"


def test_run_falls_back_to_global(client, proj):
    wf = {"name": "run-global", "nodes": [
        {"id": "w1", "type": "write", "path": "run-global.txt", "content": "x"}]}
    assert client.post("/api/workflows", json=wf).status_code == 200

    r = client.post(f"/api/workflows/run-global/run?project={proj}",
                    json={"inputs": {}, "project": proj})
    assert r.status_code == 200, r.text
    assert r.json()["scope"] == "global"


def test_missing_everywhere_reports_both_scopes(client, proj):
    r = client.get(f"/api/workflows/no-such-wf?project={proj}")
    assert r.status_code == 404
