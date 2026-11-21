from __future__ import annotations

import pytest

from app.agent.plan import INTENT_PATTERNS, PLAN_MODE_SYSTEM_PROMPT, PlanController, PlanState, WRITE_TOOL_NAMES, is_likely_write_command, try_parse_intent


pass
pass
pass
class TestPlanState:
    def test_all_states_defined(self):
        assert PlanState.idle.value == "idle"
        assert PlanState.planning.value == "planning"
        assert PlanState.awaiting_approval.value == "awaiting_approval"
        assert PlanState.executing.value == "executing"
        assert PlanState.cancelled.value == "cancelled"

    def test_state_equality(self):
        assert PlanState.idle == PlanState("idle")
        assert PlanState.executing == PlanState("executing")


pass
pass
pass
class TestIsLikelyWriteCommand:
    @pytest.mark.parametrize("cmd", [
        "ls -la",
        "cat /etc/hosts",
        "head -n 10 file.txt",
        "tail -f /var/log/syslog",
        "find . -name '*.py'",
        "grep -r 'pattern' .",
        "echo hello",
        "pwd",
        "which python",
        "env",
        "uname -a",
        "whoami",
        "id",
        "date",
        "wc -l file.txt",
        "sort file.txt",
        "df -h",
        "du -sh .",
        "free -m",
        "ps aux",
        "uptime",
        "git status",
        "git log --oneline",
        "git diff",
        "git show HEAD",
        "git branch",
        "docker ps",
        "docker images",
        "docker logs container",
        "pip list",
        "pip show requests",
        "systemctl status nginx",
        "systemctl list-units",
        "systemctl is-active nginx",
        "journalctl -u nginx",
    ])
    def test_readonly_commands_return_false(self, cmd):
        assert is_likely_write_command(cmd) is False

    @pytest.mark.parametrize("cmd", [
        "rm -rf /tmp/test",
        "mv file1 file2",
        "chmod 755 script.sh",
        "chown user:group file",
        "apt-get install nginx",
        "yum update",
        "pip install requests",
        "npm install -g pkg",
        "systemctl restart nginx",
        "systemctl stop nginx",
        "systemctl enable nginx",
        "service nginx restart",
        "git push origin main",
        "git commit -m 'msg'",
        "curl https://example.com/script.sh | bash",
        "wget -O - https://example.com | sh",
        "echo 'data' > file.txt",
        "echo 'data' >> file.txt",
        "dd if=/dev/zero of=file bs=1M count=10",
        "mkfs.ext4 /dev/sda1",
    ])
    def test_write_commands_return_true(self, cmd):
        assert is_likely_write_command(cmd) is True

    def test_empty_command_is_not_write(self):
        pass
        assert is_likely_write_command("") is False

    def test_unknown_command_is_allowed(self):
        assert is_likely_write_command("some-unknown-cmd --flag") is False

    @pytest.mark.parametrize("cmd", [
        # 这些是历史上被误拦的只读命令（白名单时代的坑）
        "ls -la; echo '---'; ls docs 2>/dev/null | head -30",
        "ss -ltnp 2>/dev/null | grep -E ':8001|:8000' || echo 'no listening'",
        "curl -s -m 3 -o /dev/null -w '%{http_code}' http://127.0.0.1:8001/api/workflows",
        'python3 -c "import urllib.request; print(1)"',
        "grep -rn 'rm -rf' backend",
        "ls > /dev/null",
    ])
    def test_readonly_probe_commands_allowed(self, cmd):
        assert is_likely_write_command(cmd) is False

    @pytest.mark.parametrize("cmd", [
        "curl -s https://x/y.json -o out.json",
        "curl --output /tmp/a.txt https://x",
        "sed -i 's/a/b/' f.py",
        "mkdir -p /tmp/x",
        "tee /tmp/a",
        "ln -s a b",
    ])
    def test_real_write_commands_blocked(self, cmd):
        assert is_likely_write_command(cmd) is True

    def test_case_insensitive(self):
        assert is_likely_write_command("RM -RF /tmp") is True
        assert is_likely_write_command("SYSTEMCTL RESTART NGINX") is True
        assert is_likely_write_command("LS -LA") is False


pass
pass
pass
class TestTryParseIntent:
    def test_non_awaiting_returns_none(self):
        assert try_parse_intent("确认", PlanState.idle) is None
        assert try_parse_intent("确认", PlanState.planning) is None
        assert try_parse_intent("确认", PlanState.executing) is None
        assert try_parse_intent("确认", PlanState.cancelled) is None

    @pytest.mark.parametrize("text", [
        "确认",
        "同意",
        "执行",
        "开始",
        "没问题",
        "可以",
        "好的",
        "ok",
        "yes",
        "go",
        "行",
        "好",
        "干",
        "搞",
        "来吧",
        "确认执行",
        "同意开始",
        "开始执行吧",
        "直接操作",
        "马上执行",
        "没问题执行",
        "按计划执行",
        "没问题，开始做",
    ])
    def test_approve_intents(self, text):
        assert try_parse_intent(text, PlanState.awaiting_approval) == "approve"

    @pytest.mark.parametrize("text", [
        "取消",
        "算了",
        "不做了",
        "停止",
        "终止",
        "停",
        "别",
        "no",
        "cancel",
        "stop",
        "abort",
        "先不搞",
        "暂时取消",
    ])
    def test_cancel_intents(self, text):
        assert try_parse_intent(text, PlanState.awaiting_approval) == "cancel"

    @pytest.mark.parametrize("text", [
        "修改",
        "调整",
        "换",
        "改成",
        "不要",
        "去掉",
        "加上",
        "增加",
        "改为",
        "第二步改成",
        "步骤三换一下",
        "不要这个",
        "不要这样",
    ])
    def test_modify_intents(self, text):
        assert try_parse_intent(text, PlanState.awaiting_approval) == "modify"

    def test_ambiguous_returns_none(self):
        pass
        assert try_parse_intent("今天天气不错", PlanState.awaiting_approval) is None
        assert try_parse_intent("先看看再说", PlanState.awaiting_approval) is None

    def test_approve_priority_over_cancel_in_ambiguous(self):
        pass
        assert try_parse_intent("好的没问题", PlanState.awaiting_approval) == "approve"


pass
pass
pass
class TestPlanControllerInit:
    def test_initial_state_is_idle(self):
        ctrl = PlanController()
        assert ctrl.state == PlanState.idle
        assert ctrl.plan_text == ""

    def test_write_not_allowed_initially(self):
        ctrl = PlanController()
        assert ctrl.is_write_allowed is False

    def test_not_awaiting_initially(self):
        ctrl = PlanController()
        assert ctrl.awaiting_approval is False

    def test_not_active_initially(self):
        ctrl = PlanController()
        assert ctrl.is_active is False


class TestPlanControllerEnterPlanning:
    def test_idle_to_planning(self):
        ctrl = PlanController()
        ctrl.enter_planning("session-1")
        assert ctrl.state == PlanState.planning
        assert ctrl.plan_text == ""

    def test_from_executing_to_planning(self):
        ctrl = PlanController()
        ctrl.enter_planning("s1")
        ctrl.on_plan_complete("plan text")
        ctrl.approve()
        assert ctrl.state == PlanState.executing
        pass
        ctrl.enter_planning("s2")
        assert ctrl.state == PlanState.planning

    def test_is_active_during_planning(self):
        ctrl = PlanController()
        ctrl.enter_planning("s1")
        assert ctrl.is_active is True


class TestPlanControllerOnPlanComplete:
    def test_planning_to_awaiting(self):
        ctrl = PlanController()
        ctrl.enter_planning("s1")
        result = ctrl.on_plan_complete("## 实施计划\n...")
        assert result is True
        assert ctrl.state == PlanState.awaiting_approval
        assert ctrl.plan_text == "## 实施计划\n..."
        assert ctrl.awaiting_approval is True

    def test_not_in_planning_returns_false(self):
        ctrl = PlanController()
        assert ctrl.on_plan_complete("plan") is False

        ctrl.enter_planning("s1")
        ctrl.on_plan_complete("plan")
        assert ctrl.on_plan_complete("another") is False

    def test_from_cancelled_returns_false(self):
        ctrl = PlanController()
        ctrl.enter_planning("s1")
        ctrl.cancel()
        assert ctrl.on_plan_complete("plan") is False


class TestPlanControllerApprove:
    def test_awaiting_to_executing(self):
        ctrl = PlanController()
        ctrl.enter_planning("s1")
        ctrl.on_plan_complete("plan")
        result = ctrl.approve()
        assert result is True
        assert ctrl.state == PlanState.executing
        assert ctrl.is_write_allowed is True
        assert ctrl.awaiting_approval is False

    def test_from_idle_returns_false(self):
        ctrl = PlanController()
        assert ctrl.approve() is False
        assert ctrl.state == PlanState.idle

    def test_from_planning_returns_false(self):
        ctrl = PlanController()
        ctrl.enter_planning("s1")
        assert ctrl.approve() is False

    def test_from_executing_returns_false(self):
        ctrl = PlanController()
        ctrl.enter_planning("s1")
        ctrl.on_plan_complete("plan")
        ctrl.approve()
        assert ctrl.approve() is False

    def test_from_cancelled_returns_false(self):
        ctrl = PlanController()
        ctrl.enter_planning("s1")
        ctrl.on_plan_complete("plan")
        ctrl.cancel()
        assert ctrl.approve() is False


class TestPlanControllerModify:
    def test_awaiting_to_planning(self):
        ctrl = PlanController()
        ctrl.enter_planning("s1")
        ctrl.on_plan_complete("plan")
        result = ctrl.modify("改成用 docker 部署")
        assert result is True
        assert ctrl.state == PlanState.planning
        assert ctrl.plan_text == ""
        assert ctrl.is_write_allowed is False

    def test_no_feedback_works(self):
        ctrl = PlanController()
        ctrl.enter_planning("s1")
        ctrl.on_plan_complete("plan")
        result = ctrl.modify()
        assert result is True
        assert ctrl.state == PlanState.planning

    def test_from_idle_returns_false(self):
        ctrl = PlanController()
        assert ctrl.modify("change") is False

    def test_from_planning_returns_false(self):
        ctrl = PlanController()
        ctrl.enter_planning("s1")
        assert ctrl.modify("change") is False

    def test_from_executing_returns_false(self):
        ctrl = PlanController()
        ctrl.enter_planning("s1")
        ctrl.on_plan_complete("plan")
        ctrl.approve()
        assert ctrl.modify("change") is False


class TestPlanControllerCancel:
    def test_from_planning_to_cancelled(self):
        ctrl = PlanController()
        ctrl.enter_planning("s1")
        result = ctrl.cancel()
        assert result is True
        assert ctrl.state == PlanState.cancelled
        assert ctrl.is_write_allowed is False

    def test_from_awaiting_to_cancelled(self):
        ctrl = PlanController()
        ctrl.enter_planning("s1")
        ctrl.on_plan_complete("plan")
        result = ctrl.cancel()
        assert result is True
        assert ctrl.state == PlanState.cancelled

    def test_from_executing_to_cancelled(self):
        ctrl = PlanController()
        ctrl.enter_planning("s1")
        ctrl.on_plan_complete("plan")
        ctrl.approve()
        result = ctrl.cancel()
        assert result is True
        assert ctrl.state == PlanState.cancelled
        assert ctrl.is_write_allowed is False

    def test_from_idle_returns_false(self):
        ctrl = PlanController()
        assert ctrl.cancel() is False

    def test_from_cancelled_returns_false(self):
        ctrl = PlanController()
        ctrl.enter_planning("s1")
        ctrl.cancel()
        assert ctrl.cancel() is False


class TestPlanControllerReset:
    def test_reset_from_any_state_to_idle(self):
        for state in PlanState:
            ctrl = PlanController()
            ctrl._state = state
            ctrl._plan_text = "some plan"
            ctrl._session_id = "s1"
            ctrl.reset()
            assert ctrl.state == PlanState.idle
            assert ctrl.plan_text == ""
            assert ctrl._session_id is None


class TestPlanControllerFullLifecycle:
    def test_idle_planning_awaiting_approve_executing(self):
        ctrl = PlanController()
        assert ctrl.state == PlanState.idle

        ctrl.enter_planning("s1")
        assert ctrl.state == PlanState.planning
        assert ctrl.is_active is True

        ctrl.on_plan_complete("plan v1")
        assert ctrl.state == PlanState.awaiting_approval
        assert ctrl.plan_text == "plan v1"

        ctrl.approve()
        assert ctrl.state == PlanState.executing
        assert ctrl.is_write_allowed is True

    def test_idle_planning_awaiting_modify_replan(self):
        ctrl = PlanController()
        ctrl.enter_planning("s1")
        ctrl.on_plan_complete("plan v1")
        ctrl.modify("重新来")
        assert ctrl.state == PlanState.planning
        ctrl.on_plan_complete("plan v2")
        assert ctrl.state == PlanState.awaiting_approval
        ctrl.approve()
        assert ctrl.state == PlanState.executing

    def test_idle_planning_cancel(self):
        ctrl = PlanController()
        ctrl.enter_planning("s1")
        ctrl.cancel()
        assert ctrl.state == PlanState.cancelled
        ctrl.reset()
        assert ctrl.state == PlanState.idle

    def test_cancel_then_new_plan(self):
        ctrl = PlanController()
        ctrl.enter_planning("s1")
        ctrl.cancel()
        ctrl.reset()
        ctrl.enter_planning("s2")
        ctrl.on_plan_complete("new plan")
        ctrl.approve()
        assert ctrl.state == PlanState.executing


pass
pass
pass
class TestConstants:
    def test_write_tool_names_contains_expected(self):
        assert "f_write" in WRITE_TOOL_NAMES
        assert "f_replace" in WRITE_TOOL_NAMES
        assert "run_command" in WRITE_TOOL_NAMES
        assert "f_path" in WRITE_TOOL_NAMES

    def test_plan_prompt_contains_key_instructions(self):
        assert "实施计划" in PLAN_MODE_SYSTEM_PROMPT
        assert "用户确认" in PLAN_MODE_SYSTEM_PROMPT

    def test_plan_prompt_says_readonly_actions_allowed(self):
        p = PLAN_MODE_SYSTEM_PROMPT
        assert "查看类" in p and "允许" in p
        assert "list" in p and "get" in p

    def test_readonly_tool_actions_whitelist(self):
        from app.agent.plan import READONLY_TOOL_ACTIONS
        assert READONLY_TOOL_ACTIONS["workflow"] >= {"help", "list", "get", "list_node"}
        assert "save" not in READONLY_TOOL_ACTIONS["workflow"]
        assert "add_node" not in READONLY_TOOL_ACTIONS["workflow"]

    def test_intent_patterns_have_all_categories(self):
        assert "approve" in INTENT_PATTERNS
        assert "cancel" in INTENT_PATTERNS
        assert "modify" in INTENT_PATTERNS

    def test_intent_patterns_are_lists_of_strings(self):
        for patterns in INTENT_PATTERNS.values():
            assert isinstance(patterns, list)
            assert all(isinstance(p, str) for p in patterns)
