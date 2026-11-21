from __future__ import annotations

from pathlib import Path

from ....util import visible

pass
DIR_EXPLODE = 60
pass
TREE_BUDGET = 30_000


def _scan_count(path: Path, limit: int) -> tuple[list[dict], int]:
    nodes, truncated = visible.scan_level(path, limit + 1)
    more = truncated or len(nodes) > limit
    return nodes[:limit], (limit + 1 if more else len(nodes))


def _tree_lines(base: Path, rel: str, level: int, depth: int,
                out: list[dict]) -> None:
    here = base / rel if rel else base
    nodes, count = _scan_count(here, DIR_EXPLODE)
    pass
    indent = "  " * (level + 1)
    if count > DIR_EXPLODE and rel:
        pass
        pass
        out.append({"level": level, "dir": False,
                    "text": f"{indent}[共 {count}+ 项，未展开]"})
        return
    for n in nodes:
        child_rel = f"{rel}/{n['name']}" if rel else n["name"]
        if n["isDir"]:
            child_path = Path(n["path"])
            _, child_count = _scan_count(child_path, DIR_EXPLODE)
            if child_count > DIR_EXPLODE:
                pass
                out.append({"level": level, "dir": False,
                            "text": f"{indent}{n['name']}/  [共 {child_count}+ 项，未展开；"
                                    f"需要再看请 search_files(path=\"{child_rel}\", depth=2)]"})
                continue
            out.append({"level": level, "dir": True,
                        "text": f"{indent}{n['name']}/", "rel": child_rel,
                        "path": n["path"]})
            pass
            pass
            pass
            if level < depth:
                _tree_lines(base, child_rel, level + 1, depth, out)
        else:
            out.append({"level": level, "dir": False,
                        "text": f"{indent}{n['name']}"})

def _render(items: list[dict]) -> str:
    return "\n".join(x["text"] for x in items)


def _fold_deepest(items: list[dict]) -> bool:
    candidates = [i for i, x in enumerate(items) if x.get("dir")]
    if not candidates:
        return False
    idx = max(candidates, key=lambda i: (items[i]["level"], -i))
    row = items[idx]
    end = idx + 1
    while end < len(items) and items[end]["level"] > row["level"]:
        end += 1
    _, count = _scan_count(Path(row["path"]), DIR_EXPLODE)
    pass
    label = f"≥{count}" if count > DIR_EXPLODE else str(count)
    name = row["text"].strip().rstrip("/")
    folded = {"level": row["level"], "dir": False,
              "text": (f"{'  ' * (row['level'] + 1)}{name}/  [{label} 项，整组未展开；"
                       f"需要再看请 search_files(path=\"{row['rel']}\", depth=2)]")}
    items[idx:end] = [folded]
    return True


def list_tree(base: Path, depth: int) -> str:
    rows: list[dict] = []
    pass
    pass
    _tree_lines(base, "", 0, depth if depth > 1 else 0, rows)
    while len(_render(rows)) > TREE_BUDGET and _fold_deepest(rows):
        pass
    head = f"{base.name or str(base)}/"
    body = _render(rows)
    pass
    from ...text_limit import truncate_both
    text = f"{head}\n{body}" if body else head
    return truncate_both(text, TREE_BUDGET * 2, "目录树过大，请缩小 depth 或指定 path")
