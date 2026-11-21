from __future__ import annotations

import time
from pathlib import Path

import pytest

from app.tools.builtin.fs import trash
from app.event.bus import HUB
import app.tools.builtin.fs as fs
from app.tools import ToolContext


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "proj"
    (root / "sub").mkdir(parents=True)
    (root / "sub" / "a.txt").write_text("hello", "utf-8")
    (root / "b.txt").write_text("bee", "utf-8")
    return root


def _stamp(days_ago: float) -> str:
    return time.strftime(trash.STAMP_FMT,
                         time.localtime(time.time() - days_ago * 86400))


pass
def test_move_keeps_relative_path(project):
    dest = trash.move_to_trash(project, project / "sub" / "a.txt")
    assert not (project / "sub" / "a.txt").exists()
    assert dest.parent.name == "sub"
    base, stamp = trash.vtree.split_stamp(dest.name)
    assert base == "a.txt" and stamp
    assert dest.read_text("utf-8") == "hello"
    assert (project / ".trash") in dest.parents
    assert dest.parent.parent.name == trash.BIN_DIR


def test_move_same_stamp_does_not_overwrite(project):
    stamp = "20261030-090000"
    d1 = trash.move_to_trash(project, project / "b.txt", stamp=stamp)
    (project / "b.txt").write_text("second", "utf-8")
    d2 = trash.move_to_trash(project, project / "b.txt", stamp=stamp)
    assert d1 != d2
    assert d1.read_text("utf-8") == "bee"
    assert d2.read_text("utf-8") == "second"


def test_move_rejects_outside_and_root(project, tmp_path):
    outside = tmp_path / "x.txt"
    outside.write_text("x", "utf-8")
    with pytest.raises(ValueError):
        trash.move_to_trash(project, outside)
    with pytest.raises(ValueError):
        trash.move_to_trash(project, project)
    assert outside.exists() and project.is_dir()


def test_move_rejects_inside_trash(project):
    dest = trash.move_to_trash(project, project / "b.txt", stamp="20261030-090001")
    with pytest.raises(ValueError):
        trash.move_to_trash(project, dest)


pass
def test_purge_all_when_days_zero(project):
    trash.move_to_trash(project, project / "b.txt", stamp=_stamp(0.1))
    trash.move_to_trash(project, project / "sub" / "a.txt", stamp=_stamp(30))
    res = trash.purge(project, days=0)
    assert res["removed"] == 2 and res["kept"] == 0
    assert res["freed_bytes"] > 0
    assert list((project / ".trash").iterdir()) == []


def test_purge_respects_retention(project):
    fresh = trash.move_to_trash(project, project / "b.txt", stamp=_stamp(1))
    old = trash.move_to_trash(project, project / "sub" / "a.txt", stamp=_stamp(30))
    res = trash.purge(project, days=7)
    assert res["removed"] == 1
    assert fresh.exists() and not old.exists()


def test_purge_never_touches_outside(project):
    trash.move_to_trash(project, project / "b.txt", stamp=_stamp(30))
    keep = project / "sub" / "a.txt"
    trash.purge(project, days=0)
    assert keep.exists()


def test_list_entries_reports_usage(project):
    trash.move_to_trash(project, project / "b.txt", stamp=_stamp(2))
    entries = trash.list_entries(project)
    assert len(entries) == 1
    e = entries[0]
    assert e["files"] == 1
    assert e["bytes"] == 3
    assert 1.5 < e["age_days"] < 2.5


def test_delete_dir_moves_whole_subtree(project):
    d = project / "logs"
    d.mkdir()
    (d / "a.log").write_text("1", "utf-8")
    (d / "sub").mkdir()
    (d / "sub" / "b.log").write_text("22", "utf-8")
    dest = trash.move_to_trash(project, d)
    assert dest.is_dir() and dest.name.startswith("logs.")
    assert (dest / "sub" / "b.log").read_text("utf-8") == "22"
    assert len(trash.list_entries(project)) == 1
    assert trash.list_entries(project)[0]["files"] == 2


def test_hard_delete_inside_only(project, tmp_path, monkeypatch):
    from app.security import core as policy_core
    monkeypatch.setattr(policy_core, "temp_roots", lambda extra=None: [])
    outside = tmp_path / "x.txt"
    outside.write_text("x", "utf-8")
    with pytest.raises(ValueError):
        trash.hard_delete(project, outside)
    with pytest.raises(ValueError):
        trash.hard_delete(project, project)
    trash.hard_delete(project, project / "sub" / "a.txt")
    assert not (project / "sub" / "a.txt").exists()
    assert outside.exists()


pass
@pytest.fixture
def ctx(project):
    return ToolContext(str(project))


@pytest.fixture
def events():
    got: list[dict] = []
    HUB.on("file.changed", got.append)
    return got


async def test_fs_delete_moves_to_trash(ctx, project, events, monkeypatch):
    monkeypatch.setattr(trash, "load_policy", lambda: (True, 7))
    msg = await fs.delete_file("sub/a.txt", ctx)
    assert "回收站" in msg and "可恢复" in msg
    assert not (project / "sub" / "a.txt").exists()
    assert not (project / "sub" / "a.txt").exists()
    assert any(p.name.startswith("a.txt.") for p in (project / ".trash").rglob("*"))
    assert events[-1]["payload"]["op"] == "deleted"


async def test_fs_delete_hard_when_disabled(ctx, project, monkeypatch):
    monkeypatch.setattr(trash, "load_policy", lambda: (False, 7))
    msg = await fs.delete_file("b.txt", ctx)
    assert "真删" in msg
    assert not (project / "b.txt").exists()
    assert not (project / ".trash").exists()


async def test_fs_delete_rejects_outside(ctx, tmp_path, monkeypatch):
    from app.security import core as policy_core
    monkeypatch.setattr(policy_core, "temp_roots", lambda extra=None: [])
    outside = tmp_path / "keep.txt"
    outside.write_text("x", "utf-8")
    msg = await fs.delete_file(str(outside), ctx)
    assert "删除被拒绝" in msg
    assert outside.exists()


async def test_fs_delete_allows_temp(ctx, tmp_path):
    target = tmp_path / "scratch.log"
    target.write_text("x", "utf-8")
    msg = await fs.delete_file(str(target), ctx)
    assert "已删除" in msg, msg
    assert not target.exists()


async def test_fs_delete_rejects_project_root(ctx, project):
    msg = await fs.delete_file(".", ctx)
    assert "删除被拒绝" in msg
    assert (project / "b.txt").exists()


async def test_trash_tool_list_and_purge(ctx, project, monkeypatch):
    monkeypatch.setattr(trash, "load_policy", lambda: (True, 7))
    await fs.delete_file("b.txt", ctx)
    listed = await fs.trash_tool("list", ctx)
    assert '"total_files":1' in listed.replace(" ", "")
    purged = await fs.trash_tool("purge", ctx, days=0)
    assert '"removed":1' in purged.replace(" ", "")
    assert list((project / ".trash").iterdir()) == []


def test_purge_tree_walks_children(project):
    child = project / "child"
    child.mkdir()
    (child / "c.txt").write_text("c", "utf-8")
    trash.move_to_trash(project, project / "b.txt", stamp=_stamp(30))
    trash.move_to_trash(child, child / "c.txt", stamp=_stamp(30))
    tree = {"name": "projects", "path": str(project),
            "children": [{"name": "child", "path": str(child), "children": []}]}
    out = trash.purge_tree(tree, days=7)
    assert str(project) in out and str(child) in out
    assert list((project / ".trash").iterdir()) == []
    assert list((child / ".trash").iterdir()) == []


pass
def test_trash_api_roundtrip(client, tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "a.txt").write_text("x", "utf-8")
    r = client.post("/api/file/delete", json={"path": str(root / "a.txt"), "project": str(root)})
    assert r.status_code == 200 and r.json()["recoverable"] is True

    info = client.get("/api/trash", params={"project": str(root)}).json()
    assert info["total_files"] == 1 and info["total_bytes"] == 1
    assert info["trash_enabled"] is True

    purge = client.post("/api/trash/purge", json={"project": str(root), "days": 0})
    assert purge.status_code == 200
    assert purge.json()["removed"] == 1 and purge.json()["freed_bytes"] == 1
    assert client.get("/api/trash", params={"project": str(root)}).json()["total_files"] == 0


def test_trash_api_requires_project(client):
    assert client.get("/api/trash").status_code == 400
    assert client.post("/api/trash/purge", json={"project": "", "days": 0}).status_code == 400


def test_trash_api_rejects_negative_days(client, tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    r = client.post("/api/trash/purge", json={"project": str(root), "days": -1})
    assert r.status_code == 400
