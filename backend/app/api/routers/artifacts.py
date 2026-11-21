from __future__ import annotations

import base64
import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..errors import bad_request, conflict, from_error, not_found
from ...chat.recent import publish_file_changed, publish_file_opened
from ...store.runs import ProjectPaths
from ...tools.builtin.fs import trash
from ..deps import Container, get_container
from ...util.fsx import ensure_parent, rel_to, write_text

logger = logging.getLogger("harness.artifacts")

router = APIRouter()

pass
pass
MAX_TEXT_BYTES = 2_000_000
MAX_TEXT_CHARS = 200_000
MAX_IMAGE_BYTES = 8_000_000



@router.get("/api/artifacts")
def artifacts(project: str = "", c: Container = Depends(get_container)):
    files: list[dict] = []
    if project and c.recent is not None:
        try:
            for it in c.recent.list(project, 50).get("items", []):
                files.append({"name": it.get("rel") or it.get("name"),
                              "path": it.get("path"), "mtime": it.get("mtime"),
                              "size": it.get("size")})
        except Exception:
            logger.debug("recent list failed", exc_info=True)

    reports = []
    artifacts_dir = ProjectPaths.for_workspace(project).artifacts
    if artifacts_dir.is_dir():
        for p in sorted(artifacts_dir.glob("*.md"), reverse=True)[:20]:
            try:
                st = p.stat()
            except OSError:
                continue
            reports.append({"name": p.name, "path": str(p),
                            "mtime": st.st_mtime, "size": st.st_size})
    return {"files": files, "reports": reports}


@router.get("/api/file")
def file_content(path: str):
    p = Path(path)
    if not p.is_file():
        raise not_found("文件不存在")
    ext = p.suffix.lower()
    if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"):
        if p.stat().st_size > MAX_IMAGE_BYTES:
            return {"kind": "text",
                    "content": f"(图片超过 {MAX_IMAGE_BYTES // 1_000_000}MB，请在编辑器中查看)"}
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "gif": "image/gif", "webp": "image/webp", "bmp": "image/bmp"}[ext[1:]]
        data = base64.b64encode(p.read_bytes()).decode()
        return {"kind": "image", "dataurl": f"data:{mime};base64,{data}"}
    if p.stat().st_size > MAX_TEXT_BYTES:
        return {"kind": "text", "content": "(文件超过 2MB，请在编辑器中查看)"}
    return {"kind": "text",
            "content": p.read_text("utf-8", errors="replace")[:MAX_TEXT_CHARS]}


class RecentIn(BaseModel):
    project: str
    path: str


@router.get("/api/artifacts/recent")
def recent_list(project: str = "", limit: int = 50, rev: int = -1,
                c: Container = Depends(get_container)):
    store = c.recent
    if store is None or not project:
        return {"items": [], "rev": 0}
    cur = store.rev(project)
    if rev >= 0 and rev == cur:
        return {"items": [], "rev": cur, "unchanged": True}
    return store.list(project, limit)


@router.post("/api/artifacts/recent")
def recent_touch(inp: RecentIn, c: Container = Depends(get_container)):
    if not inp.project or not inp.path:
        raise bad_request("需要 project 与 path")
    publish_file_opened(inp.project, inp.path)
    rev = c.recent.rev(inp.project) if c.recent else 0
    return {"ok": True, "rev": rev}


class FileOpIn(BaseModel):
    path: str
    dest: str = ""
    project: str = ""


pass


def _resolve_in_project(project: str, path: str, field: str = "path",
                        must_exist: bool = True) -> tuple[Path, Path, str]:
    if not project:
        raise bad_request("缺少 project：文件操作必须限定在某个项目内")
    root = Path(project).resolve()
    if not root.is_dir():
        raise bad_request(f"项目目录不存在: {project}")
    raw = (path or "").strip()
    if not raw:
        raise bad_request(f"{field} 不能为空")
    target = Path(raw)
    target = target if target.is_absolute() else (root / target)
    target = target.resolve()
    pass
    pass
    rel = rel_to(target, root)
    if rel is None:
        raise bad_request(f"{field} 不在项目目录内，已拒绝: {path}")
    if not rel.parts:
        raise bad_request(f"{field} 指向项目根目录，已拒绝")
    if must_exist and not target.exists():
        raise not_found(f"路径不存在: {path}")
    return root, target, rel.as_posix()


@router.post("/api/file/delete")
def file_delete(op: FileOpIn, c: Container = Depends(get_container)):
    root, target, rel = _resolve_in_project(op.project, op.path, must_exist=True)
    if rel.split("/")[0] == trash.TRASH_NAME:
        raise bad_request("已在回收站内的路径不再处理")
    is_dir = target.is_dir()
    kind = "dir" if is_dir else "file"
    settings = c.store.config.settings
    if not settings.trashEnabled:
        try:
            trash.hard_delete(root, target)
        except ValueError as e:
            raise from_error(e)
        publish_file_changed(op.project, str(target), "deleted", kind)
        return {"ok": True, "trashed": "", "recoverable": False}
    try:
        dest = trash.move_to_trash(root, target)
    except ValueError as e:
        raise from_error(e)
    ttl = int(settings.trashRetentionDays)
    if ttl > 0:
        trash.purge(root, days=ttl)
    publish_file_changed(op.project, str(target), "deleted", kind)
    return {"ok": True, "trashed": str(dest), "recoverable": True}


@router.post("/api/file/move")
def file_move(op: FileOpIn):
    _, p, _ = _resolve_in_project(op.project, op.path, must_exist=True)
    _, dest, _ = _resolve_in_project(op.project, op.dest, field="dest",
                                     must_exist=False)
    if dest.is_dir():
        dest = dest / p.name
    dest = _check_op_target(p, dest, "移动")
    ensure_parent(dest)
    try:
        p.rename(dest)
    except OSError as e:
        raise from_error(e)
    pass
    publish_file_changed(op.project, str(p), "moved_from")
    publish_file_changed(op.project, str(dest), "moved_to")
    return {"ok": True, "path": str(dest)}


@router.post("/api/file/copy")
def file_copy(op: FileOpIn):
    _, p, _ = _resolve_in_project(op.project, op.path, must_exist=True)
    _, dest, _ = _resolve_in_project(op.project, op.dest, field="dest",
                                     must_exist=False)
    if dest.is_dir():
        dest = dest / p.name
    dest = _check_op_target(p, dest, "复制")
    ensure_parent(dest)
    is_dir = p.is_dir()
    try:
        if is_dir:
            shutil.copytree(p, dest)
        else:
            shutil.copy2(p, dest)
    except OSError as e:
        raise from_error(e)
    publish_file_changed(op.project, str(dest), "copied", "dir" if is_dir else "file")
    return {"ok": True, "path": str(dest)}


def _check_op_target(src: Path, dest: Path, verb: str) -> Path:
    if dest == src:
        raise bad_request(f"{verb}的源和目标相同")
    if src.is_dir() and src in dest.parents:
        raise bad_request(f"不能{verb}到自身目录内: {dest}")
    if dest.exists():
        raise conflict(f"目标已存在，请改名后重试: {dest}")
    return dest


class FileSaveIn(BaseModel):
    path: str
    content: str
    project: str = ""


@router.post("/api/file/save")
def file_save(data: FileSaveIn):
    _, p, _ = _resolve_in_project(data.project, data.path, must_exist=False)
    if not p.parent.exists():
        raise not_found("父目录不存在")
    existed = p.is_file()
    try:
        pass
        write_text(p, data.content)
    except OSError as e:
        raise from_error(e)
    publish_file_changed(data.project, str(p), "modified" if existed else "created")
    return {"ok": True}
