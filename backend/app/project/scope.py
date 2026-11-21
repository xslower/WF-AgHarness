from __future__ import annotations

import contextlib
import contextvars

_PROJECT_CTX: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_project", default="")

__all__ = ["set_current_project", "current_project", "project_scope"]


def set_current_project(cwd: str) -> None:
    _PROJECT_CTX.set(cwd or "")


def current_project() -> str:
    return _PROJECT_CTX.get()


@contextlib.contextmanager
def project_scope(cwd: str):
    token = _PROJECT_CTX.set(cwd or "")
    try:
        yield
    finally:
        _PROJECT_CTX.reset(token)
