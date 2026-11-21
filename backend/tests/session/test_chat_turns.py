from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.agent.plan import decide_plan
from app.agent.plan import PlanController, PlanState
from app.chat.turns import apply_queue_action, queue_payload


def _item(qid: str, text: str = "x", interjecting: bool = False) -> dict:
    return {"id": qid, "req": {"content": text}, "interjecting": interjecting}


pass

def test_remove_drops_item():
    items = [_item("a"), _item("b")]
    new, notice = apply_queue_action(items, "remove", "a")
    assert [i["id"] for i in new] == ["b"]
    assert notice is None


def test_remove_missing_reports():
    items = [_item("a")]
    new, notice = apply_queue_action(items, "remove", "zzz")
    assert new is items
    assert "已不在队列" in notice


def test_remove_refuses_interjecting():
    items = [_item("a", interjecting=True)]
    new, notice = apply_queue_action(items, "remove", "a")
    assert new is items
    assert "不能删除" in notice


def test_interject_moves_to_front():
    items = [_item("a"), _item("b"), _item("c")]
    new, notice = apply_queue_action(items, "interject", "c", running=True)
    assert [i["id"] for i in new] == ["c", "a", "b"]
    assert new[0]["interjecting"] is True
    assert "已插队" in notice


def test_interject_when_idle_has_no_notice():
    items = [_item("a"), _item("b")]
    new, notice = apply_queue_action(items, "interject", "b", running=False)
    assert [i["id"] for i in new] == ["b", "a"]
    assert notice is None


def test_interject_twice_is_noop():
    items = [_item("a", interjecting=True)]
    new, notice = apply_queue_action(items, "interject", "a", running=True)
    assert new is items
    assert notice is None


def test_cancel_interject_clears_flag():
    items = [_item("a", interjecting=True)]
    new, notice = apply_queue_action(items, "cancel_interject", "a")
    assert new[0]["interjecting"] is False
    assert notice is None
    assert items[0]["interjecting"] is True, "原列表不能被改"


def test_unknown_action_reports():
    items = [_item("a")]
    new, notice = apply_queue_action(items, "explode", "a")
    assert new is items
    assert "未知的队列操作" in notice


def test_queue_payload_summarises():
    items = [{"id": "q1", "req": {"content": "全文",
                                  "images": ["a", "b"],
                                  "attachments": [{"name": "报告.pdf", "text": "很长的正文"}],
                                  "workflow": "wf"},
              "interjecting": True}]
    payload = queue_payload(items)
    assert payload == [{"id": "q1", "content": "全文", "images": 2,
                        "attachments": ["报告.pdf"],
                        "workflow": "wf", "interjecting": True}]


pass

def _plan(state: PlanState = PlanState.awaiting_approval) -> PlanController:
    pc = PlanController()
    pc._state = state
    return pc


def test_approve_when_pending_resumes():
    pc = _plan()
    etype, text, note = decide_plan(pc, "approve")
    assert etype == "plan_approved"
    assert note == "", "空串=按默认文案续跑"
    assert pc.state == PlanState.executing


def test_approve_without_plan_just_notice():
    pc = _plan(PlanState.idle)
    etype, text, note = decide_plan(pc, "approve")
    assert etype == "notice"
    assert "无待确认" in text
    assert note is None


def test_modify_returns_note_for_replan():
    pc = _plan()
    etype, text, note = decide_plan(pc, "modify", "第 2 步改成先备份")
    assert etype == "plan_modify"
    assert "第 2 步改成先备份" in text
    assert note and "第 2 步改成先备份" in note
    assert "只调整这些点" in note, "要让模型在原计划上改，而不是重新调研"
    assert pc.state == PlanState.planning


def test_modify_without_feedback_still_replans():
    pc = _plan()
    etype, _text, note = decide_plan(pc, "modify", "")
    assert etype == "plan_modify"
    assert note


def test_cancel_returns_cancelled():
    pc = _plan()
    etype, text, note = decide_plan(pc, "cancel")
    assert etype == "plan_cancelled"
    assert note is None
    pass
    assert pc.state == PlanState.cancelled


def test_unknown_decision_is_reported():
    pc = _plan()
    etype, text, note = decide_plan(pc, "approve-maybe")
    assert etype == "notice"
    assert "未知" in text
    assert note is None


pass
def _suggest(gateway_reply: str) -> list[str]:
    from app.chat.turns import quick_suggest

    class Gw:
        async def call_utility(self, *a, **kw):
            return gateway_reply

    c = SimpleNamespace(gateway=Gw())
    msgs = [{"role": "user", "content": "帮我改一下"},
            {"role": "assistant", "content": "改好了"}]
    return asyncio.run(quick_suggest(c, "s1", msgs))


def test_quick_suggest_repairs_broken_json_in_fence():
    assert _suggest('```json\n["继续", "跑测试",]\n```') == ["继续", "跑测试"]


def test_quick_suggest_repairs_prose_wrapped_json():
    assert _suggest('建议如下 ["先备份", "再回滚",] 结束') == ["先备份", "再回滚"]


def test_quick_suggest_plain_text_still_empty():
    assert _suggest("想不出来") == []
