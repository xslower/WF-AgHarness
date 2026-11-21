from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Optional

from fastapi import FastAPI, Request

from ..config import ConfigStore
from ..store import layout
from ..chat.compaction import ContextCompactor
from ..envs import EnvManager
from ..provider.gateway import ModelGateway
from ..event.bus import EventHub
from ..mcp import MCPManager
from ..tools.builtin.memory import MemoryStore
from ..plugins import PluginManager
from ..security.engine import ApprovalManager, PolicyEngine
from ..project.manager import ProjectManager
from ..chat.recent import RecentStore
from ..agent.runner import AgentRunner
from ..workflow.nodes.registry import NodeRegistry
from ..chat.session_runtime import SessionRuntimeRegistry
from ..chat.sessions import SessionStore
from ..tools import ToolRegistry
from ..store.usage import UsageTracker
from ..workflow import WorkflowEngine, WorkflowRouter

logger = logging.getLogger("harness.deps")

pass
pass
_THROTTLE_RESET_REASONS = frozenset({
    "queue", "provider-add", "provider-update", "provider-delete",
    "model-remove", "fetch-models", "provider-refresh",
})


@dataclass
class Container:

    store: ConfigStore
    sessions: SessionStore
    gateway: ModelGateway
    registry: ToolRegistry
    mcp: MCPManager
    policy: PolicyEngine
    approvals: ApprovalManager
    envs: EnvManager
    projects: ProjectManager
    memory: MemoryStore
    usage: UsageTracker
    compactor: ContextCompactor
    runner: AgentRunner
    pluginman: PluginManager
    nodes: Optional[NodeRegistry] = None
    wf_router: Optional[WorkflowRouter] = None
    _workflow_engine: Optional[WorkflowEngine] = None
    hub: Optional[EventHub] = None
    recent: Optional[RecentStore] = None
    _session_rt: Optional[SessionRuntimeRegistry] = None
    _installs: Optional[object] = None
    plugin_api: Optional[object] = None

    @property
    def installs(self):
        if self._installs is None:
            from ..plugins.install import InstallStore
            self._installs = InstallStore()
        return self._installs

    def session_rt(self) -> SessionRuntimeRegistry:
        if self._session_rt is None:
            self._session_rt = SessionRuntimeRegistry()
        return self._session_rt

    def plan_of(self, sid: str):
        return self.runner.plan_for(sid) if self.runner is not None else None


    def _ensure_router(self) -> WorkflowRouter:
        if self.wf_router is None:
            self.wf_router = WorkflowRouter(
                gateway=self.gateway, registry=self.registry,
                agent_runner=self.runner, mcp=self.mcp, nodes=self.nodes,
                sessions=self.sessions)
            self.runner.wf_engine = self.wf_router
        return self.wf_router

    def wf_engine(self, project: str = "") -> WorkflowEngine:
        router = self._ensure_router()
        if not project:
            if self._workflow_engine is None:
                self._workflow_engine = router.engine_for("")
            return self._workflow_engine
        return router.engine_for(project)

    def sync_config(self, reason: str = "") -> None:
        self.gateway.config = self.store.config
        pass
        pass
        pass
        pass
        if reason in _THROTTLE_RESET_REASONS:
            self.gateway.reset_throttle_state()
        self.envs.bindings = {"python": self.store.config.settings.envPython,
                              "node": self.store.config.settings.envNode}
        self.projects.root = (self.store.config.settings.projectsRoot
                              or str(layout.default_projects_root()))
        pass
        try:
            from ..event.bus import HUB
            (self.hub or HUB).publish("config.changed", {"reason": reason})
        except Exception:
            logger.debug("publish config.changed 失败: %s", reason, exc_info=True)


pass
pass
_ACTIVE_CONTAINER: Optional[Container] = None


def set_container(app: FastAPI, container: Container) -> None:
    global _ACTIVE_CONTAINER
    app.state.container = container
    _ACTIVE_CONTAINER = container
    hub = getattr(container, "hub", None)
    recent = getattr(container, "recent", None)
    if hub is not None and recent is not None:
        recent.attach(hub)


def active_container() -> Optional[Container]:
    return _ACTIVE_CONTAINER


def get_container(request: Request) -> Container:
    return request.app.state.container
