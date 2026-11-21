
from __future__ import annotations

from pathlib import Path

from ..store import layout
from ..util import pathx
from . import location


def home_of(plugin_id: str, project: str = "") -> Path | None:
    pid = str(plugin_id or "").strip()
    if not pid or location.unit_kind_of(pid):
        return None
    from .install import InstallStore
    rec = InstallStore().get_plugin(pid, project)
    if not rec:
        return None
    try:
        pkg = location.resolve_package(rec, project)
    except ValueError:
        return None
    return pkg if pkg.is_dir() else None


def file_in(plugin_id: str, name: str, project: str = "") -> Path | None:
    home = home_of(plugin_id, project)
    return (home / name) if home is not None else None


def data_json(plugin_id: str, project: str = "") -> Path | None:
    return file_in(plugin_id, "data.json", project)


def config_json(plugin_id: str, project: str = "") -> Path | None:
    return file_in(plugin_id, "config.json", project)


def stores_dir(plugin_id: str, project: str = "") -> Path | None:
    return file_in(plugin_id, "store.db", project)


def project_kv_path(project: str) -> Path:
    return layout.project_kv_json(pathx.project_dir(project))

__all__ = ["home_of", "file_in", "data_json", "config_json", "stores_dir",
           "project_kv_path"]
