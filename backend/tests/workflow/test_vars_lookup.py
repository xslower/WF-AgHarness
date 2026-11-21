from __future__ import annotations

import json

import pytest

from app.workflow.vars import _lookup, _walk_path


def _vars(**kw) -> dict:
    base = {"inputs": {}, "outputs": {}, "output_paths": {}}
    base.update(kw)
    return base


pass
def test_inputs_object_returns_whole_mapping():
    v = _vars(inputs={"a": 1, "b": 2})
    assert _lookup(v, "inputs") == {"a": 1, "b": 2}


def test_empty_inputs_object_returns_none():
    assert _lookup(_vars(), "inputs") is None


def test_inputs_field():
    v = _vars(inputs={"topic": "AI"})
    assert _lookup(v, "inputs.topic") == "AI"
    assert _lookup(v, "inputs.missing") is None


def test_whole_output_by_id():
    v = _vars(outputs={"s1": "原文"})
    assert _lookup(v, "s1") == "原文"


def test_unknown_bare_key_is_none():
    assert _lookup(_vars(), "nope") is None


pass
def test_output_path_meta_wins_over_json_field(tmp_path):
    f = tmp_path / "out.txt"
    f.write_text("x")
    v = _vars(outputs={"s1": json.dumps({"path": "/模型说这是路径"})},
              output_paths={"s1": str(f)})
    assert _lookup(v, "s1.path") == str(f)


def test_output_bytes_meta(tmp_path):
    f = tmp_path / "out.txt"
    f.write_text("0123456789")
    v = _vars(outputs={}, output_paths={"s1": str(f)})
    assert _lookup(v, "s1.bytes") == "10"


def test_output_bytes_missing_file_is_none(tmp_path):
    v = _vars(outputs={}, output_paths={"s1": str(tmp_path / "gone.txt")})
    assert _lookup(v, "s1.bytes") is None


def test_meta_only_covers_path_and_bytes():
    v = _vars(outputs={"s1": json.dumps({"title": "标题"})},
              output_paths={"s1": "/tmp/x"})
    assert _lookup(v, "s1.title") == "标题"


pass
def test_drill_into_json_string_output():
    v = _vars(outputs={"s1": json.dumps({"data": {"items": [{"n": 1}, {"n": 2}]}})})
    assert _lookup(v, "s1.data.items.1.n") == 2


def test_drill_list_index_out_of_range():
    v = _vars(outputs={"s1": json.dumps([1, 2])})
    assert _lookup(v, "s1.5") is None


def test_drill_non_numeric_list_index():
    v = _vars(outputs={"s1": json.dumps([1, 2])})
    assert _lookup(v, "s1.x") is None


def test_drill_into_non_container_returns_none():
    v = _vars(outputs={"s1": json.dumps({"a": 42})})
    assert _lookup(v, "s1.a.b") is None


def test_unparseable_json_output_returns_none():
    v = _vars(outputs={"s1": "这不是 JSON"})
    assert _lookup(v, "s1.any") is None


def test_walk_path_on_plain_dict():
    assert _walk_path({"a": {"b": 3}}, "a.b") == 3
    assert _walk_path({"a": [10, 20]}, "a.1") == 20
    assert _walk_path(None, "a") is None


pass
def test_drill_into_broken_json_output_repairs():
    v = _vars(outputs={"s1": '{"data": {"items": [1, 2,],}, "ok": True}'})
    assert _lookup(v, "s1.data.items.1") == 2
    assert _lookup(v, "s1.ok") is True


def test_drill_into_truncated_output_closes_structs():
    v = _vars(outputs={"s1": '{"data": {"items": [1, 2'})
    assert _lookup(v, "s1.data.items.1") == 2


def test_drill_into_unrepairable_output_stays_none():
    v = _vars(outputs={"s1": '{"data": "半截'})
    assert _lookup(v, "s1.data") is None
