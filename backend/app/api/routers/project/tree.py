from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ...errors import bad_request, forbidden, from_error
from ....project.manager import ProjectError
from ....tools.builtin.fs import trash
from ....util import pathx
from ...deps import Container, get_container

router = APIRouter()

def _move_stores(c: Container) -> dict:
    try:
        installs = c.installs
    except Exception:
        installs = None
    return {"installs": installs}


@router.get("/api/projects/tree")
def projects_tree(c: Container = Depends(get_container)):
    from ....plugins.visibility import filter_children

    def walk(node: dict) -> dict:
        row = dict(node)
        kids = [walk(ch) for ch in node.get("children") or []]
        row["children"] = filter_children(kids, c, node.get("path") or "")
        return row

    tree = c.projects.tree()
    children = [walk(ch) for ch in tree.get("children") or []]
    return {**tree, "children": filter_children(children, c, tree.get("path") or "")}


class UiPrefsIn(BaseModel):
    hiddenPluginProjects: bool = False
    hiddenWorkflows: bool = False


@router.put("/api/projects/ui-prefs")
def projects_put_ui_prefs(path: str, body: UiPrefsIn):
    from ....plugins.visibility import set_prefs
    try:
        return {"ui": set_prefs(path, body.model_dump())}
    except ValueError as e:
        raise bad_request(str(e))


class GitPrefsIn(BaseModel):
    enabled: bool = False


@router.put("/api/projects/git-prefs")
def projects_put_git_prefs(path: str, body: GitPrefsIn):
    from ....project.git_mode import set_git_enabled
    try:
        return {"git": {"enabled": set_git_enabled(path, body.enabled)}}
    except ValueError as e:
        raise bad_request(str(e))


@router.get("/api/projects/file_tree")
def projects_file_tree(project: str, c: Container = Depends(get_container)):
    return c.projects.file_tree(project)


@router.get("/api/projects/file_tree_children")
def projects_file_tree_children(project: str, dir: str = "",
                                c: Container = Depends(get_container)):
    return c.projects.file_tree_children(project, dir)


@router.get("/api/projects/browse")
def projects_browse(path: str = ""):
    base = str(pathx.project_dir(path or "~"))
    try:
        if not os.path.isdir(base):
            raise bad_request(f"不是目录: {base}")
        dirs = []
        for name in sorted(os.listdir(base)):
            full = str(pathx.project_dir(os.path.join(base, name)))
            if os.path.isdir(full) and not name.startswith("."):
                dirs.append({"name": name, "path": full})
        return {"current": base,
                "parent": str(Path(base).parent) if base != "/" else "",
                "dirs": dirs}
    except PermissionError:
        raise forbidden(f"无权限访问: {base}")
    except OSError as e:
        raise from_error(e)


class ProjectRegisterIn(BaseModel):
    path: str


@router.post("/api/projects/register")
def projects_register(p: ProjectRegisterIn, c: Container = Depends(get_container)):
    try:
        return c.projects.register(p.path, sessions=c.sessions)
    except ProjectError as e:
        raise from_error(e)


class ProjectMoveIn(BaseModel):
    path: str
    parent: str = ""


@router.post("/api/projects/move")
def projects_move(p: ProjectMoveIn, c: Container = Depends(get_container)):
    from ....project.relocate import RelocateError, relocate
    try:
        return relocate(c.projects, c.sessions, p.path, p.parent,
                        stores=_move_stores(c))
    except (RelocateError, ProjectError) as e:
        raise from_error(e)


class ProjectMigrateIn(BaseModel):
    old: str
    new: str


@router.post("/api/projects/migrate")
def projects_migrate(p: ProjectMigrateIn, c: Container = Depends(get_container)):
    from ....project.relocate import RelocateError, migrate_orphan
    try:
        return migrate_orphan(c.projects, c.sessions, p.old, p.new,
                              stores=_move_stores(c))
    except (RelocateError, ProjectError) as e:
        raise from_error(e)


@router.delete("/api/projects")
def projects_unregister(path: str, delete_files: bool = False,
                        c: Container = Depends(get_container)):
    try:
        ok = c.projects.unregister(path)
    except ProjectError as e:
        raise from_error(e)
    trashed = ""
    if delete_files and ok:
        root = Path(path)
        if root.is_dir():
            try:
                trashed = str(trash.move_to_trash(root.parent, root))
            except (ValueError, OSError) as e:
                raise from_error(e)
    return {"ok": ok, "trashed": trashed}
pass

@router.get("/api/projects/memory")
def memory_list(path: str, c: Container = Depends(get_container)):
    return {"entries": c.memory.load(path), "inherited": c.memory.effective(path),
            "docs": c.memory.docs_files(path)}


class MemoryIn(BaseModel):
    path: str
    content: str


@router.post("/api/projects/memory")
def memory_add(m: MemoryIn, c: Container = Depends(get_container)):
    try:
        return c.memory.add(m.path, m.content)
    except ValueError as e:
        raise from_error(e)


@router.delete("/api/projects/memory")
def memory_del(path: str, mid: str, c: Container = Depends(get_container)):
    return {"ok": c.memory.delete(path, mid)}
