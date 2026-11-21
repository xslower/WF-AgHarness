from __future__ import annotations

import time

import pytest

from app.chat.sessions import SessionStore


@pytest.fixture
def store(tmp_path, monkeypatch):
    from app import config
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    return SessionStore()


def test_create_and_get_keeps_scope(store):
    s = store.create("看看这个工作流", "/tmp/proj", kind="workflow",
                     origin="demo-flow")
    assert s["kind"] == "workflow" and s["origin"] == "demo-flow"
    got = store.get(s["id"])
    assert got["kind"] == "workflow" and got["origin"] == "demo-flow"


def test_plain_session_has_empty_scope(store):
    s = store.create("普通任务", "/tmp/proj")
    assert s["kind"] == "" and s["origin"] == ""


def test_list_filters_by_scope(store):
    store.create("任务A", "/tmp/proj")
    store.create("画布会话", "/tmp/proj", kind="workflow", origin="wf1")
    plain = store.list("/tmp/proj", kind="")
    assert [x["title"] for x in plain] == ["任务A"]
    wf = store.list("/tmp/proj", kind="workflow", origin="wf1")
    assert [x["title"] for x in wf] == ["画布会话"]
    assert len(store.list("/tmp/proj")) == 2


def test_save_does_not_drop_scope(store):
    s = store.create("画布会话", "/tmp/proj", kind="workflow", origin="wf1")
    store.save({"id": s["id"], "title": "改了名", "project": "/tmp/proj",
                "created_at": s["created_at"],
                "messages": [{"role": "user", "content": "hi"}]})
    got = store.get(s["id"])
    assert got["kind"] == "workflow" and got["origin"] == "wf1"


def test_purge_old_only_touches_canvas_sessions(store):
    old = time.time() - 30 * 86400
    task = store.create("项目任务", "/tmp/proj")
    wf = store.create("旧画布会话", "/tmp/proj", kind="workflow", origin="wf1")
    pass
    for sid in (task["id"], wf["id"]):
        store._sys.execute("UPDATE sessions SET created_at=? WHERE id=?",
                           (old, sid))
    store._sys.commit()

    removed = store.purge_old(7)
    assert removed == 1
    assert store.get(task["id"]) is not None
    assert store.get(wf["id"]) is None


def test_purge_old_zero_means_disabled(store):
    old = time.time() - 30 * 86400
    wf = store.create("旧画布会话", "/tmp/proj", kind="workflow", origin="wf1")
    store._sys.execute("UPDATE sessions SET created_at=? WHERE id=?", (old, wf["id"]))
    store._sys.commit()
    assert store.purge_old(0) == 0
    assert store.get(wf["id"]) is not None


def test_latest_kept_when_purging(store):
    fresh = store.create("新画布会话", "/tmp/proj", kind="workflow", origin="wf1")
    assert store.purge_old(7) == 0
    assert store.get(fresh["id"]) is not None
