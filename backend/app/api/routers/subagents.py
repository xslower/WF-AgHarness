from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ...agent.subagent_access import SubAgentAccess
from ..errors import conflict, not_found
from ..deps import Container, get_container

router = APIRouter()


def _access(c: Container, parent: str = "", project: str = "") -> SubAgentAccess:
    pass
    pass
    root = project
    if not root and parent:
        try:
            root = c.runner.sessions.session_project(parent) or ""
        except Exception:
            root = ""
    return SubAgentAccess(c.runner.sessions, c.runner.session_rt, root)


@router.get("/api/subagents")
def subagent_list(parent: str = "", project: str = "",
                  c: Container = Depends(get_container)):
    return _access(c, parent, project).list(parent, project)


@router.get("/api/subagents/{sid}")
def subagent_get(sid: str, parent: str = "", project: str = "",
                 offset: int = 0, limit: int = 100,
                 c: Container = Depends(get_container)):
    access = _access(c, parent, project)
    rec = access.get(sid, parent)
    if rec is None or (project and rec.project != project):
        raise not_found("子 Agent 不存在")
    return rec.read_messages(offset, limit)


@router.get("/api/subagents/{sid}/result")
def subagent_result(sid: str, parent: str = "", project: str = "",
                    c: Container = Depends(get_container)):
    access = _access(c, parent, project)
    rec = access.get(sid, parent)
    if rec is None or (project and rec.project != project):
        raise not_found("子 Agent 不存在")
    return {"id": rec.id, "status": rec.status,
            "content": rec.result, "path": rec.result_path,
            "chars": len(rec.result)}


class InstructionIn(BaseModel):
    text: str
    parent: str = ""


@router.post("/api/subagents/{sid}/message")
def subagent_message(sid: str, body: InstructionIn,
                     c: Container = Depends(get_container)):
    access = _access(c, body.parent)
    out = access.message(sid, body.text, body.parent)
    if "error" in out:
        raise conflict(out["error"])
    return out


class StopIn(BaseModel):
    parent: str = ""
    force: bool = True


@router.post("/api/subagents/{sid}/stop")
def subagent_stop(sid: str, body: StopIn,
                  c: Container = Depends(get_container)):
    access = _access(c, body.parent)
    out = access.stop(sid, body.parent, body.force)
    if "error" in out:
        raise not_found(out["error"])
    return out
