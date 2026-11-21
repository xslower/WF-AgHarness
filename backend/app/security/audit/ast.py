from __future__ import annotations

import ast


def attr_chain(node: ast.AST) -> tuple[list[str], ast.AST]:
    parts: list[str] = []
    current: ast.AST = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    return parts, current


def call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if not isinstance(func, ast.Attribute):
        return None
    parts, root = attr_chain(func)
    if isinstance(root, ast.Name):
        parts.append(root.id)
    parts.reverse()
    return ".".join(parts)


def dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if not isinstance(node, ast.Attribute):
        return None
    parts, root = attr_chain(node)
    if not isinstance(root, ast.Name):
        return None
    parts.append(root.id)
    parts.reverse()
    return ".".join(parts)


