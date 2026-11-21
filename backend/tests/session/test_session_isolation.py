from __future__ import annotations

import asyncio
import time
import types

from app.agent.runner import AgentRunner
from app.chat.session_runtime import SessionRuntimeRegistry
from app.tools import ToolRegistry


pass

def _c(client):
    return client.app.state.container


def _new_session(client, title: str = "任务", project: str = "",
                 kind: str = "", origin: str = "") -> str:
    r = client.post("/api/sessions", params={
        "title": title, "project": project, "kind": kind, "origin": origin})
    assert r.status_code == 200
    return r.json()["id"]


class _DummyGateway:
    config = None


async def _drain(agen):
    async for _ in agen:
        pass


pass

def test_runtime_registry_is_per_sid():
    reg = SessionRuntimeRegistry()
    a = reg.get("s1")
    b = reg.get("s2")
    assert a is not b

    a.begin_turn()
    a.enqueue({"content": "排队"})
    a.request_abort()

    pass
    assert b.running is False
    assert b.queue == []
    assert b.abort_requested is False

    pass
    assert reg.get("s1") is a
    assert reg.is_running("s1") is True
    assert reg.queued("s1") == 1


def test_runtime_survives_disconnect_and_gc_keeps_active():
    reg = SessionRuntimeRegistry()
    rt = reg.get("s1")
    rt.begin_turn()
    rt.emit = lambda ev: None
    rt.last_active = time.time() - 10_000
    assert reg.gc(ttl=60) == 0
    rt.end_turn()
    rt.emit = None
    rt.last_active = time.time() - 10_000
    assert reg.gc(ttl=60) == 1
    assert reg.peek("s1") is None


def test_runtime_begin_turn_resets_abort():
    reg = SessionRuntimeRegistry()
    rt = reg.get("s1")
    rt.request_abort()
    assert rt.abort_requested is True and rt.stop is True
    rt.begin_turn()
    assert rt.abort_requested is False and rt.stop is False
    assert rt.running is True


pass

def test_live_snapshot_empty_session(client):
    sid = _new_session(client)
    d = client.get(f"/api/sessions/{sid}/live").json()
    assert d["sid"] == sid
    assert d["running"] is False
    assert d["queue"] == []
    assert d["usage"] is None
    assert d["plan"] == {"status": "idle", "planText": ""}
    assert d["todos"] == []
    assert d["approvals"] == []


def test_live_replay_never_overshoots_last_seq(client, monkeypatch):
    from app.store import event_log

    c = _c(client)
    sid = _new_session(client)
    project = c.sessions.get(sid).get("project") or ""
    seqs = [event_log.next_seq(sid, project) for _ in range(3)]
    for s in seqs:
        event_log.append(project, sid, s, {"type": "text", "text": str(s)})
    event_log.flush(project, sid)

    pass
    real_read = event_log.read_since

    def raced_read(proj, s, since=0, limit=2000):
        out = real_read(proj, s, since=since, limit=limit)
        return [*out, (seqs[-1] + 99, {"type": "done"})]

    monkeypatch.setattr(event_log, "read_since", raced_read)
    d = client.get(f"/api/sessions/{sid}/live?since={seqs[0]}").json()
    assert all(it["i"] <= d["lastSeq"] for it in d["replay"]), d["replay"]


def test_live_snapshot_reflects_runtime(client):
    c = _c(client)
    sid = _new_session(client)
    rt = c.session_rt().get(sid)
    rt.begin_turn()
    rt.enqueue({"content": "排队中的消息"})
    d = client.get(f"/api/sessions/{sid}/live").json()
    assert d["running"] is True
    assert [it["content"] for it in d["queue"]] == ["排队中的消息"]
    pass
    other = _new_session(client, title="另一条")
    d2 = client.get(f"/api/sessions/{other}/live").json()
    assert d2["running"] is False and d2["queue"] == []


def test_live_exposes_unpersisted_draft(client):
    c = _c(client)
    sid = _new_session(client)
    rt = c.session_rt().get(sid)
    rt.begin_turn()
    rt.push_draft({"role": "assistant", "content": "正在生成的内容"})
    rt.push_draft({"role": "user", "content": "不该进草稿"})
    d = client.get(f"/api/sessions/{sid}/live").json()
    assert [m["content"] for m in d["draft"]] == ["正在生成的内容"]
    pass
    other = _new_session(client, title="另一条")
    assert client.get(f"/api/sessions/{other}/live").json()["draft"] == []


def test_begin_turn_discards_previous_draft(client):
    c = _c(client)
    sid = _new_session(client)
    rt = c.session_rt().get(sid)
    rt.begin_turn()
    rt.push_draft({"role": "assistant", "content": "上一轮"})
    rt.begin_turn()
    assert rt.draft == []


def test_draft_is_capped():
    rt = SessionRuntimeRegistry().get("s")
    for i in range(500):
        rt.push_draft({"role": "assistant", "content": f"m{i}"})
    assert len(rt.draft) == 400
    assert rt.draft[-1]["content"] == "m499"


pass

def test_live_exposes_inflight_stream(client):
    c = _c(client)
    sid = _new_session(client)
    rt = c.session_rt().get(sid)
    rt.begin_turn()
    rt.push_stream("text", "第一段")
    rt.push_stream("text", "第二段")
    rt.push_stream("reason", "先想一下")
    d = client.get(f"/api/sessions/{sid}/live").json()
    assert d["stream"]["text"] == "第一段第二段"
    assert d["stream"]["reason"] == "先想一下"
    pass
    other = _new_session(client, title="另一条")
    assert client.get(f"/api/sessions/{other}/live").json()["stream"] == {"text": "", "reason": ""}


def test_stream_cleared_when_message_forms():
    rt = SessionRuntimeRegistry().get("s")
    rt.begin_turn()
    rt.push_stream("text", "半截")
    rt.push_draft({"role": "assistant", "content": "半截完整了"})
    assert rt.stream == {"text": "", "reason": ""}
    assert [m["content"] for m in rt.draft] == ["半截完整了"]


def test_begin_turn_resets_stream():
    rt = SessionRuntimeRegistry().get("s")
    rt.begin_turn()
    rt.push_stream("text", "上一轮的尾巴")
    rt.begin_turn()
    assert rt.stream == {"text": "", "reason": ""}


def test_clear_draft_clears_stream():
    rt = SessionRuntimeRegistry().get("s")
    rt.begin_turn()
    rt.push_stream("text", "x")
    rt.push_draft({"role": "assistant", "content": "y"})
    rt.push_stream("text", "z")
    rt.clear_draft()
    assert rt.draft == []
    assert rt.stream == {"text": "", "reason": ""}


def test_emit_records_stream_even_when_socket_gone():
    from app.api.routers import chat_ws as mod
    rt = SessionRuntimeRegistry().get("s")
    rt.begin_turn()
    rt.emit = None
    pass
    rt.push_stream("text", "断线后继续写")
    assert rt.stream["text"] == "断线后继续写"
    assert rt.snapshot()["stream"]["text"] == "断线后继续写"


def test_live_usage_comes_from_last_assistant_message(client):
    c = _c(client)
    sid = _new_session(client)
    s = c.sessions.get(sid)
    s["messages"] = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "ok", "model": "m/x",
         "usage": {"prompt_tokens": 100, "completion_tokens": 20}},
    ]
    c.sessions.save(s)
    d = client.get(f"/api/sessions/{sid}/live").json()
    pass
    pass
    assert d["usage"] == {"used": 120, "model": "m/x", "estimated": False}


def test_live_usage_estimates_when_no_real_usage(client):
    c = _c(client)
    sid = _new_session(client)
    s = c.sessions.get(sid)
    s["messages"] = [{"role": "user", "content": "你好世界" * 100}]
    c.sessions.save(s)
    d = client.get(f"/api/sessions/{sid}/live").json()
    assert d["usage"]["estimated"] is True
    assert d["usage"]["used"] > 0


def test_live_missing_session_404(client):
    r = client.get("/api/sessions/nope/live")
    assert r.status_code == 404


def test_delete_session_drops_runtime(client):
    c = _c(client)
    sid = _new_session(client)
    rt = c.session_rt().get(sid)
    rt.begin_turn()
    client.delete(f"/api/sessions/{sid}")
    assert c.session_rt().peek(sid) is None


pass

def test_session_list_exposes_running_badge(client):
    c = _c(client)
    sid = _new_session(client, title="跑着的")
    idle = _new_session(client, title="闲着的")
    c.session_rt().get(sid).begin_turn()
    c.session_rt().get(sid).enqueue({"content": "x"})
    items = {it["id"]: it for it in client.get("/api/sessions").json()}
    assert items[sid]["running"] is True
    assert items[sid]["queued"] == 1
    assert items[idle]["running"] is False


pass

def test_approvals_filtered_by_session(client):
    c = _c(client)
    c.approvals.create("cmd-a", [], "原因", session_id="s1")
    c.approvals.create("cmd-b", [], "原因", session_id="s2")
    only1 = client.get("/api/approvals", params={"session": "s1"}).json()
    assert [x["command"] for x in only1] == ["cmd-a"]
    assert only1[0]["session_id"] == "s1"
    pass
    assert len(client.get("/api/approvals").json()) == 2


pass

def test_bind_session_prefers_project_then_falls_back(client):
    sid = _new_session(client, title="工作流助手", project="/p1",
                       kind="workflow", origin="工单分流")
    pass
    r = client.get("/api/sessions/bind",
                   params={"kind": "workflow", "origin": "工单分流",
                           "project": "/p1"}).json()
    assert r["id"] == sid
    pass
    r2 = client.get("/api/sessions/bind",
                    params={"kind": "workflow", "origin": "工单分流",
                            "project": "/p9"}).json()
    assert r2["id"] == sid
    pass
    r3 = client.get("/api/sessions/bind",
                    params={"kind": "workflow", "origin": "不存在"}).json()
    assert r3["id"] is None


def test_bind_requires_kind(client):
    assert client.get("/api/sessions/bind", params={"origin": "x"}).status_code == 400


def test_bind_is_not_swallowed_by_sid_route(client):
    r = client.get("/api/sessions/bind", params={"kind": "workflow", "origin": "x"})
    assert r.status_code == 200
    assert "id" in r.json()


pass

def _slow_runner(calls: dict):
    reg = ToolRegistry()

    async def slow(path: str = "", ctx=None):
        calls["n"] = calls.get("n", 0) + 1
        await asyncio.sleep(5)
        return "跑完了"

    reg.register("slow", "慢工具", {"path": {"type": "string"}}, slow, [])
    return AgentRunner(_DummyGateway(), reg)


def test_abort_cancels_running_tool_immediately():
    calls: dict = {}
    runner = _slow_runner(calls)
    ctx = types.SimpleNamespace(cwd="/tmp")
    events: list[dict] = []
    msgs: list[dict] = []
    tcs = [
        {"id": "t1", "function": {"name": "slow", "arguments": '{"path":"a"}'}},
        {"id": "t2", "function": {"name": "slow", "arguments": '{"path":"b"}'}},
    ]

    async def emit(ev):
        events.append(ev)

    async def scenario():
        abort = asyncio.Event()
        agen = runner._execute_tools(tcs, ctx, msgs, 0, emit, abort_event=abort)
        task = asyncio.create_task(_drain(agen))
        await asyncio.sleep(0.15)
        started = time.perf_counter()
        abort.set()
        await asyncio.wait_for(task, timeout=2.0)
        return time.perf_counter() - started

    elapsed = asyncio.run(scenario())
    assert elapsed < 1.0, f"中止等了 {elapsed:.2f}s，说明还在等工具跑完"
    pass
    assert len(msgs) == 2
    assert {m["tool_call_id"] for m in msgs} == {"t1", "t2"}
    assert all("已放弃" in m["content"] for m in msgs)
    pass
    ends = [e for e in events if e["type"] == "tool_end"]
    assert ends and "已中止" in str(ends[0].get("result"))
    pass
    assert calls.get("n") == 1


def test_no_abort_runs_tools_normally():
    calls: dict = {}
    runner = _slow_runner(calls)
    ctx = types.SimpleNamespace(cwd="/tmp")
    events: list[dict] = []
    msgs: list[dict] = []
    tcs = [{"id": "t1", "function": {"name": "slow", "arguments": "{}"}}]

    async def emit(ev):
        events.append(ev)

    async def scenario():
        async def fast(path: str = "", ctx=None):
            return "ok"
        runner.registry.register("slow", "快工具", {}, fast, [])
        await _drain(runner._execute_tools(tcs, ctx, msgs, 0, emit,
                                           abort_event=asyncio.Event()))

    asyncio.run(scenario())
    assert msgs[0]["content"] == "ok"
    starts = [e for e in events if e["type"] == "tool_start"]
    assert starts and starts[0]["name"] == "slow"
    pass
    assert isinstance(starts[0].get("args"), dict)
