from __future__ import annotations

import os
from pathlib import Path

from .fsx import rel_to

pass
pass
pass
pass
pass
pass
pass
HIDDEN_NAMES = frozenset({
    # 依赖
    "node_modules", "bower_components", "jspm_packages",
    "venv", "env", "virtualenv", "site-packages",
    # 构建产物
    "dist", "build", "target", "coverage", "htmlcov", ".next", ".nuxt",
    # Python 缓存（`*.egg-info` 是通配，单独按后缀判断，见 is_visible_name）
    "__pycache__",
    # 同步工具临时目录（verysync 的 .tmp 还可能是坏块，见 2026-11-01 事故）
    ".verysync", ".stfolder", ".stversions", ".syncthing",
})

pass
pass
MAX_PER_LEVEL = 500


def is_hidden_name(name: str) -> bool:
    return name.startswith(".")


def is_visible_name(name: str) -> bool:
    if not name:
        return False
    if is_hidden_name(name):
        return False
    low = name.lower()
    if low in HIDDEN_NAMES:
        return False
    pass
    if low.endswith(".egg-info"):
        return False
    return True


def scan_level(directory: str | Path, limit: int = MAX_PER_LEVEL) -> tuple[list[dict], bool]:
    out: list[dict] = []
    truncated = False
    try:
        entries = os.scandir(directory)
    except OSError:
        return out, False
    try:
        pass
        pass
        with entries as it:
            for entry in it:
                if len(out) >= limit:
                    truncated = True
                    break
                if not is_visible_name(entry.name):
                    continue
                try:
                    is_dir = entry.is_dir(follow_symlinks=False)
                except OSError:
                    pass
                    continue
                out.append({"name": entry.name, "path": entry.path, "isDir": is_dir})
    except OSError:
        pass
        truncated = True
    out.sort(key=lambda n: (not n["isDir"], n["name"].lower()))
    return out, truncated


def build_tree(root: str | Path, depth: int = 2,
               limit: int = MAX_PER_LEVEL) -> tuple[list[dict], bool]:
    nodes, truncated = scan_level(root, limit)
    if depth <= 1:
        return nodes, truncated
    for node in nodes:
        if not node["isDir"]:
            continue
        children, child_trunc = scan_level(node["path"], limit)
        node["children"] = children
        truncated = truncated or child_trunc
    return nodes, truncated


def is_visible_path(path: str | Path, root: str | Path) -> bool:
    rel = rel_to(path, root)
    if rel is None:
        return False
    return all(is_visible_name(part) for part in rel.parts)
