#!/usr/bin/env python3
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "backend" / "app"

pass
PROJECT_IDENTITY_MODULES = (
    "util/pathx.py",
    "store/layout.py",
    "chat/recent.py",
    "project/manager.py",
    "project/relocate.py",
    "api/routers/project/tree.py",
    "api/routers/project/overview.py",
)

pass
BANNED = {"resolve", "realpath"}

pass
pass
pass
pass
ALLOWED_FUNCS = {"physical", "_physical_cached", "_alias_table"}


def _banned_calls(tree: ast.AST) -> list[int]:
    out: list[int] = []
    funcs = [n for n in ast.walk(tree)
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    exempt_lines = {
        ln for fn in funcs if fn.name in ALLOWED_FUNCS
        for ln in range(fn.lineno, (fn.end_lineno or fn.lineno) + 1)
    }
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or node.lineno in exempt_lines:
            continue
        f = node.func
        name = f.attr if isinstance(f, ast.Attribute) else (
            f.id if isinstance(f, ast.Name) else "")
        if name in BANNED:
            out.append(node.lineno)
    return sorted(set(out))


def _docstring_lines(tree: ast.AST) -> set[int]:
    out: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef,
                                 ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = getattr(node, "body", None) or []
        if not body:
            continue
        first = body[0]
        if not (isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)):
            continue
        out.update(range(first.lineno, (first.end_lineno or first.lineno) + 1))
    return out



def main() -> int:
    bad: list[str] = []
    for rel in PROJECT_IDENTITY_MODULES:
        p = APP / rel
        if not p.is_file():
            print(f"  ! 模块不存在: {rel}")
            bad.append(rel)
            continue
        lines = p.read_text("utf-8").splitlines()
        tree = ast.parse("\n".join(lines), filename=str(p))
        docs = _docstring_lines(tree)
        for lineno in _banned_calls(tree):
            if lineno in docs:
                continue
            code = lines[lineno - 1].strip()
            bad.append(f"{rel}:{lineno}: {code}")
    if bad:
        print("FAIL 项目标识链路出现路径解析（应改用 util/pathx.project_dir）：")
        for item in bad:
            print("  " + item)
        return 1
    print(f"OK   项目路径解析门禁：{len(PROJECT_IDENTITY_MODULES)} 个模块零命中")
    return 0


if __name__ == "__main__":
    sys.exit(main())
