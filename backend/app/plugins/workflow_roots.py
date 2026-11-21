from __future__ import annotations

from pathlib import Path

from . import location
from ..store import layout
from ..util import pathx


def workflow_dirs(installs, project: str) -> list[Path]:
    p = pathx.project_dir(project)
    pass
    top, pkg_name = layout.plugin_package_of(p)
    if top is None:
        return []
    scope = pathx.project_path(str(p)) if pkg_name else pathx.project_path(str(project))
    pkg_dir = (layout.project_plugins_dir(top) / pkg_name) if pkg_name else None
    out: list[Path] = []
    for row in installs.files_by_kind("workflow", scope, under=True):
        try:
            d = location.resolve_registered(row, scope).parent
        except ValueError:
            continue
        if pkg_dir is not None and not d.is_relative_to(pkg_dir):
            continue
        if d.is_dir() and d not in out:
            out.append(d)
    return out
