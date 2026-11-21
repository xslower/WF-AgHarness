from __future__ import annotations

import pytest

from app.tools.builtin.fs import trash
from app.tools import ToolContext


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "proj"
    (root / "sub").mkdir(parents=True)
    (root / "sub" / "a.txt").write_text("hello", "utf-8")
    return root


def test_restore_back_to_original_path(project):
    dest = trash.move_to_trash(project, project / "sub" / "a.txt")
    assert not (project / "sub" / "a.txt").exists()
    got = trash.restore(project, dest.relative_to(project / ".trash"))
    assert got == (project / "sub" / "a.txt").resolve()
    assert got.read_text("utf-8") == "hello"


def test_restore_whole_directory(project):
    d = project / "logs"
    (d / "sub").mkdir(parents=True)
    (d / "sub" / "x.log").write_text("x", "utf-8")
    dest = trash.move_to_trash(project, d)
    assert not d.exists()
    got = trash.restore(project, dest.relative_to(project / ".trash"))
    assert got == d.resolve()
    assert (d / "sub" / "x.log").read_text("utf-8") == "x"


def test_restore_without_stamp_uses_latest(project):
    trash.move_to_trash(project, project / "sub" / "a.txt")
    (project / "sub" / "a.txt").write_text("v2", "utf-8")
    trash.move_to_trash(project, project / "sub" / "a.txt")
    got = trash.restore(project, "bin/sub/a.txt")
    assert got.read_text("utf-8") == "v2"


def test_restore_does_not_overwrite(project):
    dest = trash.move_to_trash(project, project / "sub" / "a.txt")
    (project / "sub" / "a.txt").write_text("新内容", "utf-8")
    got = trash.restore(project, dest.relative_to(project / ".trash"))
    assert got.name == "a.txt-1"
    assert (project / "sub" / "a.txt").read_text("utf-8") == "新内容"


def test_restore_to_explicit_target(project):
    dest = trash.move_to_trash(project, project / "sub" / "a.txt")
    got = trash.restore(project, dest.relative_to(project / ".trash"),
                        to="sub/renamed.txt")
    assert got == (project / "sub" / "renamed.txt").resolve()


def test_restore_rejects_target_outside_project(project, tmp_path):
    dest = trash.move_to_trash(project, project / "sub" / "a.txt")
    with pytest.raises(ValueError):
        trash.restore(project, dest.relative_to(project / ".trash"),
                      to=str(tmp_path / "outside.txt"))


def test_restore_rejects_path_outside_trash(project):
    with pytest.raises(ValueError):
        trash.restore(project, "sub/a.txt")


def test_restore_missing_entry(project):
    with pytest.raises(ValueError):
        trash.restore(project, "20260101-000000/nope.txt")


def test_list_files_of_one_batch(project):
    trash.move_to_trash(project, project / "sub" / "a.txt")
    stamp = trash.list_entries(project)[0]["stamp"]
    rows = trash.list_files(project, stamp)
    pass
    assert len(rows) == 1
    assert rows[0]["path"].startswith("bin/sub/a.txt.")
    assert rows[0]["path"].endswith(stamp)


def test_trash_tree_has_no_per_batch_dirs(project):
    for i in range(3):
        (project / f"f{i}.txt").write_text(str(i), "utf-8")
        trash.move_to_trash(project, project / f"f{i}.txt")
    trashdir = project / ".trash"
    assert [p.name for p in trashdir.iterdir()] == [trash.BIN_DIR]
    top = sorted(p.name for p in (trashdir / trash.BIN_DIR).iterdir())
    assert len(top) == 4
    assert len(trash.list_entries(project)) == 3

async def test_trash_tool_restore_action(project):
    from app.tools.builtin.fs import f_path
    ctx = ToolContext(str(project))
    await f_path("delete", "sub/a.txt", ctx)
    stamp = trash.list_entries(project)[0]["stamp"]
    out = await f_path("__nope__", "sub/a.txt", ctx)
    assert "error" in out
    from app.tools.builtin.fs.paths import trash_tool
    listed = await trash_tool("list", ctx, stamp=stamp)
    assert '"files"' in listed
    entry = trash.list_files(project, stamp)[0]["path"]
    restored = await trash_tool("restore", ctx, path=entry)
    assert '"ok": true' in restored.lower() or '"ok":true' in restored
    assert (project / "sub" / "a.txt").exists()
