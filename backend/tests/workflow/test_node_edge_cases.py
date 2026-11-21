from __future__ import annotations

import pytest

from app.workflow.nodes.registry import NodeContext
from app.workflow import WorkflowError
from app.workflow.router import WorkflowRouter

from app.workflow.nodes.subagent import run_subagent
from app.workflow.nodes.tool import run_tool


pass


class FakeAgentRunner:

    def __init__(self, msgs=None, emit_calls=None):
        self.msgs = msgs if msgs is not None else [
            {"role": "assistant", "content": None},
            {"role": "assistant", "content": "最终答案"},
            {"role": "user", "content": "噪音"},
        ]
        self.emit_calls = emit_calls if emit_calls is not None else []
        self.kwargs: dict = {}

    async def run(self, messages, cwd, emit, **kw):
        self.kwargs = {"messages": messages, "cwd": cwd, **kw}
        await emit({"type": "text", "text": "子 Agent 流式输出"})
        self.emit_calls.append(1)
        for m in self.msgs:
            yield m


class FakeTools:
    def __init__(self, result: str = "ok"):
        self.result = result
        self.calls: list[tuple] = []

    async def execute(self, name, args, ctx):
        self.calls.append((name, args))
        return self.result


pass


async def test_subagent_without_runner_raises():
    ctx = NodeContext(agent_runner=None)
    with pytest.raises(WorkflowError) as ei:
        await run_subagent({"id": "s1", "task": "做事"}, ctx, {})
    assert "s1" in str(ei.value) and "不可用" in str(ei.value)


async def test_subagent_defaults_to_summary_queue_and_keeps_last_reply():
    runner = FakeAgentRunner()
    ctx = NodeContext(workspace="/tmp/ws", agent_runner=runner, run_id="rid1")
    text, nxt = await run_subagent({"id": "s1", "task": "做事", "next": "n2"}, ctx, {})
    assert text == "最终答案"
    assert nxt == "n2"
    assert runner.kwargs["spec"] == "summary"


async def test_subagent_model_can_be_overridden():
    runner = FakeAgentRunner()
    ctx = NodeContext(agent_runner=runner, run_id="rid1")
    await run_subagent({"id": "s1", "task": "t", "model": "p/m"}, ctx, {})
    assert runner.kwargs["spec"] == "p/m"
    assert runner.kwargs["session_id"] == "wf-sub:rid1"


async def test_subagent_without_workspace_uses_dot():
    runner = FakeAgentRunner()
    ctx = NodeContext(agent_runner=runner)
    await run_subagent({"id": "s1", "task": "t"}, ctx, {})
    assert runner.kwargs["cwd"] == "."


async def test_subagent_empty_output():
    runner = FakeAgentRunner(msgs=[{"role": "assistant", "content": ""}])
    ctx = NodeContext(agent_runner=runner)
    text, nxt = await run_subagent({"id": "s1", "task": "t"}, ctx, {})
    assert text == "" and nxt is None


pass


async def test_tool_invalid_json_raises():
    ctx = NodeContext(tools=FakeTools())
    with pytest.raises(WorkflowError) as ei:
        await run_tool({"id": "t1", "tool": "f_read", "argsJson": "{不是 JSON"},
                       ctx, {})
    assert "t1" in str(ei.value) and "JSON 无效" in str(ei.value)


async def test_tool_defaults_to_empty_args():
    tools = FakeTools(result="内容")
    ctx = NodeContext(tools=tools)
    out, nxt = await run_tool({"id": "t1", "tool": "list_dir", "next": "n2"}, ctx, {})
    assert out == "内容" and nxt == "n2"
    assert tools.calls == [("list_dir", {})]


async def test_tool_error_result_raises():
    ctx = NodeContext(tools=FakeTools(result='{"error": "文件不存在"}'))
    with pytest.raises(WorkflowError) as ei:
        await run_tool({"id": "t1", "tool": "f_read", "argsJson": '{"path":"x"}'},
                       ctx, {})
    assert "tool 节点失败" in str(ei.value) and "文件不存在" in str(ei.value)


async def test_tool_leading_whitespace_error_still_detected():
    ctx = NodeContext(tools=FakeTools(result='  \n{"error": "boom"}'))
    with pytest.raises(WorkflowError):
        await run_tool({"id": "t1", "tool": "x"}, ctx, {})


async def test_tool_args_substituted_from_vars():
    tools = FakeTools()
    ctx = NodeContext(tools=tools, substitute=lambda text, v, long_ref=False:
                      text.replace("${p}", "/tmp/a.txt"))
    await run_tool({"id": "t1", "tool": "f_read", "argsJson": '{"path":"${p}"}'},
                   ctx, {})
    assert tools.calls[0][1] == {"path": "/tmp/a.txt"}


pass


async def test_run_for_dispatches_to_project_engine(tmp_path):
    router = WorkflowRouter(global_dir=tmp_path)
    called: dict = {}

    class _Eng:
        async def execute_sync(self, name, inputs, human_mode="deny", start_node="",
                               parallel_mode="", session="new"):
            called["args"] = (name, inputs)
            called["human_mode"] = human_mode
            called["start_node"] = start_node
            called["parallel_mode"] = parallel_mode
            called["session"] = session
            return "REC"

    router.engine_for = lambda project: _Eng()
    got = await router.run_for("wf1", {"x": 1}, "/proj")
    assert got == "REC"
    assert called["args"] == ("wf1", {"x": 1})
    assert called["start_node"] == ""
    pass
    assert called["human_mode"] == "deny"


async def test_engine_for_is_cached_per_project(tmp_path):
    router = WorkflowRouter(global_dir=tmp_path)
    a = router.engine_for("")
    b = router.engine_for("")
    assert a is b
    p1 = router.engine_for(str(tmp_path / "proj"))
    assert p1 is not a
    assert p1 is router.engine_for(str(tmp_path / "proj"))
    assert p1.workspace == str(tmp_path / "proj")


def test_global_dir_defaults_to_package_constant(tmp_dirs):
    router = WorkflowRouter()
    assert router.global_dir == tmp_dirs / "workflows"
