from __future__ import annotations

import pytest

from app.agent.plan import PlanController, PlanState
from app.agent.runner import AgentRunner
from app.chat.session_runtime import SessionRuntimeRegistry
from app.chat.sessions import SessionStore


class _Runner(AgentRunner):

    def __init__(self, sessions: SessionStore, rt=None) -> None:
        self.sessions = sessions
        self.session_rt = rt or SessionRuntimeRegistry()
        self._default_plan = PlanController()


@pytest.fixture()
def sess():
    return SessionStore()


@pytest.fixture()
def runner(sess):
    return _Runner(sess)


@pytest.fixture()
def sid(sess):
    return sess.create(title="计划用例")["id"]


def test_controller_states_are_memory_only():
    ctrl = PlanController()
    assert ctrl.state is PlanState.idle
    assert ctrl.is_active is False

    ctrl.enter_planning("s1")
    assert ctrl.state is PlanState.planning
    assert ctrl.plan_text == ""

    assert ctrl.on_plan_complete("## 计划") is True
    assert ctrl.state is PlanState.awaiting_approval
    assert ctrl.awaiting_approval is True
    assert ctrl.plan_text == "## 计划"

    assert ctrl.approve() is True
    assert ctrl.state is PlanState.executing
    assert ctrl.is_write_allowed is True

    ctrl.reset()
    assert ctrl.state is PlanState.idle
    assert ctrl.plan_text == ""


def test_controller_rejects_out_of_order_transitions():
    ctrl = PlanController()
    assert ctrl.on_plan_complete("x") is False
    assert ctrl.approve() is False
    assert ctrl.modify("再改改") is False
    assert ctrl.cancel() is False


def test_plan_for_is_idempotent_per_session(runner, sid):
    first = runner.plan_for(sid)
    second = runner.plan_for(sid)
    assert first is second


def test_empty_session_id_falls_back_to_default_plan(runner):
    assert runner.plan_for("") is runner._default_plan


def test_plan_state_does_not_survive_restart(runner, sid):
    ctrl = runner.plan_for(sid)
    ctrl.enter_planning(sid)
    ctrl.on_plan_complete("## 实施计划\n1. 改 A\n2. 改 B")
    assert ctrl.state is PlanState.awaiting_approval

    reborn = _Runner(SessionStore())
    assert reborn.plan_for(sid).state is PlanState.idle
    assert reborn.plans_snapshot() == {}


def test_plans_snapshot_reports_in_memory_states(runner, sid):
    ctrl = runner.plan_for(sid)
    ctrl.enter_planning(sid)
    ctrl.on_plan_complete("## 计划")
    assert runner.plans_snapshot() == {sid: "awaiting_approval"}

    ctrl.approve()
    assert runner.plans_snapshot() == {sid: "executing"}

    ctrl.reset()
    assert runner.plans_snapshot() == {}


def test_plans_snapshot_without_registry_is_empty():
    r = _Runner(SessionStore())
    r.session_rt = None
    assert r.plans_snapshot() == {}


def test_plan_state_is_per_session(runner, sess):
    a = sess.create(title="A")["id"]
    b = sess.create(title="B")["id"]
    ca, cb = runner.plan_for(a), runner.plan_for(b)
    assert ca is not cb
    ca.enter_planning(a)
    ca.on_plan_complete("## A 的计划")
    assert cb.state is PlanState.idle
    assert runner.plan_for(a) is ca


def test_drop_plan_clears_memory(runner, sid):
    ctrl = runner.plan_for(sid)
    ctrl.enter_planning(sid)
    ctrl.on_plan_complete("## 计划")
    assert runner.plans_snapshot() == {sid: "awaiting_approval"}

    runner.drop_plan(sid)
    assert runner.plans_snapshot() == {}
    pass
    assert runner.plan_for(sid) is not ctrl


def test_drop_plan_on_unknown_session_is_noop(runner):
    runner.drop_plan("不存在的会话")
    runner.drop_plan("")
    assert runner.plans_snapshot() == {}
