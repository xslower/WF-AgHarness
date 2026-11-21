from __future__ import annotations

from pathlib import Path

from ..util import pathx
from . import layout


def project_name(project: str | Path | None) -> str:
    return str(project or "").rstrip("/").rsplit("/", 1)[-1]


def project_of(project: str | Path | None) -> str:
    s = str(project or "").strip()
    if not s:
        return ""
    if "/" in s or s.startswith("~"):
        return pathx.project_path(s)
    for p in layout.registered_projects():
        if project_name(p) == s:
            return p
    return s
