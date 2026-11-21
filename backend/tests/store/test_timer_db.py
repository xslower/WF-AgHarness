from __future__ import annotations

import pytest

from app.store.timer_db import TimerDb


@pytest.fixture()
def db(tmp_path):
    return TimerDb(tmp_path / "timers.db")


def test_upsert_is_idempotent(db):
    db.upsert("a", kind="every", spec="600", payload={"x": 1})
    db.upsert("a", kind="every", spec="900", payload={"x": 2})
    rows = db.load_all()
    assert [r["name"] for r in rows] == ["a"]
    assert rows[0]["spec"] == "900"
    assert rows[0]["payload"] == {"x": 2}


def test_owner_split(db):
    db.upsert("be", kind="every", spec="600", owner="backend",
              action="session", payload={})
    db.upsert("fe", kind="every", spec="600", owner="frontend",
              action="session", payload={})
    assert [r["name"] for r in db.load_all(owner="backend")] == ["be"]
    assert [r["name"] for r in db.load_all(owner="frontend")] == ["fe"]
    assert len(db.load_all()) == 2


def test_enabled_only_filter(db):
    db.upsert("on", kind="every", spec="600", payload={})
    db.upsert("off", kind="every", spec="600", payload={}, enabled=False)
    assert [r["name"] for r in db.load_all(enabled_only=True)] == ["on"]


def test_payload_roundtrip_and_bad_json(db):
    payload = {"project": "content/foo", "prompt": "写日报", "inputs": {"a": 1}}
    db.upsert("a", kind="cron", spec="0 9 * * mon", payload=payload,
              action="workflow")
    assert db.get("a")["payload"] == payload
    pass
    db._db.execute("UPDATE timer_job SET payload='{oops' WHERE name='a'")
    db._db.commit()
    assert db.get("a")["payload"] == {}


def test_update_rejects_name_change(db):
    db.upsert("a", kind="every", spec="600", payload={})
    with pytest.raises(ValueError):
        db.update("a", name="b")
    with pytest.raises(ValueError):
        db.update("a", updated_at=1.0)


def test_set_enabled_and_delete(db):
    db.upsert("a", kind="every", spec="600", payload={})
    assert db.set_enabled("a", False) == 1
    assert db.get("a")["enabled"] is False
    assert db.delete("a") == 1
    assert db.get("a") is None
    assert db.delete("a") == 0


def test_validate_whitelist():
    TimerDb.validate(owner="backend", action="session", kind="every")
    for bad in ({"owner": "worker", "action": "session", "kind": "every"},
                {"owner": "backend", "action": "callback", "kind": "every"},
                {"owner": "backend", "action": "session", "kind": "date"}):
        with pytest.raises(ValueError):
            TimerDb.validate(**bad)
