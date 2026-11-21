from __future__ import annotations

import pytest

from app.event.bus import EventHub, match_topic


@pytest.fixture
def hub():
    h = EventHub()
    yield h
    h.clear()


def test_publish_delivers_envelope(hub):
    got = []
    hub.on("file.changed", got.append)
    ev = hub.publish("file.changed", {"path": "a.txt"})
    assert len(got) == 1
    assert got[0] is ev
    assert ev["topic"] == "file.changed"
    assert ev["payload"]["path"] == "a.txt"
    assert ev["seq"] == 1 and isinstance(ev["ts"], float)


def test_match_topic_single_segment_wildcard():
    assert match_topic("file.*", "file.changed")
    assert not match_topic("file.*", "file.changed.deep")
    assert match_topic("*", "anything.at.all")
    assert not match_topic("file.changed", "file.opened")


def test_wildcard_subscription(hub):
    got = []
    hub.on("file.*", lambda ev: got.append(ev["topic"]))
    hub.publish("file.changed")
    hub.publish("file.opened")
    hub.publish("tool.fs_write")
    assert got == ["file.changed", "file.opened"]


def test_key_replaces_previous_subscription(hub):
    hits = []
    hub.on("file.changed", lambda ev: hits.append("old"), key="recent")
    hub.on("file.changed", lambda ev: hits.append("new"), key="recent")
    hub.publish("file.changed")
    assert hits == ["new"]


def test_handler_error_is_isolated(hub):
    seen = []

    def boom(ev):
        raise RuntimeError("订阅者炸了")

    hub.on("file.changed", boom)
    hub.on("file.changed", lambda ev: seen.append(1))
    hub.publish("file.changed", {"x": 1})
    assert seen == [1]
    assert hub.stats()["errors"] == 1


def test_unsubscribe_function_and_off(hub):
    hits = []
    off = hub.on("tool.x", lambda ev: hits.append(1))
    off()
    hub.publish("tool.x")
    assert hits == []

    fn = lambda ev: hits.append(2)
    hub.on("tool.x", fn)
    hub.off("tool.x", fn)
    hub.publish("tool.x")
    assert hits == []


def test_topics_introspection(hub):
    hub.on("file.changed", lambda ev: None, key="recent")
    hub.on("tool.*", lambda ev: None, key="logger")
    topics = {t["topic"]: t["handlers"] for t in hub.topics()}
    assert topics["file.changed"] == ["recent"]
    assert topics["tool.*"] == ["logger"]


def test_clear(hub):
    hub.on("file.changed", lambda ev: None)
    hub.clear()
    assert hub.topics() == []
    assert hub.stats()["subscriptions"] == 0
