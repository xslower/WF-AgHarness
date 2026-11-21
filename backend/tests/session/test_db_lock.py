from __future__ import annotations

import sqlite3
import threading

import pytest


def test_db_lock_is_shared_by_path(tmp_path):
    from app.store.db.base import db_lock_for

    p = tmp_path / "agent.db"
    assert db_lock_for(p) is db_lock_for(p)
    assert db_lock_for(p) is db_lock_for(str(p))
    assert db_lock_for(p) is not db_lock_for(tmp_path / "other.db")


def test_all_stores_share_one_lock_for_agent_db(tmp_path, monkeypatch):
    from app import config as config_mod
    from app.store.kv import KVStore, PresetStore, RegistryStore
    from app.chat.sessions import SessionStore
    from app.chat.recent import RecentStore

    monkeypatch.setattr(config_mod, "DATA_DIR", tmp_path)
    kv = KVStore()
    ps = PresetStore()
    rs = RegistryStore()
    ss = SessionStore()
    recent = RecentStore()

    lock = kv._lock
    assert ps._lock is lock
    assert rs._lock is lock
    assert ss._sys_lock is lock
    assert recent._lock is lock


def test_open_db_sets_wal_normal_and_busy_timeout(tmp_path):
    from app.store.db.base import open_db, BUSY_TIMEOUT_MS

    conn = open_db(tmp_path / "agent.db")
    try:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        pass
        assert conn.execute("PRAGMA synchronous").fetchone()[0] == 1
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == BUSY_TIMEOUT_MS
    finally:
        conn.close()


def test_concurrent_writes_across_stores_never_locked(tmp_path, monkeypatch):
    from app import config as config_mod
    from app.store.kv import KVStore, PresetStore, RegistryStore

    monkeypatch.setattr(config_mod, "DATA_DIR", tmp_path)
    stores = [KVStore(), PresetStore(), RegistryStore()] * 2
    errors: list[Exception] = []
    barrier = threading.Barrier(len(stores))

    def worker(i: int, store):
        try:
            barrier.wait(timeout=10)
            for n in range(40):
                if isinstance(store, KVStore):
                    store.set_json(f"k{i}-{n}", {"n": n})
                elif isinstance(store, PresetStore):
                    store.upsert({"id": f"p{i}-{n}", "name": "x"})
                else:
                    store.add(f"/p{i}/{n}")
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i, s))
               for i, s in enumerate(stores)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert not any(t.is_alive() for t in threads), "写线程卡死"
    assert errors == [], f"并发写出现锁错误: {errors}"


def test_write_retries_on_busy(tmp_path, monkeypatch):
    from app.store.db import base
    from app.store.kv import KVStore

    monkeypatch.setattr(base, "_WRITE_RETRY_BASE", 0.001)
    kv = KVStore(tmp_path / "agent.db")
    calls = {"n": 0}
    real = kv._db

    class _Flaky:
        def execute(self, sql, args=()):
            if sql.lstrip().upper().startswith("INSERT") and calls["n"] < 2:
                calls["n"] += 1
                raise sqlite3.OperationalError("database is locked")
            return real.execute(sql, args)

        def commit(self):
            return real.commit()

        def rollback(self):
            return real.rollback()

    kv._db = _Flaky()
    kv.set_json("k", {"ok": 1})
    assert calls["n"] == 2
    assert kv.get_json("k") == {"ok": 1}

    pass
    class _Broken(_Flaky):
        def execute(self, sql, args=()):
            raise sqlite3.OperationalError("no such table: nope")

    kv._db = _Broken()
    with pytest.raises(sqlite3.OperationalError, match="no such table"):
        kv.set_json("k2", {})


def test_presets_api_uses_isolated_db(tmp_path, monkeypatch, client):
    from app import config as config_mod
    from app.api.routers.sessions import _preset_store

    monkeypatch.setattr(config_mod, "DATA_DIR", tmp_path)
    store = _preset_store()
    assert str(tmp_path) in str(store._db.execute("PRAGMA database_list")
                                .fetchall()[0][2])

    r = client.post("/api/presets", json={"id": "iso", "name": "x"})
    assert r.status_code == 200
    assert (tmp_path / "agent.db").exists()
    rows = sqlite3.connect(str(tmp_path / "agent.db")).execute(
        "SELECT data FROM prompt_presets WHERE id='iso'").fetchall()
    assert len(rows) == 1
