from __future__ import annotations

import pytest

from app.workflow.nodes.llm import MAX_TOOL_ROUNDS, MAX_TOOL_ROUNDS_CAP, _tool_rounds


pass

@pytest.mark.parametrize("cfg,expect", [
    (None, MAX_TOOL_ROUNDS),
    ("", MAX_TOOL_ROUNDS),
    (30, 30),
    ("30", 30),
    (1, 1),
    (0, 1),
    (-5, 1),
    ("abc", MAX_TOOL_ROUNDS),
    (MAX_TOOL_ROUNDS_CAP + 100, MAX_TOOL_ROUNDS_CAP),
])
def test_tool_rounds_resolution(cfg, expect):
    assert _tool_rounds({"id": "x", "maxToolRounds": cfg}) == expect


def test_cap_prevents_runaway():
    assert _tool_rounds({"maxToolRounds": 10_000}) == MAX_TOOL_ROUNDS_CAP


pass

class _FakeEng:
    def __init__(self, wf):
        self._wf = wf

    def resolve_workflow(self, name):
        return self._wf


class _FakeWfEngine:

    def __init__(self, wf):
        self._eng = _FakeEng(wf)

    def engine_for(self, cwd):
        return self._eng


def _mode_for(wf, asked: str, engine=None):
    from app.agent.context import ContextMixin

    class Probe(ContextMixin):
        wf_engine = engine if engine is not None else _FakeWfEngine(wf)

    return Probe()._human_mode_for("x", "/p", asked)


def test_default_human_from_workflow_declaration():
    assert _mode_for({"defaultHuman": "auto-approve"}, "") == "auto-approve"
    assert _mode_for({"defaultHuman": "auto-approve"}, "deny") == "auto-approve"


def test_explicit_caller_wins_over_declaration():
    assert _mode_for({"defaultHuman": "auto-approve"}, "auto-reject") == "auto-reject"
    assert _mode_for({"defaultHuman": "auto-approve"}, "ask") == "ask"


def test_no_declaration_falls_back_to_deny():
    assert _mode_for({}, "") == "deny"
    assert _mode_for(None, "") == "deny"


def test_declaration_is_case_insensitive():
    assert _mode_for({"defaultHuman": "  AUTO-APPROVE  "}, "") == "auto-approve"


def test_broken_engine_does_not_crash():

    class Boom:
        def engine_for(self, cwd):
            raise RuntimeError("引擎挂了")

    assert _mode_for(None, "", engine=Boom()) == "deny"
