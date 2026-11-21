from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

import pytest
from fastapi import WebSocketDisconnect

from app.chat.turns import fill_inputs
from app.provider.models import ModelInfo, ModelQueues, Provider
from app.workflow import RunRecord

pass


def _c(client):
    return client.app.state.container


def _new_session(client, title: str = "新任务", project: str = "") -> str:
    r = client.post("/api/sessions", params={"title": title, "project": project})
    assert r.status_code == 200
    return r.json()["id"]


def _fake_run(events=(), msgs=(), exc: Exception | None = None,
              delay: float = 0.0, seen: dict | None = None):
    events = list(events)
    msgs = list(msgs)

    async def _run(messages, cwd, emit, **kw):
        if seen is not None:
            seen["messages"] = [dict(m) for m in messages]
            seen["cwd"] = cwd
            seen["kwargs"] = kw
        for ev in events:
            await emit(ev)
        if delay:
            await asyncio.sleep(delay)
        if exc is not None:
            raise exc
        for m in msgs:
            yield m

    return _run


def _collect(ws, want: str, limit: int = 40, **match) -> list[dict]:
    got: list[dict] = []
    for _ in range(limit):
        ev = ws.receive_json()
        got.append(ev)
        if ev.get("type") == want and all(ev.get(k) == v for k, v in match.items()):
            return got
    raise AssertionError(f"未收到 {want}{match}，实收: {got}")


def _types(events: list[dict]) -> list[str]:
    return [e.get("type") for e in events]


def _collect_text(ws, needle: str, limit: int = 30) -> list[dict]:
    got: list[dict] = []
    for _ in range(limit):
        ev = ws.receive_json()
        got.append(ev)
        if ev.get("type") == "notice" and needle in (ev.get("text") or ""):
            return got
    raise AssertionError(f"未收到包含 {needle!r} 的 notice，实收: {got}")


def _settle(ws, tries: int = 20) -> list[dict]:
    collected: list[dict] = []
    for _ in range(tries):
        ws.send_json({"type": "stop"})
        for _ in range(20):
            try:
                ev = ws.receive_json()
            except Exception:
                return collected
            collected.append(ev)
            if ev.get("type") == "notice":
                if ev.get("text") == "当前没有正在进行的回复":
                    return collected
                break
        pass
        time.sleep(0.05)
    pass
    return collected


def _turn(ws, payload: dict, delay: float = 0.15) -> list[dict]:
    ws.send_json(payload)
    time.sleep(delay)
    return _settle(ws)


pass


def test_fill_inputs_defaults_to_task():
    assert fill_inputs(None, "hi") == {"task": "hi"}
    assert fill_inputs([], "hi") == {"task": "hi"}
    assert fill_inputs([{"desc": "无 name"}], "hi") == {"task": "hi"}


def test_fill_inputs_follows_declaration_order():
    decl = [{"name": "input"}, {"name": "context"}, {"name": "extra"}]
    assert fill_inputs(decl, "正文") == {"input": "正文", "context": "", "extra": ""}




def test_declaration_of_prefers_resolve_workflow():
    from app.chat.turns import declaration_of

    class _Both:
        def get(self, name):
            return None

        def resolve_workflow(self, name):
            return {"name": name, "inputs": [{"name": "q"}],
                    "defaultHuman": "auto-approve"}

    got = declaration_of(_Both(), "全局片段")
    assert got["defaultHuman"] == "auto-approve"
    assert got["inputs"] == [{"name": "q"}]


def test_declaration_of_falls_back_to_get_and_tolerates_plain_objects():
    from app.chat.turns import declaration_of

    class _OnlyGet:
        def get(self, name):
            return {"name": name}

    class _Empty:
        pass

    assert declaration_of(_OnlyGet(), "x") == {"name": "x"}
    assert declaration_of(_Empty(), "x") is None
    assert declaration_of(None, "x") is None
def test_fill_inputs_skips_non_dict():
    decl = [None, "x", {"name": "q"}, {"name": None}]
    assert fill_inputs(decl, "v") == {"q": "v"}


pass


def test_ws_unknown_session_closes_4404(client):
    with pytest.raises(WebSocketDisconnect) as ei:
        with client.websocket_connect("/ws/nope"):
            pass
    assert ei.value.code == 4404


pass


def test_ws_chat_streams_and_persists(client):
    c = _c(client)
    sid = _new_session(client)
    c.runner.run = _fake_run(
        events=[{"type": "text", "text": "hi "}, {"type": "done", "model": "m"}],
        msgs=[{"role": "assistant", "content": "hi there", "model": "m"}])

    with client.websocket_connect(f"/ws/{sid}") as ws:
        got = _turn(ws, {"type": "chat", "content": "你好"})
    assert "text" in _types(got)

    s = c.sessions.get(sid)
    assert s["title"] == "你好"
    assert [m["role"] for m in s["messages"]] == ["user", "assistant"]
    assert s["messages"][1]["content"] == "hi there"


def test_ws_title_keeps_existing_and_usage_saved(client):
    c = _c(client)
    sid = _new_session(client, title="已有标题")
    c.runner.run = _fake_run(
        msgs=[{"role": "assistant", "content": "ok",
               "usage": {"prompt_tokens": 3, "completion_tokens": 1}}])
    with client.websocket_connect(f"/ws/{sid}") as ws:
        _turn(ws, {"type": "chat", "content": "x"})
    s = c.sessions.get(sid)
    assert s["title"] == "已有标题"
    assert s["messages"][-1]["usage"]["prompt_tokens"] == 3


def test_ws_title_multiline_and_truncated(client):
    c = _c(client)
    sid = _new_session(client)
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "ok"}])
    long_first = "第" * 50
    with client.websocket_connect(f"/ws/{sid}") as ws:
        _turn(ws, {"type": "chat", "content": f"{long_first}\n第二行"})
    assert c.sessions.get(sid)["title"] == "第" * 30


def test_ws_runner_exception_emits_error(client):
    c = _c(client)
    sid = _new_session(client)
    c.runner.run = _fake_run(exc=RuntimeError("boom"))
    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "chat", "content": "hi"})
        got = _collect(ws, "error") + _settle(ws)
    err = [e for e in got if e["type"] == "error"][0]
    assert "boom" in err["text"]
    assert len(c.sessions.get(sid)["messages"]) == 1


def test_ws_session_refresh_from_store(client):
    c = _c(client)
    sid = _new_session(client)
    seen: dict = {}
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "ok"}], seen=seen)

    with client.websocket_connect(f"/ws/{sid}") as ws:
        pass
        s = c.sessions.get(sid)
        s["messages"] = [{"role": "user", "content": "外部消息"}]
        c.sessions.save(s)
        _turn(ws, {"type": "chat", "content": "第二条"})

    msgs = seen["messages"]
    assert msgs[0]["content"] == "外部消息"
    assert str(msgs[1]["content"]).endswith("第二条")


def test_ws_refresh_failure_is_tolerated(client):
    c = _c(client)
    sid = _new_session(client)
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "ok"}])
    real_get = c.sessions.get
    calls = {"n": 0}

    def _get(s):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("db locked")
        return real_get(s)

    c.sessions.get = _get
    with client.websocket_connect(f"/ws/{sid}") as ws:
        got = _turn(ws, {"type": "chat", "content": "hi"})
    assert "error" not in _types(got)


def test_ws_project_memory_failure_is_tolerated(client, tmp_path):
    c = _c(client)
    proj = tmp_path / "proj_mem_test"
    proj.mkdir()
    sid = _new_session(client, project=str(proj))
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "ok"}])
    c.memory.context_for = lambda p: (_ for _ in ()).throw(RuntimeError("memory down"))
    with client.websocket_connect(f"/ws/{sid}") as ws:
        got = _turn(ws, {"type": "chat", "content": "hi"})
    assert "error" not in _types(got)


pass


def test_ws_images_and_attachments(client):
    c = _c(client)
    pass
    pass
    pass
    _set_providers(c, [ModelInfo(id="m1", kind="lm", supportsImages=True)],
                   queues=ModelQueues(parent=["p1/m1"], child=[]))
    sid = _new_session(client)
    seen: dict = {}
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "ok"}], seen=seen)
    with client.websocket_connect(f"/ws/{sid}") as ws:
        _turn(ws, {
            "type": "chat", "content": "看图", "model": "p1/m1",
            "images": ["data:image/png;base64,AAA", "data:image/png;base64,BBB"],
            "attachments": [{"name": "a.md", "text": "# 文档"}],
        })
    last = seen["messages"][-1]
    assert isinstance(last["content"], list)
    assert last["content"][0]["type"] == "text"
    assert "[附件 a.md]" in last["content"][0]["text"]
    assert len([p for p in last["content"] if p["type"] == "image_url"]) == 2


def test_ws_images_described_when_model_cannot_see(client):
    c = _c(client)
    _set_providers(c, [ModelInfo(id="blind", kind="lm"),
                       ModelInfo(id="see", kind="lm", supportsImages=True)],
                   queues=ModelQueues(parent=["p1/blind"], child=[]))
    seen: dict = {}
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "ok"}], seen=seen)

    async def _describe(src, prompt="", spec=""):
        return {"ok": True, "text": "一张表单截图", "model": spec}

    c.gateway.describe_image = _describe
    c.gateway.media.describe_image = _describe
    sid = _new_session(client)
    with client.websocket_connect(f"/ws/{sid}") as ws:
        _turn(ws, {"type": "chat", "content": "看图", "model": "p1/blind",
                   "images": ["data:image/png;base64,AAA"]})
    last = seen["messages"][-1]
    assert isinstance(last["content"], list)
    assert not [p for p in last["content"] if p["type"] == "image_url"]
    assert "一张表单截图" in str(last["content"])


def test_ws_attachment_limit(client):
    c = _c(client)
    sid = _new_session(client)
    seen: dict = {}
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "ok"}], seen=seen)
    atts = [{"name": f"f{i}.txt", "text": "x"} for i in range(12)]
    with client.websocket_connect(f"/ws/{sid}") as ws:
        _turn(ws, {"type": "chat", "content": "c", "attachments": atts})
    assert seen["messages"][-1]["content"].count("[附件 ") == 8


def test_ws_cwd_priority_explicit(client):
    c = _c(client)
    sid = _new_session(client)
    seen: dict = {}
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "ok"}], seen=seen)
    with client.websocket_connect(f"/ws/{sid}") as ws:
        _turn(ws, {"type": "chat", "content": "c", "cwd": "/tmp/explicit"})
    assert seen["cwd"] == "/tmp/explicit"


def test_ws_cwd_falls_back_to_workspace_root(client):
    c = _c(client)
    c.store.config.settings.workspaceRoot = "/tmp/wsroot"
    sid = _new_session(client)
    seen: dict = {}
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "ok"}], seen=seen)
    with client.websocket_connect(f"/ws/{sid}") as ws:
        _turn(ws, {"type": "chat", "content": "c"})
    assert seen["cwd"] == "/tmp/wsroot"


pass


def test_ws_bad_json_is_ignored(client):
    sid = _new_session(client)
    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_text("not json")
        got = _settle(ws)
    assert [e for e in got if e["type"] != "notice"] == []


def test_ws_blank_content_is_ignored(client):
    sid = _new_session(client)
    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "chat", "content": "   "})
        got = _settle(ws)
    assert [e for e in got if e["type"] != "notice"] == []


def test_ws_non_dict_frame_is_ignored(client):
    sid = _new_session(client)
    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_text("[1, 2, 3]")
        ws.send_text("42")
        ws.send_text('"a string"')
        pass
        got = _settle(ws)
    assert any("当前没有正在进行" in (e.get("text") or "") for e in got)


def test_ws_chat_with_null_content_keeps_connection(client):
    sid = _new_session(client)
    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "chat", "content": None})
        ws.send_json({"type": "chat", "content": 123})
        ws.send_json({"type": "chat"})
        got = _settle(ws)
    pass
    assert [e for e in got if e["type"] not in ("notice",)] == []


def test_ws_plan_decision_lives_on_session_turn(client):
    from app.api.routers.chat_session import SessionTurn
    from app.api.routers import chat_ws as mod

    assert hasattr(SessionTurn, "handle_plan_decision")
    assert not hasattr(mod, "_on_plan_decision")


def test_ws_stop_when_idle(client):
    sid = _new_session(client)
    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "stop"})
        got = _collect(ws, "notice")
    assert got[0]["text"] == "当前没有正在进行的回复"


def _fake_tool_runner(gap_delay: float = 0.25, rounds: int = 1):
    async def _run(messages, cwd, emit, **kw):
        await emit({"type": "text", "text": "正在调工具"})
        for _ in range(rounds):
            await asyncio.sleep(gap_delay)
            check = kw.get("interject_check")
            if callable(check) and check():
                note = "⏸ 收到插队消息，本轮已中止。"
                await emit({"type": "notice", "text": note})
                await emit({"type": "done", "interrupted": True})
                yield {"role": "assistant", "content": note, "interrupted": True}
                return
        await emit({"type": "done"})
        yield {"role": "assistant", "content": "正常完成"}
    return _run


def test_ws_queue_message_while_running(client):
    c = _c(client)
    sid = _new_session(client)
    c.runner.run = _fake_run(
        events=[{"type": "text", "text": "第一轮"}],
        msgs=[{"role": "assistant", "content": "第一轮"}], delay=0.4)

    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "chat", "content": "一"})
        _collect(ws, "text")
        ws.send_json({"type": "chat", "content": "二"})
        got = _collect(ws, "queue")
        q = [e for e in got if e["type"] == "queue"][-1]
        assert q["max"] == 3 and len(q["items"]) == 1
        assert q["items"][0]["content"] == "二"
        assert q["items"][0]["interjecting"] is False
        pass
        rest = _collect(ws, "turn_start", from_queue=True)
        assert rest[-1]["content"] == "二"


def test_ws_queue_is_bounded_to_three(client):
    c = _c(client)
    sid = _new_session(client)
    c.runner.run = _fake_run(
        events=[{"type": "text", "text": "跑着"}],
        msgs=[{"role": "assistant", "content": "跑着"}], delay=1.2)

    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "chat", "content": "0"})
        _collect(ws, "text")
        for i in (1, 2, 3):
            ws.send_json({"type": "chat", "content": str(i)})
            got = _collect(ws, "queue")
            assert len([e for e in got if e["type"] == "queue"][-1]["items"]) == i
        ws.send_json({"type": "chat", "content": "4"})
        got = _collect(ws, "queue_full")
        assert got[-1]["max"] == 3
        assert "队列已满" in got[-1]["text"]


def test_ws_queue_remove(client):
    c = _c(client)
    sid = _new_session(client)
    c.runner.run = _fake_run(
        events=[{"type": "text", "text": "跑着"}],
        msgs=[{"role": "assistant", "content": "跑着"}], delay=0.8)

    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "chat", "content": "0"})
        _collect(ws, "text")
        ws.send_json({"type": "chat", "content": "一"})
        q = [e for e in _collect(ws, "queue") if e["type"] == "queue"][-1]
        qid = q["items"][0]["id"]
        ws.send_json({"type": "queue_action", "action": "remove", "id": qid})
        got = _collect(ws, "queue")
        assert [e for e in got if e["type"] == "queue"][-1]["items"] == []


def test_ws_queue_remove_unknown_id(client):
    sid = _new_session(client)
    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "queue_action", "action": "remove", "id": "nope"})
        got = _collect(ws, "notice")
        assert "已不在队列中" in got[-1]["text"]


def test_ws_queue_unknown_action(client):
    sid = _new_session(client)
    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "queue_action", "action": "explode", "id": "x"})
        got = _collect(ws, "notice")
        assert "未知的队列操作" in got[-1]["text"]


def test_ws_interject_marks_and_prioritizes(client):
    c = _c(client)
    sid = _new_session(client)
    c.runner.run = _fake_tool_runner(gap_delay=0.4)

    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "chat", "content": "0"})
        _collect(ws, "text")
        ws.send_json({"type": "chat", "content": "一"})
        q1 = [e for e in _collect(ws, "queue") if e["type"] == "queue"][-1]
        ws.send_json({"type": "chat", "content": "二"})
        q2 = [e for e in _collect(ws, "queue") if e["type"] == "queue"][-1]
        assert [i["content"] for i in q2["items"]] == ["一", "二"]
        last_id = q2["items"][1]["id"]

        ws.send_json({"type": "queue_action", "action": "interject", "id": last_id})
        q3 = [e for e in _collect(ws, "queue") if e["type"] == "queue"][-1]
        assert [i["content"] for i in q3["items"]] == ["二", "一"]
        assert q3["items"][0]["interjecting"] is True
        assert q1["items"][0]["id"] != last_id

        pass
        started = _collect(ws, "turn_start", from_queue=True)
        assert started[-1]["content"] == "二"
        after = [e for e in started if e["type"] == "queue"]
        assert after and [i["content"] for i in after[-1]["items"]] == ["一"]


def test_ws_interject_cannot_be_removed(client):
    c = _c(client)
    sid = _new_session(client)
    c.runner.run = _fake_tool_runner(gap_delay=0.5)

    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "chat", "content": "0"})
        _collect(ws, "text")
        ws.send_json({"type": "chat", "content": "一"})
        q = [e for e in _collect(ws, "queue") if e["type"] == "queue"][-1]
        qid = q["items"][0]["id"]
        ws.send_json({"type": "queue_action", "action": "interject", "id": qid})
        _collect(ws, "queue")
        ws.send_json({"type": "queue_action", "action": "remove", "id": qid})
        got = _collect_text(ws, "插队中的消息不能删除")
        assert "插队中的消息不能删除" in got[-1]["text"]


def test_ws_interject_cancel(client):
    c = _c(client)
    sid = _new_session(client)
    c.runner.run = _fake_tool_runner(gap_delay=0.6, rounds=2)

    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "chat", "content": "0"})
        _collect(ws, "text")
        ws.send_json({"type": "chat", "content": "一"})
        q = [e for e in _collect(ws, "queue") if e["type"] == "queue"][-1]
        qid = q["items"][0]["id"]
        ws.send_json({"type": "queue_action", "action": "interject", "id": qid})
        _collect(ws, "queue")
        ws.send_json({"type": "queue_action", "action": "cancel_interject", "id": qid})
        got = _collect(ws, "queue")
        item = [e for e in got if e["type"] == "queue"][-1]["items"][0]
        assert item["interjecting"] is False


def test_ws_turn_start_marks_first_message(client):
    c = _c(client)
    sid = _new_session(client)
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "ok"}])
    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "chat", "content": "直接发"})
        got = _collect(ws, "turn_start")
        assert got[0]["from_queue"] is False
        assert got[0]["content"] == "直接发"


def test_ws_stop_keeps_queue(client):
    c = _c(client)
    sid = _new_session(client)
    c.runner.run = _fake_run(
        events=[{"type": "text", "text": "跑着"}],
        msgs=[{"role": "assistant", "content": "跑着"}], delay=0.6)

    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "chat", "content": "一"})
        _collect(ws, "text")
        ws.send_json({"type": "chat", "content": "二"})
        _collect(ws, "queue")
        ws.send_json({"type": "stop"})
        got = _collect_text(ws, "已中止当前回复")
        texts = [e.get("text", "") for e in got if e["type"] == "notice"]
        assert any("队列中的 1 条" in t for t in texts)
        pass
        started = _collect(ws, "turn_start", from_queue=True)
        assert started[-1]["content"] == "二"


def test_ws_abort_does_not_shrink_other_session_queue(client):
    c = _c(client)
    sid1 = _new_session(client)
    sid2 = _new_session(client)
    rt = c.session_rt()
    c.runner.run = _fake_run(
        events=[{"type": "text", "text": "跑着"}],
        msgs=[{"role": "assistant", "content": "跑着"}], delay=0.8)

    with client.websocket_connect(f"/ws/{sid1}") as ws1:
        ws1.send_json({"type": "chat", "content": "一"})
        _collect(ws1, "text")
        ws1.send_json({"type": "chat", "content": "二"})
        _collect(ws1, "queue")
        assert rt.get(sid1).running is True
        assert rt.get(sid2).running is False
        ws1.send_json({"type": "stop"})
        _collect_text(ws1, "已中止当前回复")
        pass
        assert rt.get(sid1).abort_requested is True
        assert rt.get(sid2).abort_requested is False
        assert rt.get(sid2).queue == []


class _FakeEngine:

    def __init__(self, status="done", final="工作流输出", error="", raise_exc=None):
        self.calls: list = []
        self.status = status
        self.final = final
        self.error = error
        self.raise_exc = raise_exc

    async def execute_sync(self, name: str, inputs: dict):
        self.calls.append({"name": name, "inputs": inputs})
        if self.raise_exc:
            raise self.raise_exc
        from app.workflow import RunRecord
        rec = RunRecord("r1", name)
        rec.status = self.status
        rec.final = self.final
        rec.error = self.error
        return rec


pass


def test_ws_workflow_success(client):
    c = _c(client)
    eng = _FakeEngine(status="done", final="工作流输出")
    c.wf_engine = lambda project="": eng
    sid = _new_session(client)
    with client.websocket_connect(f"/ws/{sid}") as ws:
        got = _turn(ws, {"type": "chat", "content": "原文", "workflow": "wf1"})
    assert eng.calls[0]["name"] == "wf1"
    assert eng.calls[0]["inputs"] == {"task": "原文"}
    assert any(e.get("text") == "工作流输出" for e in got)


def test_ws_workflow_fills_declared_inputs(client):
    c = _c(client)
    eng = _FakeEngine(status="done", final="ok")
    eng.get = lambda name: {"name": name,
                            "inputs": [{"name": "input"}, {"name": "context"}]}
    c.wf_engine = lambda project="": eng
    sid = _new_session(client)
    with client.websocket_connect(f"/ws/{sid}") as ws:
        _turn(ws, {"type": "chat", "content": "正文", "workflow": "wf1"})
    assert eng.calls[0]["inputs"] == {"input": "正文", "context": ""}


def test_ws_workflow_failed(client):
    c = _c(client)
    c.wf_engine = lambda project="": _FakeEngine(status="failed", error="wf 失败")
    sid = _new_session(client)
    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "chat", "content": "x", "workflow": "wf1"})
        got = _collect(ws, "error")
    assert "wf 失败" in got[-1]["text"]


def test_ws_workflow_raise(client):
    c = _c(client)

    def _boom(project=""):
        raise LookupError("引擎不可用")

    c.wf_engine = _boom
    sid = _new_session(client)
    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "chat", "content": "x", "workflow": "wf1"})
        got = _collect(ws, "error")
    assert "工作流执行失败" in got[-1]["text"]


pass


def _set_providers(c, models, queues=None):
    c.store.config.providers = [Provider(id="p1", name="p1", baseUrl="https://x/v1",
                                        apiKey="k", models=models)]
    if queues is not None:
        c.store.config.queues = queues


def test_ws_audio_transcribed(client):
    c = _c(client)
    _set_providers(c, [ModelInfo(id="asr1", kind="asr")])
    seen: dict = {}
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "ok"}], seen=seen)

    async def _transcribe(raw, spec=""):
        assert raw == b"abc"
        pass
        assert spec == "p1/asr1"
        pass
        pass
        return {"ok": True, "text": "转写文本", "model": spec}

    c.gateway.transcribe_audio = _transcribe
    sid = _new_session(client)
    with client.websocket_connect(f"/ws/{sid}") as ws:
        _turn(ws, {"type": "chat", "content": "前面",
                   "audio": "data:audio/webm;base64,YWJj"})
    assert "转写文本" in seen["messages"][-1]["content"]


def test_ws_audio_without_asr_model(client):
    c = _c(client)
    _set_providers(c, [ModelInfo(id="m1", kind="lm")])
    seen: dict = {}
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "ok"}], seen=seen)
    sid = _new_session(client)
    with client.websocket_connect(f"/ws/{sid}") as ws:
        _turn(ws, {"type": "chat", "content": "听一下",
                   "audio": "data:audio/webm;base64,YWJj"})
    assert any("未配置 kind=asr" in str(m.get("content", "")) for m in seen["messages"])


def test_ws_audio_transcribe_error(client):
    c = _c(client)
    _set_providers(c, [ModelInfo(id="asr1", kind="asr")])
    seen: dict = {}
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "ok"}], seen=seen)

    async def _transcribe(raw, spec=""):
        raise RuntimeError("接口 500")

    c.gateway.transcribe_audio = _transcribe
    sid = _new_session(client)
    with client.websocket_connect(f"/ws/{sid}") as ws:
        _turn(ws, {"type": "chat", "content": "x",
                   "audio": "data:audio/webm;base64,YWJj"})
    assert any("语音转写失败" in str(m.get("content", "")) for m in seen["messages"])


def test_ws_audio_non_data_url_ignored(client):
    c = _c(client)
    seen: dict = {}
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "ok"}], seen=seen)
    sid = _new_session(client)
    with client.websocket_connect(f"/ws/{sid}") as ws:
        _turn(ws, {"type": "chat", "content": "x", "audio": "http://cdn/a.webm"})
    assert str(seen["messages"][-1]["content"]).endswith("x")


pass


def _make_context_overflow(c, sid, messages_before: int = 9):
    _set_providers(c, [ModelInfo(id="m1", contextLength=100, kind="lm")])
    s = c.sessions.get(sid)
    s["messages"] = [{"role": "user", "content": f"h{i}"} for i in range(messages_before)]
    c.sessions.save(s)


def test_ws_auto_compact(tmp_dirs, container, monkeypatch):
    c = container
    _set_providers(c, [ModelInfo(id="m1", contextLength=100, kind="lm")])
    sid = c.sessions.create("压缩测试", "")["id"]
    s = c.sessions.get(sid)
    s["messages"] = [{"role": "user", "content": f"h{i}"} for i in range(12)]
    c.sessions.save(s)
    s = c.sessions.get(sid)
    pass
    c.store.config.settings.compactStrategies = ["legacy"]
    c.store.config.settings.compactSummaryMode = "per_message"

    async def _summarize(folded, session_id=""):
        return {m["_seq"]: f"总结{m['_seq']}" for m in folded
                if m.get("role") in ("user", "assistant")}
    monkeypatch.setattr(c.compactor, "summarize_batch", _summarize)
    emitted: list[dict] = []

    async def _emit(ev):
        emitted.append(ev)

    from app.chat.compaction_policy import maybe_compact
    asyncio.run(maybe_compact(c, s, "p1/m1", _emit))
    assert any("正在整理上下文" in e.get("text", "") for e in emitted)

    pass
    from app.chat.tool_window import keep_from
    segs = c.sessions.get_compactions("", sid)
    after = c.sessions.get(sid)
    assert segs and segs[-1]["upto_seq"] == keep_from(after["messages"])
    pass
    assert len(after["messages"]) == 12
    pass
    flat = json.dumps(segs[0]["items"], ensure_ascii=False)
    assert "h0" in flat


def test_ws_no_compact_when_ratio_not_reached(client):
    c = _c(client)
    sid = _new_session(client)
    _make_context_overflow(c, sid)
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "ok",
                                    "usage": {"prompt_tokens": 10, "completion_tokens": 1}}])
    called = []

    async def _compact(msgs):
        called.append(1)
        return msgs

    c.compactor.compact = _compact
    with client.websocket_connect(f"/ws/{sid}") as ws:
        _turn(ws, {"type": "chat", "content": "一", "model": "p1/m1"})
        _turn(ws, {"type": "chat", "content": "二", "model": "p1/m1"})
    assert called == []


def test_ws_no_compact_when_history_short(client):
    c = _c(client)
    sid = _new_session(client)
    _set_providers(c, [ModelInfo(id="m1", contextLength=100, kind="lm")])
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "ok",
                                    "usage": {"prompt_tokens": 90, "completion_tokens": 1}}])
    called = []

    async def _compact(msgs):
        called.append(1)
        return msgs

    c.compactor.compact = _compact
    with client.websocket_connect(f"/ws/{sid}") as ws:
        _turn(ws, {"type": "chat", "content": "一", "model": "p1/m1"})
        _turn(ws, {"type": "chat", "content": "二", "model": "p1/m1"})
    assert called == []


def test_ws_no_compact_when_model_unknown(client):
    c = _c(client)
    sid = _new_session(client)
    _make_context_overflow(c, sid)
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "ok",
                                    "usage": {"prompt_tokens": 80, "completion_tokens": 1}}])
    called = []

    async def _compact(msgs):
        called.append(1)
        return msgs

    c.compactor.compact = _compact
    with client.websocket_connect(f"/ws/{sid}") as ws:
        _turn(ws, {"type": "chat", "content": "一", "model": "p1/m1"})
        _turn(ws, {"type": "chat", "content": "二", "model": "pX/unknown"})
    assert called == []


def test_ws_compact_falls_back_to_parent_queue(container, monkeypatch):
    c = container
    _set_providers(c, [ModelInfo(id="m1", contextLength=100, kind="lm")],
                   queues=ModelQueues(parent=["p1/m1"], child=[]))
    sid = c.sessions.create("队列回退", "")["id"]
    s = c.sessions.get(sid)
    s["messages"] = [
        {"role": "user" if i % 2 == 0 else "assistant",
         "content": f"h{i}"} for i in range(12)]
    c.sessions.save(s)
    s = c.sessions.get(sid)
    c.store.config.settings.compactStrategies = ["legacy"]
    c.store.config.settings.compactSummaryMode = "per_message"
    called = []

    async def _summarize(folded, session_id=""):
        called.append(1)
        return {m["_seq"]: f"总结{m['_seq']}" for m in folded}
    monkeypatch.setattr(c.compactor, "summarize_batch", _summarize)

    from app.chat.compaction_policy import maybe_compact

    async def _collect(ev):
        pass
    asyncio.run(maybe_compact(c, s, "", _collect))
    assert called


def test_ws_no_batch_no_compaction_notice(client):
    c = _c(client)
    sid = _new_session(client)
    _make_context_overflow(c, sid, messages_before=6)
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "ok",
                                    "usage": {"prompt_tokens": 80, "completion_tokens": 1}}])
    called = []

    async def _summarize(folded, session_id=""):
        called.append(1)
        return {}
    c.store.config.settings.compactStrategies = ["legacy"]
    c.store.config.settings.compactSummaryMode = "per_message"
    c.compactor.summarize_batch = _summarize
    with client.websocket_connect(f"/ws/{sid}") as ws:
        _turn(ws, {"type": "chat", "content": "一", "model": "p1/m1"})
        got = _turn(ws, {"type": "chat", "content": "二", "model": "p1/m1"})
    assert called == []
    texts = [e.get("text", "") for e in got]
    assert not any("正在整理上下文" in t for t in texts)


def test_ws_compact_failure_is_swallowed(client):
    c = _c(client)
    sid = _new_session(client)
    _make_context_overflow(c, sid)
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "ok",
                                    "usage": {"prompt_tokens": 80, "completion_tokens": 1}}])

    async def _compact(msgs):
        raise RuntimeError("压缩服务挂了")

    c.compactor.compact = _compact
    with client.websocket_connect(f"/ws/{sid}") as ws:
        _turn(ws, {"type": "chat", "content": "一", "model": "p1/m1"})
        got = _turn(ws, {"type": "chat", "content": "二", "model": "p1/m1"})
    assert "error" not in _types(got)
    assert len(c.sessions.get(sid)["messages"]) > 0


pass


def _set_suggest(c, value, ret=None, exc=None):
    settings = c.store.config.settings
    settings.quickSuggestions = value
    calls = []

    async def _utility(kind, messages, session_id=""):
        calls.append(session_id)
        if exc:
            raise exc
        return ret

    c.gateway.call_utility = _utility
    return calls


def _suggestions(events: list[dict]) -> list[dict]:
    return [e for e in events if e.get("type") == "suggestions"]


def test_ws_suggestions_emitted(client):
    c = _c(client)
    calls = _set_suggest(c, True, ret='好的：["继续","先跑测试","回滚改动"]')
    sid = _new_session(client)
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "已改完"}])
    with client.websocket_connect(f"/ws/{sid}") as ws:
        got = _turn(ws, {"type": "chat", "content": "改一下"})
    sug = _suggestions(got)
    assert sug and sug[0]["items"] == ["继续", "先跑测试", "回滚改动"]
    assert calls == [f"suggest:{sid}"]


def test_ws_suggestions_disabled(client):
    c = _c(client)
    calls = _set_suggest(c, False, ret='["继续"]')
    sid = _new_session(client)
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "ok"}])
    with client.websocket_connect(f"/ws/{sid}") as ws:
        got = _turn(ws, {"type": "chat", "content": "hi"})
    assert calls == []
    assert _suggestions(got) == []


def test_ws_suggestions_skip_without_assistant_reply(client):
    c = _c(client)
    calls = _set_suggest(c, True, ret='["继续"]')
    sid = _new_session(client)
    c.runner.run = _fake_run(events=[{"type": "text", "text": "在处理"}], msgs=[])
    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "chat", "content": "hi"})
        got = _collect(ws, "text") + _settle(ws)
    assert calls == []
    assert _suggestions(got) == []


def test_ws_suggestions_skip_when_last_reply_interrupted(client):
    c = _c(client)
    calls = _set_suggest(c, True, ret='["继续"]')
    sid = _new_session(client)
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "半截",
                                    "interrupted": True}])
    with client.websocket_connect(f"/ws/{sid}") as ws:
        got = _turn(ws, {"type": "chat", "content": "hi"})
    assert calls == []
    assert _suggestions(got) == []


def test_ws_suggestions_call_failure(client):
    c = _c(client)
    calls = _set_suggest(c, True, exc=RuntimeError("模型不可用"))
    sid = _new_session(client)
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "ok"}])
    with client.websocket_connect(f"/ws/{sid}") as ws:
        got = _turn(ws, {"type": "chat", "content": "hi"})
    assert calls and _suggestions(got) == []


@pytest.mark.parametrize("ret,expected", [
    ("没有数组", []),
    ('["未闭合', []),
    ('{"a":1}', []),
    ('["继续", 1, null, "  ", "a", "b", "c"]', ["继续", "a", "b"]),
    ('["a", ]', ["a"]),
])
def test_ws_suggestions_payload_parsing(client, ret, expected):
    c = _c(client)
    _set_suggest(c, True, ret=ret)
    sid = _new_session(client, title="t")
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "ok"}])
    with client.websocket_connect(f"/ws/{sid}") as ws:
        got = _turn(ws, {"type": "chat", "content": "hi"})
    sug = _suggestions(got)
    if expected:
        assert sug and sug[0]["items"] == expected
    else:
        assert sug == []


def test_ws_suggestions_use_child_queue_when_configured(client):
    c = _c(client)
    _set_providers(c, [ModelInfo(id="m1", kind="lm")],
                   queues=ModelQueues(parent=[], child=["p1/m1"]))
    _set_suggest(c, True, ret='["继续"]')
    sid = _new_session(client)
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "ok"}])
    with client.websocket_connect(f"/ws/{sid}") as ws:
        got = _turn(ws, {"type": "chat", "content": "hi"})
    sug = _suggestions(got)
    assert sug and sug[0]["items"] == ["继续"]


pass


def test_ws_disconnect_is_clean(client):
    sid = _new_session(client)
    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "stop"})
        _collect(ws, "notice")
    pass


pass


def test_ws_plan_flag_off_disables_readonly(client):
    c = _c(client)
    sid = _new_session(client)
    seen: dict = {}
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "ok"}], seen=seen)
    with client.websocket_connect(f"/ws/{sid}") as ws:
        _turn(ws, {"type": "chat", "content": "x", "plan": False})
    assert seen["kwargs"]["plan_mode"] == "off"


def test_ws_plan_defaults_to_off(client):
    c = _c(client)
    sid = _new_session(client)
    seen: dict = {}
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "ok"}], seen=seen)
    with client.websocket_connect(f"/ws/{sid}") as ws:
        _turn(ws, {"type": "chat", "content": "x"})
    assert seen["kwargs"]["plan_mode"] == "off"


def test_ws_plan_flag_on_enables_readonly(client):
    c = _c(client)
    sid = _new_session(client)
    seen: dict = {}
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "ok"}], seen=seen)
    with client.websocket_connect(f"/ws/{sid}") as ws:
        _turn(ws, {"type": "chat", "content": "x", "plan": True})
    assert seen["kwargs"]["plan_mode"] == "on"


def test_ws_queued_message_keeps_current_plan_mode(client):
    import asyncio

    from app.agent.plan import PlanState

    c = _c(client)
    sid = _new_session(client)
    modes: list[str] = []

    async def _run(messages, cwd, emit, **kw):
        modes.append(kw.get("plan_mode"))
        await emit({"type": "text", "text": "跑着"})
        await asyncio.sleep(0.2)
        await emit({"type": "done", "model": "m"})
        yield {"role": "assistant", "content": "ok"}

    c.runner.run = _run
    c.runner.plan_for(sid)._state = PlanState.awaiting_approval

    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "plan_decision", "decision": "approve"})
        _collect(ws, "text")
        ws.send_json({"type": "chat", "content": "顺便注意 X", "plan": True})
        _collect(ws, "queue")
        _collect(ws, "done")
        _collect(ws, "done")

    assert modes[0] == "executing"
    assert modes[1] == "executing", f"插话被打回只读: {modes}"


def test_ws_plan_approve_resumes_without_duplicate_user_message(client):
    from app.agent.plan import PlanState

    c = _c(client)
    sid = _new_session(client)
    seen: dict = {}
    c.runner.run = _fake_run(
        events=[{"type": "done", "model": "m"}],
        msgs=[{"role": "assistant", "content": "done"}], seen=seen)
    pass
    c.runner.plan_for(sid)._state = PlanState.awaiting_approval

    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "plan_decision", "decision": "approve"})
        types = []
        for _ in range(20):
            ev = ws.receive_json()
            types.append(ev.get("type"))
            if ev.get("type") == "done":
                break
    assert "plan_approved" in types
    assert seen["kwargs"]["plan_mode"] == "executing"
    s = c.sessions.get(sid)
    users = [m for m in s["messages"] if m["role"] == "user"]
    assert len(users) == 1
    assert "确认" in users[0]["content"]


def test_ws_duplicate_plan_approve_only_runs_once(client):
    import asyncio

    from app.agent.plan import PlanState

    c = _c(client)
    sid = _new_session(client)
    runs: list[dict] = []

    async def _run(messages, cwd, emit, **kw):
        runs.append(kw)
        await emit({"type": "text", "text": "执行中"})
        await asyncio.sleep(0.1)
        await emit({"type": "done", "model": "m"})
        yield {"role": "assistant", "content": "done"}

    c.runner.run = _run
    c.runner.plan_for(sid)._state = PlanState.awaiting_approval

    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "plan_decision", "decision": "approve"})
        ws.send_json({"type": "plan_decision", "decision": "approve"})
        evs = _collect(ws, "done")

    assert len(runs) == 1, f"重复 approve 起了 {len(runs)} 轮续跑"
    assert runs[0]["plan_mode"] == "executing"
    assert sum(1 for e in evs if e.get("type") == "plan_approved") == 1


pass
pass
pass

def test_ws_pending_plan_off_clears_readonly(client):
    from app.agent.plan import PlanState

    c = _c(client)
    sid = _new_session(client)
    seen: dict = {}
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "done"}], seen=seen)
    c.runner.plan_for(sid)._state = PlanState.awaiting_approval

    with client.websocket_connect(f"/ws/{sid}") as ws:
        _turn(ws, {"type": "chat", "content": "按这份计划执行", "plan": False})

    assert seen["kwargs"]["plan_mode"] == "off"
    assert c.runner.plan_for(sid).state == PlanState.idle


def test_ws_pending_plan_on_restarts_planning(client):
    from app.agent.plan import PlanState

    c = _c(client)
    sid = _new_session(client)
    seen: dict = {}
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "done"}], seen=seen)
    c.runner.plan_for(sid)._state = PlanState.awaiting_approval

    with client.websocket_connect(f"/ws/{sid}") as ws:
        _turn(ws, {"type": "chat", "content": "[对计划的修改意见] 第2步改成备份", "plan": True})

    assert seen["kwargs"]["plan_mode"] == "on"
    assert c.runner.plan_for(sid).state == PlanState.planning


pass
pass
pass
pass
pass
pass


def test_ws_error_midway_still_persists_partial_reply(client):
    c = _c(client)
    sid = _new_session(client)

    async def _boom(messages, cwd, emit, **kw):
        yield {"role": "assistant", "content": "半截回复"}
        raise RuntimeError("模型炸了")

    c.runner.run = _boom
    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "chat", "content": "问"})
        got = _collect(ws, "error")
        assert any("模型炸了" in str(e.get("text", "")) for e in got)

    detail = client.get(f"/api/sessions/{sid}").json()
    roles = [m["role"] for m in detail["messages"]]
    assert roles == ["user", "assistant"], f"回复没落库：{roles}"
    assert detail["messages"][1]["content"] == "半截回复"


def test_ws_draft_published_then_cleared(client):
    c = _c(client)
    sid = _new_session(client)
    rt = c.session_rt().get(sid)
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "答"}])

    with client.websocket_connect(f"/ws/{sid}") as ws:
        _turn(ws, {"type": "chat", "content": "问"})

    assert rt.draft == [], "轮末必须清草稿"
    detail = client.get(f"/api/sessions/{sid}").json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]


def test_ws_ping_pong(client):
    sid = _new_session(client)
    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "ping"})
        got = _collect(ws, "pong")
        assert any("ts" in e for e in got if e["type"] == "pong")


def test_emit_failure_does_not_kill_turn(client):
    c = _c(client)
    sid = _new_session(client)
    rt = c.session_rt().get(sid)
    c.runner.run = _fake_run(msgs=[{"role": "assistant", "content": "照样写完"}])

    with client.websocket_connect(f"/ws/{sid}") as ws:
        pass
        ws.send_json({"type": "ping"})
        _collect(ws, "pong")

        async def _broken(ev):
            raise RuntimeError("Cannot call 'send' once a close message has been sent.")

        rt.emit = _broken
        ws.send_json({"type": "chat", "content": "问"})
        time.sleep(0.5)

    detail = client.get(f"/api/sessions/{sid}").json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"], \
        "发送器坏掉不该让本轮丢失"
    assert rt.running is False, "本轮必须收尾，否则前端一直显示回复中"


pass
pass
pass
pass


def test_two_rapid_messages_never_double_turn(client):
    c = _c(client)
    sid = _new_session(client)
    calls: list[str] = []

    def _slow(msgs, cwd, emit, **kw):
        pass
        async def _run(messages, cwd, emit, **kw):
            pass
            calls.append(str(messages[-1]["content"]).strip()[-1])
            await emit({"type": "text", "text": "hi"})
            await asyncio.sleep(0.35)
            await emit({"type": "done"})
            yield {"role": "assistant", "content": "ok"}
        return _run(msgs, cwd, emit, **kw)

    c.runner.run = _slow

    with client.websocket_connect(f"/ws/{sid}") as ws:
        pass
        ws.send_json({"type": "chat", "content": "甲"})
        ws.send_json({"type": "chat", "content": "乙"})
        got = _collect(ws, "turn_start", from_queue=True)
        pass
        assert got[-1]["content"] == "乙"
        q = [e for e in got if e["type"] == "queue"]
        assert q and q[-1]["items"] == []
        pass
        pass
        _collect(ws, "turn_saved")

    assert calls == ["甲", "乙"], f"应当串行跑完两条，实跑: {calls}"
    rt = c.session_rt().peek(sid)
    assert rt is None or (rt.running is False and rt.queue == []), "收尾后不能留 running/队列"


def test_running_flag_and_queue_consistent_after_turn(client):
    c = _c(client)
    sid = _new_session(client)
    c.runner.run = _fake_run(events=[{"type": "done"}],
                             msgs=[{"role": "assistant", "content": "完"}])
    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "chat", "content": "问"})
        _collect(ws, "done")
    rt = c.session_rt().peek(sid)
    assert rt is not None and rt.running is False and rt.queue == []


pass

def test_validate_spec_valid_spec_kept(client):
    from app.api.routers.chat_mode import _validate_spec
    c = _c(client)
    c.store.config.providers = [Provider(id="p1", name="p1", baseUrl="https://x/v1",
                                         apiKey="k", models=[ModelInfo(id="m1", kind="lm")])]
    assert _validate_spec(c, "p1/m1") == "p1/m1"


def test_validate_spec_missing_or_disabled_raises(client):
    from app.api.routers.chat_mode import _validate_spec
    c = _c(client)
    c.store.config.providers = [Provider(id="p1", name="p1", baseUrl="https://x/v1",
                                         apiKey="k", models=[
                                             ModelInfo(id="m1", kind="lm"),
                                             ModelInfo(id="m2", kind="lm", disabled=True)])]
    pass
    with pytest.raises(Exception) as e1:
        _validate_spec(c, "p1/gone")
    assert "不存在" in str(e1.value)
    pass
    with pytest.raises(Exception) as e2:
        _validate_spec(c, "p1/m2")
    assert "禁用" in str(e2.value)
    pass
    with pytest.raises(Exception) as e3:
        _validate_spec(c, "p9/m1")
    assert "不存在" in str(e3.value)
    pass
    assert _validate_spec(c, "") == ""


def test_event_log_and_sessions_share_one_store(client):
    from app.store import event_log

    c = client.app.state.container
    assert event_log._require_store() is c.sessions, (
        "event_log 与会话库不是同一个 SessionStore：两份连接写同一个会话库，"
        "WAL 下会报 database is locked（见本用例 docstring）")


def test_plain_turn_does_not_report_database_locked(client):
    c = client.app.state.container
    sid = client.post("/api/sessions", params={"title": "落库争用"}).json()["id"]

    async def fake_run(messages, cwd, emit, **kw):
        await emit({"type": "text", "text": "好"})
        yield {"role": "assistant", "content": "好"}

    c.runner.run = fake_run

    got: list[dict] = []
    with client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "chat", "content": "你好"})
        for _ in range(30):
            ws.send_json({"type": "stop"})
            ev = ws.receive_json()
            got.append(ev)
            if ev.get("type") == "notice" and ev.get("text") == "当前没有正在进行的回复":
                break
            time.sleep(0.1)

    errs = [str(e.get("text") or "") for e in got if e.get("type") == "error"]
    assert not any("database is locked" in e for e in errs), \
        f"本轮报了 database is locked（事件写事务与 save 争锁）：{errs}"

