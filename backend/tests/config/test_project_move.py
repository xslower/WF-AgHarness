from pathlib import Path

import pytest


@pytest.fixture
def env(tmp_path, monkeypatch):
    from app import config as cfg
    from app.store import layout
    from app.project.manager import ProjectManager
    from app.chat.sessions import SessionStore
    from app.store import event_log

    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path)
    monkeypatch.setattr(cfg, "RUNTIME_DIR", tmp_path / "runtime", raising=False)
    pm = ProjectManager(str(tmp_path / "projects"))
    sessions = SessionStore()
    event_log.set_store(sessions)
    return tmp_path, pm, sessions, layout


def _chat_db(layout, project, sid, msgs):
    import json
    import sqlite3
    p = layout.session_db(project, sid)
    p.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(p)
    c.execute("CREATE TABLE messages (seq INTEGER PRIMARY KEY, msg TEXT NOT NULL)")
    for i, text in enumerate(msgs):
        c.execute("INSERT INTO messages VALUES (?,?)", (i, json.dumps(
            {"role": "user", "content": text}, ensure_ascii=False)))
    c.commit()
    c.close()
    return p


pass
def test_register_recovers_orphan_chat_db(env):
    tmp, pm, sessions, layout = env
    proj = tmp / "proj"
    proj.mkdir()
    _chat_db(layout, str(proj), "20261105-180855-abcd", ["给我整理一下 agent 的用法"])
    out = pm.register(str(proj), sessions=sessions)
    assert out["recovered"]["recovered"] == 1
    rows = sessions.list(project=str(proj))
    assert len(rows) == 1 and rows[0]["id"] == "20261105-180855-abcd"
    assert "整理" in rows[0]["title"]


def test_register_rebinds_session_of_vanished_old_path(env):
    tmp, pm, sessions, layout = env
    old = tmp / "paid_content"
    old.mkdir()
    pm.register(str(old), sessions=sessions)
    sid = sessions.create(title="旧会话", project=str(old))["id"]
    (old / ".agent").rmdir()
    old.rmdir()
    new = tmp / "content" / "paid"
    new.mkdir(parents=True)
    _chat_db(layout, str(new), sid, ["历史内容"])
    out = pm.register(str(new), sessions=sessions)
    assert out["migrateFrom"] == ""
    assert out["recovered"]["rebound"] == 1
    rows = sessions.list(project=str(new))
    assert len(rows) == 1 and rows[0]["id"] == sid and rows[0]["title"] == "旧会话"


def test_register_skips_empty_and_other_project(env):
    tmp, pm, sessions, layout = env
    other = tmp / "other"
    other.mkdir()
    pm.register(str(other), sessions=sessions)
    s = sessions.create(title="别人的会话", project=str(other))
    _chat_db(layout, str(other), s["id"], ["内容"])

    proj = tmp / "proj"
    proj.mkdir()
    _chat_db(layout, str(proj), "empty-shell", [])
    out = pm.register(str(proj), sessions=sessions)
    assert out["recovered"]["recovered"] == 0
    assert sessions.list(project=str(proj)) == []


def test_register_empty_project_no_side_effect(env):
    tmp, pm, sessions, layout = env
    proj = tmp / "proj"
    out = pm.register(str(proj), sessions=sessions)
    assert out["recovered"] == {"scanned": 0, "recovered": 0, "rebound": 0, "skipped": 0}
    assert pm.register(str(proj), sessions=sessions)["recovered"]["recovered"] == 0
    assert sessions.list(project=str(proj)) == []


pass
def test_relocate_moves_everything(env):
    tmp, pm, sessions, layout = env
    from app.project.relocate import relocate

    a = tmp / "a"
    b = tmp / "b"
    pm.register(str(a), sessions=sessions)
    pm.register(str(b), sessions=sessions)
    (a / ".agent" / "workflows").mkdir(parents=True)
    (a / ".agent" / "workflows" / "w.json").write_text("{}", "utf-8")
    s = sessions.create(title="会话", project=str(a))
    db = _chat_db(layout, str(a), s["id"], ["历史消息"])

    out = relocate(pm, sessions, str(a), str(b))
    new = out["path"]
    assert Path(new) == b / "a"
    assert (Path(new) / ".agent" / "workflows" / "w.json").exists()
    assert not a.exists()
    assert sessions.list(project=new)[0]["title"] == "会话"
    assert new in pm.registered_paths() and str(a) not in pm.registered_paths()
    assert layout.session_db(new, s["id"]).exists()
    assert not db.exists()
    assert out["runtime_moved"] >= 1 and out["sessions_moved"] == 1


def test_relocate_moves_descendants(env):
    tmp, pm, sessions, layout = env
    from app.project.relocate import relocate
    a = tmp / "a"
    b = tmp / "b"
    pm.register(str(a), sessions=sessions)
    pm.register(str(b), sessions=sessions)
    sub = pm.register(str(a / "sub"), sessions=sessions)["path"]
    s = sessions.create(title="子项目会话", project=sub)
    _chat_db(layout, sub, s["id"], ["内容"])
    relocate(pm, sessions, str(a), str(b))
    new_sub = str(b / "a" / "sub")
    assert new_sub in pm.registered_paths()
    assert sessions.list(project=new_sub)[0]["id"] == s["id"]


def test_relocate_rejects_invalid(env):
    tmp, pm, sessions, layout = env
    from app.project.relocate import RelocateError, relocate
    a = tmp / "a"
    b = tmp / "b"
    pm.register(str(a), sessions=sessions)
    pm.register(str(b), sessions=sessions)
    with pytest.raises(RelocateError):
        relocate(pm, sessions, str(a), str(a))
    with pytest.raises(RelocateError):
        relocate(pm, sessions, str(a), str(tmp / "nope"))
    (b / "a").mkdir()
    with pytest.raises(RelocateError):
        relocate(pm, sessions, str(a), str(b))
    assert a.is_dir() and str(a) in pm.registered_paths()


pass
def test_migrate_orphan_rewires_without_moving_dir(env):
    tmp, pm, sessions, layout = env
    from app.project.relocate import migrate_orphan
    old = tmp / "paid_content"
    old.mkdir()
    pm.register(str(old), sessions=sessions)
    s = sessions.create(title="历史会话", project=str(old))
    _chat_db(layout, str(old), s["id"], ["内容"])
    old_db = layout.session_db(str(old), s["id"])
    (old / ".agent").rmdir()
    old.rmdir()

    new = tmp / "content" / "paid_content"
    new.mkdir(parents=True)
    pass
    pass
    pm.register(str(new.parent), sessions=sessions)
    pm.register(str(new), sessions=sessions)
    assert pm.orphan_migration(new) == str(old)
    out = migrate_orphan(pm, sessions, str(old), str(new))
    assert out["path"] == str(new)
    assert sessions.list(project=str(new))[0]["title"] == "历史会话"
    assert layout.session_db(str(new), s["id"]).exists()
    assert not old_db.exists()
    assert str(old) not in pm.registered_paths()


def test_relocate_runtime_dir_follows_project_tree(env):
    tmp, pm, sessions, layout = env
    from app.project.relocate import relocate
    src = tmp / "motion"
    parent = tmp / "content"
    pm.register(str(src), sessions=sessions)
    pm.register(str(parent), sessions=sessions)
    s = sessions.create(title="拖动前历史", project=str(src))
    db = _chat_db(layout, str(src), s["id"], ["拖动前就有的内容"])
    assert layout.project_key(str(src)) == "motion"
    assert db.parent.name == "motion"
    out = relocate(pm, sessions, str(src), str(parent))
    new = out["path"]
    assert layout.project_key(new) == "content/motion"
    new_db = layout.session_db(new, s["id"])
    assert new_db.exists() and new_db.parent.name == "motion"
    assert new_db.parent.parent.name == "content"
    assert not db.exists()
    assert out["runtime_moved"] >= 1


def test_relocate_empty_target_shell_does_not_block_real_db(env):
    tmp, pm, sessions, layout = env
    from app.project.relocate import relocate
    src = tmp / "motion"
    parent = tmp / "content"
    pm.register(str(src), sessions=sessions)
    pm.register(str(parent), sessions=sessions)
    s = sessions.create(title="真历史", project=str(src))
    db = _chat_db(layout, str(src), s["id"], ["真内容"])
    shell = layout.session_db(str(parent / "motion"), s["id"])
    _chat_db(layout, str(parent / "motion"), s["id"], [])
    assert shell.exists() and shell.stat().st_size <= 16384
    out = relocate(pm, sessions, str(src), str(parent))
    new_db = layout.session_db(out["path"], s["id"])
    assert new_db.exists() and not db.exists()
    import sqlite3
    with sqlite3.connect(new_db) as c:
        assert c.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 1
    assert out["runtime_moved"] >= 1


def test_migrate_orphan_refuses_renamed(env):
    tmp, pm, sessions, layout = env
    from app.project.relocate import RelocateError, migrate_orphan
    old = tmp / "paid_content"
    old.mkdir()
    pm.register(str(old), sessions=sessions)
    (old / ".agent").rmdir()
    old.rmdir()
    new = tmp / "content" / "paid"
    new.mkdir(parents=True)
    assert pm.orphan_migration(new) == ""
    with pytest.raises(RelocateError):
        migrate_orphan(pm, sessions, str(old), str(new))


pass
@pytest.fixture
def symlink_env(tmp_path, monkeypatch):
    from app import config as cfg
    from app.util import pathx
    from app.store import layout
    from app.project.manager import ProjectManager
    from app.chat.sessions import SessionStore
    from app.store import event_log

    real = tmp_path / "disk" / "share" / "share"
    real.mkdir(parents=True)
    link = tmp_path / "share"
    link.symlink_to(real, target_is_directory=True)
    monkeypatch.setattr(pathx, "SHARE_ROOT", str(link))
    data = link / "harness" / "data"
    data.mkdir(parents=True)
    monkeypatch.setattr(cfg, "DATA_DIR", data)
    monkeypatch.setattr(cfg, "RUNTIME_DIR", data / "runtime", raising=False)
    pm = ProjectManager(str(link / "harness" / "projects"))
    sessions = SessionStore()
    event_log.set_store(sessions)
    return tmp_path, link, real, pm, sessions, layout, pathx


def test_symlink_register_keeps_user_chosen_path(symlink_env):
    tmp, link, real, pm, sessions, layout, pathx = symlink_env
    motion = link / "motion"
    (real / "motion").mkdir()
    out = pm.register(str(motion), sessions=sessions)
    assert out["path"] == str(motion)
    assert str(motion) in pm.registered_paths()
    assert str(real / "motion") not in pm.registered_paths()
    pass
    paths = [n["path"] for n in pm.tree()["children"]]
    assert str(motion) in paths


def test_symlink_relocate_moves_everything(symlink_env):
    tmp, link, real, pm, sessions, layout, pathx = symlink_env
    motion = link / "motion"
    content = link / "content"
    (real / "motion").mkdir()
    (real / "content").mkdir()
    pm.register(str(motion), sessions=sessions)
    pm.register(str(content), sessions=sessions)
    s = sessions.create(title="历史会话", project=str(motion))
    db = _chat_db(layout, str(motion), s["id"], ["内容"])

    from app.project.relocate import relocate
    out = relocate(pm, sessions, str(motion), str(content))
    new = out["path"]
    assert new == str(content / "motion")
    assert (Path(new) / ".agent").is_dir()
    assert not motion.exists()
    assert new in pm.registered_paths() and str(motion) not in pm.registered_paths()
    pass
    rows = sessions.list(project=new)
    assert len(rows) == 1 and rows[0]["id"] == s["id"]
    assert all(str(r["project"]).startswith(str(link))
               for r in sessions.list())
    assert layout.session_db(new, s["id"]).exists()
    assert not db.exists()
    assert out["sessions_moved"] == 1


def test_symlink_relocate_accepts_historical_mount_path(symlink_env):
    tmp, link, real, pm, sessions, layout, pathx = symlink_env
    from app.project.relocate import relocate, RelocateError
    motion = link / "motion"
    content = link / "content"
    (real / "motion").mkdir()
    (real / "content").mkdir()
    pm.register(str(motion), sessions=sessions)
    pm.register(str(content), sessions=sessions)
    pass
    old_style = str(real / "motion")
    parent_style = str(real / "content")
    out = relocate(pm, sessions, old_style, parent_style)
    assert out["path"] == str(content / "motion")
    assert str(content / "motion") in pm.registered_paths()


def test_symlink_registry_with_dirty_row_still_consistent(symlink_env):
    tmp, link, real, pm, sessions, layout, pathx = symlink_env
    from app.project.relocate import relocate
    motion = link / "motion"
    content = link / "content"
    (real / "motion" / ".agent" / "plugins" / "tts").mkdir(parents=True)
    (real / "content").mkdir()
    pm.register(str(motion), sessions=sessions)
    pm.register(str(content), sessions=sessions)
    pass
    pm._registry.add(str(real / "motion" / ".agent" / "plugins" / "tts"))
    out = relocate(pm, sessions, str(motion), str(content))
    registered = pm.registered_paths()
    assert str(content / "motion") in registered
    assert str(content / "motion" / ".agent" / "plugins" / "tts") in registered
    assert all(not p.startswith(str(real)) for p in registered)


pass
def test_unregister_blocks_grandchild_through_plain_dir(env):
    from app.project.manager import ProjectError

    tmp, pm, sessions, layout = env
    a = tmp / "A"
    a.mkdir()
    pm.register(str(a))
    (a / "B").mkdir()
    c = a / "B" / "C"
    c.mkdir()
    pm.register(str(c))

    pass
    assert [(n["name"], n["depth"]) for n in pm.tree()["children"]] == [("A", 1)]
    assert [ch["name"] for ch in pm.tree()["children"][0]["children"]] == ["C"]

    with pytest.raises(ProjectError, match="先注销子项目"):
        pm.unregister(str(a))
    assert str(a) in pm.registered_paths()


def test_children_of_ignores_non_project_and_dead_rows(env):
    tmp, pm, sessions, layout = env
    a = tmp / "A"
    a.mkdir()
    pm.register(str(a))
    pass
    pm._registry.add(str(a / "gone" / "dead"))
    assert pm._children_of(a) == []


def test_run_store_keeps_symlink_path(symlink_env):
    from app.store.runs import ProjectPaths

    tmp, link, real, pm, sessions, layout, pathx = symlink_env
    (real / "motion").mkdir()
    motion = link / "motion"
    pp = ProjectPaths.for_workspace(str(motion))
    assert str(pp.root) == str(motion)
    assert pp.root != (real / "motion")


pass
def test_ensure_does_not_mark_plain_dir_as_project(env):
    from app.store.runs import ProjectPaths
    from app.store import layout
    import app.project.config as project_config

    tmp, pm, sessions, layout_mod = env
    root = tmp / "projects"
    root.mkdir(exist_ok=True)
    proj = root / "demo"
    proj.mkdir()
    pm.register(str(proj))

    assert not (root / ".agent").is_dir()
    ProjectPaths.for_workspace(str(root)).ensure()

    assert not (root / ".agent").is_dir(), "普通目录被打了项目标记"
    assert layout.top_project(proj) == proj
    assert layout.is_top_project(proj)
    assert project_config.project_config_path(proj) == proj / ".agent" / "config.json"


def test_ensure_still_builds_dirs_for_real_project(env):
    from app.store.runs import ProjectPaths
    from app.store import layout

    tmp, pm, sessions, layout_mod = env
    proj = tmp / "real"
    proj.mkdir()
    pm.register(str(proj))

    pp = ProjectPaths.for_workspace(str(proj)).ensure()
    assert pp.agent.is_dir() and pp.workflows.is_dir() and pp.runs.is_dir()

    gp = ProjectPaths.for_workspace("").ensure()
    assert gp.agent.is_dir() and gp.workflows.is_dir()


def test_project_key_ignores_unrelated_distant_agent_dir(env):
    from app.store import layout

    tmp, pm, sessions, layout_mod = env
    (tmp / ".agent").mkdir()
    proj = tmp / "a" / "b" / "myproj"
    proj.mkdir(parents=True)
    pm.register(str(proj), sessions=sessions)

    assert layout.top_project(proj) == proj
    assert layout.project_key(proj) == "myproj"


pass
def _move_env(tmp_path, monkeypatch):
    from app import config as cfg
    from app.project.manager import ProjectManager
    from app.chat.sessions import SessionStore
    from app.store import event_log

    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path)
    monkeypatch.setattr(cfg, "RUNTIME_DIR", tmp_path / "runtime", raising=False)
    pm = ProjectManager(str(tmp_path / "projects"))
    sessions = SessionStore()
    event_log.set_store(sessions)
    return tmp_path, pm, sessions


def _seed_db(old: str, new: str):
    from pathlib import Path
    from app.plugins.install import InstallStore
    from app.store.plugin_config import PluginConfigStore
    from app.security import project_mode
    from app.chat.recent import RecentStore

    for p in (old, new):
        Path(p, ".agent").mkdir(parents=True, exist_ok=True)
    installs = InstallStore()
    files = [{"kind": "workflow", "rel_path": ".agent/workflows/w.json",
              "extra": {}}]

    class _Pkg:
        id = "remotion"
        version = "1.0"
        raw = "{}"

    installs.add_plugin(_Pkg(), old, "local", files)
    PluginConfigStore().put("remotion", old, {"outDir": "build"})
    PluginConfigStore().set_grants("remotion", old, ["orouter"])
    project_mode.set_mode(old, "yolo")
    RecentStore().touch(old, str(Path(old, "a.md")), name="a.md")
    return installs


def test_relocate_rewires_plugin_tables(tmp_path, monkeypatch):
    from pathlib import Path
    from app.project.relocate import relocate
    from app.plugins.install import InstallStore
    from app.store.plugin_config import PluginConfigStore
    from app.store import layout
    from app.security import project_mode
    from app.chat.recent import RecentStore

    tmp, pm, sessions = _move_env(tmp_path, monkeypatch)
    a, b = tmp / "a", tmp / "b"
    pm.register(str(a), sessions=sessions)
    pm.register(str(b), sessions=sessions)
    installs = _seed_db(str(a), str(b))
    old_key, new_key = layout.project_key(a), layout.project_key(b / "a")
    assert old_key != new_key

    out = relocate(pm, sessions, str(a), str(b), stores={"installs": installs})
    new = out["path"]
    assert Path(new) == b / "a"

    pass
    assert InstallStore().files_by_kind("workflow", new)
    assert InstallStore().files_by_kind("workflow", str(a)) == []
    assert InstallStore().get_plugin("remotion", new) is not None
    pass
    assert PluginConfigStore().get("remotion", new) == {"outDir": "build"}
    assert PluginConfigStore().grants("remotion", new) == ("orouter",)
    pass
    assert project_mode.get_mode(new) == "yolo"
    assert project_mode.get_mode(str(a)) == project_mode.DEFAULT_MODE
    pass
    items = RecentStore().list(new)["items"]
    assert [i["name"] for i in items] == ["a.md"]
    assert RecentStore().list(str(a))["items"] == []

    assert out["plugins_moved"] >= 1
    assert out["configs_moved"] >= 2
    assert out["policy_moved"] == 1
    assert out["recent_moved"] >= 1


def test_relocate_rewires_descendant_plugins(tmp_path, monkeypatch):
    from app.project.relocate import relocate
    from app.plugins.install import InstallStore
    from app.store import layout

    tmp, pm, sessions = _move_env(tmp_path, monkeypatch)
    a, b = tmp / "a", tmp / "b"
    pm.register(str(a), sessions=sessions)
    pm.register(str(b), sessions=sessions)
    sub = a / "sub"
    pm.register(str(sub), sessions=sessions)

    class _Pkg:
        id = "tts"
        version = "1.0"
        raw = "{}"

    installs = InstallStore()
    installs.add_plugin(_Pkg(), str(sub), "local",
                        [{"kind": "workflow", "rel_path": "w.json"}])
    out = relocate(pm, sessions, str(a), str(b), stores={"installs": installs})

    new_sub = str(b / "a" / "sub")
    assert out["path"] == str(b / "a")
    assert InstallStore().get_plugin("tts", new_sub) is not None
    assert InstallStore().get_plugin("tts", str(sub)) is None
    assert layout.project_key(new_sub) == "b/a/sub"


def test_migrate_orphan_rewires_plugin_tables(tmp_path, monkeypatch):
    import shutil
    from app.project.relocate import migrate_orphan
    from app.plugins.install import InstallStore
    from app.security import project_mode

    tmp, pm, sessions = _move_env(tmp_path, monkeypatch)
    a, b = tmp / "a", tmp / "b"
    pm.register(str(a), sessions=sessions)
    pm.register(str(b), sessions=sessions)
    installs = _seed_db(str(a), str(b))

    shutil.move(str(a), str(b / "a"))
    out = migrate_orphan(pm, sessions, str(a), str(b / "a"),
                         stores={"installs": installs})
    new = out["path"]
    assert InstallStore().get_plugin("remotion", new) is not None
    assert project_mode.get_mode(new) == "yolo"
    assert InstallStore().get_plugin("remotion", str(a)) is None


def test_retarget_does_not_touch_other_projects(tmp_path, monkeypatch):
    from app.project.relocate import relocate
    from app.plugins.install import InstallStore

    tmp, pm, sessions = _move_env(tmp_path, monkeypatch)
    a, b = tmp / "a", tmp / "b"
    other = tmp / "ab"
    for p in (a, b, other):
        pm.register(str(p), sessions=sessions)

    class _Pkg:
        def __init__(self, name):
            self.id, self.version, self.raw = name, "1.0", "{}"

    installs = InstallStore()
    for p, pid in ((a, "pa"), (other, "pab")):
        installs.add_plugin(_Pkg(pid), str(p), "local",
                            [{"kind": "workflow", "rel_path": "w.json"}])
    relocate(pm, sessions, str(a), str(b), stores={"installs": installs})

    assert InstallStore().get_plugin("pab", str(other)) is not None
    assert InstallStore().get_plugin("pa", str(b / "a")) is not None
