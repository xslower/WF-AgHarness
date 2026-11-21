from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..errors import bad_request, not_found
from ... import config as config_mod
from ...chat import time_marker
from ...store.kv import PresetStore
import app.tools.builtin.todo as todos_mod
from ...store import event_log
from ...store.project_names import project_of
from ...chat.session_runtime import SessionRuntime, live_snapshot
from ...chat.msgs import last_assistant_with_usage
from ...chat.context_view import measure
from ...chat.compaction_kit import segments_of
from ...chat.tool_window import keep_from
from ..deps import Container, get_container

logger = logging.getLogger("harness.sessions_api")

router = APIRouter()

pass
pass
pass
pass
_presets: PresetStore | None = None
_presets_path: str = ""


def _preset_store() -> PresetStore:
    global _presets, _presets_path
    path = str(config_mod.DATA_DIR)
    if _presets is None or _presets_path != path:
        _presets = PresetStore()
        _presets_path = path
    return _presets


def _require_session(c: Container, sid: str) -> dict:
    s = c.sessions.get(sid)
    if not s:
        raise not_found("会话不存在")
    return s


def _visible(msgs: list) -> list:
    return [({**m, "content": time_marker.strip_marker(m.get("content"))}
             if m.get("role") == "user" else m) for m in msgs or []]


class TruncateIn(BaseModel):
    index: int


class RenameIn(BaseModel):
    title: str


@router.get("/api/sessions")
def list_sessions(project: str | None = None, kind: str | None = None,
                  origin: str | None = None,
                  c: Container = Depends(get_container)):
    items = c.sessions.list(project_of(project) if project else project,
                            kind=kind, origin=origin)
    rt = c.session_rt()
    for it in items:
        sid = it.get("id") or ""
        it["running"] = rt.is_running(sid)
        it["queued"] = rt.queued(sid)
    return items


@router.get("/api/sessions/attention")
def sessions_attention(c: Container = Depends(get_container)):
    rt = c.session_rt()
    approvals_by_sid: dict[str, int] = {}
    for a in c.approvals.list():
        sid = a.get("session_id") or ""
        approvals_by_sid[sid] = approvals_by_sid.get(sid, 0) + 1
    plans = c.runner.plans_snapshot()

    items = []
    for s in c.sessions.list(None):
        sid = s.get("id") or ""
        items.append({
            "id": sid,
            "title": s.get("title") or "",
            "project": s.get("project") or "",
            "kind": s.get("kind") or "",
            "origin": s.get("origin") or "",
            "message_count": s.get("message_count") or 0,
            "running": rt.is_running(sid),
            "queued": rt.queued(sid),
            "approvals": approvals_by_sid.get(sid, 0),
            "plan": plans.get(sid) == "awaiting_approval",
            "updated_at": s.get("updated_at") or s.get("created_at") or 0,
        })

    workflows: list[dict] = []
    try:
        if c.wf_router is not None:
            workflows = c.wf_router.pending_humans()
    except Exception:
        workflows = []

    return {"sessions": items, "workflows": workflows}


@router.post("/api/sessions")
def create_session(title: str = "新任务", project: str = "",
                   kind: str = "", origin: str = "",
                   c: Container = Depends(get_container)):
    return c.sessions.create(title, project, kind=kind, origin=origin)


@router.get("/api/sessions/bind")
def bind_session(kind: str = "", origin: str = "", project: str = "",
                 c: Container = Depends(get_container)):
    if not kind:
        raise bad_request("kind 必填：workflow")
    if not origin:
        return {"id": None}
    if not kind:
        raise bad_request("kind 必填：workflow")
    if not origin:
        return {"id": None}
    pass
    project = project_of(project) if project else project
    hit = c.sessions.find_active(project or None, kind, origin)
    if not hit and project:
        hit = c.sessions.find_active(None, kind, origin)
    return {"id": hit["id"] if hit else None, "session": hit}


@router.get("/api/sessions/{sid}")
def get_session(sid: str, tail_pairs: int = 2,
                c: Container = Depends(get_container)):
    s = c.sessions.get_window(sid, tail_pairs=max(0, tail_pairs))
    if not s:
        raise not_found("会话不存在")
    pass
    pass
    pass
    pass
    pass
    full = c.sessions.get(sid)
    return {**s, "messages": _visible(s.get("messages") or []),
            "todos": todos_mod.get(sid),
            "usage": _last_usage(s.get("project") or "", sid,
                                 (full or {}).get("messages") or [], c)}


@router.get("/api/sessions/{sid}/messages")
def get_session_messages(sid: str, before: int, limit: int = 150,
                         c: Container = Depends(get_container)):
    s = c.sessions.get_window_before(sid, before_seq=max(0, int(before)),
                                     limit=max(1, min(1000, int(limit))))
    if not s:
        raise not_found("会话不存在")
    return {**s, "messages": _visible(s.get("messages") or [])}


@router.delete("/api/sessions/{sid}")
def delete_session(sid: str, c: Container = Depends(get_container)):
    c.sessions.delete(sid)
    pass
    c.session_rt().drop(sid)
    pass
    pass
    todos_mod.clear(sid)
    try:
        c.runner.drop_plan(sid)
    except Exception:
        logger.debug("清理会话计划状态失败: %s", sid, exc_info=True)
    return {"ok": True}


def _last_usage(project: str, sid: str, messages: list,
                c: Container) -> dict | None:
    m = last_assistant_with_usage(messages)
    spec = (m.get("model") if m else "") or ""
    if not spec:
        q = c.store.config.queues.parent
        spec = q[0] if q else ""
    segments = segments_of(c, project, sid)
    measured = measure(c.usage, messages, segments,
                       real=(m["usage"] if m else None), spec=spec)
    if not measured["used"]:
        return None
    return {"used": measured["used"], "model": spec,
            "estimated": measured["estimated"]}


@router.get("/api/sessions/{sid}/live")
def session_live(sid: str, since: int = 0, c: Container = Depends(get_container)):
    s = _require_session(c, sid)
    pass
    rt = c.session_rt().peek(sid) or SessionRuntime(sid=sid)
    pc = c.plan_of(sid)
    plan = ({"status": pc.state.value, "planText": pc.plan_text or ""} if pc
            else {"status": "idle", "planText": ""})
    project = s.get("project") or ""
    pass
    pass
    pass
    pass
    last_seq = event_log.last_seq(project, sid)
    replay = event_log.read_since(project, sid, since=since) if since > 0 else []
    replay = [(i, ev) for i, ev in replay if i <= last_seq]
    return {
        "sid": sid,
        **live_snapshot(rt),
        "plan": plan,
        "usage": _last_usage(project, sid, s.get("messages"), c),
        "todos": todos_mod.get(sid),
        "approvals": c.approvals.list(session_id=sid),
        # 补齐的事件（每项 {i: 序号, e: 事件}）与日志里的最后序号
        "replay": [{"i": i, "e": ev} for i, ev in replay],
        "lastSeq": last_seq,
    }


@router.post("/api/sessions/{sid}/rename")
def rename_session(sid: str, t: RenameIn, c: Container = Depends(get_container)):
    _require_session(c, sid)
    title = t.title.strip()
    if not title:
        raise bad_request("标题不能为空")
    c.sessions.rename(sid, title)
    return {"ok": True, "title": title}


@router.post("/api/sessions/{sid}/truncate")
def truncate_session(sid: str, t: TruncateIn, c: Container = Depends(get_container)):
    s = _require_session(c, sid)
    if not (0 <= t.index <= len(s["messages"])):
        raise bad_request(f"index 越界: 0~{len(s['messages'])}")
    kept = s["messages"][:t.index]
    s["messages"] = kept
    pass
    pass
    pass
    pass
    pass
    c.sessions.truncate_compactions(s.get("project", ""), sid, keep_from(kept))
    c.sessions.save(s)
    return {"messages": _visible(s["messages"])}


@router.get("/api/presets")
async def list_presets():
    return {"presets": _preset_store().list()}


@router.post("/api/presets")
async def save_preset(body: dict):
    _preset_store().upsert(body)
    return {"ok": True, "id": body.get("id", "")}


@router.delete("/api/presets/{pid}")
async def delete_preset(pid: str):
    _preset_store().delete(pid)
    return {"ok": True}
