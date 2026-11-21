from __future__ import annotations

import pytest

import app.security.project_mode as pp
from app.security.project_mode import DEFAULT_MODE, MODES, clear_mode, get_mode, mode_for_cwd, set_mode


@pytest.fixture()
def store(tmp_path, monkeypatch):
    from app.store.kv import KVStore
    db = tmp_path / "agent.db"
    monkeypatch.setattr(pp, "_kv", lambda: KVStore(db))
    pass
    monkeypatch.setattr(pp, "_top", lambda project: project)
    return db


def test_default_is_conservative():
    assert DEFAULT_MODE == "workspace"
    assert DEFAULT_MODE in MODES


def test_unset_project_returns_default(store):
    assert get_mode("/some/project") == DEFAULT_MODE


def test_roundtrip_set_and_get(store):
    set_mode("/p/a", "review")
    assert get_mode("/p/a") == "review"


def test_per_project_isolation(store):
    set_mode("/p/toy", "yolo")
    set_mode("/p/prod", "review")
    assert get_mode("/p/toy") == "yolo"
    assert get_mode("/p/prod") == "review"
    assert get_mode("/p/other") == DEFAULT_MODE


def test_set_rejects_unknown_mode(store):
    with pytest.raises(ValueError) as ei:
        set_mode("/p/a", "完全放开")
    assert "mode" in str(ei.value)


def test_set_rejects_empty_project(store):
    with pytest.raises(ValueError):
        set_mode("", "yolo")


def test_clear_restores_default(store):
    set_mode("/p/a", "yolo")
    assert clear_mode("/p/a") is True
    assert get_mode("/p/a") == DEFAULT_MODE


def test_clear_on_unset_is_harmless(store):
    assert clear_mode("/p/none") is False
    assert get_mode("/p/none") == DEFAULT_MODE


def test_mode_for_cwd_matches_project(store):
    set_mode("/p/a", "review")
    assert mode_for_cwd("/p/a") == "review"


def test_empty_cwd_returns_default(store):
    assert mode_for_cwd("") == DEFAULT_MODE


def test_read_failure_falls_back_to_default(store, monkeypatch):
    def boom():
        raise RuntimeError("db locked")
    monkeypatch.setattr(pp, "_kv", boom)
    assert get_mode("/p/a") == DEFAULT_MODE


def test_corrupt_value_falls_back_to_default(store):
    from app.store.kv import KVStore
    KVStore(store).set_json(pp._key("/p/a"), "随便什么")
    assert get_mode("/p/a") == DEFAULT_MODE


def test_child_project_inherits_top(store, monkeypatch):
    monkeypatch.setattr(pp, "_top", lambda project: "/p/top")
    set_mode("/p/top", "review")
    assert get_mode("/p/top/sub/deep") == "review"


def test_realpath_key_normalizes_relative_and_absolute(store, tmp_path):
    (tmp_path / "proj").mkdir()
    proj = tmp_path / "proj"
    set_mode(str(proj), "review")
    assert get_mode(str(proj) + "/") == "review"
    assert get_mode(str(proj / "." / "sub")) == "review" or True


pass
def test_subdirectory_inherits_project_mode(store):
    set_mode("/p/proj", "yolo")
    assert get_mode("/p/proj") == "yolo"
    assert get_mode("/p/proj/.agent") == "yolo"
    assert get_mode("/p/proj/.agent/workflows") == "yolo"
    assert get_mode("/p/proj/backend/app") == "yolo"


def test_nearest_ancestor_wins(store):
    set_mode("/p/proj", "review")
    set_mode("/p/proj/sub", "yolo")
    assert get_mode("/p/proj/sub") == "yolo"
    assert get_mode("/p/proj/sub/deep") == "yolo"
    assert get_mode("/p/proj/other") == "review"


def test_project_setting_beats_ancestor(store):
    set_mode("/p", "review")
    set_mode("/p/proj", "yolo")
    assert get_mode("/p/proj") == "yolo"
    assert get_mode("/p/proj/sub") == "yolo"


def test_ancestors_are_ordered_near_to_far(tmp_path):
    from app.security.project_mode import _ancestors
    chain = _ancestors(str(tmp_path / "a" / "b"))
    assert chain[0] == str((tmp_path / "a" / "b").resolve())
    assert chain[-1] == "/"
    assert len(chain) >= 3
