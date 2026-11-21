from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.plan import PlanController, PlanState


pass
pass
pass
class TestPlanDecisionApprove:

    def test_approve_transitions_to_executing(self):
        ctrl = PlanController()
        ctrl.enter_planning("sid1")
        ctrl.on_plan_complete("## 计划")
        assert ctrl.state == PlanState.awaiting_approval

        result = ctrl.approve()
        assert result is True
        assert ctrl.state == PlanState.executing
        assert ctrl.is_write_allowed is True

    def test_approve_when_no_plan_pending_returns_false(self):
        ctrl = PlanController()
        assert ctrl.approve() is False
        assert ctrl.state == PlanState.idle

    def test_approve_when_already_executing_returns_false(self):
        ctrl = PlanController()
        ctrl.enter_planning("s1")
        ctrl.on_plan_complete("plan")
        ctrl.approve()
        assert ctrl.approve() is False


class TestPlanDecisionModify:

    def test_modify_transitions_back_to_planning(self):
        ctrl = PlanController()
        ctrl.enter_planning("sid1")
        ctrl.on_plan_complete("## 计划")

        result = ctrl.modify("改成用 docker")
        assert result is True
        assert ctrl.state == PlanState.planning
        assert ctrl.plan_text == ""

    def test_modify_with_empty_feedback(self):
        ctrl = PlanController()
        ctrl.enter_planning("sid1")
        ctrl.on_plan_complete("plan")

        result = ctrl.modify()
        assert result is True
        assert ctrl.state == PlanState.planning

    def test_modify_when_not_awaiting_returns_false(self):
        ctrl = PlanController()
        assert ctrl.modify("change") is False


class TestPlanDecisionCancel:

    def test_cancel_from_planning(self):
        ctrl = PlanController()
        ctrl.enter_planning("sid1")
        result = ctrl.cancel()
        assert result is True
        assert ctrl.state == PlanState.cancelled

    def test_cancel_from_awaiting(self):
        ctrl = PlanController()
        ctrl.enter_planning("sid1")
        ctrl.on_plan_complete("plan")
        result = ctrl.cancel()
        assert result is True
        assert ctrl.state == PlanState.cancelled

    def test_cancel_from_executing(self):
        ctrl = PlanController()
        ctrl.enter_planning("sid1")
        ctrl.on_plan_complete("plan")
        ctrl.approve()
        result = ctrl.cancel()
        assert result is True
        assert ctrl.state == PlanState.cancelled
        assert ctrl.is_write_allowed is False

    def test_cancel_after_reset_allows_new_plan(self):
        ctrl = PlanController()
        ctrl.enter_planning("sid1")
        ctrl.cancel()
        ctrl.reset()
        ctrl.enter_planning("sid2")
        ctrl.on_plan_complete("new plan")
        assert ctrl.state == PlanState.awaiting_approval


class TestPlanDecisionUnknown:

    def test_plan_ctrl_rejects_unknown_decision(self):
        ctrl = PlanController()
        pass
        pass
        assert ctrl.approve() is False
        assert ctrl.modify() is False
        assert ctrl.cancel() is False


pass
pass
pass
class TestPlanDecisionJsonFormat:

    def test_approve_json(self):
        msg = json.dumps({"type": "plan_decision", "decision": "approve"})
        parsed = json.loads(msg)
        assert parsed["type"] == "plan_decision"
        assert parsed["decision"] == "approve"

    def test_modify_json_with_feedback(self):
        msg = json.dumps({
            "type": "plan_decision",
            "decision": "modify",
            "feedback": "第二步换成 docker",
        })
        parsed = json.loads(msg)
        assert parsed["decision"] == "modify"
        assert parsed["feedback"] == "第二步换成 docker"

    def test_modify_json_without_feedback(self):
        msg = json.dumps({"type": "plan_decision", "decision": "modify"})
        parsed = json.loads(msg)
        assert parsed["decision"] == "modify"
        assert parsed.get("feedback") is None

    def test_cancel_json(self):
        msg = json.dumps({"type": "plan_decision", "decision": "cancel"})
        parsed = json.loads(msg)
        assert parsed["type"] == "plan_decision"
        assert parsed["decision"] == "cancel"


pass
pass
pass
class TestChatWsPlanRouting:

    def _route_plan_decision(self, req: dict, plan_ctrl: PlanController,
                             running: bool = False):
        decision = req.get("decision", "")
        events: list[dict] = []

        if decision == "approve":
            if plan_ctrl.approve():
                events.append({"type": "plan_approved", "text": "计划已确认"})
                should_continue = True
            else:
                events.append({"type": "notice", "text": "无待确认计划"})
                should_continue = False

        elif decision == "modify":
            feedback = req.get("feedback", "")
            plan_ctrl.modify(feedback)
            events.append({"type": "plan_modify", "text": "重新生成"})
            should_continue = True

        elif decision == "cancel":
            plan_ctrl.cancel()
            events.append({"type": "plan_cancelled", "text": "已取消"})
            pass
            if not running:
                events.append({"type": "done"})
            should_continue = False

        else:
            events.append({"type": "notice", "text": f"未知决策：{decision}"})
            should_continue = False

        return events, should_continue

    def test_approve_emits_plan_approved(self):
        ctrl = PlanController()
        ctrl.enter_planning("s1")
        ctrl.on_plan_complete("plan")

        events, cont = self._route_plan_decision(
            {"type": "plan_decision", "decision": "approve"}, ctrl
        )
        assert events[0]["type"] == "plan_approved"
        assert cont is True
        assert ctrl.state == PlanState.executing

    def test_approve_no_pending_emits_notice(self):
        ctrl = PlanController()
        events, cont = self._route_plan_decision(
            {"type": "plan_decision", "decision": "approve"}, ctrl
        )
        assert events[0]["type"] == "notice"
        assert cont is False

    def test_modify_emits_plan_modify(self):
        ctrl = PlanController()
        ctrl.enter_planning("s1")
        ctrl.on_plan_complete("plan")

        events, cont = self._route_plan_decision(
            {"type": "plan_decision", "decision": "modify", "feedback": "调整步骤2"}, ctrl
        )
        assert events[0]["type"] == "plan_modify"
        assert cont is True
        assert ctrl.state == PlanState.planning

    def test_cancel_emits_plan_cancelled_and_done(self):
        ctrl = PlanController()
        ctrl.enter_planning("s1")
        ctrl.on_plan_complete("plan")

        events, cont = self._route_plan_decision(
            {"type": "plan_decision", "decision": "cancel"}, ctrl
        )
        assert events[0]["type"] == "plan_cancelled"
        assert events[1]["type"] == "done"
        assert cont is False
        assert ctrl.state == PlanState.cancelled

    def test_cancel_while_running_does_not_end_turn(self):
        ctrl = PlanController()
        ctrl.enter_planning("s1")
        ctrl.on_plan_complete("plan")

        events, _cont = self._route_plan_decision(
            {"type": "plan_decision", "decision": "cancel"}, ctrl, running=True
        )
        assert [e["type"] for e in events] == ["plan_cancelled"]
        assert ctrl.state == PlanState.cancelled

    def test_unknown_decision_emits_notice(self):
        ctrl = PlanController()
        events, cont = self._route_plan_decision(
            {"type": "plan_decision", "decision": "unknown"}, ctrl
        )
        assert events[0]["type"] == "notice"
        assert "未知" in events[0]["text"]
        assert cont is False


pass
pass
pass
class TestFullPlanInteractionFlow:

    def test_full_lifecycle_approve(self):
        ctrl = PlanController()

        pass
        ctrl.enter_planning("session-123")
        assert ctrl.state == PlanState.planning

        pass
        ctrl.on_plan_complete("## 实施计划\n| 步骤 | ... |")
        assert ctrl.state == PlanState.awaiting_approval

        pass
        ctrl.approve()
        assert ctrl.state == PlanState.executing
        assert ctrl.is_write_allowed is True

    def test_full_lifecycle_modify_then_approve(self):
        ctrl = PlanController()

        ctrl.enter_planning("session-456")
        ctrl.on_plan_complete("plan v1")

        pass
        ctrl.modify("第二步改用蓝图")
        assert ctrl.state == PlanState.planning

        pass
        ctrl.on_plan_complete("plan v2")
        assert ctrl.state == PlanState.awaiting_approval

        pass
        ctrl.approve()
        assert ctrl.state == PlanState.executing

    def test_full_lifecycle_cancel(self):
        ctrl = PlanController()

        ctrl.enter_planning("session-789")
        ctrl.on_plan_complete("plan")

        pass
        ctrl.cancel()
        assert ctrl.state == PlanState.cancelled

        pass
        ctrl.reset()
        ctrl.enter_planning("session-999")
        assert ctrl.state == PlanState.planning

    def test_multiple_modify_cycles(self):
        ctrl = PlanController()
        ctrl.enter_planning("s1")

        for i in range(3):
            ctrl.on_plan_complete(f"plan v{i + 1}")
            assert ctrl.state == PlanState.awaiting_approval
            ctrl.modify(f"修改第{i + 1}次")
            assert ctrl.state == PlanState.planning

        ctrl.on_plan_complete("final plan")
        ctrl.approve()
        assert ctrl.state == PlanState.executing
