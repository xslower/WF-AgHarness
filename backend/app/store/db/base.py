from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Sequence

from ...util.fsx import ensure_dir

logger = logging.getLogger("harness.store.db")

pass
pass
_DB_LOCKS: dict[str, threading.RLock] = {}
_DB_LOCKS_GUARD = threading.Lock()

pass
pass
BUSY_TIMEOUT_MS = 30000
pass
_WRITE_RETRIES = 3
_WRITE_RETRY_BASE = 0.05


@dataclass(frozen=True)
class Cmp:

    op: str
    value: Any


@dataclass(frozen=True)
class SqlExpr:

    sql: str


def db_lock_for(path: str | Path):
    try:
        key = str(Path(path).resolve())
    except OSError:
        key = str(path)
    with _DB_LOCKS_GUARD:
        lk = _DB_LOCKS.get(key)
        if lk is None:
            lk = _DB_LOCKS[key] = threading.RLock()
        return lk


def _is_busy(exc: sqlite3.OperationalError) -> bool:
    return "locked" in str(exc).lower() or "busy" in str(exc).lower()


def open_db(path: str | Path, schema: str = "") -> sqlite3.Connection:
    p = ensure_dir(Path(path).parent) / Path(path).name
    with db_lock_for(p):
        conn = sqlite3.connect(str(p), check_same_thread=False, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        pass
        pass
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
        if schema:
            conn.executescript(schema)
        conn.commit()
    return conn


def open_ro(path: str | Path, timeout: float = 10) -> sqlite3.Connection:
    p = Path(path).resolve()
    conn = sqlite3.connect(f"file:{p.as_posix()}?mode=ro", uri=True, timeout=timeout)
    return conn


def backup(src: str | Path, dst: str | Path) -> None:
    target = Path(dst)
    ensure_dir(target.parent)
    if target.exists():
        raise FileExistsError(f"目标已存在，拒绝覆盖：{target}")
    s = open_ro(src)
    d = sqlite3.connect(str(target), timeout=10)
    try:
        s.backup(d)
    finally:
        d.close()
        s.close()


class SqliteStore:

    _schema = ""

    def __init__(self, path: str | Path) -> None:
        pass
        self._lock = db_lock_for(path)
        self._db = open_db(path, self._schema)

    pass
    def _write(self, sql: str, args: Sequence[Any] = ()) -> int:
        with self._lock:
            for attempt in range(_WRITE_RETRIES + 1):
                try:
                    cur = self._db.execute(sql, tuple(args))
                    self._db.commit()
                    return cur.rowcount
                except sqlite3.OperationalError as e:
                    if not _is_busy(e) or attempt >= _WRITE_RETRIES:
                        raise
                    self._db.rollback()
                    delay = _WRITE_RETRY_BASE * (2 ** attempt)
                    logger.warning("SQLite 写遇到锁，%.2fs 后重试(%d/%d): %s",
                                   delay, attempt + 1, _WRITE_RETRIES, e)
                    time.sleep(delay)
        raise AssertionError("unreachable")

    def _row(self, sql: str, args: Sequence[Any] = ()) -> sqlite3.Row | tuple | None:
        return self._db.execute(sql, tuple(args)).fetchone()

    def _rows(self, sql: str, args: Sequence[Any] = ()) -> list:
        return self._db.execute(sql, tuple(args)).fetchall()

    def _exists(self, sql: str, args: Sequence[Any] = ()) -> bool:
        return self._row(sql, tuple(args)) is not None

    pass
    @staticmethod
    def dump(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def load(text: str) -> Any:
        return json.loads(text)

    def close(self) -> None:
        self._db.close()


pass
pass
pass
pass
pass
pass
pass
pass
pass
pass
pass
pass
pass
pass
pass
pass
pass
pass
pass


class Table:

    _json_columns: frozenset[str] = frozenset()

    def __init__(self, conn: sqlite3.Connection, name: str) -> None:
        self._conn = conn
        self._name = name
        self._last_cur: sqlite3.Cursor | None = None

    pass

    def insert(self, row: dict[str, Any], or_replace: bool = False) -> None:
        cooked = self._encode(row)
        cols = ", ".join(cooked)
        ph = ", ".join("?" for _ in cooked)
        action = "INSERT OR REPLACE" if or_replace else "INSERT"
        self._conn.execute(
            f"{action} INTO {self._name} ({cols}) VALUES ({ph})",
            tuple(cooked.values()))

    def insert_many(self, rows: list[dict[str, Any]],
                    or_replace: bool = False) -> None:
        if not rows:
            return
        cooked = [self._encode(r) for r in rows]
        cols = ", ".join(cooked[0])
        ph = ", ".join("?" for _ in cooked[0])
        vals = [tuple(r.values()) for r in cooked]
        action = "INSERT OR REPLACE" if or_replace else "INSERT"
        self._conn.executemany(
            f"{action} INTO {self._name} ({cols}) VALUES ({ph})", vals)

    def upsert(self, row: dict[str, Any], conflict: list[str] | tuple[str, ...],
                updates: dict[str, Any] | None = None) -> None:
        cooked = self._encode(row)
        cols = ", ".join(cooked)
        ph = ", ".join("?" for _ in cooked)
        keys = list(conflict)
        if updates is None:
            updates = {k: v for k, v in cooked.items() if k not in keys}
        set_parts: list[str] = []
        set_vals: list[Any] = []
        for k, v in updates.items():
            if isinstance(v, SqlExpr):
                set_parts.append(f"{k}={v.sql}")
            else:
                set_parts.append(f"{k}=?")
                set_vals.append(v)
        sql = (f"INSERT INTO {self._name} ({cols}) VALUES ({ph}) "
               f"ON CONFLICT({', '.join(keys)}) DO UPDATE SET {', '.join(set_parts)}")
        self._conn.execute(sql, tuple(cooked.values()) + tuple(set_vals))

    def select(self, where: dict[str, Any] | None = None,
               order: str = "", limit: int = 0,
               cols: str = "*") -> list[dict[str, Any]]:
        sql = f"SELECT {cols} FROM {self._name}"
        clause, params = self._where(where)
        if clause:
            sql += f" WHERE {clause}"
        if order:
            sql += f" ORDER BY {order}"
        if limit > 0:
            sql += f" LIMIT {limit}"
        self._last_cur = self._conn.execute(sql, tuple(params))
        rows = self._last_cur.fetchall()
        return [self._decode(r) for r in rows]

    def select_one(self, where: dict[str, Any] | None = None,
                   order: str = "", cols: str = "*") -> dict[str, Any] | None:
        rows = self.select(where=where, order=order, limit=1, cols=cols)
        return rows[0] if rows else None

    def update(self, updates: dict[str, Any],
               where: dict[str, Any] | None = None) -> int:
        if not updates:
            return 0
        cooked = self._encode(updates)
        set_ = ", ".join(f"{k}=?" for k in cooked)
        w_clause, w_params = self._where(where)
        sql = f"UPDATE {self._name} SET {set_}"
        if w_clause:
            sql += f" WHERE {w_clause}"
        cur = self._conn.execute(sql, tuple(cooked.values()) + tuple(w_params))
        return cur.rowcount

    def delete(self, where: dict[str, Any] | None = None) -> int:
        w_clause, params = self._where(where)
        if not w_clause:
            raise ValueError("delete 必须带 where 条件")
        sql = f"DELETE FROM {self._name} WHERE {w_clause}"
        cur = self._conn.execute(sql, tuple(params))
        return cur.rowcount

    def clear(self) -> int:
        cur = self._conn.execute(f"DELETE FROM {self._name}")
        return cur.rowcount

    def scalar(self, sql: str, params: Sequence[Any] = ()) -> Any:
        cur = self._conn.execute(sql, tuple(params))
        r = cur.fetchone()
        return r[0] if r else None

    pass

    def raw(self, sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
        self._last_cur = self._conn.execute(sql, tuple(params))
        rows = self._last_cur.fetchall()
        return [self._decode(r) for r in rows]

    pass

    @staticmethod
    def _where(where: dict[str, Any] | None) -> tuple[str, list[Any]]:
        if not where:
            return "", []
        parts: list[str] = []
        vals: list[Any] = []
        for k, v in where.items():
            if isinstance(v, Cmp):
                parts.append(f"{k} {v.op} ?")
                vals.append(v.value)
            elif isinstance(v, (list, tuple)):
                parts.append(f"{k} IN ({','.join('?' for _ in v)})")
                vals.extend(v)
            elif v is None:
                parts.append(f"{k} IS NULL")
            else:
                parts.append(f"{k}=?")
                vals.append(v)
        return " AND ".join(parts), vals

    def _encode(self, row: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k, v in row.items():
            if k in self._json_columns and not isinstance(v, str):
                out[k] = json.dumps(v, ensure_ascii=False)
            else:
                out[k] = v
        return out

    def _decode(self, row: sqlite3.Row | tuple) -> dict[str, Any]:
        if isinstance(row, sqlite3.Row):
            d = dict(row)
        else:
            cur = self._last_cur
            assert cur is not None, "_decode 需在 select/raw 之后调用"
            desc = cur.description
            assert desc is not None, "SELECT 未返回列描述——检查 SQL"
            d = {desc[i][0]: row[i] for i in range(len(desc))}
        for k in self._json_columns:
            v = d.get(k)
            if isinstance(v, str):
                try:
                    d[k] = json.loads(v)
                except (ValueError, TypeError):
                    pass
        return d
