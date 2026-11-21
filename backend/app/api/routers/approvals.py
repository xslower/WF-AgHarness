from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..errors import not_found
from ..deps import Container, get_container

router = APIRouter()


@router.get("/api/approvals")
def approvals_list(session: str | None = None,
                   c: Container = Depends(get_container)):
    return c.approvals.list(session_id=session or "")


class DecisionIn(BaseModel):
    approved: bool
    hunks: list[int] | None = None


@router.post("/api/approvals/{pid}/decide")
def approvals_decide(pid: str, d: DecisionIn, c: Container = Depends(get_container)):
    if not c.approvals.decide(pid, d.approved, d.hunks):
        raise not_found("审批不存在或已处理")
    return {"ok": True}
