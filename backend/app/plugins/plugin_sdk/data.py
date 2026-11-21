from __future__ import annotations

import os
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from ...store import layout
from ...util import jsonx, pathx

pass
pass
pass
CODE_PREAMBLE = ("from app.plugins.plugin_sdk import PluginHost\n"
                 "plugin = PluginHost.for_request(_WORKSPACE)\n")

pass
pass
WORKSPACE_VAR = "_WORKSPACE"

pass
pass
pass
ACTIVE_PLUGIN_ID: ContextVar[str] = ContextVar("harness_plugin_id", default="")

_SAFE_CHARS = set("abcdefghijklmnopqrstuvwxyz"
                  "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")


def _safe(name: str) -> str:
    out = "".join(c if c in _SAFE_CHARS else "_" for c in str(name))
    return (out.strip("._") or "default")[:80]


def namespace_for_plugin(plugin_id: str, project: str) -> tuple[str, str]:
    p = pathx.project_dir(project) if project else None
    return (str(p) if p else ""), f"plugin-{_safe(plugin_id)}"


def request_plugin_id() -> str:
    return (os.environ.get("HARNESS_PLUGIN_ID") or
            ACTIVE_PLUGIN_ID.get() or "").strip()


def namespace_for_request(path: str | Path | None) -> tuple[str, str]:
    pid = request_plugin_id()
    if not pid:
        return namespace_for_cwd(path)
    p = pathx.project_dir(path) if path else None
    return (str(p) if p else ""), f"plugin-{_safe(pid)}"


def namespace_for_cwd(path: str | Path | None) -> tuple[str, str]:
    cwd = Path(path or os.getcwd())
    top, pkg_name = layout.plugin_package_of(cwd)
    project = str(top) if top else ""
    if not pkg_name:
        return project, f"project-{_safe(top.name if top else 'global')}"
    pkg_root = layout.project_plugins_dir(top) / pkg_name
    try:
        from ..package import load_package
        pid = load_package(pkg_root).id
    except Exception:
        pid = pkg_name
    return project, f"plugin-{_safe(pid)}"


class PluginData:

    def __init__(self, project: str, namespace: str,
                 path: Path | None = None) -> None:
        self.project = project
        self.namespace = namespace
        self.path = path or self._default_path(project, namespace)

    @staticmethod
    def _default_path(project: str, namespace: str) -> Path:
        ns = str(namespace or "")
        if ns.startswith("plugin-"):
            pass
            pass
            pid = ns[len("plugin-"):]
            try:
                from ..homes import data_json
                p = data_json(pid, project)
            except Exception:
                p = None
            if p is not None:
                return p
            base = (layout.project_agent_dir(Path(project)) if project else
                    layout.data_dir())
            return base / f"{_safe(ns)}.json"
        if project:
            from ..homes import project_kv_path
            return project_kv_path(project)
        return layout.data_dir() / "kv.json"

    def _all(self) -> dict[str, Any]:
        data = jsonx.read_json(self.path, {})
        return data if isinstance(data, dict) else {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._all().get(str(key), default)

    def set(self, key: str, value: Any) -> None:
        data = self._all()
        data[str(key)] = value
        jsonx.write_json(self.path, data)

    def delete(self, key: str) -> bool:
        data = self._all()
        if str(key) not in data:
            return False
        del data[str(key)]
        jsonx.write_json(self.path, data)
        return True

    def keys(self) -> list[str]:
        return sorted(self._all())


__all__ = ["PluginData", "CODE_PREAMBLE", "WORKSPACE_VAR",
           "ACTIVE_PLUGIN_ID", "request_plugin_id",
           "namespace_for_plugin", "namespace_for_request",
           "namespace_for_cwd"]
