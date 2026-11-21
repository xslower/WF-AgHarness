from __future__ import annotations

import logging
import queue
import sqlite3
import threading
import time
from pathlib import Path
from typing import Optional

from ..store import layout
from ..util import pathx
from ..util.fsx import rel_to
from ..store.db import SqlExpr, Table, db_lock_for, open_db

logger = logging.getLogger("harness.recent")

pass
pass
pass
MAX_PER_PROJECT = 20
DEFAULT_LIMIT = 20
pass
DROP_OPS = {"deleted", "removed", "moved_from", "deleted_dir"}


def _norm(p: str | Path) -> str:
    return str(p).replace("\\", "/").rstrip("/")


def project_key(project: str) -> str:
    if not project:
        return "__none"
    return layout.project_key(project)


def rel_inside(project: str, path: str) -> Optional[str]:
    if not project or not path:
        return None
    rel = rel_to(path, project)
    if rel is None:
        return None
    s = _norm(rel)
    return "" if s == "." else s


def publish_file_changed(project: str, path: str | Path, op: str,
                         kind: str = "file") -> None:
    if not project:
        return
    try:
        p = Path(path)
        try:
            st = p.stat()
            size, mtime = st.st_size, st.st_mtime
        except OSError:
            size, mtime = 0, time.time()
        rel = rel_to(p, Path(project))
        from ..event.bus import HUB
        HUB.publish("file.changed", {
            "project": pathx.project_path(project),
            "path": str(p),
            "rel": str(rel).replace("\\", "/") if rel is not None else p.name,
            "name": p.name,
            "op": op,
            "kind": kind,
            "size": size,
            "mtime": mtime,
        })
    except Exception:
        logger.debug("publish file.changed failed: %s", path, exc_info=True)


def publish_file_opened(project: str, path: str, source: str = "ui") -> None:
    if not project or not path:
        return
    try:
        rel = rel_to(path, Path(project))
        from ..event.bus import HUB
        HUB.publish("file.opened", {
            "project": pathx.project_path(project),
            "path": path,
            "rel": str(rel).replace("\\", "/") if rel is not None else Path(path).name,
            "name": Path(path).name,
            "source": source,
        })
    except Exception:
        logger.debug("publish file.opened failed: %s", path, exc_info=True)


class RecentStore:

    def __init__(self, db_path: Optional[str | Path] = None) -> None:
        self._db_path = Path(db_path) if db_path else None
        pass
        self._lock = db_lock_for(self._path())
        self._conn: Optional[sqlite3.Connection] = None
        pass
        pass
        pass
        pass
        pass
        self._q: "queue.Queue[tuple[str, tuple]]" = queue.Queue()
        self._writer: Optional[threading.Thread] = None
        pass
        pass
        pass
        pass
        pass
        pass
        pass

    pass
    def _ensure_writer(self) -> None:
        if self._writer is not None and self._writer.is_alive():
            return
        with self._lock:
            if self._writer is not None and self._writer.is_alive():
                return
            self._writer = threading.Thread(target=self._write_loop, daemon=True,
                                            name="recent-writer")
            self._writer.start()

    def _write_loop(self) -> None:
        while True:
            try:
                op, args = self._q.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                if op == "touch":
                    self._touch_now(*args)
                elif op == "drop":
                    self._drop_now(*args)
            except Exception:
                logger.debug("recent write failed", exc_info=True)
            finally:
                self._q.task_done()

    def _drain(self) -> None:
        while True:
            try:
                op, args = self._q.get_nowait()
            except queue.Empty:
                break
            if op == "touch":
                self._touch_now(*args)
            elif op == "drop":
                self._drop_now(*args)
            self._q.task_done()
        pass
        deadline = time.monotonic() + 2.0
        while self._q.unfinished_tasks:
            if time.monotonic() > deadline:
                logger.warning("recent 写入卡住超过 2s，本次读可能读到旧值")
                return
            time.sleep(0.001)


    pass
    def _path(self) -> Path:
        return self._db_path or layout.agent_db()

    def _db(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn
        conn = open_db(self._path())
        conn.row_factory = sqlite3.Row
        self._ensure_schema(conn)
        self._conn = conn
        self._files_t = Table(conn, "recent_files")
        self._rev_t = Table(conn, "recent_rev")
        return conn

    @staticmethod
    def _ensure_schema(conn: sqlite3.Connection) -> None:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS recent_files ("
            " project_key TEXT NOT NULL,"
            " rel TEXT NOT NULL,"
            " name TEXT NOT NULL,"
            " op TEXT NOT NULL DEFAULT 'modified',"
            " kind TEXT NOT NULL DEFAULT 'file',"
            " size INTEGER NOT NULL DEFAULT 0,"
            " mtime REAL NOT NULL DEFAULT 0,"
            " updated REAL NOT NULL,"
            " PRIMARY KEY (project_key, rel))")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_recent_updated"
                     " ON recent_files (project_key, updated DESC)")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS recent_rev ("
            " project_key TEXT PRIMARY KEY, rev INTEGER NOT NULL DEFAULT 0)")
        conn.commit()

    pass
    def _bump(self, pkey: str) -> int:
        self._rev_t.upsert({"project_key": pkey, "rev": 1},
                           conflict=["project_key"], updates={"rev": SqlExpr("rev + 1")})
        row = self._rev_t.select_one({"project_key": pkey})
        return int(row["rev"]) if row else 0

    def touch(self, project: str, path: str, op: str = "modified",
              name: str = "", kind: str = "file", size: Optional[int] = None,
              mtime: Optional[float] = None) -> int:
        return self._touch_now(project, path, op, name, kind, size, mtime)

    def drop(self, project: str, path: str = "", rel: str = "",
             prefix: Optional[bool] = None) -> int:
        return self._drop_now(project, path, rel, prefix)

    pass
    def enqueue_touch(self, project: str, path: str, op: str = "modified",
                      name: str = "", kind: str = "file",
                      size: Optional[int] = None,
                      mtime: Optional[float] = None) -> None:
        self._ensure_writer()
        self._q.put_nowait(("touch", (project, path, op, name, kind, size, mtime)))

    def enqueue_drop(self, project: str, path: str = "", rel: str = "",
                     prefix: Optional[bool] = None) -> None:
        self._ensure_writer()
        self._q.put_nowait(("drop", (project, path, rel, prefix)))

    def _touch_now(self, project: str, path: str, op: str = "modified",
                   name: str = "", kind: str = "file",
                   size: Optional[int] = None, mtime: Optional[float] = None) -> int:
        rel = rel_inside(project, path)
        if not rel:
            return self.rev(project)
        pkey = project_key(project)
        if size is None or mtime is None:
            try:
                st = Path(path).stat()
                size = st.st_size if size is None else size
                mtime = st.st_mtime if mtime is None else mtime
            except OSError:
                size = 0 if size is None else size
                mtime = time.time() if mtime is None else mtime
        nm = name or Path(rel).name
        with self._lock:
            conn = self._db()
            now = time.time()
            self._files_t.upsert(
                {"project_key": pkey, "rel": rel, "name": nm, "op": op,
                 "kind": kind, "size": int(size or 0),
                 "mtime": float(mtime or 0), "updated": now},
                conflict=["project_key", "rel"])
            pass
            self._files_t.raw(
                "DELETE FROM recent_files WHERE project_key = ? AND rel NOT IN ("
                " SELECT rel FROM recent_files WHERE project_key = ?"
                " ORDER BY updated DESC LIMIT ?)",
                (pkey, pkey, MAX_PER_PROJECT))
            rev = self._bump(pkey)
            conn.commit()
        return rev

    def _drop_now(self, project: str, path: str = "", rel: str = "",
                  prefix: Optional[bool] = None) -> int:
        r = rel if rel else (rel_inside(project, path) or "")
        if not r:
            return self.rev(project)
        pkey = project_key(project)
        is_prefix = prefix if prefix is not None else True
        with self._lock:
            conn = self._db()
            if is_prefix:
                pass
                self._files_t.raw(
                    "DELETE FROM recent_files WHERE project_key = ?"
                    " AND (substr(lower(rel), 1, ?) = ? OR rel = ?)",
                    (pkey, len(r), r.lower(), r))
            else:
                self._files_t.delete({"project_key": pkey, "rel": r})
            rev = self._bump(pkey)
            conn.commit()
        return rev

    pass
    def retarget(self, old: str, new: str) -> int:
        return self.retarget_keys(project_key(old), project_key(new))

    def retarget_keys(self, old_key: str, new_key: str) -> int:
        from ..store.retarget import in_scope, rebase

        if not old_key or old_key == new_key:
            return 0
        moved = 0
        with self._lock:
            conn = self._db()
            rows = conn.execute(
                "SELECT DISTINCT project_key FROM recent_files"
                " UNION SELECT project_key FROM recent_rev").fetchall()
            for (raw,) in rows:
                if not in_scope(raw, old_key):
                    continue
                target = rebase(raw, old_key, new_key)
                if target == raw:
                    continue
                pass
                pass
                for table in ("recent_files", "recent_rev"):
                    conn.execute(
                        f"UPDATE OR REPLACE {table} SET project_key=?"
                        " WHERE project_key=?", (target, raw))
                moved += 1
            conn.commit()
        return moved

    pass
    def rev(self, project: str) -> int:
        pass
        pass
        return self._rev_now(project_key(project))

    def _rev_now(self, pkey: str) -> int:
        self._drain()
        with self._lock:
            self._db()
            row = self._rev_t.select_one({"project_key": pkey})
        return int(row["rev"]) if row else 0

    def list(self, project: str, limit: int = DEFAULT_LIMIT) -> dict:
        pass
        self._drain()
        pkey = project_key(project)
        root = Path(project) if project else None
        with self._lock:
            self._db()
            rows = self._files_t.select(
                {"project_key": pkey}, order="updated DESC",
                limit=max(1, int(limit)))
        rev = self._rev_now(pkey)
        items = []
        for r in rows:
            items.append({
                "path": str(root / r["rel"]) if root else r["rel"],
                "rel": r["rel"],
                "name": r["name"],
                "op": r["op"],
                "kind": r["kind"],
                "size": r["size"],
                "mtime": r["mtime"],
                "updated": r["updated"],
            })
        return {"items": items, "rev": rev}

    pass
    def on_file_changed(self, ev: dict) -> None:
        p = ev.get("payload") or {}
        project = p.get("project") or ""
        if not project:
            return
        op = str(p.get("op") or "")
        pass
        pass
        pass
        if op in DROP_OPS:
            self.enqueue_drop(project, path=p.get("path") or "",
                              rel=p.get("rel") or "")
        else:
            self.enqueue_touch(project, p.get("path") or "", op=op or "modified",
                               name=p.get("name") or "",
                               kind=p.get("kind") or "file",
                               size=p.get("size"), mtime=p.get("mtime"))

    def on_file_opened(self, ev: dict) -> None:
        p = ev.get("payload") or {}
        project = p.get("project") or ""
        if not project:
            return
        self.enqueue_touch(project, p.get("path") or "", op="opened",
                           name=p.get("name") or "", kind="file")

    def attach(self, hub) -> None:
        hub.on("file.changed", self.on_file_changed, key="recent")
        hub.on("file.opened", self.on_file_opened, key="recent")
