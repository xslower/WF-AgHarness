from __future__ import annotations

from fastapi import APIRouter

from . import approvals, artifacts, chat_ws, checkpoints, config, envs, events, mcp, plugin_api, plugins, providers, sessions, skills, subagents, themes, timers, trash, workflows
from . import project as project_routes

ROUTERS: list[APIRouter] = [
    events.router,
    chat_ws.router,
    config.router,
    providers.router,
    sessions.router,
    *project_routes.ROUTERS,
    workflows.router,
    artifacts.router,
    trash.router,
    checkpoints.router,
    envs.router,
    mcp.router,
    skills.router,
    approvals.router,
    plugins.router,
    # 插件统一入口 `/api/plugin`（query 制，静态 + handler）。**必须排在
    # plugins.router 之后**（具体路由先匹配，避免 `/api/plugins/install` 被抢），
    # 也**必须排在 factory._mount_frontend 的 SPA 兜底之前**（兜底在最后挂）。
    plugin_api.router,
    themes.router,
    timers.router,
    subagents.router,
]
