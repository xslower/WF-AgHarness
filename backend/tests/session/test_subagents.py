import asyncio
import json
import uuid
from pathlib import Path

from app.agent.runner import AgentRunner
from app.agent.subagent_access import SubAgentAccess
from app.agent.subagents import SubAgentRecord
from app.chat.session_runtime import SessionRuntimeRegistry
from app.chat.sessions import SessionStore
from app.tools.builtin import build_tools as build_registry
from app.util import status as st


class FakeGateway:
    async def chat_stream(self, *args, **kwargs):
        if False:
            yield None


async def _noop_emit(_event):
    return None


def test_subagent_files_are_project_scoped(tmp_path):
    rec = SubAgentRecord(
        id="sa_test1", parent_id="p", project=str(tmp_path),
        task="调查", child_session_id="sub_test1")
    rec.ensure()
    assert rec.dir == tmp_path / ".agent" / "subagents" / "sa_test1"
    rec.persist()
    assert (rec.dir / "meta.json").is_file()
    rec.append_message({"role": "assistant", "content": "ok"})
    pass
    rec._writer.flush()
    assert (rec.dir / "transcript.jsonl").read_text("utf-8").strip()


def test_background_subagent_can_be_queried_and_stopped(tmp_path):
    rt = SessionRuntimeRegistry()
    runner = AgentRunner(FakeGateway(), build_registry(),
                         session_rt=rt, sessions=SessionStore())

    async def fake_run(messages, cwd, emit, **kwargs):
        control = kwargs.get("control")
        yield {"role": "assistant", "content": "第一段"}
        for _ in range(100):
            if control and control.drain_instructions():
                yield {"role": "assistant", "content": "收到追加指令"}
            await asyncio.sleep(0.01)

    runner.run = fake_run

    access = SubAgentAccess(runner.sessions, runner.session_rt)

    async def go():
        handle = json.loads(await runner._spawn(
            "长任务", str(tmp_path), _noop_emit, 0,
            background=True, parent_session="p1"))
        rec = access.get(handle["subagent_id"], "p1")
        assert rec is not None
        await asyncio.sleep(0.02)
        assert "第一段" in rec.result or rec.messages
        access.message(rec.id, "补充要求", "p1")
        await asyncio.sleep(0.02)
        access.stop(rec.id, "p1")
        await access.wait(rec.id, "p1")
        return rec

    rec = asyncio.run(go())
    assert rec.status in ("stopped", "done")
    assert (tmp_path / ".agent" / "subagents" / rec.id).is_dir()


def test_subagent_tool_dispatch_and_no_legacy_names(tmp_path):
    from app.tools import ToolContext

    reg = build_registry()
    rt = SessionRuntimeRegistry()
    rec = SubAgentRecord(
        id="sa_tool1", parent_id="p", project=str(tmp_path),
        task="任务", child_session_id="sub_tool1")
    rec.ensure()
    rec.persist()
    rt.get(rec.child_session_id).subagent = rec
    access = SubAgentAccess(None, rt)

    ctx = ToolContext(str(tmp_path))
    ctx.subagents = access
    ctx.subagent_parent = "p"
    ctx.subagent_project = str(tmp_path)

    async def go():
        listed = json.loads(await reg.execute("subagent", {"action": "list"}, ctx))
        got = json.loads(await reg.execute(
            "subagent", {"action": "get", "id": rec.id}, ctx))
        bad = json.loads(await reg.execute("subagent", {"action": "nope"}, ctx))
        no_id = json.loads(await reg.execute("subagent", {"action": "stop"}, ctx))
        return listed, got, bad, no_id

    listed, got, bad, no_id = asyncio.run(go())
    assert [x["id"] for x in listed] == [rec.id]
    assert got["id"] == rec.id
    assert "error" in bad and "error" in no_id
    for old in ("spawn_agent", "list_subagents", "get_subagent",
                "message_subagent", "stop_subagent", "wait_subagent"):
        assert old not in reg.tools


def test_spawn_result_is_not_truncated(tmp_path):
    long_text = "y" * 20000
    runner = AgentRunner(FakeGateway(), build_registry(),
                         session_rt=SessionRuntimeRegistry(),
                         sessions=SessionStore())

    async def fake_run(messages, cwd, emit, **kwargs):
        yield {"role": "assistant", "content": long_text}

    runner.run = fake_run

    async def go():
        return await runner._spawn("长输出", str(tmp_path), _noop_emit, 0,
                                   parent_session="p2", background=False)

    out = asyncio.run(go())
    pass
    pass
    assert "result.md" in out and "f_read(lines=)" in out
    assert len(out) < 20000
    pass
    for sid, rt in runner.session_rt._rts.items():
        if rt.subagent is not None:
            rec = rt.subagent
            break
    else:
        raise AssertionError("没有找到子 agent record")
    assert rec.result == long_text
    assert Path(rec.result_path).read_text("utf-8") == long_text


pass

def test_wait_returns_brief_without_task_or_metadata(tmp_path):
    rec = SubAgentRecord(
        id="sa_brief", parent_id="p", project=str(tmp_path),
        task="这是一段很长的任务描述，模型刚发过一遍，不该再回显" * 10,
        child_session_id="sub_brief", rounds_limit=20, rounds_used=3)
    rt = SessionRuntimeRegistry()
    rt.get(rec.child_session_id).subagent = rec
    access = SubAgentAccess(None, rt)

    got = asyncio.run(access.wait(rec.id, "p"))
    assert got["id"] == rec.id and got["status"] == st.RUNNING
    assert got["rounds_used"] == 3 and got["rounds_left"] == 17
    for banned in ("task", "project", "parent_id", "child_session_id",
                   "transcript_path", "created_at", "finished_at",
                   "result_path", "result_chars"):
        assert banned not in got, banned
    assert len(json.dumps(got, ensure_ascii=False)) < 300


def test_wait_returns_result_but_still_no_task(tmp_path):
    rec = SubAgentRecord(
        id="sa_done", parent_id="p", project=str(tmp_path),
        task="长任务描述" * 100, child_session_id="sub_done")
    rec.finish(st.DONE, "结论：全绿")
    rt = SessionRuntimeRegistry()
    rt.get(rec.child_session_id).subagent = rec
    got = asyncio.run(SubAgentAccess(None, rt).wait(rec.id, "p"))
    assert got["result"] == "结论：全绿"
    assert "task" not in got and "transcript_path" not in got
    assert len(json.dumps(got, ensure_ascii=False)) < 300


def test_wait_actually_awaits_task_handle(tmp_path):
    rec = SubAgentRecord(
        id="sa_handle", parent_id="p", project=str(tmp_path),
        task="任务", child_session_id="sub_handle")
    rt = SessionRuntimeRegistry()
    rt.get(rec.child_session_id).subagent = rec
    access = SubAgentAccess(None, rt)

    async def go():
        started = asyncio.Event()

        async def body():
            started.set()
            await asyncio.sleep(0.05)
            rec.finish(st.DONE, "完成")

        rec.task_handle = asyncio.create_task(body())
        pass
        got = await access.wait(rec.id, "p")
        return started.is_set(), rec.task_handle.done(), got

    started, done, got = asyncio.run(go())
    assert started and done
    assert got["status"] == st.DONE and got["result"] == "完成"


def test_stop_cancels_task_handle_not_ws_slot(tmp_path):
    rec = SubAgentRecord(
        id="sa_stop", parent_id="p", project=str(tmp_path),
        task="任务", child_session_id="sub_stop")
    rt = SessionRuntimeRegistry()
    rt.get(rec.child_session_id).subagent = rec
    access = SubAgentAccess(None, rt)

    async def go():
        async def body():
            await asyncio.sleep(10)
        rec.task_handle = asyncio.create_task(body())
        out = access.stop(rec.id, "p")
        await asyncio.sleep(0)
        return out, rec.task_handle.cancelled() or rec.task_handle.done()

    out, cancelled = asyncio.run(go())
    assert out["ok"] is True and cancelled


def test_wait_timeout_returns_timed_out_without_killing_child(tmp_path):
    rec = SubAgentRecord(
        id="sa_timeout", parent_id="p", project=str(tmp_path),
        task="任务", child_session_id="sub_timeout")
    rt = SessionRuntimeRegistry()
    rt.get(rec.child_session_id).subagent = rec
    access = SubAgentAccess(None, rt)

    async def go():
        async def body():
            await asyncio.sleep(10)
            rec.finish(st.DONE, "完成")
        rec.task_handle = asyncio.create_task(body())
        await asyncio.sleep(0)
        got = await access.wait(rec.id, "p", timeout=0.02)
        pass
        pass
        assert got["timed_out"] is True
        assert got["status"] == st.RUNNING
        assert "timed_out" in json.dumps(got)
        assert not rec.task_handle.done() and not rec.task_handle.cancelled()
        rec.task_handle.cancel()
        return got

    asyncio.run(go())


def test_wait_timeout_then_second_wait_gets_result(tmp_path):
    rec = SubAgentRecord(
        id="sa_retry", parent_id="p", project=str(tmp_path),
        task="任务", child_session_id="sub_retry")
    rt = SessionRuntimeRegistry()
    rt.get(rec.child_session_id).subagent = rec
    access = SubAgentAccess(None, rt)

    async def go():
        async def body():
            await asyncio.sleep(0.05)
            rec.finish(st.DONE, "结论")
        rec.task_handle = asyncio.create_task(body())
        first = await access.wait(rec.id, "p", timeout=0.01)
        second = await access.wait(rec.id, "p", timeout=1.0)
        return first, second

    first, second = asyncio.run(go())
    assert first["timed_out"] is True
    assert "timed_out" not in second and second["status"] == st.DONE
    assert second["result"] == "结论"


def test_wait_without_timeout_still_awaits_handle(tmp_path):
    rec = SubAgentRecord(
        id="sa_notimeout", parent_id="p", project=str(tmp_path),
        task="任务", child_session_id="sub_notimeout")
    rt = SessionRuntimeRegistry()
    rt.get(rec.child_session_id).subagent = rec
    access = SubAgentAccess(None, rt)

    async def go():
        async def body():
            await asyncio.sleep(0.02)
            rec.finish(st.DONE, "完成")
        rec.task_handle = asyncio.create_task(body())
        return await access.wait(rec.id, "p")

    got = asyncio.run(go())
    assert got["status"] == st.DONE and got["result"] == "完成"


def test_to_dict_still_full_for_list_and_api(tmp_path):
    rec = SubAgentRecord(
        id="sa_full", parent_id="p", project=str(tmp_path),
        task="原文", child_session_id="sub_full")
    data = rec.to_dict()
    for key in ("task", "project", "parent_id", "child_session_id",
                "transcript_path", "created_at", "result_chars"):
        assert key in data, key


def test_spawn_background_does_not_echo_task(tmp_path):
    runner = AgentRunner(FakeGateway(), build_registry(),
                           session_rt=SessionRuntimeRegistry(),
                           sessions=SessionStore())

    async def fake_run(messages, cwd, emit, **kwargs):
        await asyncio.sleep(10)
        if False:
            yield None

    runner.run = fake_run

    async def go():
        out = json.loads(await runner._spawn(
            "长任务描述" * 100, str(tmp_path), _noop_emit, 0,
            background=True, parent_session="p_bg"))
        handle = next(rt.subagent.task_handle
                     for rt in runner.session_rt._rts.values() if rt.subagent)
        handle.cancel()
        return out

    out = asyncio.run(go())
    assert "task" not in out and out["status"] == st.RUNNING


pass
pass
pass
pass

def _seed_disk_record(tmp_path, sa_id="sa_hist", parent="p", result="历史结论"):
    rec = SubAgentRecord(
        id=sa_id, parent_id=parent, project=str(tmp_path),
        task="上个进程的任务", child_session_id="sub_hist",
        rounds_limit=20, rounds_used=2)
    rec.ensure()
    rec.append_message({"role": "user", "content": "上个进程的任务"})
    rec.append_message({"role": "assistant", "content": result})
    rec.append_event({"type": "tool_call", "name": "f_read"})
    pass
    rec.finish(st.DONE, result)
    return rec


def test_restart_then_get_by_sid_returns_history(tmp_path):
    rec = _seed_disk_record(tmp_path)
    pass
    fresh = SubAgentAccess(None, SessionRuntimeRegistry(), str(tmp_path))
    got = fresh.get(rec.id, "p")
    assert got is not None
    assert got.from_disk is True
    assert got.status == st.DONE
    assert got.result == "历史结论"
    assert [m["content"] for m in got.messages] == ["上个进程的任务", "历史结论"]
    assert got.events and got.events[0]["name"] == "f_read"
    pass
    assert fresh.read(rec.id, "p")["messages"][1]["content"] == "历史结论"
    assert got.to_dict()["task"] == "上个进程的任务"


def test_restart_then_list_includes_history(tmp_path):
    rec = _seed_disk_record(tmp_path)
    fresh = SubAgentAccess(None, SessionRuntimeRegistry(), str(tmp_path))
    ids = [x["id"] for x in fresh.list("p")]
    assert rec.id in ids
    pass
    assert fresh.list("别的会话") == []


def test_history_and_live_merge_without_duplicates(tmp_path):
    rec = _seed_disk_record(tmp_path)
    rt = SessionRuntimeRegistry()
    live = SubAgentRecord(
        id=rec.id, parent_id="p", project=str(tmp_path),
        task="在线任务", child_session_id="sub_live")
    live.status = st.RUNNING
    rt.get(live.child_session_id).subagent = live
    access = SubAgentAccess(None, rt, str(tmp_path))
    items = access.list("p")
    assert len(items) == 1
    assert items[0]["status"] == st.RUNNING
    pass
    assert access.get(rec.id, "p") is live


def test_restart_then_wait_returns_history_immediately(tmp_path):
    rec = _seed_disk_record(tmp_path)
    fresh = SubAgentAccess(None, SessionRuntimeRegistry(), str(tmp_path))
    got = asyncio.run(fresh.wait(rec.id, "p", timeout=0.01))
    assert got["status"] == st.DONE and got["result"] == "历史结论"
    assert got.get("from_disk") is True
    assert "timed_out" not in got


def test_history_record_can_queue_instruction(tmp_path):
    rec = _seed_disk_record(tmp_path)
    fresh = SubAgentAccess(None, SessionRuntimeRegistry(), str(tmp_path))
    out = fresh.message(rec.id, "继续把 b.py 看完", "p")
    assert out["ok"] is True and out["queued"] == "继续把 b.py 看完"
    assert "extend" in out["hint"]
    pass
    again = SubAgentAccess(None, SessionRuntimeRegistry(), str(tmp_path))
    restored = again.get(rec.id, "p")
    assert restored is not None
    assert restored.instructions == ["继续把 b.py 看完"]
    assert "只读" in fresh.stop(rec.id, "p")["error"]


def test_disk_lookup_respects_parent_and_missing(tmp_path):
    rec = _seed_disk_record(tmp_path)
    fresh = SubAgentAccess(None, SessionRuntimeRegistry(), str(tmp_path))
    assert fresh.get(rec.id, "别的父会话") is None
    assert fresh.get("sa_不存在", "p") is None


def test_history_result_survives_stale_absolute_path(tmp_path):
    rec = _seed_disk_record(tmp_path)
    meta = json.loads((rec.dir / "meta.json").read_text("utf-8"))
    meta["result_path"] = "/已失效/旧挂载/result.md"
    (rec.dir / "meta.json").write_text(json.dumps(meta), "utf-8")
    fresh = SubAgentAccess(None, SessionRuntimeRegistry(), str(tmp_path))
    assert fresh.get(rec.id, "p").result == "历史结论"


pass
pass
pass

def _runner_with_output(tmp_path, output="```text\n结论\n```"):
    runner = AgentRunner(FakeGateway(), build_registry(),
                         session_rt=SessionRuntimeRegistry(),
                         sessions=SessionStore())
    seen = {}

    async def fake_run(messages, cwd, emit, **kwargs):
        seen["spec"] = kwargs.get("spec")
        seen["allowed_tools"] = kwargs.get("allowed_tools")
        seen["profile_id"] = kwargs.get("profile_id")
        yield {"role": "assistant", "content": output}

    runner.run = fake_run
    return runner, seen


def test_spawn_uses_summary_queue_by_default(tmp_path):
    from app.provider.spec import QUEUE_SUMMARY
    runner, seen = _runner_with_output(tmp_path, "```text\n结论\n```")
    asyncio.run(runner._spawn("任务", str(tmp_path), _noop_emit, 0,
                              parent_session="p_q", background=False))
    assert seen["spec"] == QUEUE_SUMMARY


def test_spawn_extracts_fenced_conclusion(tmp_path):
    prose = "我先分析了一大堆……（这些不该回主会话）\n"
    body = "- 改了 a.py:3\n- 测试 12 passed"
    runner, _ = _runner_with_output(tmp_path, prose + f"```md\n{body}\n```\n收尾废话")
    out = asyncio.run(runner._spawn("任务", str(tmp_path), _noop_emit, 0,
                                    parent_session="p_f", background=False))
    assert out == body
    rec = next(rt.subagent for rt in runner.session_rt._rts.values()
               if rt.subagent is not None)
    assert rec.result == body
    assert rec.protocol == "ok"
    assert rec.raw_chars > len(body)
    assert Path(rec.result_path).read_text("utf-8") == body
    raw = Path(rec.result_path).with_name("result.raw.md")
    assert "我先分析" in raw.read_text("utf-8")


def test_spawn_without_fence_keeps_full_text(tmp_path):
    runner, _ = _runner_with_output(tmp_path, "没有围栏的普通结论")
    out = asyncio.run(runner._spawn("任务", str(tmp_path), _noop_emit, 0,
                                    parent_session="p_nf", background=False))
    assert out == "没有围栏的普通结论"


def test_spawn_long_conclusion_returns_file_hint(tmp_path):
    from app.tools.text_limit import TOOL_CONTEXT_LIMIT
    body = "结" * (TOOL_CONTEXT_LIMIT + 500)
    runner, _ = _runner_with_output(tmp_path, f"```text\n{body}\n```")
    out = asyncio.run(runner._spawn("任务", str(tmp_path), _noop_emit, 0,
                                    parent_session="p_long", background=False))
    assert len(out) < TOOL_CONTEXT_LIMIT * 2
    assert "result.md" in out and "f_read(lines=)" in out
    rec = next(rt.subagent for rt in runner.session_rt._rts.values()
               if rt.subagent is not None)
    assert rec.result == body
    pass
    assert Path(rec.result_path).read_text("utf-8") == body
    assert body in Path(rec.result_path).with_name("result.raw.md").read_text(
        "utf-8")


def test_brief_long_result_is_file_hint(tmp_path):
    from app.tools.text_limit import TOOL_CONTEXT_LIMIT
    long = "x" * (TOOL_CONTEXT_LIMIT + 100)
    rec = SubAgentRecord(
        id="sa_brieflong", parent_id="p", project=str(tmp_path),
        task="任务", child_session_id="sub_brieflong")
    rec.finish(st.DONE, long)
    got = rec.brief()
    assert "result.md" in got["result"] and len(got["result"]) < 300


pass
pass
pass
pass

def _plan_runner_with_output(tmp_path, output="```text\n结论\n```"):
    from app.agent.plan import PlanState
    runner, seen = _runner_with_output(tmp_path, output)
    runner.plan_ctrl._state = PlanState.awaiting_approval
    return runner, seen


def test_plan_spawn_forces_researcher_readonly_tools(tmp_path):
    from app.agent.profiles.researcher import RESEARCHER_PROFILE
    runner, seen = _plan_runner_with_output(tmp_path)
    pass
    asyncio.run(runner._spawn("调研", str(tmp_path), _noop_emit, 0,
                              parent_session="p_plan", profile_prompt="default",
                              tools=["run_command", "f_write", "subagent"]))
    assert seen["profile_id"] == "researcher"
    allowed = set(seen["allowed_tools"] or [])
    assert allowed == set(RESEARCHER_PROFILE.allowed_tools)
    pass
    for banned in ("run_command", "f_write", "f_replace", "f_path", "subagent",
                   "workflow", "tool"):
        assert banned not in allowed, banned


def test_plan_spawn_ignores_profile_and_tools_override(tmp_path):
    runner, seen = _plan_runner_with_output(tmp_path)
    asyncio.run(runner._spawn("调研", str(tmp_path), _noop_emit, 0,
                              parent_session="p_plan2",
                              tools=["f_write", "run_command"]))
    assert seen["profile_id"] == "researcher"
    assert "f_write" not in (seen["allowed_tools"] or [])
    assert "run_command" not in (seen["allowed_tools"] or [])


def test_spawn_outside_plan_keeps_model_choice(tmp_path):
    runner, seen = _runner_with_output(tmp_path)
    asyncio.run(runner._spawn("任务", str(tmp_path), _noop_emit, 0,
                              parent_session="p_idle", profile_prompt="default",
                              tools=["f_read", "grep"]))
    assert seen["profile_id"] == "default"
    assert seen["allowed_tools"] == ["f_read", "grep"]


def test_plan_spawn_child_cannot_respawn(tmp_path):
    from app.agent.profiles.researcher import RESEARCHER_PROFILE
    runner, _seen = _plan_runner_with_output(tmp_path)
    asyncio.run(runner._spawn("调研", str(tmp_path), _noop_emit, 0,
                              parent_session="p_depth"))
    assert RESEARCHER_PROFILE.max_spawn_depth == 0
