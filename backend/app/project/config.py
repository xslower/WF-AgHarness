from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..store import layout
from ..util import pathx
from ..util.jsonx import read_json, write_json
from ..config import McpServerCfg


def project_config_path(project: str | Path) -> Optional[Path]:
    p = pathx.project_dir(project)
    return layout.project_subdir(p, "config.json") if layout.is_project(p) else None


def read_project_config(project: str | Path) -> dict:
    p = project_config_path(project)
    if p is None:
        return {}
    data = read_json(p, {})
    return data if isinstance(data, dict) else {}


def write_project_config(project: str | Path, cfg: dict) -> Path:
    p = project_config_path(project)
    if p is None:
        raise ValueError(f"不是项目目录: {project}")
    write_json(p, cfg)
    return p


def read_project_mcp(project: str | Path) -> dict[str, McpServerCfg]:
    from ..mcp import spec as mcp_spec

    p = pathx.project_dir(project)
    if not layout.is_project(p):
        return {}
    out = mcp_spec.load_dir(layout.project_mcp_dir(p))
    legacy = read_json(layout.project_mcp_json(p), {})
    for name, cfg in mcp_spec.parse_servers(legacy).items():
        out.setdefault(name, cfg)
    return out
