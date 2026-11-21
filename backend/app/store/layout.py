from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from ..util import pathx

pass
pass
AGENT_DB = "agent.db"
CONFIG_JSON = "config.json"
USAGE_DB = "usage.db"
TIMERS_DB = "timers.db"


JSON_ERROR_LOG = "wf-json-errors.log"

pass
AGENT_DIR_NAME = ".agent"
PLUGINS_DIR_NAME = "plugins"
IMAGES_DIR_NAME = "images"
SESSIONS_DIR_NAME = "sessions"
WORKFLOWS_DIR_NAME = "workflows"
ARTIFACTS_DIR_NAME = "artifacts"
WORKSPACES_DIR_NAME = "workspaces"
GLOBAL_WORKSPACE_NAME = "_global"
PROJECTS_DIR_NAME = "projects"
SUBAGENTS_DIR_NAME = "subagents"
RUNS_DIR_NAME = "runs"
THEMES_DIR_NAME = "themes"
PROVIDERS_DIR_NAME = "providers"
KEYSTORE_DIR_NAME = "keystore"
MASTER_KEY_FILE = "master.key"
AGENTS_DIR_NAME = "agents"
SKILLS_DIR_NAME = "skills"
TOOLS_DIR_NAME = "tools"
OPS_DIR_NAME = "ops"
MCP_DIR_NAME = "mcp"
MCP_JSON = "mcp.json"


def data_dir() -> Path:
    from ..config import DATA_DIR

    return DATA_DIR


pass
def agent_db() -> Path:
    return data_dir() / AGENT_DB


def config_json() -> Path:
    return data_dir() / CONFIG_JSON


def master_key() -> Path:
    return data_dir() / KEYSTORE_DIR_NAME / MASTER_KEY_FILE


def timers_db() -> Path:
    return data_dir() / TIMERS_DB


def usage_db() -> Path:
    return data_dir() / USAGE_DB


def json_error_log() -> Path:
    return data_dir() / JSON_ERROR_LOG


def plugins_dir() -> Path:
    return SOURCE_ROOT / PLUGINS_DIR_NAME


def images_dir() -> Path:
    return data_dir() / IMAGES_DIR_NAME


def sessions_dir() -> Path:
    return data_dir() / SESSIONS_DIR_NAME


def workflows_dir() -> Path:
    return data_dir() / WORKFLOWS_DIR_NAME


def artifacts_dir() -> Path:
    return data_dir() / ARTIFACTS_DIR_NAME


def themes_dir() -> Path:
    return data_dir() / THEMES_DIR_NAME


def providers_dir() -> Path:
    return data_dir() / PROVIDERS_DIR_NAME


def mcp_dir() -> Path:
    return data_dir() / MCP_DIR_NAME


def global_workspace() -> Path:
    return data_dir() / WORKSPACES_DIR_NAME / GLOBAL_WORKSPACE_NAME


def default_projects_root() -> Path:
    return data_dir().parent / PROJECTS_DIR_NAME


def repo_root() -> Path:
    return data_dir().parent


pass
pass
pass
SOURCE_ROOT = Path(__file__).absolute().parents[3]
pass
BACKEND_ROOT = SOURCE_ROOT / "backend"


pass
def runtime_root() -> Path | None:
    from ..config import RUNTIME_DIR

    return RUNTIME_DIR


def project_key(project: str | Path) -> str:
    p = pathx.project_dir(project)
    if not p.is_absolute():
        return _norm_key(p.name or "project")
    pass
    pass
    top = top_project(p) or nearest_registered(p)
    if top is None or top == p:
        return _norm_key(p.name)
    return _norm_key(f"{top.name}/{os.path.relpath(str(p), str(top))}")


def _norm_key(rel: str) -> str:
    parts: list[str] = []
    for seg in str(rel).replace("\\", "/").strip("/").split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if parts:
                parts.pop()
            continue
        safe = "".join(c if (c.isalnum() or c in "-_.中文") else "_" for c in seg)
        parts.append(safe.replace("__", "_") or "project")
    return "/".join(parts) or "project"


def runtime_project_dir(project: str | Path) -> Path | None:
    root = runtime_root()
    if root is None:
        return None
    return root / project_key(project)


def _hot_path(project: str | Path, name: str, in_project: Path) -> Path:
    base = runtime_project_dir(project)
    if base is None:
        return in_project
    return base / name


pass
pass
pass
pass

pass
_REGISTRY: dict[str, dict[str, str]] = {}


def invalidate_project_cache() -> None:
    _REGISTRY.clear()
    pathx.invalidate_alias_cache()

def _registry() -> dict[str, str]:
    key = str(agent_db())
    hit = _REGISTRY.get(key)
    if hit is not None:
        return hit
    from .kv import RegistryStore

    table: dict[str, str] = {}
    for row in RegistryStore().list_rows():
        pass
        pass
        p = pathx.project_path(row.get("path"))
        if p:
            table[p] = pathx.project_path(row.get("parent")) if row.get("parent") else ""


    _REGISTRY[key] = table
    return table


def registered_projects() -> list[str]:
    return list(_registry())


def is_project(path: str | Path) -> bool:
    if not path:
        return False
    p = pathx.project_dir(path)
    if not p.is_absolute():
        return False
    return str(p) in _registry()


def parent_project(path: str | Path | None) -> Optional[Path]:
    if not path:
        return None
    p = str(pathx.project_dir(path))
    parent = _registry().get(p) or ""
    return Path(parent) if parent else None


def is_top_project(path: str | Path | None) -> bool:
    if not path:
        return False
    p = str(pathx.project_dir(path))
    table = _registry()
    return p in table and not table[p]


def top_project(path: str | Path | None) -> Optional[Path]:
    if not path:
        return None
    p = pathx.project_dir(path)
    if not p.is_absolute():
        return None
    table = _registry()
    cur = str(p)
    if cur not in table:
        return None
    seen: set[str] = set()
    while True:
        parent = table.get(cur) or ""
        pass
        if not parent or parent in seen:
            return Path(cur)
        seen.add(cur)
        if parent not in table:
            return Path(cur)
        cur = parent


def project_chain(path: str | Path | None) -> list[Path]:
    if not path:
        return []
    p = pathx.project_dir(path)
    out = [p]
    table = _registry()
    cur = str(p)
    cur = table.get(cur, "")
    seen = {str(p)}
    while cur and cur not in seen:
        seen.add(cur)
        out.append(Path(cur))
        cur = table.get(cur, "")
    return out


def nearest_registered(p: str | Path) -> Optional[Path]:
    key = pathx.project_path(str(p))
    if not key:
        return None
    best = ""
    for cand in _registry():
        if key == cand or key.startswith(cand + "/"):
            if len(cand) > len(best):
                best = cand
    return Path(best) if best else None


def plugin_package_of(path: str | Path | None) -> tuple[Optional[Path], str]:
    if not path:
        return None, ""
    p = pathx.project_dir(path)
    try:
        p = Path(os.path.normpath(str(p)))
    except OSError:
        return None, ""
    owner = p if is_project(p) else nearest_registered(p)
    if owner is None:
        return None, ""
    root = Path(os.path.normpath(str(project_plugins_dir(owner))))
    if p == root or not p.is_relative_to(root):
        return owner, ""
    return owner, p.relative_to(root).parts[0]


def project_agent_dir(project: str | Path) -> Path:
    return Path(project) / AGENT_DIR_NAME


def project_subdir(project: str | Path, name: str) -> Path:
    return project_agent_dir(project) / name


def project_workflows_dir(project: str | Path) -> Path:
    return project_subdir(project, WORKFLOWS_DIR_NAME)


def project_skills_dir(project: str | Path) -> Path:
    return project_subdir(project, SKILLS_DIR_NAME)


def project_agents_dir(project: str | Path) -> Path:
    return project_subdir(project, AGENTS_DIR_NAME)


def project_plugins_dir(project: str | Path) -> Path:
    return project_subdir(project, PLUGINS_DIR_NAME)


def project_tools_dir(project: str | Path) -> Path:
    return project_subdir(project, TOOLS_DIR_NAME)


def project_ops_dir(project: str | Path) -> Path:
    return project_subdir(project, OPS_DIR_NAME)


def project_kv_json(project: str | Path) -> Path:
    return project_agent_dir(project) / "kv.json"


def project_mcp_dir(project: str | Path) -> Path:
    return project_subdir(project, MCP_DIR_NAME)


def project_mcp_json(project: str | Path) -> Path:
    return project_subdir(project, MCP_JSON)

def _session_hot(project: str, name: str) -> Path:
    if project and Path(project).is_absolute():
        return _hot_path(project, name, project_agent_dir(project) / name)
    return sessions_dir() / name


def session_db(project: str, sid: str) -> Path:
    return _session_hot(project, f"chat.{sid}.db")


def session_tool_output_dir(project: str, sid: str) -> Path:
    return _session_hot(project, f"tool_output.{sid}")


def project_runs_dir(project: str | Path) -> Path:
    return _hot_path(project, RUNS_DIR_NAME, project_agent_dir(project) / RUNS_DIR_NAME)


def project_subagents_dir(project: str | Path) -> Path:
    return _hot_path(project, SUBAGENTS_DIR_NAME,
                     project_agent_dir(project) / SUBAGENTS_DIR_NAME)
