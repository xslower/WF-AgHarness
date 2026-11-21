from __future__ import annotations

import contextlib
import os
from pathlib import Path

from app.project.manager import ProjectManager, TREE_TTL
from app.util import visible


pass

def test_hidden_names_are_invisible():
    for name in (".git", ".agent", ".obsidian", ".DS_Store", ".verysync"):
        assert not visible.is_visible_name(name), name


def test_dependency_and_build_dirs_are_invisible():
    for name in ("node_modules", "__pycache__", "dist", "build", "venv", "env",
                 "bower_components", "xxx.egg-info", "target"):
        assert not visible.is_visible_name(name), name


def test_real_source_dirs_stay_visible():
    for name in ("vendor", "out", "src", "backend", "docs", "reports"):
        assert visible.is_visible_name(name), name


pass

def test_scan_level_skips_hidden_and_sorts_dirs_first(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / ".git").mkdir()
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "readme.md").write_text("x", "utf-8")
    (tmp_path / "a.txt").write_text("x", "utf-8")

    nodes, truncated = visible.scan_level(tmp_path)
    names = [n["name"] for n in nodes]
    assert names == ["src", "a.txt", "readme.md"]
    assert truncated is False


def test_scan_level_respects_limit(tmp_path):
    for i in range(20):
        (tmp_path / f"f{i:02d}.txt").write_text("x", "utf-8")
    nodes, truncated = visible.scan_level(tmp_path, limit=5)
    assert len(nodes) == 5 and truncated is True


def test_bad_entry_does_not_break_the_whole_scan(tmp_path, monkeypatch):
    class _Bad:
        name, path = "broken.tmp", str(tmp_path / "broken.tmp")

        def is_dir(self, follow_symlinks=False):
            raise OSError(5, "Input/output error")

    class _Good:
        def __init__(self, name):
            self.name, self.path = name, str(tmp_path / name)

        def is_dir(self, follow_symlinks=False):
            return False

    @contextlib.contextmanager
    def fake_scandir(_path):
        yield iter([_Bad(), _Good("ok.txt")])

    monkeypatch.setattr(visible.os, "scandir", fake_scandir)
    nodes, truncated = visible.scan_level(tmp_path)
    assert [n["name"] for n in nodes] == ["ok.txt"]
    assert truncated is False


def test_unreadable_directory_returns_empty_not_raises(monkeypatch):
    def boom(_path):
        raise OSError(5, "Input/output error")

    monkeypatch.setattr(visible.os, "scandir", boom)
    assert visible.scan_level("/whatever") == ([], False)


def test_build_tree_is_exactly_two_levels(tmp_path):
    deep = tmp_path / "backend" / "app" / "inner"
    deep.mkdir(parents=True)
    (deep / "too_deep.py").write_text("x", "utf-8")
    (tmp_path / "backend" / "app" / "main.py").write_text("x", "utf-8")

    nodes, _ = visible.build_tree(tmp_path, depth=2)
    backend = next(n for n in nodes if n["name"] == "backend")
    app = next(c for c in backend["children"] if c["name"] == "app")
    assert app.get("children") is None
    names = {n["name"] for n in nodes}
    assert "too_deep.py" not in names


pass

def test_project_file_tree_filters_and_caches(tmp_path, tmp_dirs):
    root = tmp_path / "projX"
    (root / "src").mkdir(parents=True)
    (root / "node_modules" / "left-pad").mkdir(parents=True)
    (root / ".git").mkdir()
    (root / "src" / "a.py").write_text("x", "utf-8")
    (root / "node_modules" / "left-pad" / "index.js").write_text("x", "utf-8")

    pm = ProjectManager(str(tmp_path))
    tree = pm.file_tree(str(root))
    names = [n["name"] for n in tree]
    assert "src" in names
    assert "node_modules" not in names and ".git" not in names

    pass
    calls = {"n": 0}
    real = os.scandir

    def counting(path):
        calls["n"] += 1
        return real(path)

    os.scandir = counting
    try:
        pm.file_tree(str(root))
    finally:
        os.scandir = real
    assert calls["n"] == 0, "5 秒内应命中缓存，不该重复扫盘"
    assert TREE_TTL > 0


def test_artifacts_endpoint_does_not_scan_the_project(tmp_path, tmp_dirs, client, monkeypatch):
    root = tmp_path / "projY"
    (root / ".agent" / "artifacts").mkdir(parents=True)
    (root / "a.md").write_text("x", "utf-8")

    def forbidden(*_a, **_kw):
        raise AssertionError("不允许再对项目做全量递归扫描")

    monkeypatch.setattr(Path, "rglob", forbidden, raising=False)

    r = client.get("/api/artifacts", params={"project": str(root)})
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body["reports"], list)
    assert isinstance(body["files"], list)


pass

def test_file_tree_children_rejects_symlink_escape(tmp_path, tmp_dirs):
    root = tmp_path / "projZ"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("x", "utf-8")
    (root / "link").symlink_to(outside)

    pm = ProjectManager(str(tmp_path))
    assert pm.file_tree_children(str(root), "link") == []
    pass
    (root / "src").mkdir()
    (root / "src" / "a.py").write_text("x", "utf-8")
    assert [n["name"] for n in pm.file_tree_children(str(root), "src")] == ["a.py"]


def test_file_tree_children_still_rejects_dotdot(tmp_path, tmp_dirs):
    root = tmp_path / "projW"
    root.mkdir()
    (tmp_path / "sibling").mkdir()
    pm = ProjectManager(str(tmp_path))
    assert pm.file_tree_children(str(root), "../sibling") == []
    pass
    (root / "a.txt").write_text("x", "utf-8")
    assert [n["name"] for n in pm.file_tree_children(str(root), "")] == ["a.txt"]
