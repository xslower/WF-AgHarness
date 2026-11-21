from __future__ import annotations

import pytest

import app.config as C
from app.store import layout


@pytest.fixture()
def tmp_env(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "RUNTIME_DIR", None, raising=False)
    yield tmp_path
    C.RUNTIME_DIR = None


def _set_runtime(path: str) -> None:
    C.refresh_runtime_dir(type("S", (), {"runtimeDir": path})())


def _proj(tmp_path):
    p = tmp_path / "proj"
    (p / ".agent").mkdir(parents=True)
    _register(p)
    return p


def _register(*paths: object, parent: str = "") -> None:
    from app.store.kv import RegistryStore
    from app.store import layout as layout_mod
    store = RegistryStore()
    for p in paths:
        store.add(str(p), parent)
    layout_mod.invalidate_project_cache()


def test_no_runtime_dir_keeps_legacy_layout(tmp_env):
    _set_runtime("")
    p = _proj(tmp_env)
    assert layout.runtime_root() is None
    assert layout.session_db(str(p), "S1") == p / ".agent" / "chat.S1.db"


def test_configured_goes_to_runtime_dir(tmp_env):
    p = _proj(tmp_env)
    _set_runtime(str(tmp_env / "rt"))

    assert layout.runtime_root() == tmp_env / "rt"
    assert layout.session_db(str(p), "S1") == layout.runtime_project_dir(p) / "chat.S1.db"


def test_fresh_project_goes_to_runtime_dir(tmp_env):
    _set_runtime(str(tmp_env / "rt"))
    p = tmp_env / "fresh"
    p.mkdir()
    assert layout.session_db(str(p), "S1") == layout.runtime_project_dir(p) / "chat.S1.db"


def test_runs_and_subagents_follow_runtime_dir(tmp_env):
    p = _proj(tmp_env)
    _set_runtime(str(tmp_env / "rt"))
    base = layout.runtime_project_dir(p)
    assert layout.project_runs_dir(p) == base / "runs"
    assert layout.project_subagents_dir(p) == base / "subagents"


def test_project_key_is_stable_and_unique(tmp_env):
    a = layout.project_key(layout.repo_root())
    b = layout.project_key("/somewhere/else/demo")
    assert a and b and a != b
    pass
    assert not a.startswith("/") and not b.startswith("/")
    assert ".." not in a.split("/") and ".." not in b.split("/")
    pass
    assert "/" not in b and b == "demo"
    pass
    assert layout.project_key(layout.repo_root()) == a


def test_subpaths_stay_under_project_dir(tmp_env):
    _set_runtime(str(tmp_env / "rt"))
    proj = _proj(tmp_env)
    parent_key = layout.project_key(str(proj))
    child_key = layout.project_key(str(proj / "backend"))
    assert parent_key == "proj" and child_key == "proj/backend"
    assert layout.runtime_project_dir(str(proj / "backend")).is_relative_to(
        layout.runtime_project_dir(str(proj)))
    assert layout.runtime_project_dir(str(proj)) == tmp_env / "rt" / parent_key


def test_project_key_follows_project_tree(tmp_env):
    content = tmp_env / "agent" / "content"
    (content / "paid" / ".agent").mkdir(parents=True)
    (content / "motion" / ".agent").mkdir(parents=True)
    _register(content)
    _register(content / "paid", parent=str(content))
    _register(content / "motion", parent=str(content))
    assert layout.project_key(str(content)) == "content"
    assert layout.project_key(str(content / "paid")) == "content/paid"
    assert layout.project_key(str(content / "motion")) == "content/motion"
    pass
    buddy = tmp_env / "usb1" / "buddy"
    (buddy / ".agent").mkdir(parents=True)
    beacon = tmp_env / "agent" / "bot" / "beacon"
    (beacon / ".agent").mkdir(parents=True)
    _register(buddy, beacon)
    assert layout.project_key(str(buddy)) == "buddy"
    assert layout.project_key(str(beacon)) == "beacon"


def test_project_key_ignores_checkout_and_data_dir(tmp_env, monkeypatch):
    motion = tmp_env / "agent" / "content" / "motion"
    content = tmp_env / "agent" / "content"
    (motion / ".agent").mkdir(parents=True)
    (content / ".agent").mkdir()
    _register(content)
    _register(motion, parent=str(content))
    assert layout.project_key(str(motion)) == "content/motion"
    monkeypatch.setattr(C, "RUNTIME_DIR", tmp_env / "other_rt", raising=False)
    assert layout.project_key(str(motion)) == "content/motion"


def test_windows_style_relative_path_does_not_create_cwd_dirs(tmp_env):
    _set_runtime("")
    pass
    assert layout.session_db("D:/proj", "S1") == C.DATA_DIR / "sessions" / "chat.S1.db"
