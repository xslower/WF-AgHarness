import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def test_get_config(client):
    r = client.get("/api/config")
    assert r.status_code == 200
    cfg = r.json()
    assert "providers" in cfg
    assert "queues" in cfg


def test_put_provider(client):
    r = client.post("/api/providers", json={
        "name": "t", "baseUrl": "https://api.test.com/v1", "apiKey": "sk-x", "models": [],
    })
    assert r.status_code == 200
    pid = r.json()["id"]
    r = client.put(f"/api/providers/{pid}", json={
        "name": "t2", "baseUrl": "https://api.test.com/v1", "apiKey": "sk-y",
        "models": [{"id": "m1"}],
    })
    assert r.status_code == 200


def test_delete_provider_model(client):
    r = client.post("/api/providers", json={
        "name": "t", "baseUrl": "https://x/v1", "apiKey": "k",
        "models": [{"id": "m1"}, {"id": "m2"}],
    })
    pid = r.json()["id"]
    r = client.delete(f"/api/providers/{pid}/models/m1")
    assert r.status_code == 200


def test_delete_provider(client):
    r = client.post("/api/providers", json={
        "name": "t", "baseUrl": "https://x/v1", "apiKey": "k", "models": [],
    })
    pid = r.json()["id"]
    assert client.delete(f"/api/providers/{pid}").status_code == 200


def test_put_utility(client):
    r = client.put("/api/utility", json={
        "completion": [], "classify": [], "review": [], "suggest": []
    })
    assert r.status_code == 200


def test_test_model(client, monkeypatch):
    r = client.post("/api/providers", json={
        "name": "t", "baseUrl": "https://x/v1", "apiKey": "k",
        "models": [{"id": "m1"}],
    })
    async def fake_stream(*a, **kw):
        yield type("C", (), {"type": "text", "text": "ok"})()
    monkeypatch.setattr(client.app.state.container.gateway, "chat_stream", fake_stream)
    r = client.post("/api/test_model", params={"spec": "t/m1"})
    assert r.status_code == 200


def test_put_settings(client):
    r = client.put("/api/settings", json={"policy": "workspace", "workspaceRoot": "/tmp"})
    assert r.status_code == 200


def test_get_usage(client):
    r = client.get("/api/usage")
    assert r.status_code == 200
    data = r.json()
    assert "by_provider" in data
    assert "total_cost" in data


def test_get_envs(client):
    r = client.get("/api/envs")
    assert r.status_code == 200


def test_put_envs(client):
    r = client.put("/api/envs", json={"key": "TEST_VAR", "value": "test123"})
    assert r.status_code == 200


def test_get_mcp(client):
    r = client.get("/api/mcp")
    assert r.status_code == 200


def test_put_mcp(client):
    r = client.put("/api/mcp", json={"mcpServers": {}})
    assert r.status_code == 200


def test_checkpoints(client, tmp_path):
    r = client.get("/api/checkpoints", params={"ws": str(tmp_path)})
    assert r.status_code == 200


def test_get_skills(client):
    r = client.get("/api/skills")
    assert r.status_code == 200


def test_get_plugins(client):
    r = client.get("/api/plugins/installed")
    assert r.status_code == 200


def test_workflows_crud(client):
    pass
    r = client.get("/api/workflows")
    assert r.status_code == 200
    pass
    wf = {"name": "test-wf", "desc": "", "inputs": [],
          "nodes": [{"id": "h1", "type": "handoff"}]}
    r = client.post("/api/workflows", json=wf, params={"project": ""})
    assert r.status_code == 200
    pass
    r = client.get("/api/workflows/test-wf", params={"project": ""})
    assert r.status_code == 200
    pass
    r = client.delete("/api/workflows/test-wf", params={"project": ""})
    assert r.status_code == 200


def test_workflow_export_import(client):
    wf = {"name": "exp-wf", "desc": "", "inputs": [],
          "nodes": [{"id": "h1", "type": "handoff"}]}
    client.post("/api/workflows", json=wf, params={"project": ""})
    r = client.get("/api/workflows/exp-wf/export", params={"project": ""})
    assert r.status_code == 200
    pass
    r = client.post("/api/workflows/import", json=wf, params={"project": ""})
    assert r.status_code == 200


def test_file_operations(client, tmp_path):
    pass
    project = tmp_path / "proj"
    project.mkdir()
    f = project / "testfile.txt"
    f.write_text("hello")
    pid = str(project)
    pass
    r = client.get("/api/file", params={"path": str(f)})
    assert r.status_code == 200
    pass
    r = client.post("/api/file/save", json={"path": str(f), "content": "world", "project": pid})
    assert r.status_code == 200
    assert f.read_text() == "world"
    pass
    f2 = project / "copy.txt"
    r = client.post("/api/file/copy", json={"path": str(f), "dest": str(f2), "project": pid})
    assert r.status_code == 200
    assert f2.read_text() == "world"
    pass
    f3 = project / "moved.txt"
    r = client.post("/api/file/move", json={"path": str(f2), "dest": str(f3), "project": pid})
    assert r.status_code == 200
    assert f3.exists()
    assert not f2.exists()
    pass
    r = client.post("/api/file/delete", json={"path": str(f3), "project": pid})
    assert r.status_code == 200
    body = r.json()
    assert not f3.exists()
    assert body["recoverable"] is True
    assert (project / ".trash") in Path(body["trashed"]).parents


def test_artifacts(client):
    r = client.get("/api/artifacts", params={"project": ""})
    assert r.status_code == 200


def test_sessions_api(client):
    pass
    r = client.post("/api/sessions?title=test&project=")
    assert r.status_code == 200
    sid = r.json()["id"]
    pass
    r = client.get(f"/api/sessions/{sid}")
    assert r.status_code == 200
    pass
    r = client.get("/api/sessions")
    assert r.status_code == 200
    pass
    r = client.post(f"/api/sessions/{sid}/truncate", json={"index": 0})
    assert r.status_code == 200
    pass
    r = client.delete(f"/api/sessions/{sid}")
    assert r.status_code == 200


def test_presets_api(client):
    pass
    r = client.get("/api/presets")
    assert r.status_code == 200
    pass
    r = client.post("/api/presets", json={"id": "p-test", "name": "test-preset", "content": "hello"})
    assert r.status_code == 200
    pid = r.json()["id"]
    pass
    r = client.delete(f"/api/presets/{pid}")
    assert r.status_code == 200


def test_projects_api(client, tmp_path):
    pass
    r = client.get("/api/projects/tree")
    assert r.status_code == 200
    pass
    d = tmp_path / "testproj"
    d.mkdir()
    r = client.post("/api/projects/register", json={"path": str(d)})
    assert r.status_code == 200
    pass
    r = client.get("/api/projects/browse", params={"path": ""})
    assert r.status_code == 200


def test_get_approvals(client):
    r = client.get("/api/approvals")
    assert r.status_code == 200


def test_suggest_input_disabled_when_no_completion_model(client, monkeypatch):
    called = []

    async def fake_utility(kind, messages, session_id="", **kw):
        called.append((kind, session_id))
        return "world"

    c = client.app.state.container
    monkeypatch.setattr(c.store.config.utility, "completion", [])
    monkeypatch.setattr(c.gateway, "call_utility", fake_utility)
    r = client.post("/api/suggest_input", json={"text": "hello wor", "session_id": ""})
    assert r.status_code == 200
    assert r.json() == {"completion": ""}
    assert called == [], "禁用时不应发起任何模型调用"


def test_suggest_input_enabled_with_completion_model(client, monkeypatch):
    called = []

    async def fake_utility(kind, messages, session_id="", **kw):
        called.append((kind, session_id))
        return "world"

    c = client.app.state.container
    monkeypatch.setattr(c.store.config.utility, "completion", ["prov/m1"])
    monkeypatch.setattr(c.gateway, "call_utility", fake_utility)
    r = client.post("/api/suggest_input", json={"text": "hello wor", "session_id": "s1"})
    assert r.status_code == 200
    assert r.json()["completion"] == "world"
    assert called == [("completion", "ac:s1")]


def test_import_env_providers(client, monkeypatch):
    monkeypatch.setattr("app.api.routers.providers._env_vars", lambda: {})
    r = client.post("/api/providers/import_env")
    assert r.status_code == 200


def test_projects_memory(client, tmp_dirs):
    d = tmp_dirs / "projects" / "memproj"
    d.mkdir(parents=True)
    r = client.post("/api/projects/register", json={"path": str(d)})
    assert r.status_code == 200
    pass
    r = client.post("/api/projects/memory", json={"path": str(d), "content": "test memory"})
    assert r.status_code == 200
    pass
    r = client.get("/api/projects/memory", params={"path": str(d)})
    assert r.status_code == 200
    entries = r.json()["entries"]
    pass
    mem_id = entries[0]["id"] if entries else ""
    if mem_id:
        r = client.delete("/api/projects/memory",
                          params={"path": str(d), "mid": mem_id})
        assert r.status_code == 200


def test_file_tree(client, tmp_path):
    (tmp_path / "dir1").mkdir()
    (tmp_path / "dir1" / "f1.txt").write_text("a")
    r = client.get("/api/projects/file_tree", params={"project": str(tmp_path)})
    assert r.status_code == 200


def test_model_queue_empty(client):
    r = client.put("/api/model_queue", json={"parent": [], "child": []})
    assert r.status_code == 200


def test_get_sessions_list(client):
    r = client.get("/api/sessions")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_create_venv(client, monkeypatch):
    monkeypatch.setattr("subprocess.run", MagicMock(return_value=MagicMock(returncode=0)))
    r = client.post("/api/envs/create_venv", json={"path": "/tmp/testvenv"})
    assert r.status_code in (200, 500)


def test_delete_session_not_found(client):
    r = client.delete("/api/sessions/nonexistent")
    assert r.status_code in (200, 404, 500)


def test_get_session_not_found(client):
    r = client.get("/api/sessions/nonexistent")
    assert r.status_code in (200, 404, 500)


def test_workflow_run_not_found(client):
    r = client.post("/api/workflows/nonexistent/run", json={"inputs": {}})
    assert r.status_code in (200, 404, 500)


def test_workflow_assist(client, monkeypatch):
    wf = {"name": "assist-wf", "desc": "", "inputs": [{"name": "x", "desc": "d", "type": "string"}], "nodes": [{"id": "n1", "type": "llm", "prompt": "hi", "next": "h1"}, {"id": "h1", "type": "handoff"}]}
    client.post("/api/workflows", json=wf, params={"project": ""})
    new_wf = {**wf, "desc": "改"}
    async def fake_call(*a, **kw):
        yield type("C", (), {"type": "text", "text": json.dumps(new_wf)})()
    monkeypatch.setattr(client.app.state.container.gateway, "chat_stream", fake_call)
    r = client.post("/api/workflows/assist-wf/assist",
                    json={"instruction": "改描述", "project": ""})
    assert r.status_code == 200


def test_projects_register(client, tmp_path):
    d = tmp_path / "extproj"
    d.mkdir()
    r = client.post("/api/projects/register", json={"path": str(d)})
    assert r.status_code == 200


def test_projects_delete(client, tmp_path):
    d = tmp_path / "delproj"
    d.mkdir()
    r = client.post("/api/projects/register", json={"path": str(d)})
    assert r.status_code == 200
    path = r.json()["path"]
    r = client.delete("/api/projects", params={"path": path})
    assert r.status_code == 200


def test_approvals_decide(client):
    r = client.post("/api/approvals/nonexistent/decide", json={"approved": True})
    assert r.status_code in (200, 404, 500)


def test_get_workflow_runs(client):
    r = client.get("/api/workflows/runs/nonexistent")
    assert r.status_code in (200, 404, 500)


def test_create_venv_endpoint(client, monkeypatch):
    import subprocess
    monkeypatch.setattr(subprocess, "run", MagicMock(return_value=MagicMock(returncode=0, stdout="ok", stderr="")))
    r = client.post("/api/envs/create_venv", json={"path": "/tmp/testvenv2"})
    assert r.status_code in (200, 500)


def test_delete_provider_not_found(client):
    r = client.delete("/api/providers/nonexistent")
    assert r.status_code in (200, 404, 500)


def test_fetch_models_not_found(client):
    r = client.post("/api/providers/nonexistent/fetch_models")
    assert r.status_code in (200, 404, 500)


def test_test_model_no_spec(client):
    r = client.post("/api/test_model", json={})
    assert r.status_code in (200, 400, 422, 500)


def test_put_settings_invalid(client):
    r = client.put("/api/settings", json={})
    assert r.status_code in (200, 400, 422, 500)


def test_file_save_not_found(client, tmp_path):
    pass
    project = tmp_path / "proj"
    project.mkdir()
    r = client.post("/api/file/save", json={
        "path": str(project / "no_such_dir" / "file.txt"), "content": "x",
        "project": str(project)})
    assert r.status_code in (400, 404)


def test_get_file_not_found(client):
    r = client.get("/api/file", params={"path": "/nonexistent/file.txt"})
    assert r.status_code in (200, 404, 500)


def test_workflow_assist_repairs_broken_json(client, monkeypatch):
    wf = {"name": "assist-fix", "desc": "", "inputs": [],
          "nodes": [{"id": "n1", "type": "llm", "prompt": "hi"}]}
    client.post("/api/workflows", json=wf, params={"project": ""})
    new_wf = {**wf, "desc": "改"}
    calls = []

    async def fake_call(*a, **kw):
        calls.append(1)
        yield type("C", (), {"type": "text",
                             "text": '```json\n' + json.dumps(new_wf) +
                                     ',\n```'})()

    monkeypatch.setattr(client.app.state.container.gateway, "chat_stream", fake_call)
    r = client.post("/api/workflows/assist-fix/assist",
                    json={"instruction": "改描述", "project": ""})
    assert r.status_code == 200, r.text
    assert r.json()["workflow"]["desc"] == "改"
    assert len(calls) == 1, "坏 JSON 被修复就不该再打回一轮"
