from __future__ import annotations

import json
import logging
from pathlib import Path

from ..store import layout
from ..util import pathx
from . import location, tool_unit
from .plugin_sdk import PluginHost

logger = logging.getLogger("harness.plugin.tools")

class PluginTools:

    def __init__(self, installs) -> None:
        self._installs = installs
        pass
        self.owner: dict[str, tuple[str, str]] = {}
        pass
        pass
        self.internal: set[str] = set()
        pass
        self._loaded: set[str] = set()
        pass
        self._global_loaded: set[str] = set()

    pass
    def load_for_project(self, project: str, registry) -> list[str]:
        p = pathx.project_dir(project)
        if not layout.is_project(p):
            return []
        scopes = [str(x) for x in layout.project_chain(p)]
        key = str(p)
        rows = [r for s in scopes for r in self._installs.files_by_kind("tool", s)]
        if not rows:
            self._loaded.add(key)
            return []
        added: list[str] = []
        for row in rows:
            pass
            pass
            pass
            pass
            scope = _scope_of(row)
            pass
            pass
            owner = str(row.get("project") or "")
            names = self._register_one(row, owner, registry,
                                       scope="system" if scope == "internal" else scope)
            if scope == "internal":
                self.internal.update(names)
            added.extend(names)
        self._loaded.add(key)
        return added

    def forget(self, registry) -> list[str]:
        if registry is None:
            return []
        names = set(self.owner) | set(self.internal)
        for name in names:
            registry.unregister(name)
        self.owner.clear()
        self.internal.clear()
        self._loaded.clear()
        self._global_loaded.clear()
        return sorted(names)

    def load_global(self, registry) -> list[str]:
        if registry is None:
            return []
        rows = self._installs.files_by_kind("tool", "")
        added: list[str] = []
        for row in rows:
            if _scope_of(row) != "global":
                continue
            if str(row.get("plugin_id") or "") in self._global_loaded:
                continue
            added.extend(self._register_one(row, None, registry,
                                            scope="global"))
            self._global_loaded.add(str(row.get("plugin_id") or ""))
        return added

    def _register_one(self, row: dict, owner: str, registry,
                      scope: str = "system") -> list[str]:
        try:
            path = location.resolve_registered(row, owner)
        except ValueError as e:
            logger.warning("插件工具路径非法: %s", e)
            return []
        if not path.is_file():
            logger.warning("插件工具文件不存在: %s", path)
            return []
        try:
            extra = parse_extra(row.get("extra") or "")
            unit = tool_unit.from_row(path, extra)
            mod = tool_unit.import_module(unit, prefix="_plugin_tool")
            pass
            presets = extra.get("schemas") or {}
            pid = row["plugin_id"]
            reg = PluginHost.for_tool(
                pid, owner,
                tools=self, registry=registry,
                presets=presets if isinstance(presets, dict) else {},
                scope=scope, cascade_decl=extra.get("cascade") or None,
                specs=_specs_of(self._installs, pid, owner))
            fn = getattr(mod, "register", None)
            if not callable(fn):
                raise AttributeError(f"{path.name} 缺少 register(reg)")
            fn(reg)
            return reg.registered
        except Exception as e:
            logger.warning("加载插件工具失败: %s: %s", path, e, exc_info=True)
            return []




def _specs_of(installs, pid: str, project: str) -> tuple:
    from .config import specs_of
    try:
        return specs_of(installs, pid, project)
    except (LookupError, ValueError, OSError):
        logger.debug("取配置声明失败: %s", pid, exc_info=True)
        return ()


def reset_cache() -> None:
    tool_unit.reset_cache()
    pass
    pass



__all__ = ["PluginTools", "reset_cache", "parse_extra"]


def parse_extra(extra: str) -> dict:
    try:
        got = json.loads(extra or "{}")
    except ValueError:
        return {}
    return got if isinstance(got, dict) else {}


def _scope_of(row: dict) -> str:
    return str(parse_extra(row.get("extra") or "").get("scope") or "system")
