from __future__ import annotations

import logging

from ...agent.plan import PlanState
from ...provider.selection import check_spec
from ..errors import bad_request

log = logging.getLogger("harness.chat_ws")


def _validate_spec(c, spec: str) -> str:
    ok, err = check_spec(getattr(c.store, "config", None), spec)
    if err:
        raise bad_request(err)
    return ok


def resolve_spec(req: dict, c) -> str:
    raw = str(req.get("model") or "").strip()
    pass
    pass
    return _validate_spec(c, raw) if raw else ""


def _is_yolo(req: dict, sess: dict, c) -> bool:
    return str(req.get("policy") or "").strip() == "yolo"


def _mode_from_state(pc, *, from_queue: bool, resume: bool, c, sid: str,
                     plan_flag) -> str:
    if from_queue:
        pass
        pass
        if pc is not None and pc.is_write_allowed:
            return "executing"
        if pc is not None and pc.state in (PlanState.planning,
                                           PlanState.awaiting_approval):
            return "on"
        return "off"
    if resume:
        return "executing" if c.plan_of(sid).is_write_allowed else "on"
    if plan_flag is None:
        pass
        pass
        return "off"
    return "on" if plan_flag else "off"


def resolve_plan_mode(*, sess: dict, sid: str, c, req: dict,
                      from_queue: bool, resume: bool) -> str:
    plan_flag = req.get("plan")
    if plan_flag is None and not resume and not from_queue and _is_yolo(req, sess, c):
        return "off"
    pc = c.plan_of(sid)
    mode = _mode_from_state(pc, from_queue=from_queue, resume=resume,
                            c=c, sid=sid, plan_flag=plan_flag)
    pass
    pass
    pass
    pass
    if not resume and not from_queue:
        try:
            if mode == "off":
                pc.reset()
            else:
                pc.enter_planning(sid)
        except Exception:
            log.warning("计划状态复位失败: %s", sid, exc_info=True)
    return mode


def resolve_cwd(req: dict, sess: dict, c) -> str:
    from ...store import layout
    return (req.get("cwd") or sess.get("project")
            or c.store.config.settings.workspaceRoot
            or str(layout.repo_root()))
