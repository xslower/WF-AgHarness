from __future__ import annotations

import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from . import layout
from .db import Table, db_lock_for, open_db

pass
pass
WF_SESSION_KIND = "wf-session"
WF_NODE_KIND = "wf-node"
pass
pass
WF_CHAT_KINDS = ("workflow",)
pass
PURGEABLE_KINDS = WF_CHAT_KINDS + (WF_SESSION_KIND, WF_NODE_KIND)

pass
_SYS_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  project TEXT NOT NULL DEFAULT '',
  created_at REAL NOT NULL,
  message_count INTEGER NOT NULL DEFAULT 0,
  kind TEXT NOT NULL DEFAULT '',
  origin TEXT NOT NULL DEFAULT '',
  updated_at REAL NOT NULL DEFAULT 0
);
"""

pass
_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
  seq INTEGER PRIMARY KEY,
  msg TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS compactions (
  upto_seq INTEGER PRIMARY KEY,
  items TEXT NOT NULL,
  created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
  seq INTEGER PRIMARY KEY,
  ev  TEXT NOT NULL,
  ts  REAL NOT NULL DEFAULT 0
);
"""


class SessionDb:

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sys_path = layout.agent_db()
        pass
        pass
        self._sys_lock = db_lock_for(self._sys_path)
        self._dbs: dict[str, sqlite3.Connection] = {}
        self._db_locks: dict[str, threading.RLock] = {}
        self._sys = self._open_sys(self._sys_path)
        pass
        pass
        self._persisted: dict[str, int] = {}

    def _open_sys(self, path: Path) -> sqlite3.Connection:
        return open_db(path, _SYS_SCHEMA)

    def _open_session(self, path: Path) -> sqlite3.Connection:
        return open_db(path, _SCHEMA)

    def _db_for(self, project: str, sid: str) -> sqlite3.Connection:
        with self._lock:
            conn = self._dbs.get(sid)
            if conn is None:
                conn = self._open_session(layout.session_db(project, sid))
                self._dbs[sid] = conn
            return conn

    def _db_lock(self, project: str, sid: str) -> threading.RLock:
        with self._lock:
            lk = self._db_locks.get(sid)
            if lk is None:
                lk = self._db_locks[sid] = db_lock_for(
                    layout.session_db(project, sid))
            return lk

    def _close_session(self, sid: str) -> None:
        with self._lock:
            conn = self._dbs.pop(sid, None)
            self._db_locks.pop(sid, None)
            self._persisted.pop(sid, None)
        if conn is not None:
            try:
                conn.close()
            except sqlite3.Error:
                pass

    pass
    pass
    pass
    pass
    pass
    pass

    @contextmanager
    def session_tx(self, project: str, sid: str, table: str,
                   json_columns: frozenset[str] = frozenset()):
        with self._db_lock(project, sid):
            conn = self._db_for(project, sid)
            t = Table(conn, table)
            if json_columns:
                t._json_columns = json_columns
            try:
                yield t
            except BaseException:
                conn.rollback()
                raise
            conn.commit()

    @contextmanager
    def session_lock(self, project: str, sid: str):
        with self._db_lock(project, sid):
            yield

    def session_table(self, project: str, sid: str, table: str,
                      json_columns: frozenset[str] = frozenset()) -> Table:
        t = Table(self._db_for(project, sid), table)
        if json_columns:
            t._json_columns = json_columns
        return t

    def session_commit(self, project: str, sid: str) -> None:
        self._db_for(project, sid).commit()

    @contextmanager
    def sys_tx(self, table: str = "sessions"):
        with self._sys_lock:
            try:
                yield Table(self._sys, table)
            except BaseException:
                self._sys.rollback()
                raise
            self._sys.commit()

    def sys_fetchall(self, sql: str, params=()):
        return self._sys_fetchall(sql, params)

    pass
    pass

    def _sys_fetchone(self, sql: str, params=()):
        with self._sys_lock:
            return self._sys.execute(sql, tuple(params)).fetchone()

    def _sys_fetchall(self, sql: str, params=()):
        with self._sys_lock:
            return self._sys.execute(sql, tuple(params)).fetchall()

    def insert_session(self, s: dict) -> None:
        with self._sys_lock:
            row = self._sys.execute(
                "SELECT MAX(CAST(id AS INTEGER)) FROM sessions"
                " WHERE id GLOB '[0-9]*' AND id NOT GLOB '*[^0-9]*'"
            ).fetchone()
            sid = str(int(row[0] or 0) + 1) if row else "1"
            s["id"] = sid
            Table(self._sys, "sessions").insert({
                "id": sid, "title": s["title"], "project": s["project"],
                "created_at": s["created_at"], "message_count": 0,
                "kind": s["kind"], "origin": s["origin"],
                "updated_at": s["updated_at"]})
            self._sys.commit()

    def ensure_index(self, s: dict) -> None:
        sid = s["id"]
        with self._sys_lock:
            exists = self._sys.execute(
                "SELECT 1 FROM sessions WHERE id=?", (sid,)).fetchone()
            if exists is None:
                Table(self._sys, "sessions").insert({
                    "id": sid, "title": s.get("title") or "未命名",
                    "project": s.get("project", ""),
                    "created_at": s.get("created_at") or 0,
                    "message_count": 0,
                    "kind": s.get("kind") or "",
                    "origin": s.get("origin") or "",
                    "updated_at": s.get("created_at") or 0,
                })
                self._sys.commit()

    def session_head(self, sid: str):
        return self._sys_fetchone(
            "SELECT id, title, project, created_at, kind, origin"
            " FROM sessions WHERE id=?", (sid,))

    def session_project(self, sid: str) -> str:
        row = self._sys_fetchone(
            "SELECT project FROM sessions WHERE id=?", (sid,))
        return row[0] if row else ""

    def list_rows(self, where_sql: str, params) -> list:
        sql = ("SELECT id, title, project, created_at, message_count, kind, origin,"
               " updated_at FROM sessions")
        if where_sql:
            sql += " WHERE " + where_sql
        sql += " ORDER BY created_at DESC"
        return self._sys_fetchall(sql, params)

    def active_row(self, where_sql: str, params):
        sql = ("SELECT id, title, project, created_at, message_count, kind, origin,"
               " updated_at FROM sessions WHERE " + where_sql +
               " ORDER BY (message_count > 0) DESC,"
               " COALESCE(NULLIF(updated_at, 0), created_at) DESC,"
               " created_at DESC LIMIT 1")
        return self._sys_fetchone(sql, params)

    def stale_rows(self, kinds: tuple[str, ...], cutoff: float) -> list:
        marks = ",".join("?" for _ in kinds)
        return self._sys_fetchall(
            f"SELECT id, project FROM sessions WHERE kind IN ({marks})"
            " AND created_at < ?", (*kinds, cutoff))

    def wf_node_parents(self) -> set[str]:
        rows = self._sys_fetchall(
            "SELECT DISTINCT origin FROM sessions WHERE kind=?", (WF_NODE_KIND,))
        return {str(r[0]) for r in rows if r[0]}

    pass

    def msg_count(self, project: str, sid: str) -> int:
        with self._db_lock(project, sid):
            return self._db_for(project, sid).execute(
                "SELECT COUNT(*) FROM messages").fetchone()[0]

    def msgs_since(self, project: str, sid: str, start: int,
                   upper: int | None = None) -> list:
        with self._db_lock(project, sid):
            if upper is None:
                return self._db_for(project, sid).execute(
                    "SELECT msg FROM messages WHERE seq>=?"
                    " ORDER BY seq", (start,)).fetchall()
            return self._db_for(project, sid).execute(
                "SELECT msg FROM messages WHERE seq>=? AND seq<?"
                " ORDER BY seq", (start, upper)).fetchall()

    def msgs_last(self, project: str, sid: str, upper: int, limit: int) -> list:
        with self._db_lock(project, sid):
            rows = self._db_for(project, sid).execute(
                "SELECT seq, msg FROM messages WHERE seq<?"
                " ORDER BY seq DESC LIMIT ?", (upper, limit)).fetchall()
        rows.reverse()
        return rows

    def msgs_all(self, project: str, sid: str) -> list:
        with self._db_lock(project, sid):
            return self._db_for(project, sid).execute(
                "SELECT msg FROM messages ORDER BY seq").fetchall()

    def window_start(self, project: str, sid: str, total: int,
                     tail_pairs: int) -> int:
        with self._db_lock(project, sid):
            rows = self._db_for(project, sid).execute(
                "SELECT seq FROM messages WHERE seq<?"
                " AND json_extract(msg,'$.role')='user' ORDER BY seq DESC LIMIT ?",
                (total, tail_pairs)).fetchall()
        return int(rows[-1][0]) if len(rows) >= tail_pairs else 0
