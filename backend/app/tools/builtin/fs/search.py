from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import TYPE_CHECKING

from ....util import visible
from ....util.jsonx import err
from .common import resolve

if TYPE_CHECKING:
    from ... import ToolContext

__all__ = ["search_files"]

pass
pass
_MAX_DEPTH = 3

_MAX_HITS = 300

def _list_tree(base: Path, depth: int) -> str:
    from .tree import list_tree
    return list_tree(base, depth)

def _glob_pats(pattern: str) -> list[str]:
    return [pattern, pattern[3:]] if pattern.startswith("**/") else [pattern]

def _match_names(base: Path, pats: list[str], depth: int) -> str:
    hits: list[str] = []
    frontier: list[tuple[Path, int, str]] = [(base, 0, "")]
    while frontier and len(hits) < _MAX_HITS:
        path_i, level, prefix = frontier.pop(0)
        nodes, _ = visible.scan_level(path_i, 500)
        for n in nodes:
            rel = f"{prefix}{n['name']}"
            if any(fnmatch.fnmatch(n["name"], p) or fnmatch.fnmatch(rel, p) for p in pats):
                hits.append(rel)
                if len(hits) >= _MAX_HITS:
                    break
            if n["isDir"] and level + 1 < depth:
                frontier.append((Path(n["path"]), level + 1, f"{prefix}{n['name']}/"))
    return "\n".join(hits) or "(无匹配)"

def search_files(pattern: str = "", ctx: "ToolContext" = None, path: str = ".",
                 depth: int = 3) -> str:
    base = resolve(ctx, path) if ctx else Path(path)
    if not base.is_dir():
        return err(f"目录不存在: {base}")
    depth = max(1, min(int(depth or 3), _MAX_DEPTH))

    if not pattern:
        return _list_tree(base, depth)
    return _match_names(base, _glob_pats(pattern), depth)
