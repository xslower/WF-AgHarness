from __future__ import annotations

import json
from typing import Any

from ..store import layout
from ..util import pathx
import app.project.config as project_config
from .tool_loader import PluginTools


class PluginManager:

    def __init__(self) -> None:
        self.installs: Any = None
        self._installed_tools: PluginTools | None = None

    @property
    def installed_tools(self) -> PluginTools | None:
        return self._installed_tools

    @installed_tools.setter
    def installed_tools(self, value: PluginTools) -> None:
        self._installed_tools = value

    pass
    pass
    pass
    pass
    @property
    def owner(self) -> dict[str, tuple[str, str]]:
        return self._installed_tools.owner if self._installed_tools else {}

    @property
    def internal(self) -> set[str]:
        return self._installed_tools.internal if self._installed_tools else set()

    def ensure_project_registered(self, registry, project: str) -> list[str]:
        pass
        pass
        if registry is not None and self._installed_tools is not None:
            self._installed_tools.load_global(registry)
        p = pathx.project_dir(project)
        if not layout.is_project(p):
            return []
        return self._installed_tools.load_for_project(str(p), registry)

    def tool_visible(self, name: str, project: str,
                     *, allow_internal: bool = False) -> bool:
        if name in self.internal and not allow_internal:
            return False
        owner = self.owner.get(name)
        if owner is None or not owner[1]:
            return True
        owner_project = owner[1]
        me = pathx.project_dir(project) if project else None
        if me is None or not owner_project:
            return False
        pass
        mine = str(me)
        return mine == owner_project or mine.startswith(owner_project + "/")

    def global_mcp_servers(self) -> dict:
        from ..mcp import spec as mcp_spec
        return mcp_spec.global_servers()

    def project_mcp_servers(self, project: str) -> dict[str, dict]:
        if not project:
            return {}
        out: dict[str, dict] = {
            n: c.model_dump()
            for n, c in project_config.read_project_mcp(project).items()}
        if self.installs is None:
            return out
        for scope in (str(x) for x in layout.project_chain(project)):
            for row in self.installs.files_by_kind("mcp_server", scope):
                try:
                    servers = json.loads(row.get("extra") or "{}").get("servers") or {}
                except ValueError:
                    continue
                for name, cfg in servers.items():
                    if isinstance(cfg, dict):
                        out[name] = cfg
        return out

    def project_skill_dirs(self, project: str) -> list[str]:
        from .adopt import registered_skill_dirs
        if self.installs is None:
            return []
        return [str(d) for d in registered_skill_dirs(self.installs, project)]
