from __future__ import annotations

from fastapi import APIRouter, Depends

from ..errors import bad_request, server_error
from ...checkpoints import list_checkpoints, restore, snapshot
from ..deps import Container, get_container

router = APIRouter()


def _ws_of(c: Container, req_ws: str | None = None) -> str:
    ws = req_ws or c.store.config.settings.workspaceRoot
    if not ws:
        raise bad_request("未设置工作目录")
    return ws


@router.get("/api/checkpoints")
def ck_list(ws: str | None = None, c: Container = Depends(get_container)):
    w = _ws_of(c, ws)
    return list_checkpoints(w)


@router.post("/api/checkpoints")
def ck_create(message: str = "manual", ws: str | None = None,
              c: Container = Depends(get_container)):
    w = _ws_of(c, ws)
    try:
        sha = snapshot(w, f"agent:{message}" if not message.startswith("agent:") else message)
    except ValueError as e:
        raise bad_request(str(e))
    return {"sha": sha}


@router.post("/api/checkpoints/restore")
def ck_restore(sha: str, ws: str | None = None, c: Container = Depends(get_container)):
    w = _ws_of(c, ws)
    try:
        restore(w, sha)
    except Exception as e:
        raise server_error(f"回滚失败: {e}")
    return {"ok": True}
