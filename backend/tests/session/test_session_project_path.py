from __future__ import annotations

from app.chat.sessions import SessionStore
from app.util import pathx

SHARE = pathx.SHARE_ROOT
CANON = SHARE + "/agent/content/motion"


def test_create_stores_canonical_spelling():
    store = SessionStore()
    s = store.create("t", "/home/swf/agent/content/motion")
    assert store.get(s["id"])["project"] == CANON


def test_physical_spelling_also_canonical():
    store = SessionStore()
    s = store.create("t", "/mnt/mydisk/share/agent/content/motion")
    assert store.get(s["id"])["project"] == CANON


def test_list_hits_every_spelling():
    store = SessionStore()
    sid = store.create("t", "/home/swf/agent/content/motion")["id"]
    for raw in ("/home/swf/agent/content/motion",
                "/mnt/mydisk/share/agent/content/motion",
                CANON):
        ids = [x["id"] for x in store.list(pathx.project_path(raw))]
        assert sid in ids, raw


def test_foreign_project_untouched():
    store = SessionStore()
    s = store.create("t", "/tmp/some/proj")
    assert store.get(s["id"])["project"] == "/tmp/some/proj"


def test_create_accepts_project_name(container):
    from app.store import layout
    from app.store.kv import RegistryStore

    name = "motion"
    path = pathx.project_path(str(container.projects.root) + "/" + name)
    RegistryStore().add(path)
    s = container.sessions.create("t", name)
    assert container.sessions.get(s["id"])["project"] == path
    assert layout.project_key(path) == "motion"


def test_list_and_find_active_accept_project_name(container):
    from app.store.kv import RegistryStore
    from app.store.project_names import project_of
    name = "paid"
    path = pathx.project_path(str(container.projects.root) + "/" + name)
    RegistryStore().add(path)
    sid = container.sessions.create("t", name)["id"]
    assert [x["id"] for x in container.sessions.list(project_of(name))] == [sid]

    wf = container.sessions.create("wf", name, kind="workflow", origin="wf1")
    hit = container.sessions.find_active(project_of(name), "workflow", "wf1")
    assert hit["id"] == wf["id"]
