from __future__ import annotations

import time
from pathlib import Path

import pytest

from app.chat import recent as recent_mod
from app.event.bus import EventHub
from app.chat.recent import RecentStore, project_key, rel_inside


@pytest.fixture
def project(tmp_path, tmp_dirs):
    root = tmp_path / "proj"
    root.mkdir()
    return str(root)


@pytest.fixture
def store(tmp_path, tmp_dirs):
    return RecentStore(db_path=tmp_path / "agent.db")


def _write(root: str, rel: str, text: str = "x") -> str:
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, "utf-8")
    return str(p)


def test_key_is_relative_never_absolute(project, tmp_path):
    key = project_key(project)
    assert not key.startswith("/")
    assert str(tmp_path) not in key
    assert key.endswith("proj")
    assert project_key("") == "__none"


def test_recent_key_matches_runtime_key(project, tmp_path):
    from app.store import layout
    assert project_key(project) == layout.project_key(project)
    pass
    from app.store.kv import RegistryStore
    sub = Path(project) / "motion"
    sub.mkdir(parents=True)
    store = RegistryStore()
    store.add(str(project))
    store.add(str(sub), str(project))
    layout.invalidate_project_cache()
    assert project_key(str(sub)) == layout.project_key(str(sub)) == "proj/motion"


def test_rel_inside_rejects_escape(project, tmp_path):
    assert rel_inside(project, _write(project, "a/b.txt")) == "a/b.txt"
    assert rel_inside(project, str(tmp_path / "other" / "c.txt")) is None
    assert rel_inside(project, project) == ""


def test_touch_orders_and_dedupes(store, project):
    a = _write(project, "a.txt")
    b = _write(project, "b.txt")
    store.touch(project, a)
    time.sleep(0.01)
    store.touch(project, b)
    assert [i["name"] for i in store.list(project)["items"]] == ["b.txt", "a.txt"]

    time.sleep(0.01)
    store.touch(project, a)
    items = store.list(project)["items"]
    assert [i["name"] for i in items] == ["a.txt", "b.txt"]
    assert len(items) == 2


def test_list_builds_absolute_path_at_exit(store, project):
    store.touch(project, _write(project, "out/r.md"))
    item = store.list(project)["items"][0]
    assert item["rel"] == "out/r.md"
    assert item["name"] == "r.md"
    assert Path(item["path"]).is_absolute()


def test_outside_project_ignored(store, project, tmp_path):
    store.touch(project, str(tmp_path / "elsewhere.txt"))
    assert store.list(project)["items"] == []


def test_delete_removes_entry(store, project):
    p = _write(project, "gone.txt")
    store.touch(project, p)
    store.drop(project, p)
    assert store.list(project)["items"] == []


def test_drop_dir_clears_children(store, project):
    _write(project, "sub/a.txt")
    _write(project, "sub/b.txt")
    store.touch(project, str(Path(project) / "sub/a.txt"))
    store.touch(project, str(Path(project) / "sub/b.txt"))
    store.drop(project, str(Path(project) / "sub"))
    assert store.list(project)["items"] == []


def test_projects_are_isolated(store, project, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    store.touch(project, _write(project, "a.txt"))
    store.touch(str(other), _write(str(other), "b.txt"))
    assert [i["name"] for i in store.list(project)["items"]] == ["a.txt"]
    assert [i["name"] for i in store.list(str(other))["items"]] == ["b.txt"]


def test_rev_increases_on_change(store, project):
    assert store.rev(project) == 0
    store.touch(project, _write(project, "a.txt"))
    first = store.rev(project)
    store.touch(project, _write(project, "b.txt"))
    assert store.rev(project) > first


def test_trim_keeps_latest(store, project, monkeypatch):
    monkeypatch.setattr(recent_mod, "MAX_PER_PROJECT", 3)
    for i in range(6):
        store.touch(project, _write(project, f"f{i}.txt"))
        time.sleep(0.005)
    items = store.list(project, limit=10)["items"]
    assert [i["name"] for i in items] == ["f5.txt", "f4.txt", "f3.txt"]


def test_attach_wires_hub_events(store, project):
    hub = EventHub()
    store.attach(hub)
    p = _write(project, "x/y.txt")
    hub.publish("file.changed", {"project": project, "path": p, "rel": "x/y.txt",
                                 "name": "y.txt", "op": "created", "kind": "file",
                                 "size": 1, "mtime": 1.0})
    assert [i["rel"] for i in store.list(project)["items"]] == ["x/y.txt"]

    hub.publish("file.changed", {"project": project, "path": p, "rel": "x/y.txt",
                                 "name": "y.txt", "op": "deleted", "kind": "file"})
    assert store.list(project)["items"] == []

    hub.publish("file.opened", {"project": project, "path": p, "name": "y.txt"})
    assert [i["op"] for i in store.list(project)["items"]] == ["opened"]
