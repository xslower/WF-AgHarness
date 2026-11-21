from __future__ import annotations

import time

import pytest

from app.chat.sessions import SessionStore
from app.store.session_db import (PURGEABLE_KINDS, WF_NODE_KIND,
                                  WF_SESSION_KIND)


@pytest.fixture
def store(tmp_path, monkeypatch):
    from app import config as cfg

    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path)
    monkeypatch.setattr(cfg, "RUNTIME_DIR", tmp_path / "runtime", raising=False)
    return SessionStore()


def _wf(store, project, origin="VIDEO-背景编排"):
    return store.create(title="会话", project=project,
                        kind=WF_SESSION_KIND, origin=origin)["id"]


def _node(store, project, sid, node="n1"):
    store.save({"id": f"{sid}__{node}", "title": node, "project": project,
                "created_at": time.time(), "messages": [
                    {"role": "user", "content": "任务"},
                    {"role": "assistant", "content": "结果"}],
                "kind": WF_NODE_KIND, "origin": sid})


def test_empty_shell_is_recycled_but_used_session_is_kept(store):
    p = "/home/swf/share/motion"
    empty = _wf(store, p)
    used = _wf(store, p, "VIDEO-采集与入库")
    _node(store, p, used)

    assert store.wf_node_parents() == {used}
    assert store.purge_empty_wf_sessions() == 1
    assert store.session_head(empty) is None
    assert store.session_head(used) is not None


def test_keep_protects_session_still_in_use(store):
    p = "/home/swf/share/motion"
    sid = _wf(store, p)
    assert store.purge_empty_wf_sessions(keep={sid}) == 0
    assert store.session_head(sid) is not None


def test_purge_old_covers_wf_kinds_but_never_normal_tasks(store):
    assert WF_SESSION_KIND in PURGEABLE_KINDS
    assert WF_NODE_KIND in PURGEABLE_KINDS
    p = "/home/swf/share/motion"
    task = store.create(title="普通任务", project=p)["id"]
    wf = _wf(store, p)
    node = store.create(title="节点", project=p,
                        kind=WF_NODE_KIND, origin=wf)["id"]
    with store._sys_lock:
        old = time.time() - 10 * 86400
        for sid in (task, wf, node):
            store._sys.execute("UPDATE sessions SET created_at=? WHERE id=?",
                               (old, sid))
        store._sys.commit()

    assert store.purge_old(days=7) == 2
    assert store.session_head(task) is not None
    assert store.session_head(wf) is None
    assert store.session_head(node) is None


def test_save_creates_wf_node_index_row(store):
    p = "/home/swf/share/motion"
    sid = _wf(store, p)
    _node(store, p, sid)
    rows = store.list(project=p, kind=WF_NODE_KIND)
    assert len(rows) == 1
    assert rows[0]["id"] == f"{sid}__n1"
    assert rows[0]["origin"] == sid
    assert rows[0]["message_count"] == 2


def test_project_home_lists_only_normal_tasks(store):
    from types import SimpleNamespace
    from app.api.routers.project.overview import sessions_of
    from pathlib import Path

    p = "/home/swf/share/motion"
    store.create(title="普通任务", project=p)
    _wf(store, p)
    container = SimpleNamespace(sessions=store)
    rows = sessions_of(container, Path(p))
    assert len(rows) == 1 and rows[0]["title"] == "普通任务"
