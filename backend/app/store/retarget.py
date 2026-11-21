from __future__ import annotations

import sqlite3

from ..util import pathx


def project_scope_key(project) -> str:
    return pathx.project_path(str(project or ""))


def in_scope(key: str, old_key: str) -> bool:
    return key == old_key or key.startswith(old_key + "/")


def rebase(key: str, old_key: str, new_key: str) -> str:
    return new_key + key[len(old_key):]


def retarget_project_column(conn: sqlite3.Connection, table: str,
                            old_key: str, new_key: str) -> int:
    if not old_key or old_key == new_key:
        return 0
    moved = 0
    rows = conn.execute(f"SELECT DISTINCT project FROM {table}").fetchall()
    for (raw,) in rows:
        key = project_scope_key(raw)
        if not in_scope(key, old_key):
            continue
        cur = conn.execute(
            f"UPDATE OR REPLACE {table} SET project=? WHERE project=?",
            (rebase(key, old_key, new_key), raw))
        moved += cur.rowcount
    return moved


__all__ = ["project_scope_key", "in_scope", "rebase", "retarget_project_column"]
