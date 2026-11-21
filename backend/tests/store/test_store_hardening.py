from __future__ import annotations

import threading
import time

import pytest

from app.store import layout, vault
from app.store import event_log
from app.store.event_threads import Flusher


pass
def _flusher_threads() -> int:
    return sum(1 for t in threading.enumerate() if t.name == "events-flusher")


def test_flusher_pause_resume_does_not_leak_threads():
    f = Flusher(all_dbs=lambda: [], flush_locked=lambda st: None, interval=0.01)
    f.ensure_started()
    try:
        deadline = time.time() + 2
        while _flusher_threads() < 1 and time.time() < deadline:
            time.sleep(0.01)
        base = _flusher_threads()
        assert base >= 1, "守卫线程没起来，用例前提不成立"
        for _ in range(5):
            f.pause()
            f.resume()
        time.sleep(0.1)
        assert _flusher_threads() == base, "pause/resume 泄漏了线程"
    finally:
        f.pause()


def test_flusher_pause_waits_for_inflight_commit():
    seen: list[int] = []

    class _State:
        pending = 1

        @property
        def lock(self):
            return threading.RLock()

    f = Flusher(all_dbs=lambda: [_State()], flush_locked=lambda _st: seen.append(1),
                interval=0.01)
    f.ensure_started()
    try:
        deadline = time.time() + 2
        while not seen and time.time() < deadline:
            time.sleep(0.01)
        assert seen, "守卫线程没跑起来"
        _State.pending = 0
        f.pause()
        n = len(seen)
        time.sleep(0.15)
        _State.pending = 1
        time.sleep(0.15)
        assert len(seen) == n, "pause() 返回后旧线程仍在提交"
    finally:
        f.pause()


pass
def test_redact_survives_concurrent_remember():
    stop = threading.Event()

    def adder():
        i = 0
        while not stop.is_set():
            vault.remember(f"concurrent-secret-{i}")
            i += 1

    t = threading.Thread(target=adder, daemon=True)
    t.start()
    try:
        for _ in range(3000):
            vault.redact("x" * 32)
    finally:
        stop.set()
        t.join(timeout=5)


def test_redact_plaintext_cache_is_bounded():
    for i in range(vault._MAX_PLAINTEXTS + 100):
        vault.remember(f"bounded-secret-{i}")
    assert len(vault._plaintexts) <= vault._MAX_PLAINTEXTS
    pass
    assert vault.redact(f"用 bounded-secret-{vault._MAX_PLAINTEXTS + 99} 访问") == "用 *** 访问"


def test_fernet_cache_follows_master_key_location(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.DATA_DIR", tmp_path / "d1")
    monkeypatch.delenv(vault.MASTER_KEY_ENV, raising=False)
    sealed1 = vault.seal("value-one")
    key1 = (tmp_path / "d1" / "keystore" / "master.key").read_bytes()

    pass
    monkeypatch.setattr("app.config.DATA_DIR", tmp_path / "d2")
    sealed2 = vault.seal("value-two")
    key2 = (tmp_path / "d2" / "keystore" / "master.key").read_bytes()
    assert key1 != key2, "换了数据目录却复用了旧主密钥（正是本次修的 BUG）"
    assert vault.unseal(sealed2) == "value-two"
    with pytest.raises(RuntimeError, match="密钥解不开"):
        vault.unseal(sealed1)

    pass
    monkeypatch.setattr("app.config.DATA_DIR", tmp_path / "d1")
    assert vault.unseal(sealed1) == "value-one"


pass
def test_append_serializes_event_once(monkeypatch):
    import json as _json
    calls = {"n": 0}
    real_dumps = _json.dumps

    def counting_dumps(*a, **kw):
        calls["n"] += 1
        return real_dumps(*a, **kw)

    monkeypatch.setattr(event_log.json, "dumps", counting_dumps)
    pass
    calls["n"] = 0

    class _FakeTable:
        def insert(self, row, or_replace=False):
            pass
            _json.dumps(row["ev"], ensure_ascii=False)

    class _FakeConn:
        def __init__(self):
            self.committed = 0

        def commit(self):
            self.committed += 1

    monkeypatch.setattr(event_log, "_table", lambda p, s: _FakeTable())
    monkeypatch.setattr(event_log, "_state",
                        lambda p, s: type("St", (), {"pending": 0, "top": 0})())
    monkeypatch.setattr(event_log, "_lock",
                        lambda p, s: threading.RLock())
    event_log._insert_event("", "S1", 1, {"type": "text", "text": "hi"})
    assert calls["n"] == 1, f"一次事件应只序列化一次，实际 {calls['n']} 次"


def test_append_unserializable_event_falls_back_to_placeholder():
    written: list[dict] = []

    class _FakeTable:
        def __init__(self):
            self.seen = 0

        def insert(self, row, or_replace=False):
            self.seen += 1
            if self.seen == 1:
                raise TypeError("Object of type X is not JSON serializable")
            written.append(row["ev"])

    class _Boom:
        pass

    t = _FakeTable()
    real_table = event_log._table
    event_log._table = lambda p, s: t
    try:
        event_log._insert_event("", "S1", 7, {"type": "tool.call", "x": _Boom()})
    finally:
        event_log._table = real_table
    assert written == [{"type": "tool.call", "note": "内容无法序列化"}]
    assert t.seen == 2, "失败后没有写占位事件"


pass
def test_store_all_symbols_exist():
    import app.store as store_pkg
    missing = [n for n in store_pkg.__all__ if not hasattr(store_pkg, n)]
    assert missing == []


def test_store_star_import_works():
    ns: dict = {}
    exec("from app.store import *", ns)
    assert "data_dir" in ns and "layout" in ns


def test_star_import_covers_imported_names():
    import app.store as store_pkg
    exported = {n for n in dir(store_pkg) if not n.startswith("_")}
    pass
    for name in ("session_subdir",):
        assert name not in exported, f"{name} 已删，不该还有导出"
