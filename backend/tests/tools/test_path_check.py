from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.security.engine import Decision, PolicyEngine, Verdict
from app.security.wiring import wire_policy
from app.tools import ToolContext


class _Settings:
    policy = "workspace"
    commandDenyPatterns: list[str] = []
    commandAllowPatterns: list[str] = []


class _Gw:
    def __init__(self, pass_=True):
        self.pass_ = pass_
        self.calls: list = []

    class config:
        settings = _Settings()

    async def call_utility(self, kind, messages):
        self.calls.append((kind, messages))
        return json.dumps({"verdict": "pass" if self.pass_ else "block",
                           "risks": []})


class _Approvals:
    def __init__(self, approve=True):
        self.approve = approve
        self.created: list = []

    def create(self, command, risks, reason, **kw):
        pa = MagicMock(id=f"ap{len(self.created)}", risks=risks,
                       approved_hunks=None)
        self.created.append((command, reason))
        return pa

    async def wait(self, pa, stop_check=None):
        return self.approve


def _wire(tmp_path, mode="workspace", gw=None, approvals=None):
    import app.security.project_mode as pp
    ctx = ToolContext(str(tmp_path))
    events: list = []

    async def emit(ev):
        events.append(ev)

    pe = PolicyEngine(gateway=gw if gw is not None else _Gw())
    old = pp.mode_for_cwd
    pp.mode_for_cwd = lambda cwd: mode
    try:
        wire_policy(ctx, str(tmp_path), emit,
                    [{"role": "user", "content": "改配置"}],
                    pe, approvals if approvals is not None else _Approvals(),
                    _gw_with_mode(mode))
    finally:
        pp.mode_for_cwd = old
    return ctx, events, pe


def _gw_with_mode(mode):
    class S:
        policy = mode
        commandDenyPatterns: list[str] = []
        commandAllowPatterns: list[str] = []
    gw = MagicMock()
    gw.config.settings = S()
    gw.call_utility = AsyncMock(
        return_value='{"verdict":"pass","risks":[]}')
    return gw


@pytest.fixture()
def proj(tmp_path):
    p = tmp_path / "proj"
    p.mkdir()
    return p


pass
async def test_inside_path_allowed(proj):
    ctx, events, _ = _wire(proj)
    ok, reason = await ctx.path_check("write", [str(proj / "a.txt")])
    assert ok is True and reason == ""
    assert events == []


async def test_inside_delete_allowed(proj):
    ctx, _, _ = _wire(proj)
    ok, _ = await ctx.path_check("delete", [str(proj / "old.txt")])
    assert ok is True


async def test_outside_passes_when_ai_says_ok(proj):
    gw = _gw_with_mode("workspace")
    gw.call_utility = AsyncMock(return_value='{"verdict":"pass","risks":[]}')
    approvals = _Approvals()
    ctx, events, _ = _wire(proj, gw=gw, approvals=approvals)
    ok, _ = await ctx.path_check("write", ["/var/data/elsewhere/x.txt"])
    assert ok is True
    assert approvals.created == []
    assert gw.call_utility.await_count == 1


async def test_outside_write_defers_approval_to_diff_layer(proj):
    gw = _gw_with_mode("workspace")
    gw.call_utility = AsyncMock(return_value='{"verdict":"block","risks":[]}')
    approvals = _Approvals(approve=True)
    ctx, events, _ = _wire(proj, gw=gw, approvals=approvals)
    ok, _ = await ctx.path_check("write", ["/var/data/elsewhere/x.txt"])
    assert ok is True
    assert approvals.created == []
    assert events == []


async def test_outside_delete_approves_here(proj):
    gw = _gw_with_mode("workspace")
    gw.call_utility = AsyncMock(return_value='{"verdict":"block","risks":[]}')
    approvals = _Approvals(approve=True)
    ctx, events, _ = _wire(proj, gw=gw, approvals=approvals)
    ok, _ = await ctx.path_check("delete", ["/var/data/elsewhere/x.txt"])
    assert ok is True
    assert len(approvals.created) == 1
    assert [e["type"] for e in events] == ["approval_request", "approval_done"]


async def test_outside_delete_user_rejects(proj):
    gw = _gw_with_mode("workspace")
    gw.call_utility = AsyncMock(return_value='{"verdict":"block","risks":[]}')
    ctx, _, _ = _wire(proj, gw=gw, approvals=_Approvals(approve=False))
    ok, reason = await ctx.path_check("delete", ["/var/data/elsewhere/x.txt"])
    assert ok is False and "拒绝" in reason


async def test_critical_path_denied_without_ai_call(proj):
    gw = _gw_with_mode("workspace")
    ctx, _, _ = _wire(proj, gw=gw)
    ok, reason = await ctx.path_check("write", ["/etc/passwd"])
    assert ok is False and "关键路径" in reason
    assert gw.call_utility.await_count == 0


async def test_ai_unavailable_goes_to_human(proj):
    gw = _gw_with_mode("workspace")
    gw.call_utility = AsyncMock(side_effect=RuntimeError("timeout"))
    approvals = _Approvals(approve=False)
    ctx, _, _ = _wire(proj, gw=gw, approvals=approvals)
    ok, _ = await ctx.path_check("delete", ["/var/data/elsewhere/x.txt"])
    assert ok is False
    assert len(approvals.created) == 1


pass
async def test_yolo_allows_outside_without_ai(proj):
    gw = _gw_with_mode("yolo")
    ctx, events, _ = _wire(proj, mode="yolo", gw=gw)
    ok, _ = await ctx.path_check("write", ["/var/data/elsewhere/x.txt"])
    assert ok is True
    assert gw.call_utility.await_count == 0
    assert events == []


async def test_yolo_still_denies_critical(proj):
    ctx, _, _ = _wire(proj, mode="yolo", gw=_gw_with_mode("yolo"))
    ok, _ = await ctx.path_check("write", ["/etc/passwd"])
    assert ok is False


async def test_review_mode_read_allowed_without_ai(proj):
    gw = _gw_with_mode("review")
    ctx, _, _ = _wire(proj, mode="review", gw=gw)
    ok, _ = await ctx.path_check("read", [str(proj / "a.txt")])
    assert ok is True
    assert gw.call_utility.await_count == 0


async def test_review_mode_write_inside_needs_ai(proj):
    gw = _gw_with_mode("review")
    gw.call_utility = AsyncMock(return_value='{"verdict":"pass","risks":[]}')
    ctx, _, _ = _wire(proj, mode="review", gw=gw)
    ok, _ = await ctx.path_check("write", [str(proj / "a.txt")])
    assert ok is True
    assert gw.call_utility.await_count == 1


pass
@pytest.mark.parametrize("mode,path,expected", [
    ("workspace", "inside", Decision.ALLOW),
    ("workspace", "outside", Decision.REVIEW),
    ("workspace", "critical", Decision.DENY),
    ("yolo", "inside", Decision.ALLOW),
    ("yolo", "outside", Decision.ALLOW),
    ("yolo", "critical", Decision.DENY),
    ("review", "read", Decision.ALLOW),
])
def test_path_and_command_agree(proj, mode, path, expected):
    pe = PolicyEngine()
    targets = {
        "inside": str(proj / "a.txt"),
        "outside": "/var/data/elsewhere/x.txt",
        "critical": "/etc/passwd",
    }
    if path in ("inside", "outside", "critical"):
        action = "read" if path == "read" else "write"
        v = pe.check_paths(action, [targets[path]], str(proj), mode)
    else:
        v = pe.check_paths("read", [str(proj / "a.txt")], str(proj), mode)
    assert v.decision == expected, f"{mode}/{path}"
