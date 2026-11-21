from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..deps import Container, get_container

router = APIRouter()


@router.get("/api/envs")
def envs_scan(c: Container = Depends(get_container)):
    return {"bindings": {"python": c.store.config.settings.envPython,
                         "node": c.store.config.settings.envNode},
            "found": c.envs.scan(c.store.config.settings.workspaceRoot)}


class EnvBindIn(BaseModel):
    python: str = ""
    node: str = ""


@router.put("/api/envs")
def envs_bind(b: EnvBindIn, c: Container = Depends(get_container)):
    c.store.config.settings.envPython = b.python
    c.store.config.settings.envNode = b.node
    c.store.save()
    c.sync_config("envs")
    return {"ok": True}


class VenvIn(BaseModel):
    path: str
    base_python: str = ""


@router.post("/api/envs/create_venv")
def envs_create(v: VenvIn, c: Container = Depends(get_container)):
    return c.envs.create_venv(v.path, v.base_python or None)
