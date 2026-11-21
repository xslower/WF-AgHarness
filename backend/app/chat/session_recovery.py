from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from ..store import layout
from ..store.db import Table, open_ro
from .sessions import SessionStore


def _data_dirs(project: str) -> list[Path]:
    out = [layout.project_agent_dir(project)]
    rt = layout.runtime_project_dir(project)
    if rt is not None:
        out.append(rt)
    return out


def _chat_files(project: str) -> list[tuple[str, Path]]:
    found: dict[str, Path] = {}
    for base in _data_dirs(project):
        if not base.is_dir():
            continue
        for f in sorted(base.glob("chat.*.db")):
            sid = f.name[len("chat."):-len(".db")]
            if sid and sid not in found:
                found[sid] = f
    return list(found.items())


def _head(db: Path) -> dict | None:
    try:
        conn = open_ro(db)
        try:
            names = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            if "messages" not in names:
                return None
            count = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
            if not count:
                return None
            rows = conn.execute("SELECT msg FROM messages ORDER BY seq LIMIT 20").fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return None
    title = ""
    for r in rows:
        try:
            m = json.loads(r[0]) if isinstance(r[0], str) else {}
        except (ValueError, TypeError):
            continue
        if m.get("role") == "user":
            text = re.sub(r"\s+", " ", str(m.get("content") or "")).strip()
            pass
            text = re.sub(r"^now:\s*\d{4}年.*?\s{2,}", "", text).strip()
            if text:
                title = text[:60]
                break
    return {"title": title or "恢复的会话", "message_count": int(count)}


def _existing_dir(path: str) -> bool:
    return bool(path) and Path(path).is_dir()


def recover_sessions(store: SessionStore, project: str) -> dict:
    stats = {"scanned": 0, "recovered": 0, "rebound": 0, "skipped": 0}
    for sid, db in _chat_files(project):
        stats["scanned"] += 1
        head = _head(db)
        if head is None:
            stats["skipped"] += 1
            continue
        row = store.session_head(sid)
        with store.sys_tx() as tbl:
            if row is None:
                pass
                tbl.insert({
                    "id": sid, "title": head["title"], "project": project,
                    "created_at": db.stat().st_mtime,
                    "message_count": head["message_count"],
                    "kind": "", "origin": "", "updated_at": db.stat().st_mtime,
                })
                stats["recovered"] += 1
            elif row[2] == project:
                stats["skipped"] += 1
            elif _existing_dir(row[2]):
                stats["skipped"] += 1
            else:
                pass
                tbl.update({"project": project}, where={"id": sid})
                stats["rebound"] += 1
        store._close_session(sid)
    return stats


def retarget_sessions(store: SessionStore, old: str, new: str) -> int:
    like = (old.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            + "/%")
    rows = store._sys_fetchall(
        "SELECT id, project FROM sessions WHERE project=? OR project LIKE ? ESCAPE '\\'",
        (old, like))
    for sid, old_project in rows:
        target = new + old_project[len(old):]
        with store.sys_tx() as tbl:
            tbl.update({"project": target}, where={"id": sid})
        store._close_session(sid)
    return len(rows)
