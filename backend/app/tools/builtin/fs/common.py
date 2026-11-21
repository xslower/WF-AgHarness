from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from ....chat.recent import publish_file_changed
from ....util.fsx import rel_to

logger = logging.getLogger("harness.fs")


async def guard_paths(ctx, action: str, *paths: str) -> str | None:
    check = getattr(ctx, "path_check", None)
    if check is None:
        return None
    targets = [p for p in paths if p]
    if not targets:
        return None
    allowed, reason = await check(action, targets)
    if allowed:
        return None
    return json.dumps({"error": "操作被安全策略拒绝", "reason": reason},
                      ensure_ascii=False)


def resolve(ctx, path: str) -> Path:
    p = Path(path or ".").expanduser()
    if not p.is_absolute():
        root = getattr(ctx, "project", "") or getattr(ctx, "cwd", "") or "."
        p = (Path(root) / p).resolve()
    return _fix_case(p)


def _fix_case(p: Path) -> Path:
    if p.exists():
        return p
    cur = Path(p.anchor)
    parts = p.parts[1:]
    for i, seg in enumerate(parts):
        nxt = cur / seg
        if not nxt.exists():
            try:
                hits = [e.name for e in cur.iterdir()
                        if e.name.lower() == seg.lower()]
            except OSError:
                return cur.joinpath(*parts[i:])
            if len(hits) != 1:
                return cur.joinpath(*parts[i:])
            nxt = cur / hits[0]
        cur = nxt
    return cur


def _rel(p: Path, root: Path) -> str:
    rel = rel_to(p, root)
    return str(rel).replace("\\", "/") if rel is not None else p.name

def _emit_file(ctx, path: Path, op: str, kind: str = "file") -> None:
    try:
        report = getattr(ctx, "report_file", None)
        if report is not None and kind == "file" and op in ("created", "modified", "copied", "moved_to"):
            report(str(path))
    except Exception:
        logger.debug("report_file 失败: %s", path, exc_info=True)
    publish_file_changed(str(getattr(ctx, "project_dir", lambda: "")() or ""), path, op, kind)

def _stat_info(p: Path) -> str:
    st = p.stat()
    info = {
        "path": str(p),
        "type": "directory" if p.is_dir() else "file",
        "size": st.st_size,
        "mode": oct(st.st_mode),
        "mtime": st.st_mtime,
        "suffix": p.suffix or "(none)",
    }
    if p.is_file():
        info["lines"] = len(p.read_text("utf-8", errors="replace").splitlines())
    return json.dumps(info, ensure_ascii=False)


def physical_lines(text: str) -> list[str]:
    if not text:
        return []
    rows = text.split("\n")
    if rows and rows[-1] == "":
        rows.pop()
    return [r[:-1] if r.endswith("\r") else r for r in rows]
