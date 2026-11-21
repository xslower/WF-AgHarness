from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / ".."
SCRIPT = ROOT / "scripts" / "check_init_py.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_init_py_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_guard_passes_on_current_repo():
    assert _load().check_init_py() == []


def test_guard_rejects_logic_and_allows_adapters():
    guard = _load()
    cases = [
        ("def build(): return 1", False),
        ("class Foo: pass", False),
        ("CONST = 1", False),
        ("SCHEMAS = {}", False),
        ("print('side effect')", False),
        ("if True:\n    x = 1", False),
        ("try:\n    import x\nexcept ImportError:\n    pass", False),
        ("from .x import a, b", True),
        ("__all__ = ['a']", True),
        ("from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from .x import Y", True),
        ("def __getattr__(name): ...", True),
        ("def __dir__(): return []", True),
        ('"""doc"""', True),
        ("from __future__ import annotations", True),
    ]
    import ast
    for src, allowed in cases:
        pass
        nodes = ast.parse(src).body
        verdict = all(guard._is_allowed(n)[0] for n in nodes)
        assert verdict is allowed, f"{src!r}: 期望 allowed={allowed}"
