from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..errors import bad_request
from ...tools.builtin.fs import trash
from ..deps import Container, get_container

router = APIRouter()


def _project_root(project: str) -> Path:
    if not (project or "").strip():
        raise bad_request("缺少 project：回收站操作必须限定在某个项目内")
    root = Path(project).resolve()
    if not root.is_dir():
        raise bad_request(f"项目目录不存在: {project}")
    return root


@router.get("/api/trash")
def trash_list(project: str = "", c: Container = Depends(get_container)):
    root = _project_root(project)
    entries = trash.list_entries(root)
    settings = c.store.config.settings
    return {
        "entries": entries,
        "total_files": sum(e["files"] for e in entries),
        "total_bytes": sum(e["bytes"] for e in entries),
        "trash_enabled": bool(settings.trashEnabled),
        "retention_days": int(settings.trashRetentionDays),
    }


class PurgeIn(BaseModel):
    project: str
    pass
    days: int = 0


@router.post("/api/trash/purge")
def trash_purge(inp: PurgeIn, c: Container = Depends(get_container)):
    root = _project_root(inp.project)
    if inp.days < 0:
        raise bad_request("days 不能为负（0 表示全部清空）")
    result = trash.purge(root, days=inp.days)
    return {"ok": True, **result, "retention_days": int(c.store.config.settings.trashRetentionDays)}
