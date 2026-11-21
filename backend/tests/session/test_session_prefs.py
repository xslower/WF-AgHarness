from __future__ import annotations

import pytest

from app.chat.sessions import SessionStore


@pytest.fixture
def store(tmp_dirs):
    return SessionStore()


def test_api_prefs_route_is_gone(tmp_dirs, client):
    c = client.app.state.container
    sid = c.sessions.create("t")["id"]
    r = client.post(f"/api/sessions/{sid}/prefs", json={"prefs": {"model": "a/b"}})
    assert r.status_code in (404, 405)


def test_session_detail_has_no_prefs(tmp_dirs, client):
    c = client.app.state.container
    sid = c.sessions.create("t")["id"]
    assert "prefs" not in client.get(f"/api/sessions/{sid}").json()


def test_schema_has_no_prefs_column(store):
    cols = [r[1] for r in store._sys.execute("PRAGMA table_info(sessions)")]
    assert "prefs" not in cols
