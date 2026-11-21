from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

from app.agent.limits import (SUB_ROUND_CAP, SUB_ROUND_EXTEND,
                              SUB_ROUND_LIMIT)
from app.agent.loop_utils import budget_note
from app.agent.runner import AgentRunner
from app.agent.subagent_access import SubAgentAccess
from app.agent.subagents import SubAgentRecord
from app.chat.session_runtime import SessionRuntimeRegistry
from app.tools.builtin import build_tools as build_registry
from app.util import status as st


class FakeGateway:
    config = None
    last_spec = ""


    async def chat_stream(self, *args, **kwargs):
        if False:
            yield None


async def _noop_emit(_event):
    return None


def _runner() -> AgentRunner:
    return AgentRunner(FakeGateway(), build_registry(),
                       session_rt=SessionRuntimeRegistry())


pass

def test_budget_note_only_for_subagent():
    assert budget_note(0, 5, 20) == ""
    txt = budget_note(1, 5, 20)
    assert "剩 5 次" in txt and "20" in txt and "合并操作" in txt


def test_budget_note_never_negative():
    pass
    txt = budget_note(1, -3, 20)
    assert "已用尽" in txt and "阶段总结" in txt
    assert "禁止工具" in txt and "路径:行号" in txt


def test_budget_note_one_left_warns_about_wrapup():
    txt = budget_note(1, 1, 20)
    assert "只剩 1 次" in txt and "阶段总结" in txt


def test_budget_note_is_baked_in_before_persist(monkeypatch):
    runner = _runner()

    async def fake_one(tc, args, arg_err, ctx, messages, depth, emit,
                       fix_note=""):
        return "工具输出"

    monkeypatch.setattr(runner, "_execute_one", fake_one)
    monkeypatch.setattr(runner, "_parse_args", lambda tc: ({}, ""))
    monkeypatch.setattr(runner, "_wait_tool_or_abort", None)

    tcs = [{"id": "a", "function": {"name": "f_read", "arguments": "{}"}},
           {"id": "b", "function": {"name": "f_read", "arguments": "{}"}}]

    async def go():
        out, messages, emitted = [], [], []

        async def emit(ev):
            emitted.append(ev)

        async for msg in runner._execute_tools(
                tcs, None, messages, 1, emit,
                budget_left=7, budget_total=20):
            out.append(dict(msg))
        return out, messages

    out, messages = asyncio.run(go())
    assert "剩 7 次" not in out[0]["content"]
    assert "剩 7 次" in out[1]["content"]
    pass
    assert [m["content"] for m in out] == [m["content"] for m in messages]


def test_rounds_left_on_record():
    rec = SubAgentRecord(
        id="sa_budget_rl", parent_id="p", project="/tmp",
        task="任务", child_session_id="sub_budget_rl",
        rounds_limit=SUB_ROUND_LIMIT, rounds_used=7
    )
    assert rec.rounds_left == SUB_ROUND_LIMIT - 7
    rec.rounds_used = SUB_ROUND_LIMIT + 5
    assert rec.rounds_left == 0


pass

def test_run_stream_exhausts_budget_and_wraps_up(monkeypatch):
    runner = _runner()
    rec = SubAgentRecord(
        id="sa_budget_stream", parent_id="p", project="/tmp",
        task="任务", child_session_id="sub_budget_stream",
        rounds_limit=2, rounds_used=0
    )

    pass
    async def fake_prepare(messages, cwd, emit, depth, session_id, profile,
                           project_context, plan_mode, allowed_tools,
                           stop_check=None, policy_mode=""):
        pass
        pass
        return (SimpleNamespace(suggested_tools=None),
                [{"role": "system", "content": "S"}, *messages,
                 {"role": "system", "content": "CTX"}],
                [{"function": {"name": "f_read"}}])

    seen_requests = []

    async def fake_consume(messages, tools, spec, session_id, emit,
                           stop_check=None, abort_event=None):
        seen_requests.append({"tools": tools, "messages": list(messages)})
        if not tools:
            pass
            return ("```text\n已查明：a.py:12 create_order；\n"
                    "未完成：还没看 b.py；\n下一步：读 b.py L20-40\n```",
                    "", [], {"prompt_tokens": 10, "completion_tokens": 5})
        return ("", "", [{"id": "c1", "function": {
            "name": "f_read", "arguments": "{}"}}], None)

    async def fake_tool_round(round_no, acc_text, acc_reason, tool_calls, usage,
                              ctx, messages, depth, emit, boost,
                              abort_event=None, budget_left=0, budget_total=0):
        msg = {"role": "tool", "tool_call_id": "c1", "content": "读到的内容"}
        messages.append(msg)
        yield {"role": "assistant", "content": "", "tool_calls": tool_calls}
        yield msg

    async def noop_done(*args, **kwargs):
        return None

    async def no_list(*args, **kwargs):
        return []

    monkeypatch.setattr(runner, "_prepare_turn", fake_prepare)
    monkeypatch.setattr(runner, "_consume_stream", fake_consume)
    monkeypatch.setattr(runner, "_tool_round", fake_tool_round)
    monkeypatch.setattr(runner, "_emit_request_debug", noop_done)
    monkeypatch.setattr(runner, "_drain_control", noop_done)
    monkeypatch.setattr(runner, "_drain_bg_jobs", no_list)
    monkeypatch.setattr(runner, "_emit_done", noop_done)
    monkeypatch.setattr(runner, "_cost_of", lambda *a: 0.0)
    monkeypatch.setattr(runner, "_turn_meta", lambda *a: {})
    monkeypatch.setattr(runner, "_round_gap_note", lambda *a: None)

    async def go():
        out = []
        async for msg in runner.run(
                [{"role": "user", "content": "干活"}], "/tmp", _noop_emit,
                depth=1, session_id="sub1", control=rec.control):
            out.append(msg)
        return out

    out = asyncio.run(go())
    assert rec.paused is False
    assert rec.status != st.PAUSED
    assert rec.rounds_used == 2

    pass
    assert len(seen_requests) == 3
    assert all(r["tools"] for r in seen_requests[:2])
    wrap = seen_requests[-1]
    assert wrap["tools"] == [], "收尾请求必须不带工具，模型才能被物理禁调"
    pass
    assert wrap["messages"][-1]["role"] == "user"
    assert "阶段总结" in wrap["messages"][-1]["content"]
    assert "路径:行号" in wrap["messages"][-1]["content"]
    pass
    assert any(m.get("role") == "tool" and "读到的内容" in str(m.get("content"))
               for m in wrap["messages"])

    pass
    final = next(m for m in out if m.get("role") == "assistant"
                 and "create_order" in str(m.get("content")))
    assert "下一步" in final["content"] and "b.py" in final["content"]
    assert not any("[子 Agent 工具轮额度已用尽]" in str(m.get("content"))
                   for m in out)
    assert not rec.paused_messages


def test_paused_is_neither_active_nor_terminal():
    assert not st.is_active(st.PAUSED)
    assert not st.is_terminal(st.PAUSED)


pass

def test_spawn_starts_with_bounded_budget(tmp_path):
    runner = _runner()
    seen = {}

    async def fake_run(messages, cwd, emit, **kwargs):
        seen["control"] = kwargs.get("control")
        yield {"role": "assistant", "content": "完成"}

    runner.run = fake_run

    async def go():
        return await runner._spawn("任务", str(tmp_path), _noop_emit, 0,
                                   parent_session="p", background=False)

    assert asyncio.run(go()) == "完成"
    assert seen["control"].record.rounds_limit == SUB_ROUND_LIMIT
    assert seen["control"].record.status == st.DONE


def test_exhausted_rounds_finishes_as_done(tmp_path):
    runner = _runner()
    calls: list[list[dict]] = []

    async def fake_run(messages, cwd, emit, **kwargs):
        calls.append(list(messages))
        rec = kwargs["control"].record
        rec.rounds_used = rec.rounds_limit
        pass
        pass
        tool_msg = {"role": "tool", "tool_call_id": "t1", "content": "结果"}
        messages.append(tool_msg)
        rec.append_message(tool_msg)
        rec.paused = True
        rec.status = st.PAUSED
        yield {"role": "assistant", "content": "[工具轮额度用尽] 任务未完成"}

    runner.run = fake_run

    async def go():
        return await runner._spawn("闭环任务", str(tmp_path), _noop_emit, 0,
                                   parent_session="p1", rounds=2,
                                   background=False)

    got = asyncio.run(go())
    pass
    assert "阶段总结" in got and "extend" in got
    assert "路径:行号" in got and "历史" in got
    rec = next(r.subagent for r in runner.session_rt._rts.values() if r.subagent)
    assert rec.status == st.DONE and not rec.paused
    assert any(m.get("role") == "tool" and m.get("content") == "结果"
               for m in rec.messages)

    pass
    pass
    calls = []

    async def fake_run2(messages, cwd, emit, **kwargs):
        calls.append(list(messages))
        yield {"role": "assistant", "content": "```text\n续跑完成\n```"}

    runner.run = fake_run2
    result = asyncio.run(runner._extend_subagent(
        rec.id, "p1", _noop_emit, 0, task="把 b.py 看完", background=False))
    assert "续跑完成" in result
    assert calls and any(m.get("role") == "tool" for m in calls[0])
    assert any("把 b.py 看完" in str(m.get("content")) for m in calls[0])


def test_extend_rejects_wrong_state(tmp_path):
    runner = _runner()
    rec = SubAgentRecord(
        id="sa_budget_reject", parent_id="p", project=str(tmp_path),
        task="任务", child_session_id="sub_budget_reject"
    )
    rec.status = st.DONE
    pass
    pass
    runner.session_rt.get(rec.child_session_id).subagent = rec
    out = asyncio.run(runner._extend_subagent(rec.id, "p", _noop_emit, 0))
    assert "error" in json.loads(out)


def test_extend_stops_at_cap(tmp_path):
    runner = _runner()
    rec = SubAgentRecord(
        id="sa_budget_cap", parent_id="p", project=str(tmp_path),
        task="任务", child_session_id="sub_budget_cap",
        rounds_limit=SUB_ROUND_CAP
    )
    rec.status = st.PAUSED
    rec.paused = True
    pass
    pass
    runner.session_rt.get(rec.child_session_id).subagent = rec
    out = asyncio.run(runner._extend_subagent(rec.id, "p", _noop_emit, 0))
    assert "硬顶" in json.loads(out)["error"]


pass

def test_spawn_honors_explicit_profile(tmp_path):
    runner = _runner()
    seen = {}

    async def fake_run(messages, cwd, emit, **kwargs):
        seen["profile_id"] = kwargs.get("profile_id")
        yield {"role": "assistant", "content": "要点列表"}

    runner.run = fake_run

    async def go():
        return await runner._spawn("调研", str(tmp_path), _noop_emit, 0,
                                   parent_session="p", profile_prompt="researcher")

    asyncio.run(go())
    assert seen["profile_id"] == "researcher"


def test_spawn_unknown_profile_falls_back(tmp_path):
    runner = _runner()
    seen = {}

    async def fake_run(messages, cwd, emit, **kwargs):
        seen["profile_id"] = kwargs.get("profile_id")
        yield {"role": "assistant", "content": "ok"}

    runner.run = fake_run

    async def go():
        return await runner._spawn("任务", str(tmp_path), _noop_emit, 0,
                                   parent_session="p",
                                   profile_prompt="不存在的profile")

    asyncio.run(go())
    assert seen["profile_id"] == "default"



pass

def test_extend_background_returns_immediately_and_runs(tmp_path):
    from app.agent.subagents import SubAgentRecord
    from app.util import status as st

    (tmp_path / ".agent").mkdir(exist_ok=True)
    rec = SubAgentRecord(
        id="sa_bg_extend", parent_id="p", project=str(tmp_path),
        task="原任务", child_session_id="sub_bg",
        rounds_limit=12, rounds_used=12)
    rec.profile_id = "researcher"
    rec.tools = ["f_read"]
    rec.ensure()
    rec.append_message({"role": "user", "content": "原任务"})
    rec.append_message({"role": "assistant", "content": "```text\nA 已查明\n```"})
    rec.finish(st.DONE, "A 已查明")

    runner = _runner()
    gate = asyncio.Event()
    seen = []

    async def fake_run(messages, cwd, emit, **kwargs):
        seen.append(list(messages))
        await gate.wait()
        yield {"role": "assistant", "content": "```text\n续跑完成\n```"}

    runner.run = fake_run
    from app.agent.subagent_access import SubAgentAccess

    async def go():
        out = await runner._extend_subagent(
            rec.id, "p", _noop_emit, 0, task="继续查 B",
            cwd=str(tmp_path), background=True)
        pass
        access = SubAgentAccess(None, runner.session_rt, str(tmp_path))
        live = access.get(rec.id, "p")
        assert live is not None and live.task_handle is not None
        pass
        brief = await access.wait(rec.id, "p", timeout=0.01)
        gate.set()
        await live.task_handle
        return out, brief, live

    out, brief, live = asyncio.run(go())
    data = json.loads(out)
    assert data["background"] is True and data["status"] == st.RUNNING
    assert data["subagent_id"] == rec.id and "wait" in data["message"]
    assert seen and any("继续查 B" in str(m.get("content")) for m in seen[0])
    pass
    assert brief.get("timed_out") is True
    assert live.task_handle is not None and live.task_handle.done()


def test_extend_background_task_handle_registered_and_discoverable(tmp_path):
    from app.agent.subagents import SubAgentRecord
    from app.util import status as st

    (tmp_path / ".agent").mkdir(exist_ok=True)
    rec = SubAgentRecord(
        id="sa_bg_handle", parent_id="p", project=str(tmp_path),
        task="原任务", child_session_id="sub_bg_h",
        rounds_limit=12, rounds_used=12)
    rec.profile_id = "researcher"
    rec.tools = ["f_read"]
    rec.ensure()
    rec.append_message({"role": "user", "content": "原任务"})
    rec.finish(st.DONE, "原结论")

    runner = _runner()

    async def fake_run(messages, cwd, emit, **kwargs):
        yield {"role": "assistant", "content": "```text\n后台续跑完成\n```"}

    runner.run = fake_run
    from app.agent.subagent_access import SubAgentAccess

    async def go():
        out = await runner._extend_subagent(
            rec.id, "p", _noop_emit, 0, cwd=str(tmp_path), background=True)
        access = SubAgentAccess(None, runner.session_rt, str(tmp_path))
        live = access.get(rec.id, "p")
        assert live is not None and live.task_handle is not None
        brief = await access.wait(rec.id, "p", timeout=1)
        return out, brief

    out, brief = asyncio.run(go())
    assert json.loads(out)["background"] is True
    assert brief["status"] == st.DONE
    assert "后台续跑完成" in brief.get("result", "")


def test_extend_sync_path_still_available(tmp_path):
    from app.agent.subagents import SubAgentRecord
    from app.util import status as st

    (tmp_path / ".agent").mkdir(exist_ok=True)
    rec = SubAgentRecord(
        id="sa_sync_extend", parent_id="p", project=str(tmp_path),
        task="原任务", child_session_id="sub_sync",
        rounds_limit=12, rounds_used=12)
    rec.profile_id = "researcher"
    rec.tools = ["f_read"]
    rec.ensure()
    rec.append_message({"role": "user", "content": "原任务"})
    rec.finish(st.DONE, "原结论")

    runner = _runner()

    async def fake_run(messages, cwd, emit, **kwargs):
        yield {"role": "assistant", "content": "```text\n同步续跑完成\n```"}

    runner.run = fake_run
    out = asyncio.run(runner._extend_subagent(
        rec.id, "p", _noop_emit, 0, cwd=str(tmp_path), background=False))
    assert "同步续跑完成" in out and rec.task_handle is None


def test_orchestration_forwards_background_to_extend():
    from app.tools.builtin.subagent_tool import subagent as subagent_tool

    sent = {}

    async def fake_extend(sid, parent, rounds=0, task="", background=False):
        sent.update(sid=sid, parent=parent, rounds=rounds, task=task,
                    background=background)
        return '{"ok":true}'

    ctx = SimpleNamespace(
        cwd="/proj", spawn=None, subagents=object(),
        subagent_parent="s1", subagent_project="/proj", extend=fake_extend)
    out = asyncio.run(subagent_tool(ctx, action="extend", id="sa_1",
                                    rounds=7, task="继续", background=True))
    assert out == '{"ok":true}'
    assert sent == {"sid": "sa_1", "parent": "s1", "rounds": 7,
                    "task": "继续", "background": True}


def test_tool_layer_background_defaults_to_true():
    import inspect

    from app.tools.builtin.subagent_tool import subagent as subagent_tool

    pass
    sig = inspect.signature(subagent_tool)
    assert sig.parameters["background"].default is True

    pass
    sent = {}

    async def fake_spawn(task, c, t=None, bg=None, profile_prompt="",
                         rounds=0, hints=None):
        sent["bg"] = bg
        return '{"ok":true}'

    async def fake_extend(sid, parent, rounds=0, task="", background=None):
        sent["extend_bg"] = background
        return '{"ok":true}'

    ctx = SimpleNamespace(
        cwd="/proj", spawn=fake_spawn, subagents=object(),
        subagent_parent="s1", subagent_project="/proj", extend=fake_extend,
        project_dir=lambda: "/proj")
    asyncio.run(subagent_tool(ctx, action="spawn", task="x"))
    assert sent["bg"] is True
    asyncio.run(subagent_tool(ctx, action="extend", id="sa_1"))
    assert sent["extend_bg"] is True

    pass
    asyncio.run(subagent_tool(ctx, action="spawn", task="x", background=False))
    assert sent["bg"] is False
    asyncio.run(subagent_tool(ctx, action="extend", id="sa_1",
                              background=False))
    assert sent["extend_bg"] is False

pass

def test_subagent_tool_exposes_extend_action():
    from app.tools.builtin.subagent_tool import SUBAGENT_ACTIONS
    assert "extend" in SUBAGENT_ACTIONS


def test_to_dict_reports_budget(tmp_path):
    rec = SubAgentRecord(
        id="sa_budget_dict", parent_id="p", project=str(tmp_path),
        task="任务", child_session_id="sub_budget_dict",
        rounds_limit=20, rounds_used=13
    )
    data = rec.to_dict()
    assert data["rounds_left"] == 7
    assert data["rounds_limit"] == 20
    assert data["paused"] is False


def test_all_calls_done_before_first_yield(monkeypatch):
    runner = _runner()
    done: list[str] = []

    async def fake_one(tc, args, arg_err, ctx, messages, depth, emit,
                       fix_note=""):
        await asyncio.sleep(0)
        done.append(tc["id"])
        return "工具输出"

    monkeypatch.setattr(runner, "_execute_one", fake_one)
    monkeypatch.setattr(runner, "_parse_args", lambda tc: ({}, ""))
    tcs = [{"id": f"c{i}", "function": {"name": "f_read", "arguments": "{}"}}
           for i in range(4)]

    async def go():
        messages, first_yield_state = [], None
        async for _msg in runner._execute_tools(tcs, None, messages, 0, _noop_emit):
            if first_yield_state is None:
                first_yield_state = list(done)
        return first_yield_state

    assert asyncio.run(go()) == ["c0", "c1", "c2", "c3"]
    assert done == ["c0", "c1", "c2", "c3"]


pass

def test_spawn_injects_code_map_into_first_user_message(tmp_path):
    (tmp_path / ".agent").mkdir()
    (tmp_path / "svc").mkdir()
    (tmp_path / "svc" / "orders.py").write_text(
        'class OrderService:\n'
        '    """处理订单"""\n'
        '    def create_order(self, x):\n'
        '        return x\n', encoding="utf-8")

    runner = _runner()
    seen = {}

    async def fake_run(messages, cwd, emit, **kwargs):
        seen["messages"] = list(messages)
        yield {"role": "assistant", "content": "完成"}

    runner.run = fake_run

    async def go():
        return await runner._spawn(
            "核查 create_order", str(tmp_path / "svc"), _noop_emit, 0,
            parent_session="p", hints=["order"])

    asyncio.run(go())
    first = seen["messages"][0]
    assert first["role"] == "user"
    assert "项目代码地图" in first["content"]
    assert "OrderService" in first["content"]
    assert "核查 create_order" in first["content"]
    assert "return x" not in first["content"], "地图不能塞函数体全文"
    pass
    assert not any(m.get("role") == "system" for m in seen["messages"])


def test_spawn_without_project_has_no_map(tmp_path):
    runner = _runner()
    seen = {}

    async def fake_run(messages, cwd, emit, **kwargs):
        seen["first"] = messages[0]["content"]
        yield {"role": "assistant", "content": "完成"}

    runner.run = fake_run

    async def go():
        return await runner._spawn("纯任务", str(tmp_path), _noop_emit, 0,
                                   parent_session="p", hints=["x"],
                                   background=False)

    assert asyncio.run(go()) == "完成"
    assert seen["first"] == "纯任务"


def test_spawn_resume_does_not_reinject_map(tmp_path):
    (tmp_path / ".agent").mkdir()
    (tmp_path / "svc").mkdir()
    (tmp_path / "svc" / "a.py").write_text("def foo():\n    pass\n",
                                             encoding="utf-8")
    runner = _runner()
    seen = []

    async def fake_run(messages, cwd, emit, **kwargs):
        seen.append(list(messages))
        yield {"role": "assistant", "content": "完成"}

    runner.run = fake_run

    async def go():
        return await runner._spawn(
            "任务", str(tmp_path / "svc"), _noop_emit, 0,
            parent_session="p", hints=["foo"])

    asyncio.run(go())
    runner_instance = next(
        r.subagent for r in runner.session_rt._rts.values() if r.subagent)
    history = [{"role": "user", "content": "原来的历史"}]
    asyncio.run(runner_instance.control.run_child(messages=history, fresh=False))
    assert seen[-1] == history, "续跑必须原样复用传入历史，不注入地图"


pass

def test_wrapup_prompt_does_not_touch_system_prefix():
    from app.agent.loop_utils import BUDGET_WRAPUP_PROMPT
    from app.agent.prompt import SUBAGENT_CLOSING_RULE
    pass
    assert "[工具轮额度已用尽]" not in SUBAGENT_CLOSING_RULE
    assert "已用" not in SUBAGENT_CLOSING_RULE
    assert "阶段总结" in SUBAGENT_CLOSING_RULE
    assert "路径:行号" in BUDGET_WRAPUP_PROMPT
    assert "下一步" in BUDGET_WRAPUP_PROMPT
    assert "主 LLM" in BUDGET_WRAPUP_PROMPT or "父级" in BUDGET_WRAPUP_PROMPT


def test_wrapup_request_failure_still_finishes(monkeypatch):
    runner = _runner()
    rec = SubAgentRecord(
        id="sa_wrap_fail", parent_id="p", project="/tmp",
        task="任务", child_session_id="sub_wrap_fail",
        rounds_limit=1, rounds_used=0)

    async def fake_prepare(messages, cwd, emit, depth, session_id, profile,
                           project_context, plan_mode, allowed_tools,
                           stop_check=None, policy_mode=""):
        return (SimpleNamespace(suggested_tools=None),
                [{"role": "system", "content": "S"}, *messages],
                [{"function": {"name": "f_read"}}])

    calls = []

    async def fake_consume(messages, tools, spec, session_id, emit,
                           stop_check=None, abort_event=None):
        calls.append(tools)
        if not tools:
            raise RuntimeError("收尾请求挂了")
        return ("", "", [{"id": "c1", "function": {
            "name": "f_read", "arguments": "{}"}}], None)

    async def fake_tool_round(round_no, acc_text, acc_reason, tool_calls, usage,
                              ctx, messages, depth, emit, boost,
                              abort_event=None, budget_left=0, budget_total=0):
        msg = {"role": "tool", "tool_call_id": "c1", "content": "读到的内容"}
        messages.append(msg)
        yield {"role": "assistant", "content": "", "tool_calls": tool_calls}
        yield msg

    async def noop(*a, **k):
        return None

    async def no_list(*a, **k):
        return []

    monkeypatch.setattr(runner, "_prepare_turn", fake_prepare)
    monkeypatch.setattr(runner, "_consume_stream", fake_consume)
    monkeypatch.setattr(runner, "_tool_round", fake_tool_round)
    monkeypatch.setattr(runner, "_emit_request_debug", noop)
    monkeypatch.setattr(runner, "_drain_control", noop)
    monkeypatch.setattr(runner, "_drain_bg_jobs", no_list)
    monkeypatch.setattr(runner, "_emit_done", noop)
    monkeypatch.setattr(runner, "_cost_of", lambda *a: 0.0)
    monkeypatch.setattr(runner, "_turn_meta", lambda *a: {})
    monkeypatch.setattr(runner, "_round_gap_note", lambda *a: None)

    async def go():
        out = []
        async for m in runner.run(
                [{"role": "user", "content": "干活"}], "/tmp", _noop_emit,
                depth=1, session_id="s1", control=rec.control):
            out.append(m)
        return out

    out = asyncio.run(go())
    assert len(calls) == 2 and calls[-1] == []
    final = out[-1]
    assert final["role"] == "assistant"
    assert "阶段总结" in final["content"]
    assert "extend" in final["content"] and "历史" in final["content"]
    assert rec.rounds_used == 1 and not rec.paused_messages


def test_budget_wrapup_module_empty_output_fallback():
    from app.agent.budget_wrapup import budget_wrapup

    class _R:
        async def _consume_stream(self, messages, tools, spec, session_id, emit,
                                  stop_check=None, abort_event=None):
            assert tools == [], "收尾请求必须禁工具"
            assert messages[-1]["role"] == "user"
            assert "阶段总结" in messages[-1]["content"]
            return "", "", [], None

        def _cost_of(self, *a):
            return 0.0

        def _last_model_spec(self):
            return "m"

        def _turn_meta(self, *a):
            return {}

        async def _emit_done(self, *a, **k):
            return None

    async def go():
        return await budget_wrapup(
            _R(), [{"role": "user", "content": "原任务"},
                   {"role": "tool", "content": "读到 a.py:12"}],
            "summary", "", "s1", _noop_emit)

    msg, _usage = asyncio.run(go())
    assert msg["role"] == "assistant" and "阶段总结" in msg["content"]
    assert "extend" in msg["content"] and "历史" in msg["content"]



def test_extend_resolves_project_from_parent_session(tmp_path):
    from app.agent.subagents import SubAgentRecord
    from app.util import status as st

    old = SubAgentRecord(
        id="sa_parent_lookup", parent_id="p", project=str(tmp_path),
        task="旧任务", child_session_id="sub_parent",
        rounds_limit=12, rounds_used=12)
    old.profile_id = "researcher"
    old.tools = ["f_read"]
    old.ensure()
    old.append_message({"role": "user", "content": "旧任务"})
    old.finish(st.DONE, "旧结论")
    (tmp_path / ".agent").mkdir(exist_ok=True)

    runner = _runner()
    runner.sessions = SimpleNamespace(
        session_project=lambda sid: str(tmp_path) if sid == "p" else "")
    calls = []

    async def fake_run(messages, cwd, emit, **kwargs):
        calls.append(kwargs)
        yield {"role": "assistant", "content": "```text\n兜底续跑 ok\n```"}

    runner.run = fake_run
    got = asyncio.run(runner._extend_subagent(
        old.id, "p", _noop_emit, 0, task="继续", background=False))
    assert "兜底续跑 ok" in got and calls


def test_extend_legacy_disk_record_stays_readonly(tmp_path):
    from app.agent.subagents import SubAgentRecord
    from app.util import status as st

    old = SubAgentRecord(
        id="sa_legacy", parent_id="p", project=str(tmp_path),
        task="旧任务", child_session_id="sub_legacy",
        rounds_limit=12, rounds_used=12)
    pass
    old.ensure()
    old.append_message({"role": "user", "content": "旧任务"})
    old.finish(st.DONE, "旧结论")
    (tmp_path / ".agent").mkdir(exist_ok=True)

    runner = _runner()
    calls = []

    async def fake_run(messages, cwd, emit, **kwargs):
        calls.append(kwargs)
        yield {"role": "assistant", "content": "```text\n只读续跑 ok\n```"}

    runner.run = fake_run
    got = asyncio.run(runner._extend_subagent(
        old.id, "p", _noop_emit, 0, task="继续", cwd=str(tmp_path),
        background=False))
    assert "只读续跑 ok" in got and calls
    assert calls[0]["profile_id"] == "researcher"
    assert set(calls[0]["allowed_tools"] or ()) <= {
        "f_read", "search_files", "grep", "web"}

pass

def test_extend_done_record_from_disk_rebuilds_runner(tmp_path):
    from app.agent.subagents import SubAgentRecord
    from app.util import status as st


    pass
    old = SubAgentRecord(
        id="sa_after_restart", parent_id="p", project=str(tmp_path),
        task="上个进程的任务", child_session_id="sub_hist",
        rounds_limit=12, rounds_used=12)
    old.profile_prompt = "researcher"
    old.profile_base = "researcher"
    old.tools = ["f_read", "grep"]
    old.ensure()
    old.append_message({"role": "user", "content": "上个进程的任务"})
    old.append_message({"role": "assistant",
                        "content": "```text\n已查明 a.py:12\n```"})
    old.finish(st.DONE, "已查明 a.py:12")

    pass
    (tmp_path / ".agent").mkdir(exist_ok=True)

    runner = _runner()
    calls = []

    async def fake_run(messages, cwd, emit, **kwargs):
        calls.append({"messages": list(messages), "kwargs": kwargs})
        yield {"role": "assistant", "content": "```text\n续跑完成 b.py\n```"}

    runner.run = fake_run

    pass
    got = asyncio.run(runner._extend_subagent(
        old.id, "p", _noop_emit, 0, task="把 b.py 也看完",
        cwd=str(tmp_path), background=False))

    assert "续跑完成" in got
    assert calls, "必须真的基于历史重新跑了一轮"
    hist = calls[0]["messages"]
    pass
    assert any("a.py:12" in str(m.get("content")) for m in hist)
    pass
    assert "把 b.py 也看完" in str(hist[-1].get("content"))
    assert not any(m.get("role") == "system" for m in hist)
    pass
    assert calls[0]["kwargs"]["profile_id"] == "researcher"
    assert calls[0]["kwargs"]["allowed_tools"] == ["f_read", "grep"]
    pass
    assert calls[0]["kwargs"]["session_id"] == "sub_hist"


def test_extend_rejects_failed_record_but_accepts_done(tmp_path):
    from app.agent.subagents import SubAgentRecord
    from app.util import status as st

    rec = SubAgentRecord(
        id="sa_failed", parent_id="p", project=str(tmp_path),
        task="任务", child_session_id="sub_failed",
        rounds_limit=12, rounds_used=1)
    rec.ensure()
    rec.finish(st.FAILED, "", "boom")

    (tmp_path / ".agent").mkdir(exist_ok=True)
    runner = _runner()
    got = asyncio.run(runner._extend_subagent(
        rec.id, "p", _noop_emit, 0, cwd=str(tmp_path)))
    assert "无法续跑" in got or "error" in got


pass
pass
pass
pass
pass

async def test_parent_stop_closes_turn_without_model_request():
    runner = _runner()
    calls = {"n": 0}

    async def _chat_stream(*a, **kw):
        calls["n"] += 1
        if False:
            yield None

    runner.gateway.chat_stream = _chat_stream

    async def _prep(*a, **k):
        return SimpleNamespace(suggested_tools=None, stop_check=None), [], []
    runner._prepare_turn = _prep

    class _Ctrl:
        def drain_instructions(self):
            return []

        @property
        def stop_requested(self):
            return True

    out = [m async for m in runner.run(
        [], "/tmp", _noop_emit, depth=1, control=_Ctrl())]

    assert calls["n"] == 0, "父级已要求中止，不该再发模型请求"
    assert len(out) == 1, f"应只有一条中止收尾消息，实收 {out}"
    assert "(空回复)" not in str(out)


def test_stopped_status_is_terminal():
    assert st.is_terminal(st.STOPPED)
    assert not st.is_active(st.STOPPED)


def test_extend_rejects_stopped_subagent(tmp_path):
    runner = _runner()
    rec = SubAgentRecord(
        id="sa_stopped", parent_id="p", project=str(tmp_path),
        task="任务", child_session_id="sub_stopped")
    rec.finish(st.STOPPED, "", "已中止")
    runner.session_rt.get(rec.child_session_id).subagent = rec
    out = json.loads(asyncio.run(
        runner._extend_subagent(rec.id, "p", _noop_emit, 0)))
    assert "无法续跑" in out["error"]
