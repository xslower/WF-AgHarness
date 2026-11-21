from __future__ import annotations

from fastapi import APIRouter

from .home import router as home_router
from .policy import router as policy_router
from .tree import router as tree_router

ROUTERS: list[APIRouter] = [tree_router, home_router, policy_router]

__all__ = ["ROUTERS"]
