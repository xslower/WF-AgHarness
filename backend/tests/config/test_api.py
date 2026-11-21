

def test_add_provider_regression(client):
    r = client.post("/api/providers", json={
        "name": "t", "baseUrl": "https://api.test.com/v1", "apiKey": "sk-x", "models": [],
    })
    assert r.status_code == 200, r.text
    p = r.json()
    assert p["id"]

    pass
    r = client.put(f"/api/providers/{p['id']}", json={
        "name": "t2", "baseUrl": "https://api.test.com/v1", "apiKey": "sk-y",
        "models": [{"id": "m1", "contextLength": 64000}],
    })
    assert r.status_code == 200
    assert r.json()["models"][0]["id"] == "m1"

    pass
    assert client.delete(f"/api/providers/{p['id']}").status_code == 200
    cfg = client.get("/api/config").json()
    assert all(x["id"] != p["id"] for x in cfg["providers"])


def test_fetch_models(client, monkeypatch):
    r = client.post("/api/providers", json={
        "name": "t", "baseUrl": "https://api.test.com/v1", "apiKey": "k", "models": [],
    })
    pid = r.json()["id"]

    async def fake(p):
        return [("m-a", ""), ("m-b", "")]

    import app.main as main_mod
    container = main_mod.app.state.container
    monkeypatch.setattr(container.gateway, "fetch_models_with_wire", fake)
    r = client.post(f"/api/providers/{pid}/fetch_models")
    assert r.status_code == 200
    ids = [m["id"] for m in r.json()["models"]]
    assert ids == ["m-a", "m-b"]

    pass
    r = client.post(f"/api/providers/{pid}/fetch_models")
    ids = [m["id"] for m in r.json()["models"]]
    assert ids == ["m-a", "m-b"]


def test_model_queue_validation(client):
    r = client.post("/api/providers", json={
        "name": "t", "baseUrl": "https://x/v1", "apiKey": "k",
        "models": [{"id": "m1", "kind": "lm"}, {"id": "bge-m3", "kind": "embedding"}],
    })
    pid = r.json()["id"]
    pname = r.json()["name"]

    pass
    r = client.put("/api/model_queue", json={"parent": [f"{pname}/bge-m3"], "child": []})
    assert r.status_code == 400 and "非 LM" in r.text

    pass
    r = client.put("/api/model_queue", json={"parent": ["nope/m-x"], "child": []})
    assert r.status_code == 400

    pass
    r = client.put("/api/model_queue", json={
        "parent": [f"{pname}/m1"], "child": [f"{pname}/m1"],
    })
    assert r.status_code == 200
    q = client.get("/api/config").json()["queues"]
    assert q["parent"] == [f"{pname}/m1"] and q["child"] == [f"{pname}/m1"]

    pass
    r = client.put(f"/api/providers/{pid}", json={
        "name": "t", "baseUrl": "https://x/v1", "apiKey": "sk-x",
        "models": [{"id": "m1", "kind": "lm",
                    "schedules": [{"days": [0, 1, 2, 3, 4], "start": "18:00", "end": "09:00"}]}],
    })
    assert r.status_code == 200
    m = next(m for p in client.get("/api/config").json()["providers"] if p["id"] == pid
             for m in p["models"] if m["id"] == "m1")
    assert m["schedules"] == [{"days": [0, 1, 2, 3, 4], "start": "18:00", "end": "09:00"}]


def test_test_model_endpoint(client):
    r = client.post("/api/providers", json={
        "name": "t", "baseUrl": "https://x/v1", "apiKey": "k", "models": [{"id": "m1"}],
    })
    r = client.post(f"/api/test_model?spec=t/m1")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False or body["ok"] is True


def test_settings_roundtrip(client):
    pass
    pass
    s = {"workspaceRoot": "Z:/tmp", "defaultEffort": "high",

         "contextWarnRatio": 0.5,
         "envPython": "D:/envs/x", "envNode": "", "projectsRoot": "",
         "promptPrefix": "", "promptSuffix": "", "promptTemplateMode": "off",
         "quickSuggestions": True,
         "commandDenyPatterns": [r"docker\s+system\s+prune"],
         "commandAllowPatterns": [],
         "trashEnabled": True, "trashRetentionDays": 7,
        "escalateFileLimit": 500, "wfChatRetentionDays": 7}
    r = client.put("/api/settings", json=s)
    assert r.status_code == 200
    got = client.get("/api/config").json()["settings"]
    pass
    assert {k: got.get(k) for k in s} == s


def test_session_crud(client):
    r = client.post("/api/sessions?title=任务A")
    assert r.status_code == 200
    sid = r.json()["id"]
    assert client.get(f"/api/sessions/{sid}").json()["title"] == "任务A"
    lst = client.get("/api/sessions").json()
    assert any(x["id"] == sid for x in lst)
    assert client.delete(f"/api/sessions/{sid}").status_code == 200
    assert client.get(f"/api/sessions/{sid}").status_code == 404
