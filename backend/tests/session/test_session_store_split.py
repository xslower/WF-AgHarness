from __future__ import annotations


import pytest

from app import config as config_mod
from app.chat.sessions import SessionStore
from app.store import layout


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(config_mod, "DATA_DIR", tmp_path)
    return SessionStore()


pass
def test_store_exposes_physical_handles(store):
    assert store._sys is not None
    assert store.compactions is not None


def test_each_session_gets_its_own_db(store, tmp_path):
    db1 = store._db_for("", "sid-A")
    db2 = store._db_for("", "sid-B")
    assert db1 is not db2
    assert store._db_for("", "sid-A") is db1


def test_no_project_session_db_under_data_sessions(store, tmp_path):
    db = store._db_for("", "sid-C")
    p = layout.session_db("", "sid-C")
    assert p.name == "chat.sid-C.db"
    assert p.parent.name == "sessions"
    assert p.is_file()
    assert db is store._db_for("", "sid-C")


pass
def test_compactions_are_append_only_and_scoped(store, tmp_path):
    proj = tmp_path / "projB"
    proj.mkdir()
    s = store.create("t", project=str(proj))
    store.add_compaction(str(proj), s["id"], 3, [{"text": "摘要一"}])
    store.add_compaction(str(proj), s["id"], 5, [{"text": "摘要二"}])
    segs = store.get_compactions(str(proj), s["id"])
    assert [x["upto_seq"] for x in segs] == [3, 5]
    assert segs[0]["items"] == [{"text": "摘要一"}]

    store.clear_compactions(str(proj), s["id"])
    assert store.get_compactions(str(proj), s["id"]) == []


def test_compaction_ignores_empty_payload(store):
    store.add_compaction("", "sid-x", 0, [{"a": 1}])
    store.add_compaction("", "sid-x", 2, [])
    assert store.get_compactions("", "sid-x") == []
