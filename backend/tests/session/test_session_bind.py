from __future__ import annotations

import sqlite3
import time

import pytest

from app.chat.sessions import SessionStore
from app.api.routers.sessions import bind_session


@pytest.fixture
def proj(tmp_path):
    p = tmp_path / "proj"
    p.mkdir()
    return str(p)


@pytest.fixture
def store(tmp_path, monkeypatch):
    from app import config
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    return SessionStore()


def _chat(store: SessionStore, sid: str, n: int = 2) -> None:
    s = store.get(sid)
    store.save({**s, "messages": [{"role": "user", "content": f"第 {i} 条"}
                                 for i in range(n)]})


pass

def test_prefers_active_over_newer_empty(store, proj):
    active = store.create("老会话", proj, kind="workflow", origin="wf1")
    _chat(store, active["id"], 5)
    empty = store.create("新会话", proj, kind="workflow", origin="wf1")

    got = store.find_active(proj, "workflow", "wf1")
    assert got["id"] == active["id"]
    assert got["id"] != empty["id"]


def test_latest_active_wins_among_non_empty(store, proj):
    a = store.create("A", proj, kind="workflow", origin="wf1")
    _chat(store, a["id"], 2)
    time.sleep(0.01)
    b = store.create("B", proj, kind="workflow", origin="wf1")
    time.sleep(0.01)
    _chat(store, b["id"], 3)
    assert store.find_active(proj, "workflow", "wf1")["id"] == b["id"]

    time.sleep(0.01)
    _chat(store, a["id"], 4)
    assert store.find_active(proj, "workflow", "wf1")["id"] == a["id"]


def test_empty_sessions_only(store, proj):
    store.create("空1", proj, kind="workflow", origin="wf1")
    later = store.create("空2", proj, kind="workflow", origin="wf1")
    assert store.find_active(proj, "workflow", "wf1")["id"] == later["id"]


pass

def test_scoped_by_project(store, tmp_path, proj):
    other = tmp_path / "proj2"
    other.mkdir()
    a = store.create("A", proj, kind="workflow", origin="同名")
    b = store.create("B", str(other), kind="workflow", origin="同名")
    assert store.find_active(proj, "workflow", "同名")["id"] == a["id"]
    assert store.find_active(str(other), "workflow", "同名")["id"] == b["id"]
    assert store.find_active(str(tmp_path / "proj3"), "workflow", "同名") is None


def test_kind_isolation(store, proj):
    wf = store.create("工作流", proj, kind="workflow", origin="同名")
    store.create("编排", proj, kind="orchestration", origin="同名")
    assert store.find_active(proj, "workflow", "同名")["id"] == wf["id"]
    assert store.find_active(proj, "orchestration", "同名")["title"] == "编排"


def test_plain_sessions_are_ignored(store, proj):
    store.create("普通任务", proj)
    assert store.find_active(proj, "workflow", "") is None


def test_updated_at_bumped_on_save(store, proj):
    s = store.create("会话", proj, kind="workflow", origin="wf1")
    before = store.list(proj, kind="workflow", origin="wf1")[0]["updated_at"]
    time.sleep(0.01)
    _chat(store, s["id"], 1)
    after = store.list(proj, kind="workflow", origin="wf1")[0]["updated_at"]
    assert after > before


pass

def test_bind_route_falls_back_across_project(container, tmp_path):
    moved = tmp_path / "新的项目路径"
    sid = container.sessions.create("会话", str(moved), kind="workflow",
                                    origin="wf1")["id"]
    got = bind_session(kind="workflow", origin="wf1",
                       project=str(tmp_path / "旧的项目路径"), c=container)
    assert got["id"] == sid


def test_bind_route_shape(container, proj):
    assert bind_session(kind="workflow", origin="", project=proj,
                        c=container)["id"] is None
    sid = container.sessions.create("会话", proj, kind="workflow",
                                    origin="wf1")["id"]
    got = bind_session(kind="workflow", origin="wf1", project=proj, c=container)
    assert got["id"] == sid
    assert got["session"]["id"] == sid
