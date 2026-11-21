from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from pathlib import Path

from . import layout
from .db import Cmp, Table
from .event_threads import FLUSH_INTERVAL as _FLUSH_INTERVAL
from .event_threads import Flusher, Writer

logger = logging.getLogger("harness.events")

pass
pass
KEEP_PER_SESSION = 5000

pass
pass
pass
COMMIT_EVERY = 64

FLUSH_INTERVAL = _FLUSH_INTERVAL

pass
_store = None


class _State:

    __slots__ = ("project", "sid", "pending", "last_commit", "top")

    def __init__(self, project: str, sid: str) -> None:
        self.project = project
        self.sid = sid
        self.pending = 0
        self.last_commit = 0.0
        self.top = 0

    @property
    def lock(self):
        return _lock(self.project, self.sid)


_registry_lock = threading.RLock()
_states: dict[str, _State] = {}
pass
_last_seq: dict[str, int] = {}


def set_store(store) -> None:
    global _store
    _store = store


def _require_store():
    global _store
    h = _store
    if h is None:
        raise RuntimeError(
            "event_log 未注入 SessionDb：请先调用 event_log.set_store(SessionStore())")
    pass
    pass
    if callable(h):
        h = _store = h()
    return h


def _table(project: str, sid: str) -> Table:
    return _require_store().session_table(project, sid, "events", frozenset({"ev"}))


def _lock(project: str, sid: str):
    return _require_store().session_lock(project, sid)

def _tx(project: str, sid: str):
    return _require_store().session_tx(project, sid, "events", frozenset({"ev"}))


def _state(project: str, sid: str) -> _State:
    with _registry_lock:
        st = _states.get(sid)
        if st is None:
            st = _states[sid] = _State(project, sid)
        return st


def _all_states() -> list[_State]:
    with _registry_lock:
        return list(_states.values())


pass
def _write_one(item) -> None:
    project, sid, seq, ev = item
    append(project, sid, seq, ev)


def _flush_state(st: _State) -> None:
    with _tx(st.project, st.sid) as t:
        pass
        if st.top > KEEP_PER_SESSION:
            t.delete({"seq": Cmp("<=", st.top - KEEP_PER_SESSION)})
    st.pending = 0
    st.last_commit = time.time()


_WRITER = Writer(lambda item: _write_one(item))
_FLUSHER = Flusher(all_dbs=_all_states,
                   flush_locked=lambda st: _flush_state(st))


def _ensure_flusher() -> None:
    _FLUSHER.ensure_started()


pass
def next_seq(sid: str, project: str = "") -> int:
    with _registry_lock:
        cached = _last_seq.get(sid)
    cur = _query_last_seq(project, sid) if cached is None else cached
    cur += 1
    with _registry_lock:
        cur = max(cur, _last_seq.get(sid, 0) + 1)
        _last_seq[sid] = cur
    return cur


def _query_last_seq(project: str, sid: str) -> int:
    try:
        return int(_table(project, sid).scalar("SELECT MAX(seq) FROM events") or 0)
    except (sqlite3.Error, OSError, AttributeError):
        return 0


pass
pass
pass
pass
pass
pass
pass
pass


def _drain_all() -> None:
    _WRITER.drain()


def append_async(project: str, sid: str, seq: int, ev: dict) -> None:
    if not sid or not ev:
        return
    _WRITER.ensure_started()
    _WRITER.put((project, sid, int(seq), ev))


def append(project: str, sid: str, seq: int, ev: dict) -> None:
    if not sid or not ev:
        return
    st = _state(project, sid)
    with _lock(project, sid):
        try:
            _insert_event(project, sid, seq, ev)
            st.pending += 1
            st.top = int(seq)
            if st.pending < COMMIT_EVERY:
                _ensure_flusher()
                return
            _flush_state(st)
        except (sqlite3.Error, OSError):
            logger.debug("event append failed: %s", sid, exc_info=True)


def _insert_event(project: str, sid: str, seq: int, ev: dict) -> None:
    try:
        _table(project, sid).insert(
            {"seq": int(seq), "ev": ev, "ts": 0.0}, or_replace=True)
    except (TypeError, ValueError):
        pass
        pass
        logger.debug("event not serializable: %s", sid, exc_info=True)
        _table(project, sid).insert({
            "seq": int(seq), "ts": 0.0, "ev": {
                "type": (ev.get("type") if isinstance(ev, dict) else "") or "unknown",
                "note": "内容无法序列化"}}, or_replace=True)


def flush(project: str = "", sid: str = "") -> None:
    _drain_all()
    if not sid:
        return
    st = _state(project, sid)
    with _lock(project, sid):
        try:
            if st.pending:
                _flush_state(st)
        except (sqlite3.Error, OSError):
            logger.debug("event flush failed", exc_info=True)


def read_since(project: str, sid: str, since: int = 0,
               limit: int = 2000) -> list[tuple[int, dict]]:
    if not sid:
        return []
    since = max(0, int(since or 0))
    flush(project, sid)
    try:
        rows = _table(project, sid).select(
            where={"seq": Cmp(">", since)}, order="seq DESC",
            limit=max(1, int(limit)), cols="seq, ev")
    except (sqlite3.Error, OSError):
        return []
    out: list[tuple[int, dict]] = []
    for r in rows:
        ev = r["ev"]
        pass
        if isinstance(ev, dict):
            out.append((int(r["seq"]), ev))
    out.sort(key=lambda x: x[0])
    return out


def last_seq(project: str, sid: str) -> int:
    _drain_all()
    with _registry_lock:
        cached = _last_seq.get(sid)
        if cached is not None:
            return cached
    return _query_last_seq(project, sid)


def count(project: str, sid: str) -> int:
    flush(project, sid)
    try:
        return int(_table(project, sid).scalar("SELECT COUNT(*) FROM events") or 0)
    except (sqlite3.Error, OSError):
        return 0


def trim(project: str, sid: str, keep: int = KEEP_PER_SESSION) -> None:
    flush(project, sid)
    try:
        with _tx(project, sid) as t:
            top = int(t.scalar("SELECT MAX(seq) FROM events") or 0)
            if top > 0:
                t.delete({"seq": Cmp("<=", top - max(0, int(keep)))})
    except (sqlite3.Error, OSError):
        logger.debug("event trim failed: %s", sid, exc_info=True)


def clear(project: str, sid: str) -> None:
    flush(project, sid)
    try:
        with _tx(project, sid) as t:
            t.clear()
        _state(project, sid).pending = 0
    except (sqlite3.Error, OSError):
        logger.debug("event clear failed: %s", sid, exc_info=True)
    with _registry_lock:
        _last_seq.pop(sid, None)


def forget_seq(sid: str, project: str = "") -> None:
    with _registry_lock:
        _last_seq.pop(sid, None)


def db_path(project: str, sid: str) -> Path:
    return layout.session_db(project, sid)


def reset_caches() -> None:
    with _registry_lock:
        _states.clear()
        _last_seq.clear()
