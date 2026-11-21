from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Optional

from . import layout
from .db import SqliteStore

pass
OWNERS = ("backend", "frontend")
pass
ACTIONS = ("session", "workflow")
pass
KINDS = ("every", "cron")

COLS = ("name", "owner", "action", "kind", "spec", "payload", "enabled", "updated_at")


class TimerDb(SqliteStore):

    _schema = ("CREATE TABLE IF NOT EXISTS timer_job ("
               " name TEXT PRIMARY KEY,"
               " owner TEXT NOT NULL DEFAULT 'frontend',"
               " action TEXT NOT NULL DEFAULT 'session',"
               " kind TEXT NOT NULL,"
               " spec TEXT NOT NULL,"
               " payload TEXT NOT NULL DEFAULT '{}',"
               " enabled INTEGER NOT NULL DEFAULT 1,"
               " updated_at REAL NOT NULL)")

    def __init__(self, db_path: Path | None = None) -> None:
        super().__init__(db_path or layout.timers_db())

    pass
    def load_all(self, owner: str | None = None,
                 enabled_only: bool = False) -> list[dict[str, Any]]:
        sql = f"SELECT {', '.join(COLS)} FROM timer_job"
        where: list[str] = []
        args: list[Any] = []
        if owner is not None:
            where.append("owner = ?")
            args.append(owner)
        if enabled_only:
            where.append("enabled = 1")
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY name"
        return [self._row_dict(r) for r in self._rows(sql, args)]

    def get(self, name: str) -> Optional[dict[str, Any]]:
        row = self._row(f"SELECT {', '.join(COLS)} FROM timer_job WHERE name = ?",
                        (name,))
        return None if row is None else self._row_dict(row)

    @staticmethod
    def _row_dict(row) -> dict[str, Any]:
        return {"name": row[0], "owner": row[1], "action": row[2], "kind": row[3],
                "spec": row[4], "payload": self_load(row[5]),
                "enabled": bool(row[6]), "updated_at": row[7]}

    pass
    def upsert(self, name: str, kind: str, spec: str, payload: Any = None,
               owner: str = "frontend", action: str = "session",
               enabled: bool = True, updated_at: float = 0.0) -> None:
        self.validate(owner=owner, action=action, kind=kind)
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO timer_job"
                " (name, owner, action, kind, spec, payload, enabled, updated_at)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (name, owner, action, kind, spec, self.dump(payload or {}),
                 1 if enabled else 0, updated_at or time.time()))
            self._db.commit()

    def update(self, name: str, /, **fields: Any) -> int:
        sets: list[str] = []
        args: list[Any] = []
        for key, val in fields.items():
            if key not in COLS or key in ("name", "updated_at"):
                raise ValueError(f"不可修改的字段：{key!r}")
            if key == "payload":
                val = self.dump(val or {})
            elif key == "enabled":
                val = 1 if val else 0
            sets.append(f"{key} = ?")
            args.append(val)
        if not sets:
            return 0
        sets.append("updated_at = ?")
        args.append(time.time())
        args.append(name)
        return self._write(f"UPDATE timer_job SET {', '.join(sets)} WHERE name = ?",
                           args)

    def set_enabled(self, name: str, enabled: bool) -> int:
        return self.update(name, enabled=enabled)

    def delete(self, name: str) -> int:
        return self._write("DELETE FROM timer_job WHERE name = ?", (name,))

    pass
    @staticmethod
    def validate(owner: str, action: str, kind: str) -> None:
        if owner not in OWNERS:
            raise ValueError(f"owner 只能是 {'/'.join(OWNERS)}：{owner!r}")
        if action not in ACTIONS:
            raise ValueError(f"action 只能是 {'/'.join(ACTIONS)}：{action!r}")
        if kind not in KINDS:
            raise ValueError(f"kind 只能是 {'/'.join(KINDS)}：{kind!r}")


def self_load(text: str) -> Any:
    import json
    try:
        return json.loads(text) if text else {}
    except Exception:
        return {}
