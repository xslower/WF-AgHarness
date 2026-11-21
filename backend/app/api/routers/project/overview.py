from __future__ import annotations

from pathlib import Path
from typing import Any

from ....store import layout
from ....util import pathx

pass
MAX_SESSIONS = 20


def find_children(tree: dict, p: Path) -> list[dict]:

    def walk(node: dict) -> list[dict]:
        if Path(node.get("path", "")) == p:
            return [{"name": ch["name"], "path": ch["path"],
                     "depth": ch.get("depth", 1),
                     "children": len(ch.get("children") or [])}
                    for ch in node.get("children") or []]
        for ch in node.get("children") or []:
            hit = walk(ch)
            if hit:
                return hit
        return []

    return walk(tree)


def children_of(container: Any, p: Path) -> list[dict]:
    from ....plugins.visibility import filter_children

    try:
        ids = find_children(container.projects.tree(), p)
    except Exception:
        return []
    return filter_children(ids, container, p)



def parent_of(p: Path, is_project: bool, is_top: bool) -> str | None:
    if not is_project or is_top:
        return None
    parent = layout.parent_project(p)
    return str(parent) if parent else None


def _session_row(it: dict) -> dict:
    return {
        "id": it.get("id"), "title": it.get("title") or "未命名",
        "kind": it.get("kind") or "chat",
        "created_at": it.get("created_at"),
        "updated_at": it.get("updated_at"),
        "message_count": it.get("message_count") or 0,
    }


def sessions_of(container: Any, p: Path) -> list[dict]:
    try:
        items = container.sessions.list(str(p), kind="")
        items = sorted(items,
                       key=lambda s: s.get("updated_at") or s.get("created_at") or 0,
                       reverse=True)[:MAX_SESSIONS]
        return [_session_row(it) for it in items]
    except Exception:
        return []


def workflows_of(container: Any, p: Path) -> list[dict]:
    try:
        from ....plugins.visibility import filter_workflows
        out = []
        for wf in container.wf_engine(str(p)).list():
            pass
            if wf.get("internal"):
                continue
            nodes = wf.get("nodes")
            out.append({
                "name": wf.get("name"),
                "status": wf.get("status") or "",
                "nodes": nodes if isinstance(nodes, int) else len(nodes or []),
                "updated_at": wf.get("updated_at") or wf.get("mtime"),
            })
        return filter_workflows(out, p)
    except Exception:
        return []



def _readme_of(root: Path) -> str:
    from ....plugins import detail

    return detail.readme_of(root)


def _plugin_workflow_names(root: Path) -> list[str]:
    from ....plugins import detail

    return detail.workflow_names(root)


def _plugin_state_keys(plugin_id: str, project: str) -> list[str]:
    from ....plugins import detail

    return detail.state_keys(plugin_id, project)





def skills_of(p: Path) -> list[str]:
    try:
        from ....skills import list_skills_of
        return list_skills_of(str(p))
    except Exception:
        return []




def overview(container: Any, path: str) -> dict:
    from ....plugins.visibility import prefs_of
    from ....project.git_mode import git_enabled
    p = pathx.project_dir(path)
    pass
    pass
    pass
    is_proj = layout.is_project(p)
    is_top = layout.is_top_project(p)
    return {
        "path": str(p),
        "name": p.name,
        "is_project": is_proj,
        "is_top": is_top,
        "parent": parent_of(p, is_proj, is_top),
        "children": children_of(container, p),
        "sessions": sessions_of(container, p),
        "workflows": workflows_of(container, p),
        "plugins": plugins_of(container, p),
        "tools": tools_of(container, p),
        "skills": skills_of(p),
        # 扫描结果不在这里返回（2026-11-08 用户要求「插件扫描改为手动，不自动进行」）。
        # 唯一真源是 GET /api/plugins/discover；主页点「扫描插件」才调，结果只存前端 state。
        "ui": prefs_of(p),
        "git": {"enabled": git_enabled(p)},
    }


def _rows_of(container: Any, p: Path) -> list[dict]:
    try:
        return container.installs.list_plugins(str(p))
    except Exception:
        return []


def plugins_of(container: Any, p: Path) -> list:
    from ....plugins import detail

    out = []
    for row in _rows_of(container, p):
        if _is_pseudo_row(row):
            continue
        out.append(detail.describe(row))
    return out




def _is_pseudo_row(row: dict) -> bool:

    from ....plugins.location import unit_kind_of

    return bool(unit_kind_of(str(row.get("id") or "")))


def tools_of(container: Any, p: Path) -> list:
    from ....plugins import location, tool_unit

    rows = _rows_of(container, p)
    out = []
    for row in rows:
        pid = str(row.get("id") or "")
        if location.unit_kind_of(pid) != "tool":
            continue
        item = {"id": row.get("id"), "name": location.unit_name_of(pid),
                "desc": "", "path": "", "has_config": False,
                "project": row.get("project") or ""}
        try:
            root = location.resolve_package(row, str(row.get("project") or ""))
            item["path"] = str(root)
            pass
            if (root / tool_unit.TOOL_YAML).is_file():
                unit = tool_unit.from_dir(root)
                item["name"] = unit.meta.get("name") or item["name"]
                item["desc"] = unit.meta.get("desc") or ""
                item["has_config"] = bool(unit.meta.get("config"))
                if unit.meta.get("config_error"):
                    item["config_error"] = unit.meta["config_error"]
        except (ValueError, OSError) as e:
            pass
            pass
            item["error"] = str(e)
        out.append(item)
    return out
