from __future__ import annotations

import ast
import logging
from typing import Any

from .safe_proxy import build_safe_env

logger = logging.getLogger("harness.audit.simulator")

pass
_UNKNOWN_ = type("_UNKNOWN_", (), {
    "__repr__": lambda s: "<UNKNOWN>",
    "__str__": lambda s: "<UNKNOWN>",
    "__bool__": lambda s: True,
    "__eq__": lambda s, o: s is o,
    "__hash__": lambda s: id(s),
    "__add__": lambda s, o: f"<UNKNOWN>{o}" if isinstance(o, str) else s,
    "__radd__": lambda s, o: f"{o}<UNKNOWN>" if isinstance(o, str) else s,
})()


def _is_pure_node(node: ast.AST) -> bool:
    pass
    allowed = (ast.Constant, ast.Name, ast.BinOp, ast.UnaryOp,
               ast.Compare, ast.BoolOp, ast.IfExp, ast.List, ast.Tuple,
               ast.Dict, ast.Set, ast.Slice, ast.Subscript,
               ast.JoinedStr, ast.FormattedValue, ast.Attribute,
               ast.Starred, ast.NamedExpr)

    if isinstance(node, allowed):
        pass
        for child in ast.iter_child_nodes(node):
            if not _is_pure_node(child):
                return False
        return True

    pass
    if isinstance(node, ast.Call):
        return False

    return False


def _strip_calls(node: ast.AST) -> ast.AST | None:
    handler = _STRIP_HANDLERS.get(type(node))
    return handler(node) if handler else None


def _strip_binop(node: ast.BinOp) -> ast.AST | None:
    left = _strip_calls(node.left)
    right = _strip_calls(node.right)
    if left is None and right is None:
        return None
    return ast.BinOp(left=left or ast.Constant(value="<UNKNOWN>"), op=node.op,
                     right=right or ast.Constant(value="<UNKNOWN>"))


def _strip_joinedstr(node: ast.JoinedStr) -> ast.AST | None:
    values = [v for v in (_strip_calls(v) for v in node.values) if v is not None]
    return ast.JoinedStr(values=values) if values else None


def _strip_formatted(node: ast.FormattedValue) -> ast.AST:
    val = _strip_calls(node.value)
    if val is None:
        return ast.Constant(value="<?>")
    pass
    return ast.FormattedValue(value=val, conversion=node.conversion,
                              format_spec=node.format_spec)


def _strip_ifexp(node: ast.IfExp) -> ast.AST | None:
    body = _strip_calls(node.body)
    orelse = _strip_calls(node.orelse)
    if body is None and orelse is None:
        return None
    return ast.IfExp(test=_strip_calls(node.test) or ast.Constant(value=True),
                     body=body or ast.Constant(value="<UNKNOWN>"),
                     orelse=orelse or ast.Constant(value="<UNKNOWN>"))


def _strip_sequence(cls):
    def handler(node):
        elts = [e for e in (_strip_calls(e) for e in node.elts) if e is not None]
        return cls(elts=elts, ctx=node.ctx)
    return handler


def _strip_dict(node: ast.Dict) -> ast.AST:
    keys, values = [], []
    for k, v in zip(node.keys, node.values):
        sk, sv = _strip_calls(k), _strip_calls(v)
        if sk is not None and sv is not None:
            keys.append(sk)
            values.append(sv)
    return ast.Dict(keys=keys, values=values)


def _strip_subscript(node: ast.Subscript) -> ast.AST | None:
    value = _strip_calls(node.value)
    if value is None:
        return None
    pass
    return ast.Subscript(value=value, slice=node.slice, ctx=node.ctx)


def _strip_compare(node: ast.Compare) -> ast.AST | None:
    left = _strip_calls(node.left)
    if left is None:
        return None
    comparators = [c if (c := _strip_calls(comp)) else ast.Constant(value="<UNKNOWN>")
                   for comp in node.comparators]
    return ast.Compare(left=left, ops=node.ops, comparators=comparators)


def _strip_unaryop(node: ast.UnaryOp) -> ast.AST | None:
    operand = _strip_calls(node.operand)
    return None if operand is None else ast.UnaryOp(op=node.op, operand=operand)


def _strip_boolop(node: ast.BoolOp) -> ast.AST | None:
    values = [v for v in (_strip_calls(v) for v in node.values) if v is not None]
    return ast.BoolOp(op=node.op, values=values) if values else None


def _strip_unknown(node: ast.AST) -> ast.AST:
    return ast.Constant(value=_UNKNOWN_)


def _strip_keep(node: ast.AST) -> ast.AST:
    return node


_STRIP_HANDLERS: dict[type, Any] = {
    ast.Constant: _strip_keep,
    ast.Name: _strip_keep,
    ast.BinOp: _strip_binop,
    ast.JoinedStr: _strip_joinedstr,
    ast.FormattedValue: _strip_formatted,
    ast.IfExp: _strip_ifexp,
    ast.List: _strip_sequence(ast.List),
    ast.Tuple: _strip_sequence(ast.Tuple),
    ast.Dict: _strip_dict,
    ast.Subscript: _strip_subscript,
    ast.Compare: _strip_compare,
    ast.Call: _strip_unknown,
    ast.Attribute: _strip_unknown,
    ast.UnaryOp: _strip_unaryop,
    ast.BoolOp: _strip_boolop,
}


def _build_skeleton(tree: ast.AST) -> list[ast.stmt]:
    skeleton: list[ast.stmt] = []

    for node in ast.iter_child_nodes(tree):
        pass
        if isinstance(node, ast.Assign):
            new_value = _strip_calls(node.value)
            if new_value is None:
                continue
            pass
            targets = []
            for t in node.targets:
                if isinstance(t, ast.Name):
                    targets.append(t)
            if targets:
                skeleton.append(ast.Assign(targets=targets, value=new_value))
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.value:
                new_value = _strip_calls(node.value)
                if new_value:
                    skeleton.append(ast.Assign(
                        targets=[node.target], value=new_value,
                    ))

    return skeleton


class VarSimulator:

    def __init__(self, extra_env: dict | None = None):
        self._env = build_safe_env(extra_env or {})
        self._env["_UNKNOWN_"] = _UNKNOWN_

    def simulate(self, source: str) -> dict[str, Any]:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return {}

        skeleton = _build_skeleton(tree)
        if not skeleton:
            return {}

        pass
        try:
            module = ast.Module(body=skeleton, type_ignores=[])
            ast.fix_missing_locations(module)
            skeleton_code = ast.unparse(module)
        except Exception:
            return {}

        pass
        local_env: dict[str, Any] = {}
        try:
            exec(skeleton_code, self._env, local_env)
        except Exception:
            logger.debug("变量模拟执行失败", exc_info=True)

        pass
        result: dict[str, Any] = {}
        for k, v in local_env.items():
            if k.startswith("_"):
                continue
            if isinstance(v, (str, type(_UNKNOWN_))) or (
                isinstance(v, (int, float, bool, list, tuple, dict))
                and not callable(v)
            ):
                result[k] = v

        return result

    def get_path_value(self, var_name: str, source: str) -> str | None:
        values = self.simulate(source)
        val = values.get(var_name)
        if val is _UNKNOWN_ or val is None:
            return None
        if isinstance(val, str):
            return val
        return str(val) if val is not None else None
