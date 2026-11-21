from __future__ import annotations

from pathlib import Path
from typing import Any

import app.project.config as project_config
from ..store import layout
from ..util import pathx

HIDE_PLUGINS = "hiddenPluginProjects"
HIDE_WORKFLOWS = "hiddenWorkflows"


def prefs_of(project: str | Path) -> dict:
    p = pathx.project_dir(project)
    if not layout.is_project(p):
        return {}
    cfg = project_config.read_project_config(p)
    ui = cfg.get("ui") if isinstance(cfg, dict) else None
    return ui if isinstance(ui, dict) else {}


def set_prefs(project: str | Path, values: dict) -> dict:
    p = pathx.project_dir(project)
    if not layout.is_project(p):
        raise ValueError(f"不是项目目录: {project}")
    cfg = project_config.read_project_config(p)
    cfg["ui"] = {**(cfg.get("ui") or {}), **{
        k: bool(v) for k, v in (values or {}).items()
        if k in (HIDE_PLUGINS, HIDE_WORKFLOWS)}}
    project_config.write_project_config(p, cfg)
    return dict(cfg["ui"])


def _is_plugin_package_path(path: str) -> bool:
    marker = f"/{layout.AGENT_DIR_NAME}/{layout.PLUGINS_DIR_NAME}/"
    return marker in path


def filter_children(nodes: list[dict], container: Any,
                    project: str | Path) -> list[dict]:
    out: list[dict] = []
    for n in nodes:
        path = pathx.project_path(str(n.get("path") or ""))
        if _is_plugin_package_path(path):
            continue
        row = dict(n)
        row["path"] = path
        out.append(row)
    return out


def filter_workflows(rows: list[dict], project: str | Path) -> list[dict]:
    if prefs_of(project).get(HIDE_WORKFLOWS):
        return []
    return rows
