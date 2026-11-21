from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.config import Settings
from app.security.engine import ApprovalManager, Decision, PolicyEngine, Risk, Verdict, build_file_hunks
from app.security.wiring import wire_policy
from app.tools import ToolContext

CWD = "/tmp/proj"


pass


class _FakeGateway:

    def __init__(self, policy: str = "yolo", text: str = "", exc: Exception | None = None,
                 deny=None, allow=None):
        self.config = SimpleNamespace(settings=Settings(
            policy=policy,
            commandDenyPatterns=deny or [],
            commandAllowPatterns=allow or [],
        ))
        self._text = text
        self._exc = exc
        self.calls: list[tuple] = []

    async def call_utility(self, kind, messages):
        self.calls.append((kind, messages))
        if self._exc:
            raise self._exc
        return self._text


class _GwNoUtility:

    def __init__(self, policy: str = "review"):
        self.config = SimpleNamespace(settings=Settings(policy=policy))


class _Approvals:

    def __init__(self, approve: bool = True, hunks: list[int] | None = None):
        self.approve = approve
        self.hunks = hunks
        self.created: list[SimpleNamespace] = []
        self.waited = 0

    def create(self, command, risks, reason, session_id="", kind="command",
               file_diff=None):
        pa = SimpleNamespace(id=f"ap{len(self.created) + 1}", command=command,
                             risks=list(risks or []), reason=reason, kind=kind,
                             file_diff=file_diff, approved_hunks=self.hunks)
        self.created.append(pa)
        return pa

    async def wait(self, pa, stop_check=None):
        self.waited += 1
        return self.approve


def _emit_collector():
    events: list[dict] = []

    async def _emit(ev: dict) -> None:
        events.append(ev)

    return _emit, events


def _wire(policy=None, approvals=None, gateway=None, messages=None, mode=None):
    ctx = ToolContext(CWD)
    emit, events = _emit_collector()
    old = None
    if mode is not None:
        import app.security.project_mode as pp
        old = pp.mode_for_cwd
        pp.mode_for_cwd = lambda cwd: mode
    try:
        wire_policy(ctx, CWD, emit, messages if messages is not None else
                    [{"role": "user", "content": "改一下配置"}],
                    policy, approvals, gateway or _FakeGateway())
    finally:
        if old is not None:
            import app.security.project_mode as pp
            pp.mode_for_cwd = old
    return ctx, events


pass


def test_policy_none_leaves_context_untouched():
    ctx, _ = _wire(policy=None)
    assert ctx.policy_check is None
    assert ctx.request_approval is None
    assert ctx.request_file_approval is None


def test_policy_injected():
    ctx, _ = _wire(policy=PolicyEngine())
    assert callable(ctx.policy_check)
    assert callable(ctx.request_approval)
    assert callable(ctx.request_file_approval)


def test_settings_without_policy_field_defaults_to_yolo():
    gw = SimpleNamespace(config=SimpleNamespace(settings=SimpleNamespace()))
    ctx, _ = _wire(policy=PolicyEngine(), gateway=gw)
    assert callable(ctx.policy_check)


async def test_missing_pattern_settings_are_tolerated():
    gw = SimpleNamespace(config=SimpleNamespace(settings=SimpleNamespace(policy="yolo")))
    policy = MagicMock()
    policy.check.return_value = Verdict(Decision.ALLOW)
    ctx, _ = _wire(policy=policy, gateway=gw)
    await ctx.policy_check("ls")
    kwargs = policy.check.call_args.kwargs
    assert kwargs["deny_patterns"] == [] and kwargs["allow_patterns"] == []


pass


async def test_policy_check_passes_through_allow():
    ctx, _ = _wire(policy=PolicyEngine())
    v = await ctx.policy_check("ls -la")
    assert v.decision in (Decision.ALLOW, Decision.REVIEW)


async def test_policy_check_denies_dangerous_command():
    ctx, _ = _wire(policy=PolicyEngine())
    v = await ctx.policy_check("sudo rm -rf /")
    assert v.decision == Decision.DENY
    assert v.risks


async def test_policy_check_uses_cwd_and_mode_from_settings():
    policy = MagicMock()
    policy.check.return_value = Verdict(Decision.ALLOW)
    ctx, _ = _wire(policy=policy, gateway=_FakeGateway(policy="workspace",
                                                       deny=["^bad"], allow=["^ok"]))
    await ctx.policy_check("ok cmd")
    args, kwargs = policy.check.call_args
    assert args[0] == "ok cmd"
    assert args[1] == CWD
    assert args[2] == "workspace"
    assert kwargs["deny_patterns"] == ["^bad"]
    assert kwargs["allow_patterns"] == ["^ok"]


async def test_policy_check_ai_review_only_in_review_mode():
    review_verdict = Verdict(Decision.REVIEW, [Risk(target="x", description="边界")], "需要复核")
    ai_verdict = Verdict(Decision.ALLOW, reason="AI 认为安全")
    policy = MagicMock()
    policy.check.return_value = review_verdict
    policy.ai_review = AsyncMock(return_value=ai_verdict)

    ctx, _ = _wire(policy=policy, gateway=_FakeGateway(policy="review"), mode="review")
    got = await ctx.policy_check("cat /etc/passwd")
    assert got is ai_verdict
    policy.ai_review.assert_awaited_once()
    args = policy.ai_review.call_args.args
    assert args[:2] == ("cat /etc/passwd", CWD)
    assert args[2] == "改一下配置"


async def test_policy_check_ai_review_runs_in_workspace_mode_too():
    policy = MagicMock()
    policy.check.return_value = Verdict(Decision.REVIEW, reason="越界")
    policy.ai_review = AsyncMock(
        return_value=Verdict(Decision.ALLOW, reason="AI 评审通过"))
    ctx, _ = _wire(policy=policy, gateway=_FakeGateway(policy="workspace"), mode="workspace")
    v = await ctx.policy_check("cat /etc/passwd")
    assert v.decision == Decision.ALLOW
    policy.ai_review.assert_awaited_once()


async def test_policy_check_ai_block_keeps_review():
    policy = MagicMock()
    policy.check.return_value = Verdict(Decision.REVIEW, reason="越界")
    policy.ai_review = AsyncMock(
        return_value=Verdict(Decision.REVIEW, reason="AI 认为有风险"))
    ctx, _ = _wire(policy=policy, gateway=_FakeGateway(policy="workspace"), mode="workspace")
    v = await ctx.policy_check("cat /etc/passwd")
    assert v.decision == Decision.REVIEW


async def test_policy_check_deny_skips_ai_review():
    policy = MagicMock()
    policy.check.return_value = Verdict(Decision.DENY, reason="高危")
    policy.ai_review = AsyncMock()
    ctx, _ = _wire(policy=policy, gateway=_FakeGateway(policy="review"), mode="review")
    v = await ctx.policy_check("sudo x")
    assert v.decision == Decision.DENY
    policy.ai_review.assert_not_awaited()


async def test_intent_ignores_non_string_content():
    policy = MagicMock()
    policy.check.return_value = Verdict(Decision.REVIEW)
    policy.ai_review = AsyncMock(return_value=Verdict(Decision.ALLOW))
    ctx, _ = _wire(policy=policy, gateway=_FakeGateway(policy="review"), messages=[
        {"role": "user", "content": "早先的需求"},
        {"role": "assistant", "content": "好的"},
        {"role": "user", "content": [{"type": "text", "text": "看图"}]},
    ])
    await ctx.policy_check("rm x")
    assert policy.ai_review.call_args.args[2] == "早先的需求"


async def test_intent_empty_when_no_user_message():
    policy = MagicMock()
    policy.check.return_value = Verdict(Decision.REVIEW)
    policy.ai_review = AsyncMock(return_value=Verdict(Decision.ALLOW))
    ctx, _ = _wire(policy=policy, gateway=_FakeGateway(policy="review"),
                   messages=[{"role": "assistant", "content": "hi"}])
    await ctx.policy_check("rm x")
    assert policy.ai_review.call_args.args[2] == ""


pass


async def test_request_approval_without_manager_returns_false():
    ctx, events = _wire(policy=PolicyEngine(), approvals=None)
    ok = await ctx.request_approval("rm -rf build", Verdict(Decision.REVIEW))
    assert ok is False
    assert events == []


async def test_request_approval_approved_emits_events():
    approvals = _Approvals(approve=True)
    ctx, events = _wire(policy=PolicyEngine(), approvals=approvals)
    verdict = Verdict(Decision.REVIEW, [Risk(target="/p/a", description="覆盖文件",
                                             severity="high")], "需要确认")
    ok = await ctx.request_approval("rm -rf build", verdict)
    assert ok is True
    assert approvals.waited == 1
    assert [e["type"] for e in events] == ["approval_request", "approval_done"]
    req, done = events
    assert req["command"] == "rm -rf build"
    assert req["reason"] == "需要确认"
    assert req["risks"] == [{"target": "/p/a", "description": "覆盖文件",
                             "severity": "high"}]
    assert done["approved"] is True and done["id"] == req["id"]


async def test_request_approval_rejected():
    approvals = _Approvals(approve=False)
    ctx, events = _wire(policy=PolicyEngine(), approvals=approvals)
    ok = await ctx.request_approval("rm x", Verdict(Decision.REVIEW))
    assert ok is False
    assert events[-1] == {"type": "approval_done", "id": "ap1", "approved": False}


pass


async def test_file_approval_without_manager_auto_passes():
    ctx, events = _wire(policy=PolicyEngine(), approvals=None)
    ok, hunks = await ctx.request_file_approval("写文件", "/p/a.txt", "a", "b")
    assert (ok, hunks) == (True, None)
    assert events == []


async def test_file_approval_yolo_does_not_bother():
    approvals = _Approvals()
    ctx, events = _wire(policy=PolicyEngine(), approvals=approvals,
                        gateway=_FakeGateway(), mode="yolo")
    ok, hunks = await ctx.request_file_approval("写文件", "/p/a.txt", "a", "b")
    assert (ok, hunks) == (True, None)
    assert approvals.created == [] and events == []


async def test_file_approval_asks_hunks_in_workspace_mode():
    approvals = _Approvals(approve=True, hunks=[0])
    gw = _FakeGateway()
    ctx, events = _wire(policy=PolicyEngine(), approvals=approvals, gateway=gw,
                        mode="workspace")
    ok, hunks = await ctx.request_file_approval(
        "改配置", "/p/config.json", '{"a":1}', '{"a":2}', "调整参数")
    assert ok is True and hunks == [0]
    assert gw.calls == []
    pa = approvals.created[0]
    assert pa.kind == "file" and pa.file_diff["path"] == "/p/config.json"
    assert [e["type"] for e in events] == ["approval_request", "approval_done"]
    req = events[0]
    assert req["kind"] == "file"
    assert req["risks"][0]["description"] == "调整参数"
    assert req["file_diff"]["hunks"]


async def test_file_approval_human_rejects():
    approvals = _Approvals(approve=False)
    ctx, events = _wire(policy=PolicyEngine(), approvals=approvals,
                        gateway=_FakeGateway(), mode="review")
    ok, hunks = await ctx.request_file_approval("改", "/p/a", "a", "b")
    assert (ok, hunks) == (False, None)
    assert events[-1]["approved"] is False


async def test_file_approval_without_manager_passes():
    ctx, _ = _wire(policy=PolicyEngine(), approvals=None, gateway=_FakeGateway(),
                   mode="review")
    ok, hunks = await ctx.request_file_approval("改", "/p/a", "a", "b")
    assert (ok, hunks) == (True, None)


async def test_file_approval_without_reason_uses_default():
    approvals = _Approvals(approve=True)
    ctx, _ = _wire(policy=PolicyEngine(), approvals=approvals,
                   gateway=_FakeGateway(), mode="workspace")
    await ctx.request_file_approval("改文件", "/p/a", "a", "b")
    assert approvals.created[0].reason == "文件修改"


pass


async def test_approval_manager_end_to_end():
    import asyncio

    mgr = ApprovalManager()
    ctx, events = _wire(policy=PolicyEngine(), approvals=mgr)
    verdict = Verdict(Decision.REVIEW, [Risk(target="/p", description="删除")], "确认")

    async def _decide_soon():
        while not mgr._pending:
            await asyncio.sleep(0.01)
        pid = next(iter(mgr._pending))
        mgr.decide(pid, True, hunks=[1])

    task = asyncio.create_task(_decide_soon())
    ok = await ctx.request_approval("rm -rf /p", verdict)
    await task
    assert ok is True
    assert events[0]["type"] == "approval_request"
    assert mgr.list() == []


async def test_file_hunks_are_stable_shape():
    hunks = build_file_hunks("a\nb\nc", "a\nB\nc")
    assert hunks and set(hunks[0]) >= {"id", "tag", "old", "new"}


async def test_extra_safe_paths_skip_file_approval(tmp_path):
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    target = scratch / "a.txt"
    target.write_text("x")
    proj = tmp_path / "proj"
    proj.mkdir()

    gw = _FakeGateway(policy="workspace")
    gw.config.settings.policyExtraSafePaths = [str(scratch)]
    approvals = _Approvals(approve=False)
    ctx = ToolContext(str(proj))
    emit, _events = _emit_collector()
    import app.security.project_mode as pp
    old = pp.mode_for_cwd
    pp.mode_for_cwd = lambda cwd: "workspace"
    try:
        wire_policy(ctx, str(proj), emit, [], PolicyEngine(gateway=gw), approvals, gw)
    finally:
        pp.mode_for_cwd = old

    allowed, _hunks = await ctx.request_file_approval(
        "改文件", str(target), "old", "new", "改一下")
    assert allowed is True
    assert approvals.created == []
