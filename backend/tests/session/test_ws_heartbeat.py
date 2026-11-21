from __future__ import annotations

import json

from app.store import event_log


def _new_session(client, project: str) -> str:
    r = client.post("/api/sessions", params={"title": "心跳测试", "project": project})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _ping(ws) -> dict:
    ws.send_text(json.dumps({"type": "ping"}))
    return json.loads(ws.receive_text())


def test_ping_gets_pong(client, tmp_dirs):
    sid = _new_session(client, str(tmp_dirs / "proj"))
    with client.websocket_connect(f"/ws/{sid}") as ws:
        got = _ping(ws)
        assert got["type"] == "pong"
        assert "ts" in got


def test_pong_not_written_to_event_log(client, tmp_dirs):
    project = str(tmp_dirs / "proj")
    sid = _new_session(client, project)
    with client.websocket_connect(f"/ws/{sid}") as ws:
        for _ in range(3):
            assert _ping(ws)["type"] == "pong"
    events = event_log.read_since(project, sid, since=0)
    assert all(ev.get("type") != "pong" for _i, ev in events)


def test_pong_still_works_after_session_outlet_is_gone(client, tmp_dirs):
    sid = _new_session(client, str(tmp_dirs / "proj"))
    with client.websocket_connect(f"/ws/{sid}") as ws:
        assert _ping(ws)["type"] == "pong"

        pass
        rt = client.app.state.container.session_rt().get(sid)
        rt.emit = None

        pass
        assert _ping(ws)["type"] == "pong"
