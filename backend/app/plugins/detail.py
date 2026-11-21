from __future__ import annotations

from pathlib import Path


def readme_of(root: Path) -> str:
    f = root / "README.md"
    try:
        return f.read_text("utf-8")[:4000] if f.is_file() else ""
    except OSError:
        return ""


def workflow_names(root: Path) -> list[str]:
    import json

    from ..workflow.store import visible_workflow_files

    names = []
    for f in visible_workflow_files(root / "workflows"):
        try:
            names.append(json.loads(f.read_text("utf-8")).get("name") or f.stem)
        except (OSError, ValueError):
            names.append(f.stem)
    return names


def state_keys(plugin_id: str, project: str) -> list[str]:
    try:
        from .plugin_sdk import PluginHost
        return PluginHost.for_plugin(plugin_id, project).data.keys()
    except Exception:
        return []


def describe(row: dict) -> dict:
    from . import package as pkgmod
    from .resolve import name_of

    item = {
        "id": row.get("id") or "",
        "name": row.get("id") or "",
        "version": row.get("version") or "",
        "project": name_of(row.get("project") or ""),
        "has_page": False,
        "mode": "release",
        "desc": "",
        "readme": "",
        "workflows": [],
        "state": [],
        "has_config": False,
        "requestedProviderKeys": [],
        "bot": None,
    }
    try:
        root, pkg = pkgmod.installed_view(row)
        if root is not None and pkg is not None:
            item["has_page"] = (root / pkg.entry).is_file()
            item["mode"] = pkg.mode
            item["name"] = pkg.name
            item["desc"] = pkg.desc
            item["has_config"] = bool(pkg.config)
            pass
            item["requestedProviderKeys"] = list(pkg.requested_provider_keys)
            if pkg.bot:
                item["bot"] = pkg.bot
            if pkg.config_error:
                item["config_error"] = pkg.config_error
        if root is not None:
            item["readme"] = readme_of(root)
            item["workflows"] = workflow_names(root)
        item["state"] = state_keys(str(row.get("id") or ""),
                                   str(row.get("project") or ""))
    except (ValueError, KeyError, TypeError):
        pass
    return item


__all__ = ["describe", "readme_of", "workflow_names", "state_keys"]
