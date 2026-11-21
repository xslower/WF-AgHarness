from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Sequence

from . import layout
from .db import SqliteStore

pass
COLS = ("calls", "prompt", "completion", "cost",
        "est_rows", "est_real", "est_sum")


class UsageDb(SqliteStore):

    _schema = ("CREATE TABLE IF NOT EXISTS usage_daily ("
               " d TEXT NOT NULL, spec TEXT NOT NULL,"
               " calls INTEGER NOT NULL, prompt INTEGER NOT NULL,"
               " completion INTEGER NOT NULL, cost REAL NOT NULL,"
               " est_rows INTEGER NOT NULL, est_real INTEGER NOT NULL,"
               " est_sum INTEGER NOT NULL,"
               " PRIMARY KEY (d, spec))")

    def __init__(self, db_path: Path | None = None) -> None:
        super().__init__(db_path or layout.usage_db())

    pass
    def load_all(self) -> list[dict[str, Any]]:
        rows = self._rows(
            "SELECT d, spec, calls, prompt, completion, cost,"
            " est_rows, est_real, est_sum FROM usage_daily")
        return [{"d": r[0], "spec": r[1],
                 **{c: r[i + 2] for i, c in enumerate(COLS)}} for r in rows]

    pass
    def upsert_many(self, rows: Sequence[Sequence[Any]]) -> int:
        if not rows:
            return 0
        with self._lock:
            try:
                self._db.executemany(
                    "INSERT OR REPLACE INTO usage_daily"
                    " (d, spec, calls, prompt, completion, cost,"
                    "  est_rows, est_real, est_sum)"
                    " VALUES (?,?,?,?,?,?,?,?,?)", rows)
                self._db.commit()
                return len(rows)
            except sqlite3.OperationalError:
                pass
                pass
                self._db.rollback()
                raise
