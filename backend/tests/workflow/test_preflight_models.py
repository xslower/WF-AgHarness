from __future__ import annotations

from types import SimpleNamespace

from app.provider.models import ModelInfo, Provider
from app.workflow.preflight import check_models


def _cfg(parent=None, child=None):
    return SimpleNamespace(
        providers=[Provider(id="p", name="p", baseUrl="", apiKey="",
                            models=[ModelInfo(id="m"), ModelInfo(id="off", disabled=True)])],
        queues=SimpleNamespace(parent=parent or [], child=child or [], summary=[]))


def _wf(*nodes):
    return {"name": "t", "nodes": list(nodes)}


def test_bad_model_value_is_reported():
    issues: list[str] = []
    check_models(_wf({"id": "l", "type": "llm", "model": "p/gone"}), _cfg(), issues)
    assert len(issues) == 1 and "l" in issues[0] and "不存在" in issues[0]


def test_disabled_model_is_reported():
    issues: list[str] = []
    check_models(_wf({"id": "l", "type": "llm", "model": "p/off"}), _cfg(), issues)
    assert any("已禁用" in i for i in issues)


def test_empty_queue_is_reported():
    issues: list[str] = []
    check_models(_wf({"id": "l", "type": "llm", "model": "child"}), _cfg(), issues)
    assert any("child 队列是空的" in i for i in issues)


def test_valid_values_pass():
    issues: list[str] = []
    check_models(_wf({"id": "a", "type": "llm", "model": "p/m"},
                     {"id": "b", "type": "llm", "model": ""},
                     {"id": "c", "type": "llm", "model": "child"},
                     {"id": "d", "type": "image", "model": "${inputs.m}"}),
               _cfg(child=["p/m"]), issues)
    assert issues == []


def test_condition_and_subagent_model_values_are_checked():
    issues: list[str] = []
    check_models(_wf({"id": "c", "type": "condition", "mode": "llm", "model": "p/gone"},
                     {"id": "s", "type": "subagent", "model": "p/nope"},
                     {"id": "b", "type": "condition", "model": ""},
                     {"id": "t", "type": "subagent", "model": ""}), _cfg(), issues)
    assert len(issues) == 2
    assert any("c" in i and "不存在" in i for i in issues)
    assert any("s" in i and "不存在" in i for i in issues)


def test_no_config_is_skipped():
    issues: list[str] = []
    check_models(_wf({"id": "l", "type": "llm", "model": "p/gone"}), None, issues)
    assert issues == []
