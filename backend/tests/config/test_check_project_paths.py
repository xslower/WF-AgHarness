from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _load_gate():
    path = ROOT / "scripts" / "check_project_paths.py"
    spec = importlib.util.spec_from_file_location("_gate_paths", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_gate_paths"] = mod
    spec.loader.exec_module(mod)
    return mod


gate = _load_gate()


def test_flags_resolve_inside_dict_literal():
    src = (
        "from pathlib import Path\n"
        "def publish(project):\n"
        "    return {\n"
        '        "project_real": str(Path(project).resolve()),\n'
        "    }\n"
    )
    tree = __import__("ast").parse(src)
    assert gate._banned_calls(tree) == [4]
    docs = gate._docstring_lines(tree)
    assert 4 not in docs


def test_docstring_examples_are_ignored():
    src = (
        '"""说明。\n'
        "\n"
        "示例：Path(x).resolve() 不能这么用。\n"
        '"""\n'
        "def f():\n"
        '    """内部示例 realpath(p)。"""\n'
        "    return 1\n"
    )
    tree = __import__("ast").parse(src)
    assert gate._banned_calls(tree) == []
    docs = gate._docstring_lines(tree)
    assert 1 in docs and 6 in docs
    assert 3 in docs


def test_allowed_funcs_are_exempt():
    src = (
        "import os\n"
        "def physical(p):\n"
        "    return os.path.realpath(p)\n"
        "def other(p):\n"
        "    return os.path.realpath(p)\n"
    )
    lines = gate._banned_calls(__import__("ast").parse(src))
    assert lines == [5]


def test_current_repo_is_clean():
    assert gate.main() == 0
