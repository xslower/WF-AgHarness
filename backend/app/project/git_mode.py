from __future__ import annotations

from pathlib import Path

from ..store import layout
from ..util import pathx
from . import config as project_config


def git_enabled(project: str | Path) -> bool:
    p = pathx.project_dir(project)
    cfg = project_config.read_project_config(p)
    git = cfg.get("git") if isinstance(cfg, dict) else None
    if isinstance(git, dict) and isinstance(git.get("enabled"), bool):
        return git["enabled"]
    return (p / ".git").exists()


def set_git_enabled(project: str | Path, enabled: bool) -> bool:
    p = pathx.project_dir(project)
    if not layout.is_project(p):
        raise ValueError(f"不是项目目录: {project}")
    cfg = project_config.read_project_config(p)
    git = cfg.get("git") if isinstance(cfg.get("git"), dict) else {}
    cfg["git"] = {**git, "enabled": bool(enabled)}
    project_config.write_project_config(p, cfg)
    return bool(enabled)
