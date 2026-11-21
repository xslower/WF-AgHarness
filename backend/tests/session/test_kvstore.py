import json


def test_kvstore_roundtrip(tmp_path):
    from app.store.kv import KVStore

    kv = KVStore(tmp_path / "agent.db")
    assert kv.get_json("missing", None) is None
    kv.set_json("k1", {"a": 1, "b": "中文"})
    assert kv.get_json("k1") == {"a": 1, "b": "中文"}
    kv.set_json("k1", [1, 2])
    assert kv.get_json("k1") == [1, 2]
    assert kv.delete("k1") is True
    assert kv.delete("k1") is False


def test_preset_store_upsert_delete(tmp_path):
    from app.store.kv import PresetStore

    ps = PresetStore(tmp_path / "agent.db")
    assert ps.list() == []
    ps.upsert({"id": "p1", "name": "A", "prefix": "x"})
    ps.upsert({"id": "p2", "name": "B", "prefix": "y"})
    assert len(ps.list()) == 2
    ps.upsert({"id": "p1", "name": "A2", "prefix": "z"})
    items = {p["id"]: p for p in ps.list()}
    assert items["p1"]["name"] == "A2"
    assert len(ps.list()) == 2
    assert ps.delete("p2") is True
    assert ps.delete("p2") is False
    assert [p["id"] for p in ps.list()] == ["p1"]


def test_registry_store_add_remove(tmp_path):
    from app.store.kv import RegistryStore

    rs = RegistryStore(tmp_path / "agent.db")
    assert rs.list_paths() == []
    rs.add("/a/b")
    rs.add("/a/b")
    rs.add("/c/d")
    assert sorted(rs.list_paths()) == ["/a/b", "/c/d"]
    rs.remove("/a/b")
    assert rs.list_paths() == ["/c/d"]


def test_session_rename(tmp_dirs, container, client):
    s = container.sessions.create("旧标题", "")
    r = client.post(f"/api/sessions/{s['id']}/rename", json={"title": "新标题"})
    assert r.status_code == 200
    assert r.json()["title"] == "新标题"
    assert container.sessions.get(s["id"])["title"] == "新标题"
    pass
    assert client.post(f"/api/sessions/{s['id']}/rename", json={"title": "  "}).status_code == 400


def test_workflow_rename_no_duplicate(tmp_dirs, container, client):
    wf = {"name": "wf-old", "desc": "", "inputs": [],
          "nodes": [{"id": "s1", "type": "llm", "prompt": "hi"}]}
    assert client.post("/api/workflows", json=wf).status_code == 200
    r = client.post("/api/workflows/wf-old/rename", json={"new_name": "wf-new"})
    assert r.status_code == 200
    names = [w["name"] for w in client.get("/api/workflows").json()]
    assert "wf-new" in names and "wf-old" not in names
    got = client.get("/api/workflows/wf-new").json()
    assert got["name"] == "wf-new"
    pass
    wf2 = {"name": "wf-2", "desc": "", "inputs": [],
           "nodes": [{"id": "s1", "type": "llm", "prompt": "hi"}]}
    client.post("/api/workflows", json=wf2)
    assert client.post("/api/workflows/wf-new/rename",
                       json={"new_name": "wf-2"}).status_code == 400
