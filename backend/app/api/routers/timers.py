from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..errors import bad_request, not_found
from ...event.schedule import TIMERS, next_fire
from ...store.timer_db import TimerDb

router = APIRouter()


class TimerIn(BaseModel):

    name: str
    owner: str = "frontend"
    action: str = "session"
    kind: str = "every"
    spec: str
    payload: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class TimerPatch(BaseModel):

    owner: str | None = None
    action: str | None = None
    kind: str | None = None
    spec: str | None = None
    payload: dict[str, Any] | None = None
    enabled: bool | None = None


def _db() -> TimerDb:
    return TIMERS.db


def _row(row: dict) -> dict:
    try:
        row = {**row, "nextRunAt": next_fire(row["kind"], row["spec"])}
    except ValueError:
        row = {**row, "nextRunAt": None, "invalid": True}
    return row


@router.get("/api/timers")
def list_timers(owner: str = "", project: str = ""):
    rows = _db().load_all(owner=owner or None)
    if project:
        rows = [r for r in rows
                if str((r.get("payload") or {}).get("project") or "") == project]
    return [_row(r) for r in rows]


@router.post("/api/timers")
def create_timer(body: TimerIn):
    _validate(body.owner, body.action, body.kind, body.spec, body.payload)
    db = _db()
    db.upsert(body.name, kind=body.kind, spec=body.spec, payload=body.payload,
              owner=body.owner, action=body.action, enabled=body.enabled)
    _resync()
    return _row(db.get(body.name) or {})


@router.patch("/api/timers/{name}")
def update_timer(name: str, body: TimerPatch):
    db = _db()
    cur = db.get(name)
    if cur is None:
        raise not_found(f"定时任务不存在: {name}")
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    merged = {**cur, **fields}
    _validate(merged["owner"], merged["action"], merged["kind"],
              merged["spec"], merged["payload"])
    if fields:
        db.update(name, **fields)
    _resync()
    return _row(db.get(name) or {})


@router.delete("/api/timers/{name}")
def delete_timer(name: str):
    if _db().get(name) is None:
        raise not_found(f"定时任务不存在: {name}")
    TIMERS.remove(name)
    return {"ok": True}


pass

def _validate(owner: str, action: str, kind: str, spec: str,
              payload: dict) -> None:
    try:
        TimerDb.validate(owner=owner, action=action, kind=kind)
        next_fire(kind, spec)
    except ValueError as e:
        raise bad_request(str(e)) from None
    payload = payload or {}
    if action == "session":
        if not str(payload.get("project") or "").strip():
            raise bad_request("定时会话必须指定项目（payload.project）")
        if not str(payload.get("prompt") or "").strip():
            raise bad_request("定时会话必须设置提示词（payload.prompt）")
    elif not str(payload.get("workflow") or "").strip():
        raise bad_request("定时工作流必须指定工作流名（payload.workflow）")


def _resync() -> None:
    TIMERS.refresh()
