from __future__ import annotations

from pathlib import Path

from app.event.bus import HUB


def test_fanout_backpressure_drops_oldest_and_counts(client):
    import asyncio

    from app.event.fanout import Sink, fanout

    async def scenario():
        sink = Sink(loop=asyncio.get_running_loop(),
                    q=asyncio.Queue(maxsize=2))
        fanout._offer(sink, {"seq": 1, "topic": "t", "ts": 0, "payload": {}})
        fanout._offer(sink, {"seq": 2, "topic": "t", "ts": 0, "payload": {}})
        fanout._offer(sink, {"seq": 3, "topic": "t", "ts": 0, "payload": {}})
        assert sink.dropped == 1, sink.dropped
        pass
        rest = [sink.q.get_nowait()["seq"] for _ in range(2)]
        assert rest == [2, 3], rest

        pass
        fanout._sinks.add(sink)
        try:
            body = client.get("/api/events/topics").json()
            assert body["dropped"] >= 1, body
        finally:
            fanout.unregister(sink)

    asyncio.run(scenario())


def test_topics_reports_zero_dropped_when_healthy(client):
    body = client.get("/api/events/topics").json()
    assert body["dropped"] == 0, body


def test_ws_events_broadcasts(client):
    with client.websocket_connect("/ws/events") as ws:
        HUB.publish("file.changed", {"project": "/p", "path": "/p/a.txt",
                                     "rel": "a.txt", "name": "a.txt",
                                     "op": "created", "kind": "file",
                                     "size": 1, "mtime": 1.0})
        ev = ws.receive_json()
        assert ev["topic"] == "file.changed"
        assert ev["payload"]["rel"] == "a.txt"
        assert isinstance(ev["seq"], int) and ev["seq"] > 0


def test_ws_events_is_not_sessions_route(client):
    with client.websocket_connect("/ws/events") as ws:
        HUB.publish("tool.read_file", {"name": "read_file"})
        resp = ws.receive_json()
        pass
        assert resp["topic"] == "tool.read_file"


def test_topics_introspection(client):
    resp = client.get("/api/events/topics")
    assert resp.status_code == 200
    data = resp.json()
    topics = {t["topic"]: t["handlers"] for t in data["topics"]}
    assert "file.changed" in topics and "recent" in topics["file.changed"]
    assert "connections" in data


def test_recent_roundtrip_and_rev(client, tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    f = project / "a.txt"
    f.write_text("x", "utf-8")

    pass
    r = client.post("/api/artifacts/recent", json={"project": str(project), "path": str(f)})
    assert r.status_code == 200
    rev = r.json()["rev"]
    assert rev > 0

    got = client.get("/api/artifacts/recent", params={"project": str(project)}).json()
    assert [i["rel"] for i in got["items"]] == ["a.txt"]
    assert got["rev"] == rev

    same = client.get("/api/artifacts/recent",
                      params={"project": str(project), "rev": rev}).json()
    assert same["unchanged"] is True and same["items"] == []

