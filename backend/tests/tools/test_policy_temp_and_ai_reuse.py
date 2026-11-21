from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.security import core as policy_core
from app.security.engine import Decision, PolicyEngine


pass
def test_linux_tmp_is_temp():
    assert policy_core.is_temp_path("/tmp/a.log") is True
    assert policy_core.is_temp_path("/var/tmp/b.log") is True


def test_env_temp_root_honoured(monkeypatch, tmp_path):
    d = tmp_path / "mytemp"
    d.mkdir()
    monkeypatch.setenv("TMPDIR", str(d))
    assert policy_core.is_temp_path(str(d / "x.log")) is True


def test_extra_safe_paths_configurable(monkeypatch, tmp_path):
    pass
    pass
    monkeypatch.setattr(policy_core, "temp_roots",
                        lambda extra=None: list(extra or []))
    d = tmp_path / "scratch"
    d.mkdir()
    assert policy_core.is_temp_path(str(d / "a")) is False
    assert policy_core.is_temp_path(str(d / "a"), [str(d)]) is True


def test_temp_does_not_swallow_traversal():
    assert policy_core.is_temp_path("/tmp/../etc/passwd") is False


def test_grade_puts_temp_in_scratch_not_outside():
    g = policy_core.grade_paths(["/tmp/a.log"], "/some/project")
    assert g.scratch and not g.outside
    assert g.all_safe is True


def test_grade_keeps_critical_priority():
    g = policy_core.grade_paths(["/etc/passwd", "/tmp/a"], "/some/project")
    assert g.critical and g.scratch and g.all_safe is False


pass
@pytest.mark.parametrize("mode", ["workspace", "review"])
def test_command_touching_only_temp_is_allowed(mode):
    pe = PolicyEngine()
    v = pe.check("python3 build.py > /tmp/out.log", "/some/project", mode)
    assert v.decision == Decision.ALLOW


def test_command_outside_and_temp_still_reviews():
    pe = PolicyEngine()
    v = pe.check("cp /tmp/a.log /var/data/x/b.log", "/some/project", "workspace")
    assert v.decision == Decision.REVIEW


pass
@pytest.mark.parametrize("mode", ["workspace", "review"])
def test_check_paths_temp_allowed(mode):
    pe = PolicyEngine()
    v = pe.check_paths("write", ["/tmp/a.log"], "/some/project", mode)
    assert v.decision == Decision.ALLOW


def test_check_paths_temp_still_denies_critical():
    pe = PolicyEngine()
    v = pe.check_paths("write", ["/etc/passwd"], "/some/project", "workspace")
    assert v.decision == Decision.DENY


def test_extra_safe_injected_via_engine_attr(tmp_path, monkeypatch):
    pass
    monkeypatch.setattr(policy_core, "temp_roots",
                        lambda extra=None: list(extra or []))
    d = tmp_path / "scratch"
    d.mkdir()

    class _S:
        policyExtraSafePaths = [str(d)]

    pe = PolicyEngine(settings_getter=lambda: _S())
    v = pe.check_paths("write", [str(d / "a.txt")], "/some/project", "workspace")
    assert v.decision == Decision.ALLOW
    pass
    pe2 = PolicyEngine()
    v2 = pe2.check_paths("write", [str(d / "a.txt")], "/some/project",
                         "workspace")
    assert v2.decision == Decision.REVIEW


pass
class _Approvals:
    def __init__(self, approve: bool = True) -> None:
        self.created: list = []
        self._approve = approve

    def create(self, command, risks, reason, session_id="", kind="cmd",
               file_diff=None):
        pa = type("PA", (), {"id": f"p{len(self.created)}", "risks": risks,
                             "approved_hunks": None})()
        self.created.append(pa)
        return pa

    async def wait(self, pa, stop=None):
        return self._approve


def _wire(tmp_path, gw, approvals, mode="workspace"):
    from app.security.engine import PolicyEngine as PE
    from app.security.wiring import wire_policy
    from app.tools import ToolContext

    async def emit(_e):
        return None

    ctx = ToolContext(str(tmp_path))
    pe = PE(gw)
    wire_policy(ctx, str(tmp_path), emit, [], pe, approvals, gw)
    return ctx


def _gw(verdict_json: str):
    g = AsyncMock()
    g.call_utility = AsyncMock(return_value=verdict_json)
    return g


@pytest.mark.asyncio
async def test_ai_pass_on_write_suppresses_later_dialog(tmp_path, monkeypatch):
    pass
    outside = "/var/data/elsewhere/x.txt"
    approvals = _Approvals(approve=True)
    ctx = _wire(tmp_path, _gw('{"verdict":"pass","risks":[]}'), approvals)

    ok, _ = await ctx.path_check("write", [outside])
    assert ok is True
    assert approvals.created == []

    pass
    ok2, hunks = await ctx.request_file_approval(
        "写 x.txt", outside, "a", "b")
    assert ok2 is True
    assert approvals.created == []


@pytest.mark.asyncio
async def test_ai_block_on_write_still_asks_human(tmp_path):
    outside = "/var/data/elsewhere/x.txt"
    approvals = _Approvals(approve=True)
    ctx = _wire(tmp_path, _gw('{"verdict":"block","risks":[]}'), approvals)

    ok, _ = await ctx.path_check("write", [outside])
    assert ok is True

    ok2, _ = await ctx.request_file_approval("写 x.txt", outside, "a", "b")
    assert ok2 is True
    assert len(approvals.created) == 1


@pytest.mark.asyncio
async def test_temp_write_never_asks(tmp_path, monkeypatch):
    monkeypatch.setattr(policy_core, "temp_roots", lambda extra=None: ["/tmp"])
    gw = _gw('{"verdict":"pass","risks":[]}')
    approvals = _Approvals(approve=True)
    ctx = _wire(tmp_path, gw, approvals)

    ok, _ = await ctx.path_check("write", ["/tmp/a.log"])
    assert ok is True
    assert approvals.created == []
    assert gw.call_utility.await_count == 0
