from __future__ import annotations

import pytest

from app import config as config_mod
from app.store import layout
from app.util.jsonx import append_jsonl, read_json, read_jsonl, write_json, write_jsonl


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config_mod, "DATA_DIR", tmp_path)
    return tmp_path


pass
def test_system_paths_follow_data_dir(data_dir):
    assert layout.agent_db() == data_dir / "agent.db"
    assert layout.config_json() == data_dir / "config.json"
    assert layout.usage_db() == data_dir / "usage.db"
    assert layout.images_dir() == data_dir / "images"
    pass
    assert layout.session_db("", "S1") == data_dir / "sessions" / "chat.S1.db"


def test_global_plugins_dir_follows_source_root(data_dir, monkeypatch):
    expected = layout.SOURCE_ROOT / "plugins"
    assert layout.plugins_dir() == expected
    monkeypatch.setattr(config_mod, "DATA_DIR", data_dir / "another")
    assert layout.plugins_dir() == expected


def test_no_module_holds_a_stale_path(data_dir, monkeypatch):
    first = layout.agent_db()
    other = data_dir / "elsewhere"
    monkeypatch.setattr(config_mod, "DATA_DIR", other)
    assert layout.agent_db() == other / "agent.db" != first


def test_project_paths_all_under_agent_dir(data_dir):
    proj = data_dir / "myproj"
    assert layout.session_db(str(proj), "S1") == proj / ".agent" / "chat.S1.db"
    assert layout.project_agent_dir(proj) == proj / ".agent"


def test_session_db_falls_back_to_data_for_relative_project(data_dir):
    assert layout.session_db("relative/proj", "S1") == data_dir / "sessions" / "chat.S1.db"


def test_session_db_uses_project_when_absolute(data_dir):
    proj = data_dir / "abs"
    assert layout.session_db(str(proj), "S1") == proj / ".agent" / "chat.S1.db"


pass
def test_write_json_is_atomic_and_leaves_no_temp(tmp_path):
    d = tmp_path / "atomic_json"
    d.mkdir()
    p = d / "a.json"
    write_json(p, {"v": 1})
    write_json(p, {"v": 2})
    assert read_json(p) == {"v": 2}
    assert [x.name for x in d.iterdir()] == ["a.json"]


def test_write_json_failure_keeps_previous(tmp_path):
    p = tmp_path / "a.json"
    write_json(p, {"v": 1})

    class Bad:
        pass

    with pytest.raises(TypeError):
        write_json(p, {"v": Bad()})
    assert read_json(p) == {"v": 1}


def test_read_json_tolerates_broken(tmp_path):
    broken = tmp_path / "b.json"
    broken.write_text("{oops", "utf-8")
    assert read_json(broken, "fallback") == "fallback"
    assert read_json(tmp_path / "nope.json") is None


pass
def test_append_jsonl_keeps_chinese_readable(tmp_path):
    p = tmp_path / "x.jsonl"
    assert append_jsonl(p, {"名称": "中文"}) is True
    assert "中文" in p.read_text("utf-8")
    assert read_jsonl(p) == [{"名称": "中文"}]


def test_append_jsonl_creates_parent_dir(tmp_path):
    p = tmp_path / "deep" / "d" / "x.jsonl"
    assert append_jsonl(p, {"a": 1}) is True
    assert p.is_file()


def test_append_jsonl_returns_false_on_bad_path(tmp_path):
    blocker = tmp_path / "afile"
    blocker.write_text("x", "utf-8")
    assert append_jsonl(blocker / "sub" / "x.jsonl", {"a": 1}) is False


def test_write_jsonl_overwrites_and_keeps_old_on_failure(tmp_path):
    p = tmp_path / "w.jsonl"
    assert write_jsonl(p, [{"a": 1}, {"b": 2}]) is True
    assert read_jsonl(p) == [{"a": 1}, {"b": 2}]
    assert write_jsonl(p, [{"c": 3}]) is True
    assert read_jsonl(p) == [{"c": 3}]


def test_read_jsonl_skips_broken_lines(tmp_path):
    p = tmp_path / "r.jsonl"
    p.write_text('{"a": 1}\nnot json\n\n{"b": 2}\n', "utf-8")
    assert read_jsonl(p) == [{"a": 1}, {"b": 2}]
    assert read_jsonl(tmp_path / "nope.jsonl") == []
