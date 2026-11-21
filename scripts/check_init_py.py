from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"

pass
ALLOWED: dict[str, str] = {}


def _is_allowed(node: ast.stmt) -> tuple[bool, str]:
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) \
            and isinstance(node.value.value, str):
        return True, ""
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return True, ""
    if isinstance(node, ast.Assign):
        pass
        if all(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets):
            return True, ""
        return False, "顶层赋值（常量/表/状态）应迁到同目录模块"
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) \
            and node.target.id == "__all__":
        return True, ""
    if isinstance(node, ast.If):
        pass
        if "TYPE_CHECKING" in ast.unparse(node.test):
            return True, ""
        return False, "顶层 if 控制流应迁到同目录模块"
    if isinstance(node, ast.Try):
        return False, "顶层 try 兼容兜底应迁到同目录模块（或改用 __getattr__ 转发）"
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if node.name in ("__getattr__", "__dir__"):
            return True, ""
        return False, f"函数定义 {node.name}() 应迁到同目录模块"
    if isinstance(node, ast.ClassDef):
        return False, f"类定义 {node.name} 应迁到同目录模块"
    if isinstance(node, ast.Pass):
        return True, ""
    if isinstance(node, (ast.For, ast.While, ast.With)):
        return False, f"顶层 {type(node).__name__} 控制流应迁到同目录模块"
    if isinstance(node, ast.Expr):
        return False, "顶层表达式/调用（副作用）应迁到同目录模块"
    if isinstance(node, (ast.Raise, ast.Assert, ast.Delete, ast.Global, ast.Nonlocal)):
        return False, f"顶层 {type(node).__name__} 语句应迁到同目录模块"
    return False, f"顶层 {type(node).__name__} 语句应迁到同目录模块"


def check_init_py() -> list[str]:
    errors: list[str] = []
    for p in sorted(BACKEND.rglob("__init__.py")):
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        if "vendor" in p.parts or rel in ALLOWED:
            continue
        try:
            tree = ast.parse(p.read_text("utf-8-sig"), filename=rel)
        except SyntaxError as e:
            errors.append(f"{rel}:{e.lineno}: 语法错误：{e.msg}")
            continue
        for node in tree.body:
            ok, why = _is_allowed(node)
            if not ok:
                errors.append(f"{rel}:{node.lineno}: {why}"
                              f"（见 ARCH_STYLE §零 R5：__init__.py 只许导入/适配）")
    return errors


def main() -> int:
    errors = check_init_py()
    if errors:
        print("包边界检查失败（__init__.py 出现逻辑代码）:")
        for e in errors:
            print(" -", e)
        return 1
    print("包边界检查通过（所有 __init__.py 只含导入/适配）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
