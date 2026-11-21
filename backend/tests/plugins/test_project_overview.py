from __future__ import annotations

import pytest

from app.api.routers.project.overview import MAX_SESSIONS, children_of, find_children, parent_of, sessions_of


def _mk_project(root, name, nested=()):
    p = root / name
    (p / ".agent").mkdir(parents=True)
    for sub in nested:
        (p / sub / ".agent").mkdir(parents=True)
    return p


pass
def test_find_children_flat():
    tree = {"path": "/a", "children": [
        {"name": "x", "path": "/a/x", "depth": 1, "children": [{}, {}]},
        {"name": "y", "path": "/a/y", "depth": 1, "children": []},
    ]}
    got = find_children(tree, __import__("pathlib").Path("/a"))
    assert [c["name"] for c in got] == ["x", "y"]
    assert got[0]["children"] == 2
    assert got[1]["children"] == 0


def test_find_children_recurses_into_deep_nodes():
    from pathlib import Path
    deep = {"path": "/a/b/c", "children": [{"name": "d", "path": "/a/b/c/d",
                                            "depth": 3, "children": []}]}
    tree = {"path": "/a", "children": [
        {"path": "/a/b", "children": [deep]},
    ]}
    got = find_children(tree, Path("/a/b/c"))
    assert [c["name"] for c in got] == ["d"]


def test_find_children_missing_node_returns_empty():
    from pathlib import Path
    assert find_children({"path": "/a", "children": []}, Path("/nope")) == []


def test_children_only_from_registry_no_dir_scan(tmp_path):
    proj = _mk_project(tmp_path, "top", nested=("s1", "s2"))
    (proj / "plain").mkdir()

    class C:
        class projects:
            @staticmethod
            def tree():
                return {"path": "/elsewhere", "children": []}

    assert children_of(C, proj) == []


def test_children_from_registry(tmp_path):
    from pathlib import Path
    proj = _mk_project(tmp_path, "top")

    class C:
        class projects:
            @staticmethod
            def tree():
                return {"path": "/projects", "children": [
                    {"name": "top", "path": str(proj), "depth": 1,
                     "children": [{"name": "s1", "path": str(proj / "s1"),
                                   "depth": 2, "children": []}]}]}

    assert [c["name"] for c in children_of(C, proj)] == ["s1"]


def test_children_of_unreadable_dir_is_empty(tmp_path):
    class C:
        class projects:
            @staticmethod
            def tree():
                return {"path": "/elsewhere", "children": []}

    got = children_of(C, tmp_path / "does-not-exist")
    assert got == []



pass
def test_parent_none_for_plain_dir(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    assert parent_of(plain, is_project=False, is_top=False) is None


def test_parent_none_for_top_project(tmp_path):
    outer = _mk_project(tmp_path, "outer", nested=("inner",))
    inner = outer / "inner"
    assert parent_of(inner, is_project=True, is_top=True) is None


def test_parent_from_registry(tmp_path):
    from app.store import layout as layout_mod
    from app.store.kv import RegistryStore

    outer = _mk_project(tmp_path, "outer")
    mid = outer / "mid"
    mid.mkdir()
    sub = mid / "sub"
    sub.mkdir()
    store = RegistryStore()
    store.add(str(outer))
    store.add(str(sub), str(outer))
    layout_mod.invalidate_project_cache()
    try:
        assert parent_of(sub, is_project=True, is_top=False) == str(outer)
        assert parent_of(outer, is_project=True, is_top=True) is None
    finally:
        store.remove(str(outer))
        store.remove(str(sub))
        layout_mod.invalidate_project_cache()


pass
def test_sessions_sorted_by_updated_at_and_capped():
    items = [{"id": str(i), "updated_at": i, "created_at": 0} for i in range(MAX_SESSIONS + 5)]

    class C:
        class sessions:
            @staticmethod
            def list(path, kind=None):
                assert kind == ""
                return items

    got = sessions_of(C, __import__("pathlib").Path("/x"))
    assert len(got) == MAX_SESSIONS
    assert got[0]["id"] == str(MAX_SESSIONS + 4)


def test_sessions_falls_back_to_created_at():
    class C:
        class sessions:
            @staticmethod
            def list(path, kind=None):
                return [{"id": "a", "created_at": 5}, {"id": "b", "created_at": 1}]

    got = sessions_of(C, __import__("pathlib").Path("/x"))
    assert [s["id"] for s in got] == ["a", "b"]


def test_sessions_error_degrades_to_empty():
    class C:
        class sessions:
            @staticmethod
            def list(path, kind=None):
                raise RuntimeError("db locked")

    assert sessions_of(C, __import__("pathlib").Path("/x")) == []


def test_session_row_defaults():
    class C:
        class sessions:
            @staticmethod
            def list(path, kind=None):
                return [{}]

    got = sessions_of(C, __import__("pathlib").Path("/x"))
    assert got[0]["title"] == "未命名" and got[0]["kind"] == "chat"
    assert got[0]["message_count"] == 0


pass
def test_workflows_nodes_count_is_int():
    from app.api.routers.project.overview import workflows_of

    class C:
        class _E:
            @staticmethod
            def list():
                return [{"name": "wf1", "status": "draft", "nodes": 12}]

        @staticmethod
        def wf_engine(_p):
            return C._E

    got = workflows_of(C, __import__("pathlib").Path("/x"))
    assert got == [{"name": "wf1", "status": "draft", "nodes": 12, "updated_at": None}]


def test_workflows_accepts_node_list():
    from app.api.routers.project.overview import workflows_of

    class C:
        class _E:
            @staticmethod
            def list():
                return [{"name": "wf2", "nodes": [{"id": "a"}, {"id": "b"}]}]

        @staticmethod
        def wf_engine(_p):
            return C._E

    got = workflows_of(C, __import__("pathlib").Path("/x"))
    assert got[0]["nodes"] == 2 and got[0]["status"] == ""


def test_workflows_error_degrades_to_empty():
    from app.api.routers.project.overview import workflows_of

    class C:
        @staticmethod
        def wf_engine(_p):
            raise RuntimeError("boom")

    assert workflows_of(C, __import__("pathlib").Path("/x")) == []
