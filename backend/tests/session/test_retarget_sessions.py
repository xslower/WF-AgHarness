from __future__ import annotations
from contextlib import contextmanager


def _fake_store(projects: list[str]):
    import sqlite3
    import threading

    from app.store.db import Table

    class _S:
        def __init__(self) -> None:
            self._sys = sqlite3.connect(":memory:")
            self._sys.execute(
                "CREATE TABLE sessions (id TEXT PRIMARY KEY, project TEXT)")
            for i, p in enumerate(projects):
                self._sys.execute("INSERT INTO sessions VALUES (?,?)", (str(i), p))
            self._sys_lock = threading.RLock()
            self.closed: list[str] = []

        def _sys_fetchall(self, sql, params):
            return self._sys.execute(sql, params).fetchall()

        @contextmanager
        def sys_tx(self, table: str = "sessions"):
            try:
                yield Table(self._sys, table)
            except BaseException:
                self._sys.rollback()
                raise
            self._sys.commit()

        def _close_session(self, sid):
            self.closed.append(sid)

        def projects(self) -> dict:
            return {r[0]: r[1] for r in self._sys.execute(
                "SELECT id, project FROM sessions")}

    return _S()


def test_underscore_in_old_path_is_not_a_wildcard():
    from app.chat.session_recovery import retarget_sessions

    s = _fake_store([
        "/p/my_proj", "/p/my_proj/sub",
        "/p/myXproj", "/p/myXproj/sub",
        "/p/my_proj2",
    ])
    n = retarget_sessions(s, "/p/my_proj", "/new/my_proj")
    assert n == 2
    got = set(s.projects().values())
    assert got == {"/new/my_proj", "/new/my_proj/sub", "/p/myXproj",
                   "/p/myXproj/sub", "/p/my_proj2"}


def test_percent_in_old_path_is_not_a_wildcard():
    from app.chat.session_recovery import retarget_sessions

    s = _fake_store(["/p/a%b", "/p/a%b/sub", "/p/aXb/sub"])
    n = retarget_sessions(s, "/p/a%b", "/new/a%b")
    assert n == 2
    assert "/p/aXb/sub" in set(s.projects().values())
