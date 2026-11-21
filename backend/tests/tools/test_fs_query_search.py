from __future__ import annotations

import fnmatch

import pytest

from app.tools.builtin.fs.read import _MAX_DEPTH, _MAX_HITS, _glob_pats, _match_names


class _Ctx:
    def __init__(self, cwd):
        self.cwd = str(cwd)


def _mk(root, files=(), dirs=()):
    for d in dirs:
        (root / d).mkdir(parents=True, exist_ok=True)
    for f in files:
        p = root / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x")
    return root


pass
def test_double_star_prefix_gets_short_form():
    assert _glob_pats("**/*.py") == ["**/*.py", "*.py"]


def test_plain_pattern_is_kept_as_is():
    assert _glob_pats("*.py") == ["*.py"]
    assert _glob_pats("src/**/*.ts") == ["src/**/*.ts"]


def test_root_level_file_found_with_double_star(tmp_path):
    _mk(tmp_path, files=["main.py", "pkg/mod.py"])
    out = _match_names(tmp_path, _glob_pats("**/*.py"), _MAX_DEPTH)
    assert "main.py" in out and "pkg/mod.py" in out


def test_fnmatch_double_star_really_misses_root():
    assert not fnmatch.fnmatch("main.py", "**/*.py")


pass
def test_depth_one_lists_only_top_level(tmp_path):
    _mk(tmp_path, files=["a.txt"], dirs=["d1", "d1/d2"])
    _mk(tmp_path, files=["d1/b.txt", "d1/d2/c.txt"])
    out = _match_names(tmp_path, ["*.txt"], 1)
    assert "a.txt" in out
    assert "b.txt" not in out and "c.txt" not in out


def test_depth_two_reaches_grandchildren(tmp_path):
    _mk(tmp_path, dirs=["d1"])
    _mk(tmp_path, files=["d1/b.txt"])
    out = _match_names(tmp_path, ["*.txt"], 2)
    assert "d1/b.txt" in out


def test_max_depth_constant_is_three():
    assert _MAX_DEPTH == 3


def test_no_match_returns_placeholder(tmp_path):
    _mk(tmp_path, files=["a.txt"])
    assert _match_names(tmp_path, ["*.zzz"], _MAX_DEPTH) == "(无匹配)"


def test_hits_are_capped(tmp_path):
    _mk(tmp_path, files=[f"f{i}.txt" for i in range(_MAX_HITS + 50)])
    out = _match_names(tmp_path, ["*.txt"], _MAX_DEPTH)
    assert len(out.split("\n")) == _MAX_HITS


def test_relative_path_prefix_includes_parent_dir(tmp_path):
    _mk(tmp_path, dirs=["pkg"])
    _mk(tmp_path, files=["pkg/mod.py"])
    out = _match_names(tmp_path, ["mod.py"], _MAX_DEPTH)
    assert out.strip() == "pkg/mod.py"
