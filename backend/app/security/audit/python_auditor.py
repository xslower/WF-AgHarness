from __future__ import annotations

import ast
import logging
from typing import Any

from .call_policy import BLACKLIST, FORBIDDEN_CALLS
from .base import Auditor, AuditResult, CallSite, CallSiteRisk, PathInfo, PathConfidence

logger = logging.getLogger("harness.audit.python")

pass
pass
pass
pass
_BLACKLIST = BLACKLIST

pass

pass
_FORBIDDEN = FORBIDDEN_CALLS

pass
_BLACKLIST_MAP: dict[str, tuple[str, int, list[int]]] = {
    name: (full, risk, path_idxs) for name, full, risk, path_idxs in _BLACKLIST
}
_FORBIDDEN_SET: set[str] = {name for name, _ in _FORBIDDEN}

pass
_SAFE_MODULES = {
    "os.path", "os.sep", "json", "json.loads", "json.dumps",
    "math", "re", "datetime", "collections", "itertools",
    "pathlib.PurePath", "pathlib.Path",
}


class PythonAuditor(Auditor):

    def __init__(self):
        self._imports: dict[str, str] = {}
        self._var_values: dict[str, Any] = {}

    def audit(self, source: str, script_path: str = "") -> AuditResult:
        self._imports.clear()
        self._var_values.clear()

        try:
            tree = ast.parse(source, filename=script_path or "<string>")
        except SyntaxError as e:
            return AuditResult(
                language="python", safe=False,
                errors=[f"语法错误: {e}"],
            )

        callsites: list[CallSite] = []
        forbidden: list[CallSite] = []

        pass
        self._collect_imports(tree)
        self._collect_assignments(tree)

        pass
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                result = self._check_call(node)
                if result is None:
                    continue
                if result.risk == CallSiteRisk.dangerous:
                    forbidden.append(result)
                else:
                    callsites.append(result)

        return AuditResult(
            language="python",
            safe=len(callsites) == 0 and len(forbidden) == 0,
            callsites=callsites,
            forbidden_calls=forbidden,
        )

    pass
    def _collect_imports(self, tree: ast.AST):
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._imports[alias.asname or alias.name] = alias.name
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    full = f"{module}.{alias.name}" if module else alias.name
                    self._imports[alias.asname or alias.name] = full

    pass
    def _collect_assignments(self, tree: ast.AST):
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    name = self._get_name(target)
                    if name:
                        val = self._eval_expr(node.value)
                        if val is not None:
                            self._var_values[name] = val

    def _get_name(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        return None

    def _eval_expr(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return self._var_values.get(node.id)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left = self._eval_expr(node.left)
            right = self._eval_expr(node.right)
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            if left is not None and right is not None:
                return f"{left}{right}"
        if isinstance(node, ast.JoinedStr):
            parts = []
            for v in node.values:
                if isinstance(v, ast.Constant):
                    parts.append(str(v.value))
                elif isinstance(v, ast.FormattedValue):
                    pv = self._eval_expr(v.value)
                    parts.append(str(pv) if pv is not None else "<?>")
            return "".join(parts)
        if isinstance(node, ast.Call):
            name = self._resolve_call_name(node)
            if name and name.startswith("os.path.join"):
                return self._simulate_join(node)
        return None

    def _simulate_join(self, node: ast.Call) -> str | None:
        import os
        parts = []
        for arg in node.args:
            val = self._eval_expr(arg)
            if val is None:
                return None
            parts.append(str(val))
        return os.path.join(*parts)

    pass
    def _check_call(self, node: ast.Call) -> CallSite | None:
        name = self._resolve_call_name(node)
        if not name:
            return None

        pass
        if name in _FORBIDDEN_SET:
            return CallSite(
                method=name, line_no=node.lineno,
                risk=CallSiteRisk.dangerous,
                expression=self._src_slice(node),
            )

        pass
        if name in _BLACKLIST_MAP:
            full_name, risk_level, path_idxs = _BLACKLIST_MAP[name]
            paths = self._extract_paths(node, path_idxs)
            return CallSite(
                method=name, line_no=node.lineno,
                paths=paths, risk=CallSiteRisk.monitored,
                expression=self._src_slice(node),
            )

        return None

    def _resolve_call_name(self, node: ast.Call) -> str | None:
        if isinstance(node.func, ast.Name):
            raw = node.func.id
            return self._imports.get(raw, raw)
        if isinstance(node.func, ast.Attribute):
            base = self._resolve_attr_chain(node.func)
            return base
        return None

    def _resolve_attr_chain(self, node: ast.Attribute) -> str:
        pass
        pass
        from .ast import attr_chain
        parts, root = attr_chain(node)
        if isinstance(root, ast.Call):
            callee_name = self._resolve_call_name(root)
            if callee_name:
                parts.append(callee_name)
        elif isinstance(root, ast.Name):
            parts.append(self._imports.get(root.id, root.id))
        parts.reverse()
        return ".".join(parts)

    def _extract_paths(self, node: ast.Call, path_idxs: list[int]) -> list[PathInfo]:
        paths: list[PathInfo] = []

        if not path_idxs:
            pass
            if isinstance(node.func, ast.Attribute):
                base = node.func.value
                expr = self._expr_text(base)
                paths.append(PathInfo(
                    value=expr, confidence=PathConfidence.unknown,
                    expression=expr, line_no=node.lineno,
                ))
            return paths

        args = node.args
        for idx in path_idxs:
            if idx >= len(args):
                continue
            arg_node = args[idx]
            expr = self._expr_text(arg_node)
            val = self._eval_expr(arg_node)

            if val is not None and isinstance(val, str):
                paths.append(PathInfo(
                    value=val, confidence=PathConfidence.known,
                    expression=expr, line_no=node.lineno,
                ))
            elif "<UNKNOWN>" in str(val or ""):
                paths.append(PathInfo(
                    value=str(val), confidence=PathConfidence.partial,
                    expression=expr, line_no=node.lineno,
                ))
            else:
                paths.append(PathInfo(
                    value=expr, confidence=PathConfidence.unknown,
                    expression=expr, line_no=node.lineno,
                ))

        return paths

    def _expr_text(self, node: ast.AST) -> str:
        try:
            return ast.unparse(node)
        except Exception:
            return str(type(node).__name__)

    def _src_slice(self, node: ast.Call) -> str:
        try:
            src = ast.unparse(node)
            return src[:200]
        except Exception:
            return f"<line {node.lineno}>"
