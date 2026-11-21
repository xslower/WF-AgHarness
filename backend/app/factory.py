from __future__ import annotations

import asyncio
import logging
import logging.handlers
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import boot
from .api.deps import Container, set_container
from .api.routers import ROUTERS
from .config import ConfigStore
from .chat.compaction import ContextCompactor
from .envs import EnvManager
from .provider.gateway import ModelGateway
from .provider.registry import ModelRegistry
from .event.bus import HUB
from .mcp import MCPManager
from .mcp import spec as mcp_spec
from .tools.builtin.memory import MemoryStore
from .plugins import PluginManager
from .plugins.install import InstallStore
from .agent.profiles import build_profile_registry
from .provider.adapters.registry import build_adapter_registry
from .security.engine import ApprovalManager, PolicyEngine
from .project.manager import ProjectManager
from .chat.recent import RecentStore
from .agent.runner import AgentRunner
from .workflow.nodes import build_default_nodes
from .chat.sessions import SessionStore
from .chat.session_runtime import SessionRuntimeRegistry
from .tools.builtin import build_tools
from .skills import bind_pluginman

from .store.usage import UsageTracker
from .workflow import WorkflowRouter

pass
_LOG_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.handlers.RotatingFileHandler(
            _LOG_DIR / "server.log", maxBytes=10 * 1024 * 1024,
            backupCount=5, encoding="utf-8"),
    ],
)
logger = logging.getLogger("harness")


def build_container() -> Container:
    store = ConfigStore()
    sessions = SessionStore()
    pass
    from .store import event_log
    event_log.set_store(sessions)
    gateway = ModelGateway(store.config, adapters=build_adapter_registry())
    pass
    pass
    registry = build_tools(gateway)
    mcp = MCPManager(mcp_spec.global_servers)
    pass
    pass
    from . import github as github_api
    github_api.client.bind_settings(lambda: store.config.settings)
    policy = PolicyEngine(gateway,
                          settings_getter=lambda: store.config.settings)
    approvals = ApprovalManager()
    envs = EnvManager({"python": store.config.settings.envPython,
                       "node": store.config.settings.envNode})
    projects = ProjectManager(store.config.settings.projectsRoot)
    memory = MemoryStore(projects)
    usage = UsageTracker(unit_price=ModelRegistry(store.config).unit_price)
    compactor = ContextCompactor(gateway)
    pass
    pass
    pass
    pass
    gateway.usage_sink = usage.record
    gateway.usage_today = usage.today_tokens
    nodes = build_default_nodes()
    pass
    pass
    session_rt = SessionRuntimeRegistry()
    runner = AgentRunner(gateway, registry, mcp=mcp, policy=policy,
                         approvals=approvals, envs=envs, memory=memory,
                         profiles=build_profile_registry(), sessions=sessions,
                         session_rt=session_rt)
    pass
    pass
    pass
    pass
    installs = InstallStore()
    wf_router = WorkflowRouter(
        gateway=gateway, registry=registry, agent_runner=runner, mcp=mcp,
        nodes=nodes, sessions=sessions, installs=installs,
        # 传取值函数：设置页改完 wfMaxConcurrency 立刻生效，不用重建引擎
        max_concurrency=lambda: store.config.settings.wfMaxConcurrency)
    runner.wf_engine = wf_router
    pluginman = PluginManager()
    pass
    recent = RecentStore()
    recent.attach(HUB)
    return Container(
        _installs=installs,
        store=store, sessions=sessions, gateway=gateway,
        registry=registry, mcp=mcp, policy=policy, approvals=approvals,
        envs=envs, projects=projects, memory=memory, usage=usage,
        compactor=compactor, runner=runner, pluginman=pluginman, nodes=nodes,
        wf_router=wf_router, hub=HUB, recent=recent, _session_rt=session_rt)


def register_builtin_plugins(c: Container) -> None:
    c.registry.pluginman = c.pluginman
    from .tools.builtin.meta import update_dynamic_schemas
    c.registry.describe_hook = update_dynamic_schemas
    from .tools import cascade
    cascade.reset()
    from .plugins.tool_loader import PluginTools
    c.pluginman.installed_tools = PluginTools(c.installs)
    c.pluginman.installs = c.installs
    pass
    pass
    try:
        c.pluginman.installed_tools.load_global(c.registry)
    except Exception:
        logger.warning("加载全局插件工具失败", exc_info=True)
    bind_pluginman(c.pluginman)





def create_app() -> FastAPI:
    app = FastAPI(title="Agent Harness")
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
        allow_headers=["*"],
    )
    container = build_container()
    register_builtin_plugins(container)
    _install_plugin_api(container)
    set_container(app, container)
    _install_lifecycle(app)
    for r in ROUTERS:
        app.include_router(r)
    _mount_frontend(app)
    return app


def _install_plugin_api(container) -> None:
    from .plugins.api_dispatch import PluginApiRouter, reset_cache as reset_api
    from .plugins.install import bind_runtime_reload
    from .plugins.tool_loader import reset_cache as reset_tools
    from .plugins import provider_setup

    container.plugin_api = PluginApiRouter(container.installs)

    def reload_runtime() -> None:
        reset_api()
        reset_tools()
        pass
        pass
        from .tools import cascade
        cascade.reset()
        container.plugin_api.reload()
        _reload_outbound(container)
        pass
        pass
        pass
        from .plugins.tool_loader import PluginTools
        old = container.pluginman.installed_tools
        if old is not None:
            old.forget(container.registry)
        container.pluginman.installed_tools = PluginTools(container.installs)
        pass
        pass
        if getattr(container, "wf_router", None) is not None:
            container.wf_router.invalidate()

    bind_runtime_reload(reload_runtime)
    _bind_provider_registrar(container)
    try:
        container.plugin_api.reload()
        _reload_outbound(container)
    except Exception:
        logger.warning("插件注册表重建失败", exc_info=True)


def _bind_provider_registrar(container) -> None:
    from .plugins import provider_setup
    from .provider.models import Provider
    from .provider.meta import make_model

    def registrar(action: str, plugin_id: str, payload: dict):
        cfg = container.store.config
        if action == "create":
            data = dict(payload)
            pass
            if any(p.name == data.get("name") for p in cfg.providers):
                raise ValueError(f"provider 名称已存在: {data.get('name')}")
            p = Provider(**data)
            container.store.add_provider(p)
            pass
            pass
            if (p.apiKey and not p.models
                    and (not p.adapter or p.adapter == "openai_compatible")):

                try:
                    from .plugins.schema_llm import run_sync
                    pairs = run_sync(container.gateway.fetch_models_with_wire(p))
                    for mid, wire in pairs:
                        p.models.append(make_model(mid, wire))
                    container.store.persist_provider(p)
                except Exception:
                    logger.warning("插件 provider %s 模型拉取失败", p.name,
                                   exc_info=True)
            container.sync_config("plugin-provider-add")
            return {"id": p.id, "name": p.name, "models": len(p.models)}
        if action == "delete":
            removed = []
            for p in list(cfg.providers):
                if getattr(p, "pluginId", "") != plugin_id:
                    continue
                name = p.name
                container.store.delete_provider(p.id)
                pass
                for q in (cfg.queues.parent, cfg.queues.child, cfg.queues.summary):
                    q[:] = [s for s in q if not s.startswith(name + "/")]
                removed.append(name)
            container.store.save()
            if removed:
                container.sync_config("plugin-provider-delete")
            return removed
        raise ValueError(f"未知 provider registrar action: {action}")

    provider_setup.bind_provider_registrar(registrar)


def _reload_outbound(container) -> None:
    from .provider.outbound import OUTBOUND
    from .plugins import location
    from .plugins.tool_loader import parse_extra
    import importlib.util

    OUTBOUND.clear()
    for row in container.installs.files_by_kind("outbound_switch", None):
        plugin_id = row.get("plugin_id", "")
        rel_path = row.get("rel_path", "")
        pass
        pass
        extra = parse_extra(row.get("extra") or "")
        handler_name = str(extra.get("handler") or "handle")
        if not plugin_id or not rel_path:
            continue
        try:
            resolved = location.resolve_registered(
                {"rel_path": rel_path, "plugin_id": plugin_id,
                 "kind": "outbound_switch", "project": ""}, "")
            from pathlib import Path
            path = Path(resolved)
            spec = importlib.util.spec_from_file_location(
                f"_harness_outbound_{plugin_id}", str(path))
            if spec is None or spec.loader is None:
                continue
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            handler = getattr(mod, handler_name, None)
            if callable(handler):
                OUTBOUND.register(plugin_id, handler)
        except Exception:
            logger.warning("outbound switch handler load failed plugin=%s",
                           plugin_id, exc_info=True)


pass

pass
pass
_BG_TASK_NAMES = ("janitors_task", "wf_sweep_task")


def _install_lifecycle(app: FastAPI) -> None:

    @app.on_event("startup")
    async def _startup() -> None:
        _on_startup(app)

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        await _on_shutdown(app)


def _on_startup(app: FastAPI) -> None:
    c = app.state.container
    pass
    from .event.fanout import fanout
    fanout.attach()
    pass
    import app.util.loopwatch as loopwatch
    loopwatch.start()
    pass
    pass
    boot.wire_timers(c)
    from .event.schedule import TIMERS
    TIMERS.start(owner="backend")
    pass
    pass
    boot.migrate_legacy(c)
    app.state.janitors_task = asyncio.create_task(boot.run_janitors_once(c))
    pass
    app.state.wf_sweep_task = asyncio.create_task(
        asyncio.to_thread(boot.sweep_workflow_runs, c))

    pass
    pass
    pass
    pass
    app.state.boot_task = asyncio.create_task(boot.warmup(c))

async def _on_shutdown(app: FastAPI) -> None:
    pass
    try:
        boot.dump_shutdown_forensics(app)
    except Exception:
        logger.debug("shutdown forensics 失败", exc_info=True)
    pass
    from .event.fanout import fanout
    fanout.detach()
    pass
    from .event.schedule import TIMERS
    TIMERS.stop()
    import app.util.loopwatch as loopwatch
    loopwatch.stop()
    _cancel_bg_tasks(app)
    warmup_task = getattr(app.state, "boot_task", None)
    pass
    pass
    pass
    try:
        await asyncio.to_thread(app.state.container.usage.close)
    except Exception:
        logger.debug("usage close 失败", exc_info=True)
    if warmup_task is not None and not warmup_task.done():
        warmup_task.cancel()
        try:
            await warmup_task
        except (asyncio.CancelledError, Exception):
            logger.debug("boot_task 取消时抛错", exc_info=True)
    await app.state.container.mcp.close()


def _cancel_bg_tasks(app: FastAPI) -> None:
    for name in _BG_TASK_NAMES:
        task = getattr(app.state, name, None)
        if task is not None:
            task.cancel()


pass

def _mount_frontend(app: FastAPI) -> None:
    dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if not dist.is_dir():
        return
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    pass
    pass
    pass
    @app.middleware("http")
    async def _static_cache_headers(request, call_next):
        resp = await call_next(request)
        path = request.url.path
        if path.startswith("/assets/"):
            resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif not path.startswith("/api/"):
            resp.headers["Cache-Control"] = "no-cache, must-revalidate"
        return resp

    @app.get("/{full_path:path}", include_in_schema=False)
    async def _spa(full_path: str):
        if full_path:
            f = dist / full_path
            if f.is_file():
                return FileResponse(f)
        return FileResponse(dist / "index.html")
