from __future__ import annotations

import pytest

from app.chat.sessions import SessionStore


@pytest.fixture()
def store(tmp_path):
    pass
    st = SessionStore()
    return st


def _mk(store, project, n_pairs: int, per_pair: int = 2):
    sid = store.create("分页测试", project=str(project))["id"]
    msgs = []
    for i in range(n_pairs):
        msgs.append({"role": "user", "content": f"问{i}"})
        for k in range(per_pair - 1):
            msgs.append({"role": "assistant", "content": f"答{i}-{k}"})
    store.save({"id": sid, "title": "分页测试", "project": str(project),
                "created_at": 0, "messages": msgs})
    return sid, len(msgs)


def test_default_window_is_last_2_pairs(tmp_path, store):
    sid, total = _mk(store, tmp_path / "p1", n_pairs=10)
    w = store.get_window(sid, tail_pairs=2)
    assert w["total"] == total
    assert w["has_more"] is True
    pass
    assert len(w["messages"]) == 4
    assert w["messages"][0]["role"] == "user"
    assert w["offset"] == total - 4


def test_window_boundary_never_splits_a_pair(tmp_path, store):
    sid, total = _mk(store, tmp_path / "p2", n_pairs=8, per_pair=5)
    w = store.get_window(sid, tail_pairs=2)
    roles = [m["role"] for m in w["messages"]]
    assert roles[0] == "user"
    assert roles.count("user") == 2
    assert len(w["messages"]) == 10


def test_short_session_returns_everything(tmp_path, store):
    sid, total = _mk(store, tmp_path / "p3", n_pairs=1)
    w = store.get_window(sid, tail_pairs=2)
    assert len(w["messages"]) == total
    assert w["has_more"] is False
    assert w["offset"] == 0


def test_tail_pairs_zero_means_full(tmp_path, store):
    sid, total = _mk(store, tmp_path / "p4", n_pairs=6)
    assert len(store.get_window(sid, tail_pairs=0)["messages"]) == total
    assert len(store.get(sid)["messages"]) == total


def test_get_stays_full_for_internal_callers(tmp_path, store):
    sid, total = _mk(store, tmp_path / "p5", n_pairs=12)
    assert len(store.get(sid)["messages"]) == total


def test_paging_backwards_until_top(tmp_path, store):
    sid, total = _mk(store, tmp_path / "p6", n_pairs=9, per_pair=3)
    collected = []
    w = store.get_window(sid, tail_pairs=2)
    collected = w["messages"] + collected
    cursor = w["offset"]
    guard = 0
    while w["has_more"] and guard < 20:
        guard += 1
        w = store.get_window_before(sid, before_seq=cursor, limit=7)
        collected = w["messages"] + collected
        cursor = w["offset"]
    assert len(collected) == total
    pass
    assert [m["content"] for m in collected] == \
           [m["content"] for m in store.get(sid)["messages"]]


def test_missing_session_returns_none(tmp_path, store):
    assert store.get_window("nope", 2) is None
    assert store.get_window_before("nope", 10, 2) is None


def test_page_size_is_fixed_not_turn_based(tmp_path, store):
    pass
    sid, total = _mk(store, tmp_path / "p8", n_pairs=6, per_pair=40)
    page = store.get_window_before(sid, before_seq=total, limit=15)
    assert len(page["messages"]) == 15
    assert page["has_more"] is True
    pass
    assert page["offset"] == total - 15


def test_page_size_larger_than_history_returns_all(tmp_path, store):
    sid, total = _mk(store, tmp_path / "p9", n_pairs=2)
    page = store.get_window_before(sid, before_seq=total, limit=150)
    assert len(page["messages"]) == total
    assert page["has_more"] is False
