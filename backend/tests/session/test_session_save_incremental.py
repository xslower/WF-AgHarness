from __future__ import annotations

import json

import pytest

from app.chat.sessions import SessionStore


@pytest.fixture
def store(tmp_dirs):
    return SessionStore()


def _msgs(*texts: str) -> list[dict]:
    return [{"role": "user" if i % 2 == 0 else "assistant", "content": t}
            for i, t in enumerate(texts)]


def _rows(store, sid):
    project = store.get(sid)["project"]
    db = store._db_for(project, sid)
    return [json.loads(r[0]) for r in
            db.execute("SELECT msg FROM messages ORDER BY seq").fetchall()]


def test_first_save_writes_everything(store):
    sid = store.create("t")["id"]
    store.save({"id": sid, "title": "t", "project": "", "created_at": 0,
                "messages": _msgs("a", "b", "c")})
    assert [m["content"] for m in _rows(store, sid)] == ["a", "b", "c"]


def test_second_save_only_appends(store):
    sid = store.create("t")["id"]
    base = {"id": sid, "title": "t", "project": "", "created_at": 0}
    store.save({**base, "messages": _msgs("a", "b")})
    store.save({**base, "messages": _msgs("a", "b", "c")})
    store.save({**base, "messages": _msgs("a", "b", "c")})
    assert [m["content"] for m in _rows(store, sid)] == ["a", "b", "c"]
    assert store.get(sid)["messages"] and len(store.get(sid)["messages"]) == 3


def test_compaction_rewrites_whole_history(store):
    sid = store.create("t")["id"]
    base = {"id": sid, "title": "t", "project": "", "created_at": 0}
    store.save({**base, "messages": _msgs("a", "b", "c", "d", "e")})
    store.save({**base, "messages": [{"role": "user", "content": "摘要后的历史"}]})
    assert [m["content"] for m in _rows(store, sid)] == ["摘要后的历史"]


def test_save_on_fresh_store_after_restart(store, tmp_dirs):
    sid = store.create("t")["id"]
    base = {"id": sid, "title": "t", "project": "", "created_at": 0}
    store.save({**base, "messages": _msgs("a", "b")})

    fresh = SessionStore()
    fresh.save({**base, "messages": _msgs("a", "b", "c")})
    assert [m["content"] for m in _rows(fresh, sid)] == ["a", "b", "c"]


def test_delete_clears_counter(store):
    sid = store.create("t")["id"]
    base = {"id": sid, "title": "t", "project": "", "created_at": 0}
    store.save({**base, "messages": _msgs("a", "b")})
    store.delete(sid)
    assert sid not in store._persisted
