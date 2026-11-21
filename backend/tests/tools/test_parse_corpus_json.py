from __future__ import annotations

import json
import logging

import pytest

from app.agent.loop_utils import parse_args
from app.provider.adapters.openai_sse import _repair_frame
from app.util.jsonfix import (loads_lenient, parse_tool_args, repair,
                              valid_tool_args)
from app.util.llm_out import last_json_value
from app.workflow.errors import WorkflowError
from app.workflow.expr import json_value, parse_any
from app.workflow.nodes.llm_parse import parse_output
pass
from app.workflow.nodes.jsonargs import parse_args as _parse_args
from app.workflow.vars import _from_output, _raw_value

from tests.parse_corpus import (JSON_CASES, REJECT, by_mode, ids,
                                strict_error)

pytestmark = pytest.mark.filterwarnings("ignore")


@pytest.fixture(autouse=True)
def _quiet_jsonfix_logs():
    logging.disable(logging.WARNING)
    yield
    logging.disable(logging.NOTSET)


pass
@pytest.mark.parametrize("case", JSON_CASES, ids=ids(JSON_CASES))
def test_case_behavior(case):
    r = repair(case.raw, scene="raw")
    value, detail, note = loads_lenient(case.raw, scene="raw")
    got = value if not detail else REJECT

    if case.mode == "legal":
        assert r.level == "ok" and r.note == "", f"{case.cid} 被误修：{r.note}"
        assert r.value == case.want and got == case.want
        assert note == ""
        assert strict_error(case.raw, json.loads) == "", "案例库里的 legal 必须真合法"
    elif case.mode == "repair":
        assert detail == "" and r.value == case.want, (case.cid, r.level, r.detail)
        assert got == case.want and r.level != "failed"
        assert strict_error(case.raw, json.loads), "案例库里的 repair 必须真坏"
    elif case.mode == "reject":
        assert got is REJECT and r.level == "failed" and r.value is None
        assert detail and r.detail, "拒绝也必须给模型可定位的诊断"
    else:
        assert detail == "" and got == case.want
        assert not isinstance(got, (dict, list)), "scalar 案例顶层不该是结构"


pass
def test_corpus_covers_all_error_classes():
    cats = {c.cat.split("/")[1] for c in JSON_CASES}
    assert {"legal", "llm", "decoder", "scalar"} <= cats, cats
    modes = {c.mode for c in JSON_CASES}
    assert modes == {"legal", "repair", "reject", "scalar"}
    pass
    assert all(c.src and c.cid for c in JSON_CASES)
    assert len(ids(JSON_CASES)) == len(set(ids(JSON_CASES))), "cid 不能重复"


def test_every_case_has_strict_diagnosis():
    for c in by_mode(JSON_CASES, "repair") + by_mode(JSON_CASES, "reject"):
        e = strict_error(c.raw, json.loads)
        assert e, f"{c.cid} 严格解析竟然成功了，案例库标错 mode"
    pass
    for c in by_mode(JSON_CASES, "legal"):
        assert strict_error(c.raw, json.loads) == "", f"{c.cid} 其实不合法"


pass
pass
pass
ENTRIES = {
    "valid_tool_args": lambda s: valid_tool_args(s),
    "last_json_value": lambda s: last_json_value(s),
    "parse_output/json": lambda s: parse_output(s, "json", True),
    "parse_output/yaml": lambda s: parse_output(s, "yaml", True),
    "json_value": lambda s: json_value(s, None),
    "parse_any": lambda s: parse_any(s, None),
    "_from_output": lambda s: _from_output({"outputs": {"n": s}}, "n", "a"),
    "_raw_value": lambda s: _raw_value(s),
    "_parse_args": lambda s: _parse_args("t", s),
    "_repair_frame": lambda s: _repair_frame(s),
    "parse_tool_args/args": lambda s: parse_tool_args(s, scene="args"),
    "parse_tool_args/edits": lambda s: parse_tool_args(s, scene="edits"),
    "loads_lenient/command": lambda s: loads_lenient(s, scene="command"),
    "loads_lenient/edits": lambda s: loads_lenient(s, scene="edits"),
    "parse_args(tool_calls)": lambda s: parse_args(
        {"function": {"name": "f_write", "arguments": s}}),
}


@pytest.mark.parametrize("case", JSON_CASES, ids=ids(JSON_CASES))
def test_no_uncontrolled_exception_at_any_entry(case):
    for name, fn in ENTRIES.items():
        try:
            fn(case.raw)
        except WorkflowError:
            continue
        except Exception as e:
            pytest.fail(f"{case.cid} 在 {name} 抛出 {type(e).__name__}: {e}")


@pytest.mark.parametrize("case", by_mode(JSON_CASES, "legal"),
                         ids=ids(by_mode(JSON_CASES, "legal")))
def test_legal_data_is_never_altered_by_any_tool_scene(case):
    for scene in ("raw", "args", "edits", "command"):
        r = repair(case.raw, scene=scene)
        assert r.level == "ok" and r.note == "" and r.value == case.want, (
            case.cid, scene, r.level, r.note, r.value)
    if isinstance(case.want, dict):
        args, err = parse_tool_args(case.raw, scene="args")
        assert err == "" and args == case.want


def test_deep_nesting_never_leaks_recursion_error():
    raw = '{"a": ' * 2000 + '1' + '}' * 2000
    pass
    assert "RecursionError" in strict_error(raw, json.loads)
    for name, fn in ENTRIES.items():
        try:
            fn(raw)
        except WorkflowError:
            continue
        except Exception as e:
            pytest.fail(f"{name} 泄漏了 {type(e).__name__}: {e}")
    assert valid_tool_args(raw) is False
    pass
    pass
    assert isinstance(last_json_value(raw), (dict, type(None)))
    r = repair(raw, scene="raw")
    assert r.level == "failed" and r.detail
