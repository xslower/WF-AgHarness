from __future__ import annotations

from fastapi import APIRouter, Depends

from ...deps import Container, get_container
from .overview import overview

router = APIRouter()


@router.get("/api/projects/overview")
def project_overview(path: str, c: Container = Depends(get_container)):
    return overview(c, path)
