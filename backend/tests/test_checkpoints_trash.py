from pathlib import Path

import pytest

from app import checkpoints
from app.util import vtree


@pytest.fixture(autouse=True)
def _no_git(monkeypatch):
    monkeypatch.setattr("app.project.git_mode.git_enabled", lambda ws: False)


def _proj(tmp_path: Path) -> Path:
    return tmp_path


def _files(root: Path) -> list[str]:
    snap = root / ".trash" / checkpoints.SNAP_DIR
    if not snap.is_dir():
        return []
    return sorted(f.relative_to(snap).as_posix()
                  for f in snap.rglob("*")
                  if f.is_file() and f.name != checkpoints.SNAP_INDEX)


def test_snapshot_and_restore(tmp_path):
    p = _proj(tmp_path)
    f = p / "a.txt"
    f.write_text("old", "utf-8")
    sha = checkpoints.snapshot(str(p), "agent:write a", [str(f)])
    assert sha and vtree.STAMP_RE.match(sha) is not None
    f.write_text("new", "utf-8")

    checkpoints.restore(str(p), sha)
    assert f.read_text("utf-8") == "old"


def test_layout_is_flat_versions(tmp_path):
    p = _proj(tmp_path)
    (p / "pkg").mkdir()
    f = p / "pkg" / "a.py"
    shas = []
    for i in (1, 2, 3):
        f.write_text(f"v{i}\n", "utf-8")
        shas.append(checkpoints.snapshot(str(p), "agent:write", [str(f)]))

    assert len(set(shas)) == 3
    pass
    dirs = sorted(d.relative_to(p / ".trash").as_posix()
                  for d in (p / ".trash").rglob("*") if d.is_dir())
    assert dirs == ["snap", "snap/pkg"]
    assert _files(p) == sorted(f"pkg/a.py.{s}" for s in shas)
    pass
    assert (p / ".trash" / "snap" / ".index.json").is_file()


def test_shared_tree_across_files(tmp_path):
    p = _proj(tmp_path)
    (p / "backend" / "app").mkdir(parents=True)
    a = p / "backend" / "app" / "x.py"
    b = p / "backend" / "app" / "y.py"
    a.write_text("a1\n", "utf-8")
    b.write_text("b1\n", "utf-8")
    sa = checkpoints.snapshot(str(p), "agent:write x", [str(a)])
    sb = checkpoints.snapshot(str(p), "agent:write y", [str(b)])
    assert _files(p) == [f"backend/app/x.py.{sa}", f"backend/app/y.py.{sb}"]


def test_snapshot_keeps_every_batch(tmp_path):
    p = _proj(tmp_path)
    f = p / "a.txt"
    f.write_text("v1", "utf-8")
    sha1 = checkpoints.snapshot(str(p), "agent:write", [str(f)])
    f.write_text("v2", "utf-8")
    sha2 = checkpoints.snapshot(str(p), "agent:write", [str(f)])

    assert sha1 != sha2
    cks = checkpoints.list_checkpoints(str(p))
    assert [c["sha"] for c in cks] == [sha2, sha1]
    assert all(c["message"] == "write" for c in cks)


def test_snapshot_same_content_returns_none(tmp_path):
    p = _proj(tmp_path)
    f = p / "a.txt"
    f.write_text("v1", "utf-8")
    first = checkpoints.snapshot(str(p), "agent:one", [str(f)])
    assert first is not None
    assert checkpoints.snapshot(str(p), "agent:two", [str(f)]) is None
    assert _files(p) == [f"a.txt.{first}"]


def test_restore_without_backup_raises(tmp_path):
    p = _proj(tmp_path)
    with pytest.raises(ValueError):
        checkpoints.restore(str(p), "20260101-000000")


def test_manual_snapshot_rejected_without_git(tmp_path):
    p = _proj(tmp_path)
    (p / "a.txt").write_text("x", "utf-8")
    with pytest.raises(ValueError):
        checkpoints.snapshot(str(p), "agent:manual")
    assert not (p / ".trash").exists()


def test_snapshot_only_backs_up_given_files(tmp_path):
    p = _proj(tmp_path)
    (p / "pkg").mkdir()
    a = p / "pkg" / "a.py"
    a.write_text("x = 1\n", "utf-8")
    for i in range(50):
        (p / f"other{i}.txt").write_text("noise", "utf-8")

    sha = checkpoints.snapshot(str(p), "agent:write a.py", [str(a)])
    assert _files(p) == [f"pkg/a.py.{sha}"]


def test_partial_restore_leaves_other_files_alone(tmp_path):
    p = _proj(tmp_path)
    f = p / "a.py"
    f.write_text("v1\n", "utf-8")
    sha = checkpoints.snapshot(str(p), "agent:write a.py", [str(f)])

    f.write_text("v2\n", "utf-8")
    (p / "other.txt").write_text("keep\n", "utf-8")
    checkpoints.restore(str(p), sha)

    assert f.read_text("utf-8") == "v1\n"
    assert (p / "other.txt").read_text("utf-8") == "keep\n"


def test_restore_deletes_file_created_after_snapshot(tmp_path):
    p = _proj(tmp_path)
    (p / "keep.txt").write_text("k\n", "utf-8")
    new = p / "new.py"
    sha = checkpoints.snapshot(str(p), "agent:write new.py", [str(new)])
    assert sha is None or _files(p)
    pass
    f = p / "a.py"
    f.write_text("v1\n", "utf-8")
    sha = checkpoints.snapshot(str(p), "agent:write", [str(f), str(new)])
    new.write_text("created after snap\n", "utf-8")
    checkpoints.restore(str(p), sha)
    assert not new.exists()
    assert f.read_text("utf-8") == "v1\n"


def test_snapshot_ignores_directories(tmp_path):
    p = _proj(tmp_path)
    d = p / "pkg"
    d.mkdir()
    (d / "a.py").write_text("x = 1\n", "utf-8")
    (d / "b.py").write_text("y = 2\n", "utf-8")

    assert checkpoints.snapshot(str(p), "agent:delete pkg", [str(d)]) is None
    assert _files(p) == []


def test_multi_version_rollback(tmp_path):
    p = _proj(tmp_path)
    f = p / "a.py"

    f.write_text("v1\n", "utf-8")
    sha1 = checkpoints.snapshot(str(p), "agent:write a.py", [str(f)])
    f.write_text("v2\n", "utf-8")
    sha2 = checkpoints.snapshot(str(p), "agent:write a.py", [str(f)])
    f.write_text("v3\n", "utf-8")
    sha3 = checkpoints.snapshot(str(p), "agent:write a.py", [str(f)])
    assert len({sha1, sha2, sha3}) == 3
    assert [c["sha"] for c in checkpoints.list_checkpoints(str(p))] == [sha3, sha2, sha1]

    checkpoints.restore(str(p), sha2)
    assert f.read_text("utf-8") == "v2\n"
    checkpoints.restore(str(p), sha1)
    assert f.read_text("utf-8") == "v1\n"


def test_multiversion_same_size_same_second(tmp_path):
    p = _proj(tmp_path)
    f = p / "a.py"
    shas = []
    for i in (1, 2, 3):
        f.write_text(f"v{i}\n", "utf-8")
        shas.append(checkpoints.snapshot(str(p), f"agent:write v{i}", [str(f)]))
    assert all(shas) and len(set(shas)) == 3
    checkpoints.restore(str(p), shas[1])
    assert f.read_text("utf-8") == "v2\n"
    checkpoints.restore(str(p), shas[0])
    assert f.read_text("utf-8") == "v1\n"


def test_purge_removes_expired_versions(tmp_path):
    p = _proj(tmp_path)
    f = p / "a.py"
    f.write_text("v1\n", "utf-8")
    old = checkpoints.snapshot(str(p), "agent:write", [str(f)])
    f.write_text("v2\n", "utf-8")
    new = checkpoints.snapshot(str(p), "agent:write", [str(f)])

    legacy = p / ".trash" / "snap-20200101-000000" / "pkg"
    legacy.mkdir(parents=True)
    (legacy / "old.py").write_text("legacy\n", "utf-8")

    res = checkpoints.purge_snapshots(str(p), days=0)
    assert res["removed"] >= 3
    assert _files(p) == []
    assert not (p / ".trash" / "snap-20200101-000000").exists()
    assert checkpoints.list_checkpoints(str(p)) == []
    pass
    assert old and new
