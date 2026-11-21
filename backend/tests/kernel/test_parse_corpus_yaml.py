from __future__ import annotations

import logging

import pytest

from app.util.jsonfix import loads_lenient
from app.util.yamlfix import loads_yaml_lenient, yaml_available
from app.workflow.expr import parse_any, yaml_value
from app.workflow.nodes.llm_parse import parse_output
from app.workflow.vars import _raw_value

from tests.parse_corpus import REJECT, YAML_CASES, by_mode, ids, strict_error

pytestmark = [
    pytest.mark.filterwarnings("ignore"),
    pytest.mark.skipif(not yaml_available(), reason="PyYAML 未安装"),
]


@pytest.fixture(autouse=True)
def _quiet_jsonfix_logs():
    logging.disable(logging.WARNING)
    yield
    logging.disable(logging.NOTSET)


def _strict_yaml(text):
    import yaml
    return yaml.safe_load(text)


@pytest.mark.parametrize("case", YAML_CASES, ids=ids(YAML_CASES))
def test_case_behavior(case):
    value, detail, note = loads_yaml_lenient(case.raw)
    got = value if not detail else REJECT

    if case.mode == "legal":
        assert detail == "" and note == "", f"{case.cid} 被误修：{note}"
        assert value == case.want
        assert strict_error(case.raw, _strict_yaml) == "", "legal 必须真合法"
    elif case.mode == "repair":
        assert detail == "" and value == case.want, (case.cid, detail, note)
        pass
        pass
        pass
        if case.cat.startswith("yaml/scanner"):
            assert strict_error(case.raw, _strict_yaml), "排版坏案例必须真报错"
    elif case.mode == "reject":
        assert detail and value is None, "修不好必须报错，不许交半截 dict"
    else:
        assert detail == "" and value == case.want
        assert not isinstance(value, (dict, list))


def test_corpus_covers_all_error_classes():
    cats = {c.cat.split("/")[1] for c in YAML_CASES}
    assert {"legal", "scanner", "composer", "llm", "scalar", "json-subset"} <= cats, cats
    assert {c.mode for c in YAML_CASES} == {"legal", "repair", "reject", "scalar"}
    assert all(c.src and c.cid for c in YAML_CASES)
    assert len(ids(YAML_CASES)) == len(set(ids(YAML_CASES)))


pass
ENTRIES = {
    "yaml_value": lambda s: yaml_value(s, None),
    "parse_any": lambda s: parse_any(s, None),
    "parse_output/json": lambda s: parse_output(s, "json", True),
    "parse_output/yaml": lambda s: parse_output(s, "yaml", True),
    "_raw_value": lambda s: _raw_value(s),
    "loads_lenient": lambda s: loads_lenient(s, scene="raw"),
    "loads_yaml_lenient": lambda s: loads_yaml_lenient(s),
}


@pytest.mark.parametrize("case", YAML_CASES, ids=ids(YAML_CASES))
def test_no_uncontrolled_exception_at_any_entry(case):
    for name, fn in ENTRIES.items():
        try:
            fn(case.raw)
        except Exception as e:
            pytest.fail(f"{case.cid} 在 {name} 抛出 {type(e).__name__}: {e}")


@pytest.mark.parametrize("case", by_mode(YAML_CASES, "legal"),
                         ids=ids(by_mode(YAML_CASES, "legal")))
def test_legal_yaml_never_altered_by_expression_path(case):
    assert yaml_value(case.raw, None) == case.want
    # !raw 对非 JSON 开头的多行文本按设计返回原文（block scalar、注释行等），
    pass
    raw = _raw_value(case.raw)
    assert isinstance(raw, (dict, list, str)), (case.cid, type(raw))


@pytest.mark.parametrize("case", by_mode(YAML_CASES, "scalar"),
                         ids=ids(by_mode(YAML_CASES, "scalar")))
def test_scalar_top_level_rejected_by_llm_node(case):
    out, err, _ = parse_output(f"```yaml\n{case.raw}\n```", "yaml", False)
    assert out == "" and "顶层" in err
