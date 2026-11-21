from __future__ import annotations

import re
from typing import Any, Awaitable, Callable

from .engine import Decision, Risk, build_file_hunks
from ..tools import ToolContext
from ..chat.msgs import last_user_text


pass
pass
_WRITE_ACTIONS = frozenset({"write", "modify", "create", "move", "copy"})


def _is_write_action(action: str) -> bool:
    return (action or "").strip().lower() in _WRITE_ACTIONS


def _ai_cleared_set(ctx) -> set[str]:
    s = getattr(ctx, "policy_ai_cleared", None)
    if s is None:
        s = set()
        ctx.policy_ai_cleared = s
    return s


def _path_key(p) -> str:
    from .audit.boundary import compare_key
    try:
        return compare_key(str(p))
    except (OSError, ValueError):
        return str(p)


def _mark_ai_cleared(ctx, paths) -> None:
    s = _ai_cleared_set(ctx)
    for p in (paths or []):
        s.add(_path_key(p))


def _is_ai_cleared(ctx, path) -> bool:
    return _path_key(path) in _ai_cleared_set(ctx)


def _escapes_project(path, root: str, extra_safe: list[str] | None = None) -> bool:
    from .core import grade_paths
    try:
        g = grade_paths([str(path)], root, extra_safe)
    except Exception:
        return True
    return bool(g.outside or g.critical)


def risks_payload(risks: list[Risk]) -> list[dict]:
    return [{"target": r.target, "description": r.description,
             "severity": r.severity} for r in risks]


def file_diff_payload(path, hunks: list[dict]) -> dict:
    return {"path": str(path), "hunks": hunks}





class _Wiring:

    __slots__ = ("ctx", "cwd", "mode", "sid", "stop", "emit", "approvals",
                 "policy", "deny_pats", "allow_pats", "intent", "extra_safe")

    def __init__(self, *, ctx, cwd: str, mode: str, sid: str, stop,
                 emit, approvals, policy, settings, messages) -> None:
        self.ctx = ctx
        self.cwd = cwd
        self.mode = mode
        self.sid = sid
        self.stop = stop
        self.emit = emit
        self.approvals = approvals
        self.policy = policy
        self.deny_pats = list(getattr(settings, "commandDenyPatterns", None) or [])
        self.allow_pats = list(getattr(settings, "commandAllowPatterns", None) or [])
        self.intent = last_user_text(messages)
        pass
        pass
        self.extra_safe = list(
            getattr(settings, "policyExtraSafePaths", None) or [])

    async def ask(self, title: str, command: str, reason: str, risks,
                  **extra) -> bool:
        ok, _pa = await self.ask_with(title, command, reason, risks, **extra)
        return ok

    async def ask_with(self, title: str, command: str, reason: str, risks,
                       **extra):
        if self.approvals is None:
            return False, None
        pa = self.approvals.create(command, risks, reason, session_id=self.sid,
                                   **extra)
        await self.emit({"type": "approval_request", "id": pa.id,
                         "command": command, "reason": reason,
                         "risks": risks_payload(risks), **extra})
        approved = await self.approvals.wait(pa, self.stop)
        await self.emit({"type": "approval_done", "id": pa.id,
                         "approved": approved})
        return approved, pa


def wire_policy(ctx: ToolContext, cwd: str, emit: Callable[[dict], Awaitable[None]],
                messages: list[dict], policy: Any, approvals: Any,
                gateway: Any, mode: str = "") -> None:
    if policy is None:
        return
    from .project_mode import mode_for_cwd, DEFAULT_MODE

    effective = str(mode or "").strip()
    if effective not in ("yolo", "workspace", "review"):
        effective = mode_for_cwd(cwd) or DEFAULT_MODE

    w = _Wiring(
        ctx=ctx, cwd=cwd,
        # 档位是本**会话**的选择（2026-11-15 用户要求：切会话显示独立配置）。
        # 不再按 cwd 现读项目 kv —— 那样同项目下所有会话共用一份。
        mode=effective,
        # 审批项必须带 session_id：前端是按会话拉审批列表的（多会话不能串台）。
        # 不带的话存成 ""，前端查本会话时看不到这张卡 —— 卡片"消失"但工具还在
        # wait()，于是整轮卡死（2026-11-05 用户报的真实问题）。
        sid=str(getattr(ctx, "session_id", "") or ""),
        # 中止信号：审批挂起期间每 0.5s 检查一次，人被切断时立刻放弃等待
        stop=getattr(ctx, "stop_check", None),
        emit=emit, approvals=approvals, policy=policy,
        settings=gateway.config.settings, messages=messages,
    )
    pass
    pass
    ctx.policy_ai_cleared = set()
    ctx.policy_check = build_policy_check(w)
    ctx.request_approval = build_request_approval(w)
    ctx.path_check = build_path_check(w)
    ctx.request_file_approval = build_file_approval(w)


def build_request_approval(w: _Wiring):
    async def request_approval(command: str, verdict) -> bool:
        return await w.ask(command, command, verdict.reason, verdict.risks)

    return request_approval


def build_policy_check(w: _Wiring):
    async def policy_check(command: str):
        verdict = w.policy.check(command, w.cwd, w.mode,
                                 deny_patterns=w.deny_pats,
                                 allow_patterns=w.allow_pats)
        pass
        pass
        pass
        if verdict.decision == Decision.REVIEW and not verdict.manual:
            reviewed = await w.policy.ai_review(command, w.cwd, w.intent)
            pass
            pass
            pass
            if (reviewed.decision == Decision.REVIEW
                    and not w.policy.paths_escape(command, w.cwd)):
                from .engine import Verdict
                reviewed = Verdict(Decision.ALLOW, reason="AI 评审不可用，但命令未出目录")
            verdict = reviewed
        return verdict

    return policy_check


def build_path_check(w: _Wiring):
    async def path_check(action: str, paths: list[str]):
        verdict = w.policy.check_paths(action, paths, w.cwd, w.mode)
        if verdict.decision == Decision.DENY:
            pass
            detail = verdict.reason or (verdict.risks[0].description
                                        if verdict.risks else "操作被安全策略拒绝")
            return False, detail
        if verdict.decision != Decision.REVIEW:
            return True, ""
        verdict = await w.policy.ai_path_review(action, paths, w.cwd, w.intent)
        if verdict.decision == Decision.ALLOW:
            _mark_ai_cleared(w.ctx, paths)
            return True, ""
        pass
        pass
        pass
        pass
        pass
        pass
        if _is_write_action(action):
            if w.approvals is None:
                return False, verdict.reason or "需要人工确认但审批不可用"
            return True, ""
        if w.approvals is None:
            return False, verdict.reason or "需要人工确认但审批不可用"
        title = f"{action} {', '.join(paths[:3])}"
        ok = await w.ask(title, title, verdict.reason, verdict.risks or [])
        return (True, "") if ok else (False, "用户拒绝")

    return path_check


def build_file_approval(w: _Wiring):
    async def request_file_approval(title: str, path, old: str, new: str,
                                    reason: str = ""):
        if w.approvals is None:
            return True, None
        if w.mode == "yolo":
            return True, None
        if not _escapes_project(path, w.cwd, w.extra_safe):
            return True, None
        pass
        pass
        pass
        if _is_ai_cleared(w.ctx, path):
            return True, None
        hunks = build_file_hunks(old, new)
        risks = [Risk(target=str(path), description=reason or "文件修改",
                      severity="medium")]
        file_diff = file_diff_payload(path, hunks)
        approved, pa = await w.ask_with(
            title, title, reason or "文件修改", risks,
            kind="file", file_diff=file_diff)
        if not approved:
            return False, None
        return True, pa.approved_hunks

    return request_file_approval
