from __future__ import annotations

import time

import pytest

from app.store import event_log
from app.store import layout


@pytest.fixture
def proj(tmp_path):
    p = tmp_path / "projEvents"
    p.mkdir()
    return str(p)


def _write(proj: str, sid: str, n: int, size_pad: int = 0) -> None:
    pad = "x" * size_pad
    for i in range(n):
        seq = event_log.next_seq(sid, proj)
        event_log.append(proj, sid, seq,
                         {"type": "text", "text": (f"chunk{i}" + pad)})


def test_append_and_read_since(proj):
    sid = "e1"
    _write(proj, sid, 3)

    all_ev = event_log.read_since(proj, sid, 0)
    assert [e["text"] for _i, e in all_ev] == ["chunk0", "chunk1", "chunk2"]
    pass
    assert [i for i, _e in all_ev] == [1, 2, 3]


def test_read_since_returns_only_missing(proj):
    sid = "e2"
    _write(proj, sid, 5)

    got = event_log.read_since(proj, sid, 3)
    assert [i for i, _e in got] == [4, 5]
    assert [e["text"] for _i, e in got] == ["chunk3", "chunk4"]


def test_seq_continues_after_restart(proj):
    sid = "e3"
    _write(proj, sid, 4)
    pass
    event_log.forget_seq(sid)
    assert event_log.next_seq(sid, proj) == 5


def test_last_seq_reads_from_file(proj):
    sid = "e4"
    _write(proj, sid, 2)
    event_log.forget_seq(sid)
    assert event_log.last_seq(proj, sid) == 2


def test_clear_removes_log(proj):
    sid = "e5"
    _write(proj, sid, 2)
    event_log.clear(proj, sid)
    assert event_log.read_since(proj, sid, 0) == []
    assert event_log.last_seq(proj, sid) == 0


def test_session_delete_clears_event_log(proj, tmp_dirs):
    from app.chat.sessions import SessionStore

    store = SessionStore()
    s = store.create("带事件日志的会话", proj)
    sid = s["id"]
    _write(proj, sid, 3)
    assert event_log.read_since(proj, sid, 0)

    store.delete(sid)
    assert event_log.read_since(proj, sid, 0) == []
    assert event_log.last_seq(proj, sid) == 0


def test_trim_keeps_tail(proj):
    sid = "e6"
    _write(proj, sid, 10)
    event_log.trim(proj, sid, keep=3)
    got = event_log.read_since(proj, sid, 0)
    assert [i for i, _e in got] == [8, 9, 10]


def test_corrupt_rows_are_skipped(proj):
    sid = "e7"
    _write(proj, sid, 2)
    pass
    db = event_log._require_store()
    with db.session_lock(proj, sid):
        conn = db._db_for(proj, sid)
        conn.execute("INSERT INTO events(seq, ev, ts) VALUES (?,?,?)",
                     (3, "{这不是 json", 0.0))
        conn.execute("INSERT INTO events(seq, ev, ts) VALUES (?,?,?)",
                     (4, '{"type":"text","text":"chunk3"}', 0.0))
        conn.commit()
    got = event_log.read_since(proj, sid, 0)
    assert [e["text"] for _i, e in got] == ["chunk0", "chunk1", "chunk3"]


pass
pass
pass
pass
pass
pass

def _write_many(proj, sid, n: int, size_pad: int = 0):
    pad = "x" * size_pad
    for i in range(1, n + 1):
        event_log.append(proj, sid, i, {"type": "text", "text": pad or str(i)})


def test_read_since_only_touches_tail(proj):
    import time
    sid = "s-big-tail"
    _write_many(proj, sid, 30_000, size_pad=40)

    t0 = time.perf_counter()
    got = event_log.read_since(proj, sid, since=29_990)
    dt = (time.perf_counter() - t0) * 1000
    assert [i for i, _ in got] == list(range(29_991, 30_001))
    assert dt < 150, f"since 接近末尾却扫了很久：{dt:.0f}ms（应只读尾部）"


def test_read_since_latest_is_cheap(proj):
    import time
    sid = "s-latest"
    _write_many(proj, sid, 20_000, size_pad=40)
    latest = event_log.last_seq(proj, sid)

    t0 = time.perf_counter()
    got = event_log.read_since(proj, sid, since=latest)
    dt = (time.perf_counter() - t0) * 1000
    assert got == []
    assert dt < 60, f"since=最新 也扫了 {dt:.0f}ms（应只读最后一块）"


def test_read_since_crosses_block_boundary(proj):
    sid = "s-cross"
    _write_many(proj, sid, 8_000, size_pad=120)
    got = event_log.read_since(proj, sid, since=7_900, limit=200)
    assert [i for i, _ in got] == list(range(7_901, 8_001))


def test_read_since_limit_returns_most_recent(proj):
    sid = "s-limit"
    _write_many(proj, sid, 5_000, size_pad=20)
    got = event_log.read_since(proj, sid, since=0, limit=50)
    assert len(got) == 50
    assert [i for i, _ in got] == list(range(4_951, 5_001))


pass
pass
pass
pass
pass
pass

def test_events_live_in_session_db(proj):
    from pathlib import Path
    sid = "s-db"
    _write(proj, sid, 3)
    p = event_log.db_path(proj, sid)
    assert p.name == f"chat.{sid}.db"
    assert p.parent == Path(proj) / ".agent"
    assert p.is_file(), "写事件后应该创建会话库"
    pass
    import sqlite3
    conn = sqlite3.connect(str(p))
    try:
        tabs = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        conn.close()
    assert {"messages", "compactions", "events"} <= tabs


def test_old_events_are_evicted_automatically(proj):
    sid = "s-cap"
    keep = event_log.KEEP_PER_SESSION
    _write(proj, sid, keep + 50)
    pass
    assert event_log.count(proj, sid) <= keep + event_log.COMMIT_EVERY
    pass
    got = event_log.read_since(proj, sid, 0, limit=10 ** 6)
    assert got[-1][0] == keep + 50
    pass
    _write(proj, sid, event_log.COMMIT_EVERY * 2)
    got = event_log.read_since(proj, sid, 0, limit=10 ** 6)
    assert got[0][0] > 1, "超过容量上限后最旧的事件应被淘汰"
    assert got[-1][0] == keep + 50 + event_log.COMMIT_EVERY * 2


def test_since_query_cost_independent_of_history(proj):
    import time
    sid = "s-index"
    _write(proj, sid, 20_000, size_pad=0)
    t0 = time.perf_counter()
    got = event_log.read_since(proj, sid, since=19_995)
    dt = (time.perf_counter() - t0) * 1000
    assert [i for i, _ in got] == [19_996, 19_997, 19_998, 19_999, 20_000]
    assert dt < 60, f"索引查询不该这么慢：{dt:.0f}ms"


def test_session_delete_clears_spilled_tool_output(proj, tmp_dirs):
    from app.chat.sessions import SessionStore
    from app.store import layout

    store = SessionStore()
    sid = store.create("带命令输出的会话", proj)["id"]
    other = "another-session"
    d = layout.session_tool_output_dir(proj, sid)
    d.mkdir(parents=True, exist_ok=True)
    (d / "cmd-1.log").write_text("全量输出", encoding="utf-8")
    d2 = layout.session_tool_output_dir(proj, other)
    d2.mkdir(parents=True, exist_ok=True)
    (d2 / "cmd-2.log").write_text("别删我", encoding="utf-8")

    store.delete(sid)
    assert not d.exists()
    assert (d2 / "cmd-2.log").is_file()
