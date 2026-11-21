from __future__ import annotations

from pathlib import Path

from app.tools.builtin.fs import tree
from app.tools.builtin.fs.read import _MAX_DEPTH, search_files


class _Ctx:
    def __init__(self, cwd):
        self.cwd = str(cwd)


def _mk(root: Path, files=(), dirs=()):
    for d in dirs:
        (root / d).mkdir(parents=True, exist_ok=True)
    for f in files:
        p = root / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x")
    return root


pass
def test_depth_three_reaches_third_level_files(tmp_path):
    _mk(tmp_path, dirs=["a/b/c"], files=["a/b/c/leaf.py", "root.txt"])
    out = search_files(ctx=_Ctx(tmp_path), depth=3)
    assert "a/" in out and "b/" in out and "c/" in out
    assert "leaf.py" in out and "root.txt" in out


def test_default_depth_is_three(tmp_path):
    _mk(tmp_path, dirs=["a/b/c"], files=["a/b/c/leaf.py"])
    assert search_files(ctx=_Ctx(tmp_path)) == \
        search_files(ctx=_Ctx(tmp_path), depth=3)


def test_depth_cap_is_three(tmp_path):
    _mk(tmp_path, dirs=["a/b/c/d/e"], files=["a/b/c/d/e/too_deep.py"])
    out = search_files(ctx=_Ctx(tmp_path), depth=99)
    assert _MAX_DEPTH == 3
    assert "too_deep.py" not in out


def test_depth_one_only_lists_top_level(tmp_path):
    _mk(tmp_path, dirs=["d1/d2"], files=["d1/x.py", "root.py"])
    out = search_files(ctx=_Ctx(tmp_path), depth=1)
    assert "d1/" in out and "root.py" in out
    assert "x.py" not in out
    assert "d2/" not in out


pass
def test_huge_dir_is_folded_to_one_count_line(tmp_path):
    _mk(tmp_path, dirs=["huge"], files=["root.py"])
    for i in range(tree.DIR_EXPLODE + 30):
        (tmp_path / "huge" / f"tmp{i}.log").write_text("x")
    out = search_files(ctx=_Ctx(tmp_path), depth=3)
    assert "tmp0.log" not in out and "tmp1.log" not in out
    assert "未展开" in out and "路径" not in out
    assert 'path="huge"' in out
    assert "huge/" in out
    assert "root.py" in out


def test_hidden_dirs_are_skipped(tmp_path):
    _mk(tmp_path, dirs=[".git", "node_modules", "src"],
        files=[".git/config", "node_modules/x.js", "src/a.py"])
    out = search_files(ctx=_Ctx(tmp_path), depth=3)
    assert ".git" not in out and "node_modules" not in out
    assert "x.js" not in out
    assert "src/" in out and "a.py" in out


pass
def test_fold_deepest_removes_whole_subtree_no_partial_files(tmp_path):
    _mk(tmp_path, dirs=["top/mid/leaf", "other"],
        files=["top/mid/m.py", "other/o.py", "root.py"])
    for i in range(8):
        (tmp_path / "top/mid/leaf" / f"f{i}.py").write_text("x")
    rows: list[dict] = []
    tree._tree_lines(tmp_path, "", 0, 3, rows)
    assert any("f0.py" in x["text"] for x in rows)

    assert tree._fold_deepest(rows) is True
    text = tree._render(rows)
    pass
    pass
    assert "f0.py" not in text and "f7.py" not in text
    assert "leaf/" in text and "未展开" in text
    pass
    assert "top/" in text and "mid/" in text and "root.py" in text
    pass
    assert "path=" in text and "未展开" in text


def test_fold_keeps_parent_directories_until_last(tmp_path):
    _mk(tmp_path, dirs=["a/b/c", "d"], files=["a/b/c/x.py", "d/y.py", "r.py"])
    rows: list[dict] = []
    tree._tree_lines(tmp_path, "", 0, 3, rows)
    for _ in range(6):
        tree._fold_deepest(rows)
    text = tree._render(rows)
    assert "a/" in text and "d/" in text and "r.py" in text
    assert "x.py" not in text and "y.py" not in text


def test_budget_fold_triggers_when_output_too_large(tmp_path, monkeypatch):
    _mk(tmp_path, dirs=["d0", "d1", "d2", "d3"])
    for d in range(4):
        for i in range(40):
            (tmp_path / f"d{d}" / f"a_very_long_filename_{i:03d}_module.py").write_text("x")
    monkeypatch.setattr(tree, "TREE_BUDGET", 1200)
    out = search_files(ctx=_Ctx(tmp_path), depth=3)
    assert len(out) <= 1200 * 2 + 200
    assert "未展开" in out
    assert "d0/" in out and "d3/" in out


pass
def test_glob_mode_unchanged(tmp_path):
    _mk(tmp_path, files=["main.py", "pkg/mod.py"])
    assert "main.py" in search_files(ctx=_Ctx(tmp_path), pattern="**/*.py", depth=3)
    assert "pkg/mod.py" in search_files(ctx=_Ctx(tmp_path), pattern="**/*.py", depth=3)


def test_missing_dir_errors(tmp_path):
    assert "目录不存在" in search_files(ctx=_Ctx(tmp_path), path="nope")
