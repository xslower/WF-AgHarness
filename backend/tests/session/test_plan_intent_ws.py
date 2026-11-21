from __future__ import annotations

import time

from app.agent.plan import PlanState


def _wait_until(fn, timeout: float = 3.0, step: float = 0.05):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = fn()
        if last:
            return last
        time.sleep(step)
    return last


def _c(client):
    return client.app.state.container


def _new_session(client, title: str = "新任务") -> str:
    r = client.post("/api/sessions", params={"title": title})
    assert r.status_code == 200
    return r.json()["id"]


def _pending_plan(client, sid: str, text: str = "## 📋 实施计划\n1. 改 A") -> None:
    ctl = _c(client).runner.plan_for(sid)
    ctl.enter_planning(sid)
    ctl.on_plan_complete(text)


def _settle(ws, tries: int = 8) -> list[dict]:
    got: list[dict] = []
    for _ in range(tries):
        ws.send_json({"type": "stop"})
        while True:
            ev = ws.receive_json()
            got.append(ev)
            if ev.get("type") == "notice":
                if ev.get("text") == "当前没有正在进行的回复":
                    return got
                break
    raise AssertionError(f"会话未回到空闲，实收 {got}")


def _types(events: list[dict]) -> list[str]:
    return [e.get("type") for e in events]


def test_natural_language_approve_runs_the_plan(client):
    c = _c(client)
    sid = _new_session(client, title="自然语言确认")
    _pending_plan(client, sid)

    ran: list[str] = []

    async def fake_run(messages, cwd, emit, **kw):
        ran.append(kw.get("plan_mode", ""))
        await emit({"type": "text", "text": "开始执行"})
        yield {"role": "assistant", "content": "开始执行"}

    c.runner.run = fake_run

    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "chat", "content": "确认"})
        time.sleep(0.2)
        got = _settle(ws)

    assert c.runner.plan_for(sid).state is PlanState.executing
    assert ran == ["executing"], "确认后这一轮必须放行写操作（plan_mode=executing）"
    pass
    def _user_texts():
        return [m.get("content") for m in c.sessions.get(sid)["messages"]
                if m.get("role") == "user"]
    texts = _wait_until(lambda: _user_texts() if _user_texts() else None)
    assert "确认" not in texts
    assert any("用户已确认实施计划" in str(t) for t in texts)
    assert "text" in _types(got)


def test_natural_language_approve_emits_plan_approved(client):
    c = _c(client)
    sid = _new_session(client, title="自然语言确认-事件")
    _pending_plan(client, sid)

    async def fake_run(messages, cwd, emit, **kw):
        await emit({"type": "text", "text": "开始执行"})
        yield {"role": "assistant", "content": "开始执行"}

    c.runner.run = fake_run

    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "chat", "content": "确认"})
        time.sleep(0.2)
        got = _settle(ws)

    assert "plan_approved" in _types(got), \
        "打字确认与按钮确认都得让前端看见 plan_approved"


def test_natural_language_cancel_emits_plan_cancelled(client):
    c = _c(client)
    sid = _new_session(client, title="自然语言取消")
    _pending_plan(client, sid)

    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "chat", "content": "算了"})
        got = []
        for _ in range(10):
            ev = ws.receive_json()
            got.append(ev)
            if ev.get("type") == "done":
                break

    assert "plan_cancelled" in _types(got)
    assert c.runner.plan_for(sid).state is PlanState.cancelled


def test_natural_language_modify_rewrites_plan(client):
    c = _c(client)
    sid = _new_session(client, title="自然语言改计划")
    _pending_plan(client, sid)

    seen: list[str] = []

    async def fake_run(messages, cwd, emit, **kw):
        seen.append(str(messages[-1].get("content") or ""))
        await emit({"type": "text", "text": "新计划"})
        yield {"role": "assistant", "content": "新计划"}

    c.runner.run = fake_run
    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "chat", "content": "改成先备份再覆盖"})
        time.sleep(0.2)
        _settle(ws)

    assert c.runner.plan_for(sid).state is PlanState.planning
    assert _wait_until(lambda: [t for t in seen if "计划修改意见" in t]), \
        "修改意见必须转成续跑消息"


def test_natural_language_not_used_when_no_pending_plan(client):
    c = _c(client)
    sid = _new_session(client, title="无计划")
    seen: list[str] = []

    async def fake_run(messages, cwd, emit, **kw):
        seen.append(str(messages[-1].get("content") or ""))
        await emit({"type": "text", "text": "ok"})
        yield {"role": "assistant", "content": "ok"}

    c.runner.run = fake_run
    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "chat", "content": "确认"})
        time.sleep(0.2)
        _settle(ws)

    pass
    pass
    assert c.runner.plan_for(sid).state is not PlanState.executing
    assert _wait_until(lambda: [t for t in seen if "确认" in t]), \
        "普通消息必须原样送到模型"


def test_natural_language_skipped_when_message_has_attachments(client):
    c = _c(client)
    sid = _new_session(client, title="带附件确认")
    _pending_plan(client, sid)
    seen: list[str] = []

    async def fake_run(messages, cwd, emit, **kw):
        seen.append(str(messages[-1].get("content") or ""))
        await emit({"type": "text", "text": "ok"})
        yield {"role": "assistant", "content": "ok"}

    c.runner.run = fake_run
    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "chat", "content": "确认",
                      "attachments": [{"name": "a.txt", "text": "内容"}]})
        time.sleep(0.2)
        _settle(ws)

    assert c.runner.plan_for(sid).state is not PlanState.executing
    assert _wait_until(lambda: [t for t in seen if "a.txt" in t]), \
        "带附件的消息必须走正常对话"
