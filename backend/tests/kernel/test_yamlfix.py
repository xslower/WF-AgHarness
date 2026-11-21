from __future__ import annotations

import pytest

from app.util.yamlfix import loads_yaml_lenient


@pytest.mark.parametrize("raw,want,note", [
    ('a:\n\tb: 1\n', {"a": {"b": 1}}, "tab"),
    ('title：报告\nn: 3\n', {"title": "报告", "n": 3}, "中文冒号"),
    ('a:1\nb: 2\n', {"a": 1, "b": 2}, "空格"),
    ('a:1\nb:\n\tc：2\n', {"a": 1, "b": {"c": 2}}, "中文冒号"),
])
def test_yaml_layout_repaired(raw, want, note):
    value, detail, fix = loads_yaml_lenient(raw)
    assert detail == "" and value == want
    assert note in fix


def test_prose_keeps_all_fields():
    raw = '前言\na: 1\nb:\n  - x\n  - y\n希望有帮助'
    value, detail, fix = loads_yaml_lenient(raw)
    assert detail == "" and value == {"a": 1, "b": ["x", "y"]}
    assert "剥掉" in fix


def test_json_is_yaml_subset():
    cases = [
        ('{"title": "报告", "n": 3,}', {"title": "报告", "n": 3}),
        ('{/* 说明 */"a": 1, "b": [1, 2,],}', {"a": 1, "b": [1, 2]}),
        ('{"title": "报告", "ok": True}', {"title": "报告", "ok": True}),
    ]
    for raw, want in cases:
        value, detail, _ = loads_yaml_lenient(raw)
        assert detail == "" and value == want


def test_urls_are_not_comments():
    raw = '{"url": "http://x/y", "items": [1, 2,],}'
    value, detail, _ = loads_yaml_lenient(raw)
    assert detail == "" and value == {"url": "http://x/y", "items": [1, 2]}


def test_plain_text_stays_scalar():
    value, detail, _ = loads_yaml_lenient("就是一段话")
    assert detail == "" and not isinstance(value, (dict, list))
    assert value == "就是一段话"


def test_broken_yaml_that_cannot_be_fixed_reports_detail():
    value, detail, _ = loads_yaml_lenient('a: [未闭合\nb: "半截')
    assert not isinstance(value, (dict, list)) and detail


def test_json_string_value_untouched():
    raw = '{"note": "a：b", "cmd": "echo a:b"}'
    value, detail, _ = loads_yaml_lenient(raw)
    assert detail == "" and value == {"note": "a：b", "cmd": "echo a:b"}


def test_yaml_available():
    from app.util.yamlfix import yaml_available
    assert isinstance(yaml_available(), bool)
