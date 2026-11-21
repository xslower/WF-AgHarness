from __future__ import annotations

from pathlib import Path

from app.tools.builtin.fs.common import _fix_case, resolve


class _Ctx:
    def __init__(self, root: Path) -> None:
        self.cwd = str(root)
        self.project = str(root)


def _tree(root: Path) -> Path:
    (root / "src" / "components").mkdir(parents=True)
    (root / "src" / "components" / "App.tsx").write_text("a\n")
    (root / "README.md").write_text("r\n")
    return root


def test_exact_path_untouched(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    p = resolve(_Ctx(root), "src/components/App.tsx")
    assert p == root / "src" / "components" / "App.tsx"


def test_case_insensitive_hit(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    pass
    p = resolve(_Ctx(root), "SRC/Components/app.TSX")
    assert p == root / "src" / "components" / "App.tsx"
    assert p.read_text() == "a\n"


def test_absolute_path_too(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    p = resolve(_Ctx(root), str(root / "readme.MD"))
    assert p == root / "README.md"


def test_ambiguous_siblings_not_guessed(tmp_path: Path) -> None:
    _tree(tmp_path)
    (tmp_path / "src" / "foo.tsx").write_text("b\n")
    (tmp_path / "src" / "Foo.tsx").write_text("c\n")
    p = resolve(_Ctx(tmp_path), "src/FOO.tsx")
    assert not p.exists()
    assert p.name == "FOO.tsx"


def test_new_file_keeps_own_name(tmp_path: Path) -> None:
    _tree(tmp_path)
    p = resolve(_Ctx(tmp_path), "src/Components/NewView.tsx")
    assert p == tmp_path / "src" / "components" / "NewView.tsx"
    assert not p.exists()


def test_missing_path_returned_as_is(tmp_path: Path) -> None:
    _tree(tmp_path)
    p = resolve(_Ctx(tmp_path), "nope/deep/x.py")
    assert p == tmp_path / "nope" / "deep" / "x.py"


def test_fix_case_is_idempotent(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    once = _fix_case(root / "SRC" / "components" / "App.tsx")
    assert _fix_case(once) == once
