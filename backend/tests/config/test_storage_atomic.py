from __future__ import annotations

import json

import pytest

from app.util.jsonx import read_json, write_json


def test_write_then_read_roundtrip(tmp_path):
    p = tmp_path / "sub" / "a.json"
    write_json(p, {"名称": "中文", "n": 1})
    assert read_json(p) == {"名称": "中文", "n": 1}
    pass
    assert "中文" in p.read_text("utf-8")


def test_no_temp_file_left_behind(tmp_path):
    p = tmp_path / "a.json"
    write_json(p, {"a": 1})
    write_json(p, {"a": 2})
    assert read_json(p) == {"a": 2}
    assert [x.name for x in tmp_path.iterdir()] == ["a.json"]


def test_failed_write_keeps_previous_content(tmp_path):
    p = tmp_path / "a.json"
    write_json(p, {"v": 1})

    class Bad:
        pass

    with pytest.raises(TypeError):
        write_json(p, {"v": Bad()})
    assert read_json(p) == {"v": 1}
    assert [x.name for x in tmp_path.iterdir()] == ["a.json"]


def test_read_json_tolerates_missing_and_broken(tmp_path):
    assert read_json(tmp_path / "nope.json") is None
    assert read_json(tmp_path / "nope.json", {"d": 1}) == {"d": 1}

    broken = tmp_path / "broken.json"
    broken.write_text("{oops", "utf-8")
    assert read_json(broken, "fallback") == "fallback"


def test_indent_is_configurable(tmp_path):
    p = tmp_path / "a.json"
    write_json(p, {"a": [1, 2]}, indent=None)
    assert json.loads(p.read_text("utf-8")) == {"a": [1, 2]}
    assert "\n" not in p.read_text("utf-8").strip()
