from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.plan import PlanController, PlanState
from app.agent.runner import AgentRunner, PLAN_MODE_SUFFIX


pass
pass
pass
class TestPlanModeConstants:
    def test_plan_mode_suffix_is_string(self):
        assert isinstance(PLAN_MODE_SUFFIX, str)
        assert len(PLAN_MODE_SUFFIX) > 50

    def test_plan_mode_suffix_mentions_plan(self):
        assert "计划" in PLAN_MODE_SUFFIX or "plan" in PLAN_MODE_SUFFIX.lower()


pass
pass
pass
class TestAgentRunnerPlanInit:
    def test_plan_ctrl_created(self):
        gateway = MagicMock()
        registry = MagicMock()
        runner = AgentRunner(gateway, registry)
        assert hasattr(runner, "plan_ctrl")
        assert isinstance(runner.plan_ctrl, PlanController)
        assert runner.plan_ctrl.state == PlanState.idle


pass
pass
pass
class TestCheckPlanBlock:
    @pytest.fixture
    def runner(self):
        gateway = MagicMock()
        registry = MagicMock()
        return AgentRunner(gateway, registry)

    @pytest.fixture
    def emit(self):
        return AsyncMock()

    async def test_not_awaiting_no_block(self, runner, emit):
        runner.plan_ctrl._state = PlanState.idle
        result = await runner._check_plan_block("f_write", {"path": "/tmp/test"}, emit)
        assert result is False
        emit.assert_not_called()

    async def test_executing_no_block(self, runner, emit):
        runner.plan_ctrl._state = PlanState.executing
        result = await runner._check_plan_block("f_write", {"path": "/tmp/test"}, emit)
        assert result is False

    async def test_awaiting_blocks_f_write(self, runner, emit):
        runner.plan_ctrl._state = PlanState.awaiting_approval
        result = await runner._check_plan_block("f_write", {"path": "/tmp/test"}, emit)
        assert result is True
        emit.assert_called_once()

    async def test_awaiting_allows_subagent_spawn(self, runner, emit):
        runner.plan_ctrl._state = PlanState.awaiting_approval
        result = await runner._check_plan_block(
            "subagent", {"action": "spawn", "task": "只读调研"}, emit)
        assert result is False

    async def test_awaiting_blocks_subagent_control_actions(self, runner, emit):
        runner.plan_ctrl._state = PlanState.awaiting_approval
        for act in ("message", "stop", "extend"):
            blocked = await runner._check_plan_block(
                "subagent", {"action": act, "id": "sa_x"}, emit)
            assert blocked is True, act

    async def test_awaiting_blocks_run_command_write(self, runner, emit):
        runner.plan_ctrl._state = PlanState.awaiting_approval
        result = await runner._check_plan_block("run_command", {"command": "rm -rf /tmp"}, emit)
        assert result is True

    async def test_awaiting_allows_run_command_readonly(self, runner, emit):
        runner.plan_ctrl._state = PlanState.awaiting_approval
        result = await runner._check_plan_block("run_command", {"command": "ls -la"}, emit)
        assert result is False
        emit.assert_not_called()

    async def test_awaiting_allows_git_status(self, runner, emit):
        runner.plan_ctrl._state = PlanState.awaiting_approval
        result = await runner._check_plan_block("run_command", {"command": "git status"}, emit)
        assert result is False

    async def test_awaiting_blocks_f_path_create(self, runner, emit):
        runner.plan_ctrl._state = PlanState.awaiting_approval
        result = await runner._check_plan_block("f_path", {"action": "create"}, emit)
        assert result is True

    async def test_awaiting_blocks_f_path_delete(self, runner, emit):
        runner.plan_ctrl._state = PlanState.awaiting_approval
        result = await runner._check_plan_block("f_path", {"action": "delete"}, emit)
        assert result is True

    async def test_awaiting_blocks_f_path_move(self, runner, emit):
        runner.plan_ctrl._state = PlanState.awaiting_approval
        result = await runner._check_plan_block("f_path", {"action": "move"}, emit)
        assert result is True

    async def test_awaiting_blocks_f_path_copy(self, runner, emit):
        runner.plan_ctrl._state = PlanState.awaiting_approval
        result = await runner._check_plan_block("f_path", {"action": "copy"}, emit)
        assert result is True

    async def test_awaiting_does_not_block_f_path_unknown_action(self, runner, emit):
        runner.plan_ctrl._state = PlanState.awaiting_approval
        pass
        result = await runner._check_plan_block("f_path", {"action": "list"}, emit)
        assert result is False

    async def test_awaiting_does_not_block_read_tool(self, runner, emit):
        runner.plan_ctrl._state = PlanState.awaiting_approval
        result = await runner._check_plan_block("f_read", {"path": "/tmp/test"}, emit)
        assert result is False

    async def test_awaiting_does_not_block_grep(self, runner, emit):
        runner.plan_ctrl._state = PlanState.awaiting_approval
        result = await runner._check_plan_block("grep", {"key": ["test"]}, emit)
        assert result is False


pass
pass
pass
class TestCheckEscalationPlan:
    @pytest.fixture
    def runner(self):
        gateway = MagicMock()
        registry = MagicMock()
        r = AgentRunner(gateway, registry)
        r._escalation = {"files": set(), "escalated": False}
        return r

    @pytest.fixture
    def emit(self):
        return AsyncMock()

    async def test_escalation_returns_note_without_touching_messages(self, runner, emit):
        runner.plan_ctrl._state = PlanState.planning
        runner.gateway.config.settings.escalateFileLimit = 2
        runner._escalation["files"] = {"/a/file1.py"}
        messages: list[dict] = [{"role": "tool", "content": "ok"}]

        note = await runner._check_escalation(
            "f_write", {"path": "/a/file2.py"}, messages, 0, emit
        )
        assert note and "计划" in note
        assert runner._escalation["escalated"] is True
        assert len(messages) == 1
        assert all(m.get("role") != "system" for m in messages)

    async def test_escalation_ignores_file_count_when_plan_off(self, runner, emit):
        runner.plan_ctrl._state = PlanState.idle
        runner.gateway.config.settings.escalateFileLimit = 2
        runner._escalation["files"] = {f"/a/{i}.py" for i in range(10)}
        note = await runner._check_escalation(
            "f_write", {"path": "/a/9.py"}, [], 0, emit
        )
        assert note is None
        assert runner._escalation["escalated"] is False

    async def test_escalation_default_limit_is_500(self, runner, emit):
        runner.plan_ctrl._state = PlanState.planning
        runner.gateway.config.settings = MagicMock(spec=[])
        runner._escalation["files"] = {f"/a/{i}.py" for i in range(6)}
        note = await runner._check_escalation(
            "f_write", {"path": "/a/5.py"}, [], 0, emit
        )
        assert note is None

    async def test_escalation_triggers_on_config_delete_command(self, runner, emit):
        runner.plan_ctrl._state = PlanState.planning
        runner.gateway.config.settings.escalateFileLimit = 0
        note = await runner._check_escalation(
            "run_command", {"command": "rm -rf .env"}, [], 0, emit
        )
        assert note is not None

    async def test_escalation_only_triggers_once(self, runner, emit):
        runner.plan_ctrl._state = PlanState.planning
        runner._escalation["escalated"] = True
        note = await runner._check_escalation(
            "f_write", {"path": "/a/file7.py"}, [], 0, emit
        )
        assert note is None


    async def test_escalation_keeps_awaiting_plan_text(self, runner, emit):
        runner.plan_ctrl._state = PlanState.awaiting_approval
        runner.plan_ctrl._plan_text = "## 📋 实施计划\n1. 改 A"
        runner.gateway.config.settings.escalateFileLimit = 1
        runner._escalation["files"] = {"/a/x.py"}

        note = await runner._check_escalation(
            "f_write", {"path": "/a/y.py"}, [], 0, emit)
        assert note is not None
        assert runner.plan_ctrl.state is PlanState.awaiting_approval
        assert runner.plan_ctrl.plan_text == "## 📋 实施计划\n1. 改 A"


pass
pass
pass
class TestBuildSystemPlan:
    @pytest.fixture
    def runner(self):
        gateway = MagicMock()
        gateway.call_utility = AsyncMock(return_value=" minor ")
        registry = MagicMock()
        return AgentRunner(gateway, registry)

    @pytest.fixture
    def emit(self):
        return AsyncMock()

    async def test_always_mode_enters_planning(self, runner, emit):
        from app.agent.profile import AgentProfile
        profile = AgentProfile(
            id="test", system_prompt="", allowed_tools=None,
            max_rounds=25, spec="parent", plan_mode="always",
            max_spawn_depth=0, subagent_profile="default",
        )
        system = await runner._build_system(profile, [], 0, emit, "sid1")
        assert runner.plan_ctrl.state == PlanState.planning
        assert "计划" in system
        emit.assert_called()
        pass
        call_args = emit.call_args_list[0]
        assert call_args[0][0]["type"] == "plan_start"

    async def test_always_mode_skipped_at_depth_gt_0(self, runner, emit):
        from app.agent.profile import AgentProfile
        profile = AgentProfile(
            id="test", system_prompt="", allowed_tools=None,
            max_rounds=25, spec="parent", plan_mode="always",
            max_spawn_depth=0, subagent_profile="default",
        )
        await runner._build_system(profile, [], 1, emit, "sid1")
        assert runner.plan_ctrl.state == PlanState.idle

    async def test_classify_mode_enters_readonly_without_extra_llm_call(
            self, runner, emit):
        from app.agent.profile import AgentProfile
        runner.gateway.call_utility = AsyncMock(return_value="major")
        profile = AgentProfile(
            id="test", system_prompt="", allowed_tools=None,
            max_rounds=25, spec="parent", plan_mode="classify",
            max_spawn_depth=0, subagent_profile="default",
        )
        system = await runner._build_system(
            profile,
            [{"role": "user", "content": "帮我改个变量名"}],
            0, emit, "sid2",
        )
        assert runner.plan_ctrl.state == PlanState.planning
        assert "只读" in system
        runner.gateway.call_utility.assert_not_called()

    async def test_plan_mode_override_turns_off(self, runner, emit):
        from app.agent.profile import AgentProfile
        profile = AgentProfile(
            id="test", system_prompt="", allowed_tools=None,
            max_rounds=25, spec="parent", plan_mode="always",
            max_spawn_depth=0, subagent_profile="default",
        )
        await runner._build_system(profile, [], 0, emit, "sid6", "off")
        assert runner.plan_ctrl.state == PlanState.idle

    async def test_system_prompt_is_constant_across_plan_modes(self, runner, emit):
        from app.agent.profile import AgentProfile
        profile = AgentProfile(
            id="test", system_prompt="基础提示", allowed_tools=None,
            max_rounds=25, spec="parent", plan_mode="always",
            max_spawn_depth=0, subagent_profile="default",
        )
        got = []
        for i, mode in enumerate(("on", "executing", "off", "on")):
            emit.reset_mock()
            runner.plan_ctrl._state = PlanState.idle
            got.append(await runner._build_system(
                profile, [], 0, emit, f"sid{i}", mode))
        assert len(set(got)) == 1
        assert got[0].startswith("基础提示")
        assert "计划" in got[0]

    async def test_off_mode_never_enters_planning(self, runner, emit):
        from app.agent.profile import AgentProfile
        profile = AgentProfile(
            id="test", system_prompt="", allowed_tools=None,
            max_rounds=25, spec="parent", plan_mode="off",
            max_spawn_depth=0, subagent_profile="default",
        )
        await runner._build_system(
            profile,
            [{"role": "user", "content": "重构整个认证模块"}],
            0, emit, "sid6",
        )
        assert runner.plan_ctrl.state == PlanState.idle


pass
pass
pass
class TestExecuteToolsPlanBlock:
    @pytest.fixture
    def runner(self):
        gateway = MagicMock()
        registry = MagicMock()
        r = AgentRunner(gateway, registry)
        return r

    @pytest.fixture
    def emit(self):
        return AsyncMock()

    async def test_execute_tools_blocked_returns_error_json(self, runner, emit):
        runner.plan_ctrl._state = PlanState.awaiting_approval
        runner.registry.execute = AsyncMock(return_value='{"ok": true}')

        from app.agent.runner import ToolContext
        ctx = ToolContext("/tmp")
        tool_calls = [
            {
                "id": "call_1",
                "function": {
                    "name": "f_write",
                    "arguments": json.dumps({"path": "/tmp/test", "content": "hello"}),
                },
            }
        ]
        messages: list[dict] = []
        results = []
        async for msg in runner._execute_tools(tool_calls, ctx, messages, 0, emit):
            results.append(msg)

        assert emit.called
        pass
        notice_calls = [c for c in emit.call_args_list
                        if c[0][0].get("type") == "notice"]
        assert len(notice_calls) >= 1
        assert "拦下" in notice_calls[0][0][0]["text"]

        pass
        tool_end_calls = [c for c in emit.call_args_list
                          if c[0][0].get("type") == "tool_end"]
        assert len(tool_end_calls) >= 1
        result = tool_end_calls[0][0][0]["result"]
        assert "plan_blocked" in result

    async def test_execute_tools_not_blocked_runs_normally(self, runner, emit):
        runner.plan_ctrl._state = PlanState.idle

        from app.agent.runner import ToolContext
        ctx = ToolContext("/tmp")

        pass
        runner.registry.execute = AsyncMock(return_value="success")

        tool_calls = [
            {
                "id": "call_1",
                "function": {
                    "name": "f_write",
                    "arguments": json.dumps({"path": "/tmp/test", "content": "hello"}),
                },
            }
        ]
        messages: list[dict] = []
        results = []
        async for msg in runner._execute_tools(tool_calls, ctx, messages, 0, emit):
            results.append(msg)

        assert runner.registry.execute.called
        assert len(results) == 1
        assert results[0]["content"] == "success"


pass
pass
pass
class TestFinishPlanRound:
    @pytest.fixture
    def runner(self):
        gateway = MagicMock()
        registry = MagicMock()
        r = AgentRunner(gateway, registry)
        r._plan_blocked = False
        return r

    @pytest.fixture
    def emit(self):
        return AsyncMock()

    async def test_blocked_round_publishes_plan_ready(self, runner, emit):
        runner.plan_ctrl._state = PlanState.planning
        runner._plan_blocked = True
        await runner._finish_plan_round("## 📋 实施计划\n| 步骤 | ... |", "", emit)
        assert runner.plan_ctrl.state == PlanState.awaiting_approval
        assert runner.plan_ctrl.plan_text.startswith("## 📋")
        kinds = [c[0][0].get("type") for c in emit.call_args_list]
        assert "plan_ready" in kinds

    async def test_readonly_round_does_not_bother_user(self, runner, emit):
        runner.plan_ctrl._state = PlanState.planning
        runner._plan_blocked = False
        await runner._finish_plan_round("这个函数是这么用的……", "", emit)
        assert runner.plan_ctrl.state == PlanState.idle
        assert not emit.called

    async def test_executing_round_is_noop(self, runner, emit):
        runner.plan_ctrl._state = PlanState.executing
        runner._plan_blocked = True
        await runner._finish_plan_round("改完了", "", emit)
        assert runner.plan_ctrl.state == PlanState.executing
        assert not emit.called


class TestReadOnlyBlocksFromPlanning:

    @pytest.fixture
    def runner(self):
        r = AgentRunner(MagicMock(), MagicMock())
        r._plan_blocked = False
        r._plan_notice_sent = False
        return r

    async def test_planning_state_blocks_f_write(self):
        from app.agent.runner import ToolContext

        r = AgentRunner(MagicMock(), MagicMock())
        r._plan_blocked = False
        r._plan_notice_sent = False
        r.plan_ctrl._state = PlanState.planning
        r.registry.execute = AsyncMock(return_value="written")
        emit = AsyncMock()
        calls = [{"id": "c1", "function": {
            "name": "f_write",
            "arguments": json.dumps({"path": "/tmp/a", "content": "x"})}}]
        out = []
        async for msg in r._execute_tools(calls, ToolContext("/tmp"), [], 0, emit):
            out.append(msg)
        assert "plan_blocked" in out[0]["content"]
        assert r.registry.execute.called is False
        assert r._plan_blocked is True

    async def test_planning_state_allows_read_tools(self):
        from app.agent.runner import ToolContext

        r = AgentRunner(MagicMock(), MagicMock())
        r._plan_blocked = False
        r._plan_notice_sent = False
        r.plan_ctrl._state = PlanState.planning
        r.registry.execute = AsyncMock(return_value="file body")
        emit = AsyncMock()
        calls = [{"id": "c1", "function": {
            "name": "f_read",
            "arguments": json.dumps({"path": "/tmp/a"})}}]
        out = []
        async for msg in r._execute_tools(calls, ToolContext("/tmp"), [], 0, emit):
            out.append(msg)
        assert out[0]["content"] == "file body"
        assert r._plan_blocked is False


pass
pass
pass
class TestPlanSessionIsolation:
    def test_plan_for_returns_distinct_controllers(self):
        from app.agent.runner import AgentRunner

        r = AgentRunner(MagicMock(), MagicMock())
        a, b = r.plan_for("s1"), r.plan_for("s2")
        a.enter_planning("s1")
        assert b.state == PlanState.idle
        assert r.plan_for("s1") is a

    def test_run_binds_session_plan(self):
        from app.agent.runner import AgentRunner

        r = AgentRunner(MagicMock(), MagicMock())
        default = r.plan_ctrl
        tokens = r.bind_plan("s9")
        try:
            assert r.plan_ctrl is r.plan_for("s9")
            assert r.plan_ctrl is not default
        finally:
            r.unbind_plan(tokens)
        assert r.plan_ctrl is default

    async def test_concurrent_tasks_do_not_share_state(self):
        from app.agent.runner import AgentRunner
        import asyncio as _aio

        r = AgentRunner(MagicMock(), MagicMock())

        async def one(sid):
            tokens = r.bind_plan(sid)
            try:
                r.plan_ctrl.enter_planning(sid)
                r._plan_blocked = True
                await _aio.sleep(0)
                return (r.plan_ctrl.state, r._plan_blocked, id(r.plan_ctrl))
            finally:
                r.unbind_plan(tokens)

        async def quiet(sid):
            tokens = r.bind_plan(sid)
            try:
                await _aio.sleep(0)
                return (r.plan_ctrl.state, r._plan_blocked)
            finally:
                r.unbind_plan(tokens)

        busy, clean = await _aio.gather(one("a"), quiet("b"))
        assert busy[0] == PlanState.planning and busy[1] is True
        assert clean[0] == PlanState.idle and clean[1] is False

    def test_escalation_flags_are_per_round(self):
        from app.agent.runner import AgentRunner

        r = AgentRunner(MagicMock(), MagicMock())
        r._plan_blocked = True
        r._escalation["files"].add("/a.py")
        tokens = r.bind_plan("fresh")
        try:
            assert r._plan_blocked is False
            assert r._escalation["files"] == set()
        finally:
            r.unbind_plan(tokens)


class TestPlanTextTriggersCard:

    @pytest.fixture
    def runner(self):
        r = AgentRunner(MagicMock(), MagicMock())
        r._plan_blocked = False
        r._plan_notice_sent = False
        return r

    async def test_plan_text_triggers_plan_ready(self, runner):
        runner.plan_ctrl._state = PlanState.planning
        emit = AsyncMock()
        await runner._finish_plan_round("## 📋 实施计划\n1. 新建目录", "", emit)
        assert runner.plan_ctrl.state == PlanState.awaiting_approval
        assert any(c[0][0].get("type") == "plan_ready" for c in emit.call_args_list)

    async def test_plain_answer_resets(self, runner):
        runner.plan_ctrl._state = PlanState.planning
        emit = AsyncMock()
        await runner._finish_plan_round("这个函数返回布尔值。", "", emit)
        assert runner.plan_ctrl.state == PlanState.idle
        assert not emit.called


pass
pass
pass
class TestReadonlyActionsInPlanMode:
    @pytest.fixture
    def runner(self):
        r = AgentRunner(MagicMock(), MagicMock())
        r._plan_blocked = False
        r._plan_notice_sent = False
        r.plan_ctrl._state = PlanState.planning
        return r

    async def test_workflow_list_allowed(self, runner):
        emit = AsyncMock()
        for act in ("help", "list", "get", "list_node"):
            blocked = await runner._check_plan_block(
                "workflow", {"action": act, "name": "x"}, emit)
            assert blocked is False, act

    async def test_workflow_save_blocked(self, runner):
        emit = AsyncMock()
        for act in ("save", "add_node", "edit_node", "del_node", "run"):
            blocked = await runner._check_plan_block(
                "workflow", {"action": act, "name": "x"}, emit)
            assert blocked is True, act

    async def test_table_inspect_allowed_rows_query(self, runner):
        emit = AsyncMock()
        assert await runner._check_plan_block(
            "table", {"action": "inspect", "path": "a.xlsx"}, emit) is False
        assert await runner._check_plan_block(
            "table", {"action": "query", "path": "a.db"}, emit) is False

    async def test_readonly_probe_command_allowed(self, runner):
        emit = AsyncMock()
        blocked = await runner._check_plan_block(
            "run_command",
            {"command": "ls -la; ls docs 2>/dev/null | head -30"}, emit)
        assert blocked is False

    async def test_destructive_command_blocked(self, runner):
        emit = AsyncMock()
        blocked = await runner._check_plan_block(
            "run_command", {"command": "rm -rf build"}, emit)
        assert blocked is True
