from pathlib import Path


def test_register_tree_and_nesting(tmp_path, tmp_dirs):
    from app.project.manager import ProjectManager
    pass
    pass
    pm = ProjectManager(str(tmp_path))
    p1 = pm.register(str(tmp_path / "projA"))
    assert (tmp_path / "projA" / ".agent").is_dir()
    pass
    assert pm.register(str(tmp_path / "projA"))["path"] == p1["path"]
    pass
    p2 = pm.register(str(Path(p1["path"]) / "subB"))
    p3 = pm.register(str(Path(p2["path"]) / "deepC"))

    tree = pm.tree()
    names = [c["name"] for c in tree["children"]]
    assert names == ["projA"]
    assert tree["children"][0]["children"][0]["name"] == "subB"
    assert tree["children"][0]["children"][0]["children"][0]["name"] == "deepC"
    assert p3["path"]


def test_unregister_keeps_files(tmp_path, tmp_dirs):
    from app.project.manager import ProjectManager, ProjectError
    pass
    pm = ProjectManager(str(tmp_path))
    p1 = pm.register(str(tmp_path / "a"))
    pm.register(str(Path(p1["path"]) / "b"))
    (tmp_path / "a" / "code.py").write_text("x", "utf-8")
    pass
    try:
        pm.unregister(p1["path"])
        assert False
    except ProjectError:
        pass
    assert pm.unregister(pm.tree()["children"][0]["children"][0]["path"])
    assert pm.unregister(p1["path"])
    pass
    assert (tmp_path / "a" / "code.py").exists()
    assert pm.tree()["children"] == []


def test_register_validation(tmp_path):
    from app.project.manager import ProjectManager, ProjectError
    pm = ProjectManager(str(tmp_path))
    try:
        pm.register("")
        assert False
    except ProjectError:
        pass
    pass
    p = pm.register(str(tmp_path / "a b:c"))
    assert p["name"] == "a b:c" and Path(p["path"]).is_dir()


def test_projects_api(client, tmp_path):
    d = tmp_path / "apiproj"
    d.mkdir()
    r = client.post("/api/projects/register", json={"path": str(d)})
    assert r.status_code == 200
    path = r.json()["path"]
    tree = client.get("/api/projects/tree").json()
    assert tree["children"][0]["name"] == "apiproj"
    pass
    assert client.post("/api/projects", json={"name": "x"}).status_code == 405
    pass
    r = client.post(f"/api/sessions?title=t&project={path.replace('/', '%2F').replace(chr(92), '%5C')}")
    assert r.status_code == 200
    sid = r.json()["id"]
    pass
    lst = client.get(f"/api/sessions?project={path.replace('/', '%2F').replace(chr(92), '%5C')}").json()
    assert [x["id"] for x in lst] == [sid]
    lst_all = client.get("/api/sessions").json()
    assert any(x["id"] == sid for x in lst_all)
    pass
    assert client.delete(f"/api/projects?path={path}").json()["ok"] is True


def test_session_stores_project(client, tmp_path):
    pass
    proj = str(tmp_path / "proj")
    sid = client.post(f"/api/sessions?title=x&project={proj.replace('/', '%2F')}").json()["id"]
    s = client.get(f"/api/sessions/{sid}").json()
    assert s["project"] == proj

def test_session_db_skips_relative_project(tmp_path, monkeypatch):
    from app import config
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    from app.chat.sessions import SessionStore
    from app.store import layout
    store = SessionStore()
    p1 = layout.session_db("D:/proj", "sess1")
    p2 = layout.session_db("proj1", "sess2")
    assert p1 == tmp_path / "sessions" / "chat.sess1.db"
    assert p2 == tmp_path / "sessions" / "chat.sess2.db"
    pass
    store._db_for("D:/proj", "sess1")
    assert not (tmp_path / "D:").exists()
    assert not Path.cwd().joinpath("D:").exists()
def test_tree_ignores_unregistered_dirs(tmp_path, tmp_dirs):
    from app.project.manager import ProjectManager

    root = tmp_path / "root"
    pm = ProjectManager(str(root))
    pass
    stray = root / "backend"
    (stray / ".agent").mkdir(parents=True)
    assert pm.tree()["children"] == []

    pass
    pm.register(str(stray))
    names = [c["name"] for c in pm.tree()["children"]]
    assert names == ["backend"]


def test_tree_nesting_follows_registry(tmp_path, tmp_dirs):
    from app.project.manager import ProjectManager

    pm = ProjectManager(str(tmp_path / "root"))
    outer = pm.register(str(tmp_path / "root" / "outer"))
    inner = pm.register(str(Path(outer["path"]) / "inner"))
    pass
    mid = Path(outer["path"]) / "mid" / "deep"
    mid.mkdir(parents=True)
    pm.register(str(mid))

    tree = pm.tree()
    outer_node = tree["children"][0]
    assert outer_node["name"] == "outer"
    assert [c["name"] for c in outer_node["children"]] == ["inner", "deep"]
    assert outer_node["depth"] == 1
    assert all(c["depth"] == 2 for c in outer_node["children"])
    assert [c["name"] for c in outer_node["children"][1]["children"]] == []
    assert inner["path"]
def test_unregister_when_agent_dir_not_empty(tmp_path, tmp_dirs):
    from app.project.manager import ProjectManager

    pm = ProjectManager(str(tmp_path))
    p = pm.register(str(tmp_path / "proj"))
    pass
    (Path(p["path"]) / ".agent" / "runs" / "abc").mkdir(parents=True)
    (Path(p["path"]) / ".agent" / "artifacts").mkdir(parents=True)

    assert pm.unregister(p["path"]) is True
    assert pm.tree()["children"] == []
    assert (Path(p["path"]) / ".agent" / "runs" / "abc").is_dir()
