from __future__ import annotations

from typing import Literal, Optional

import pytest

from app.tools import toolschema as ts


def _mk(fn):
    return fn


def test_params_from_signature_types_and_required():
    def demo(text: str, count: int = 3, flag: bool = False) -> str:
        return text

    rules, required = ts.params_from_signature(demo)
    assert rules["text"]["type"] == "string"
    assert rules["text"]["description"] == "要处理的文本"
    assert rules["count"] == {"type": "integer", "description": "重复次数"}
    assert rules["flag"]["type"] == "boolean"
    assert required == ["text"]


def test_ctx_param_is_skipped():
    def demo(topic: str, ctx) -> str:
        return topic

    rules, required = ts.params_from_signature(demo)
    assert "ctx" not in rules
    assert required == ["topic"]


def test_optional_and_literal():
    def demo(mode: Literal["fast", "precise"] = "fast",
             note: Optional[str] = None) -> str:
        return mode

    rules, required = ts.params_from_signature(demo)
    assert rules["mode"]["enum"] == ["fast", "precise"]
    assert rules["note"]["type"] == "string"
    assert required == []


def test_missing_annotation_raises_with_param_name():
    def demo(mystery) -> str:
        return ""

    with pytest.raises(ts.SchemaError, match="mystery"):
        ts.params_from_signature(demo)


def test_explicit_params_win():
    def demo(action: str = "list") -> str:
        return action

    params = {"action": {"type": "string", "enum": ["list", "purge"],
                         "description": "声明里的说法"}}
    rules, required = ts.build(demo, params=params, required=["action"])
    assert rules["action"]["enum"] == ["list", "purge"]
    assert rules["action"]["description"] == "声明里的说法"
    assert required == ["action"]


def test_explicit_params_missing_arg_is_filled_from_signature():
    def demo(path: str, mode: int = 1) -> str:
        return path

    rules, required = ts.build(demo, params={"path": {"type": "string"}})
    assert set(rules) == {"path", "mode"}
    assert rules["mode"]["type"] == "integer"
    assert required == ["path"]


def test_required_inferred_when_not_given():
    def demo(a: str, b: str = "") -> str:
        return a + b

    _, required = ts.build(demo, params={"a": {"type": "string"},
                                        "b": {"type": "string"}})
    assert required == ["a"]


def test_docstring_without_args_section():
    def demo(path: str) -> str:
        return path

    summary, args = ts.parse_docstring_args(demo.__doc__)
    assert summary.startswith("读一个文件。")
    assert args == {}


def test_missing_description_detected():
    def no_doc(a: str) -> str:
        return a

    assert ts.missing_description(no_doc) == "no_doc"
    assert ts.missing_description(lambda a: a) == "<lambda>"


def test_schema_error_does_not_leak_partial_rules():
    def demo(ok: str, broken) -> str:
        return ok

    with pytest.raises(ts.SchemaError):
        ts.params_from_signature(demo)


def test_string_annotations_from_future_import():
    namespace: dict = {}
    exec(
        "from __future__ import annotations\n"
        "def demo(name: str, n: int = 1, tags: list[str] | None = None,\n"
        "         kind: Literal['a', 'b'] = 'a', ratio: float = 0.5) -> str:\n"
        "    '''演示。'''\n"
        "    return name\n",
        {"Literal": Literal}, namespace)
    rules, required = ts.params_from_signature(namespace["demo"])
    assert rules["name"]["type"] == "string"
    assert rules["n"]["type"] == "integer"
    assert rules["tags"]["type"] == "array"
    assert rules["kind"]["enum"] == ["a", "b"]
    assert rules["ratio"]["type"] == "number"
    assert required == ["name"]


def test_explicit_required_filters_unknown_names():
    def demo(name: str, n: int = 1) -> str:
        return name

    rules, required = ts.build(
        demo, params={"name": {"type": "string"}, "n": {"type": "integer"}},
        required=["name", "gone_param"])
    assert set(rules) == {"name", "n"}
    assert required == ["name"]
