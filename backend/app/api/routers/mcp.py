from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..errors import bad_request, conflict, not_found, server_error
from ...config import McpServerCfg
from ...github import GitHubError, whoami
from ...github import status as github_status
from ...mcp import spec as mcp_spec
from ...store import layout, vault
from ..deps import Container, get_container

router = APIRouter()


def _dir_of(project: str) -> Path:
    if not project:
        return layout.mcp_dir()
    p = Path(project)
    if not layout.is_project(p):
        raise bad_request(f"不是项目目录: {project}")
    return layout.project_mcp_dir(p)


def _cfg_of(name: str, project: str = "") -> McpServerCfg:
    raw = mcp_spec.load_dir(_dir_of(project)).get(name)
    if raw is None and project:
        raw = mcp_spec.project_servers(project).get(name)
    if raw is None:
        raise not_found(f"MCP 服务器 {name} 不存在")
    return raw


def _save(name: str, cfg: McpServerCfg, project: str,
          c: Container) -> None:
    mcp_spec.save_file(_dir_of(project), name, cfg)
    if not project:
        return
    from ...plugins.adopt import adopt_mcp
    try:
        adopt_mcp(project, name, installs=c.installs)
    except ValueError:
        pass


pass
class GithubTokenIn(BaseModel):
    token: str = ""


@router.get("/api/mcp/github")
def github_get():
    return github_status()


@router.put("/api/mcp/github")
def github_put(body: GithubTokenIn, c: Container = Depends(get_container)):
    raw = (body.token or "").strip()
    if raw == vault.MASKED:
        return {**github_status(), "ok": True}
    c.store.config.settings.githubToken = raw
    c.store.save()
    from ...github.client import clear_cache
    clear_cache()
    return {**github_status(), "ok": True}


@router.post("/api/mcp/github/test")
def github_test():
    try:
        return {"ok": True, **whoami()}
    except GitHubError as e:
        return {"ok": False, "error": str(e)}


pass
@router.get("/api/mcp")
def mcp_status(project: str = "", c: Container = Depends(get_container)):
    servers = mcp_spec.load_dir(_dir_of(project))
    if project:
        for n, cfg in mcp_spec.project_servers(project).items():
            servers.setdefault(n, cfg)
    return {"servers": {n: mcp_spec.public(cfg) for n, cfg in servers.items()},
            "status": c.mcp.status(),
            "github": github_status()}


@router.post("/api/mcp")
async def mcp_add(body: dict, c: Container = Depends(get_container)):
    name = str(body.get("name") or "").strip()
    if not name:
        raise bad_request("缺少服务器名 name")
    project = str(body.get("project") or "")
    if name in mcp_spec.load_dir(_dir_of(project)):
        raise conflict(f"MCP 服务器 {name} 已存在")
    cfg = McpServerCfg(**{k: v for k, v in body.items()
                          if k not in ("name", "project")})
    _save(name, cfg, project, c)
    conn = await c.mcp.replace_server(name, mcp_spec.effective(name, cfg))
    return {"ok": True, "name": name, "connected": bool(conn.ready),
            "error": conn.error}


@router.patch("/api/mcp/{name}")
async def mcp_update(name: str, body: dict, project: str = "",
                     c: Container = Depends(get_container)):
    old = _cfg_of(name, project)
    merged = mcp_spec.merge_masked(body, old)
    merged.pop("name", None)
    cfg = McpServerCfg(**{**old.model_dump(), **merged})
    _save(name, cfg, project, c)
    conn = await c.mcp.replace_server(name, mcp_spec.effective(name, cfg))
    return {"ok": True, "name": name, "connected": bool(conn.ready),
            "error": conn.error}


@router.delete("/api/mcp/{name}")
async def mcp_delete(name: str, project: str = "",
                     c: Container = Depends(get_container)):
    _cfg_of(name, project)
    mcp_spec.delete_file(_dir_of(project), name)
    if project:
        from ...plugins.adopt import unadopt_mcp
        unadopt_mcp(project, name, installs=c.installs)
    await c.mcp.remove_server(name)
    return {"ok": True}


@router.post("/api/mcp/{name}/reload")
async def mcp_reload_server(name: str, project: str = "",
                            c: Container = Depends(get_container)):
    cfg = _cfg_of(name, project)
    conn = await c.mcp.replace_server(name, mcp_spec.effective(name, cfg),
                                      wait_ready=15)
    return {"ok": True, "connected": bool(conn.ready), "error": conn.error,
            "error_detail": conn.error_detail}


@router.post("/api/mcp/{name}/refresh")
async def mcp_refresh_tools(name: str, c: Container = Depends(get_container)):
    _cfg_of(name)
    result = await c.mcp.refresh_tools(name)
    if "error" in result:
        raise server_error(result["error"])
    return result


class McpTestIn(BaseModel):
    tool: str
    args: dict = {}


@router.post("/api/mcp/{name}/test")
async def mcp_test_tool(name: str, body: McpTestIn,
                        c: Container = Depends(get_container)):
    _cfg_of(name)
    full_name = f"mcp__{name}__{body.tool}"
    result = await c.mcp.call(full_name, body.args)
    return {"result": result}
