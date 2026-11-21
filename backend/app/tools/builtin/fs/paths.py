from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from ....util.jsonx import err
from . import trash
from .common import _emit_file, _rel, guard_paths, resolve
from .write import f_replace, f_write
from .read import f_read, grep, search_files
from ....util.fsx import ensure_dir, ensure_parent

__all__ = [
    "copy_file", "create_file", "delete_file", "f_read", "f_replace",
    "f_write", "f_path", "grep",
    "move_file", "register", "search_files", "trash_tool",
]

logger = logging.getLogger("harness.fs")

if TYPE_CHECKING:
    from ... import ToolContext, ToolRegistry


def _outside_sandbox(p: Path, ctx, extra_safe) -> bool:
    from ....security.core import grade_paths
    root = str(ctx.project_dir())
    g = grade_paths([str(p)], root, extra_safe)
    return bool(g.outside or g.critical)


async def delete_file(path: str, ctx: "ToolContext") -> str:
    blocked = await guard_paths(ctx, "delete", path)
    if blocked:
        return blocked
    p = resolve(ctx, path)
    ws = Path(ctx.project_dir()).resolve()
    rp = p.resolve()
    if rp == ws:
        return json.dumps({"error": "删除被拒绝：不允许删除项目根目录"},
                          ensure_ascii=False)
    pass
    pass
    pass
    pass
    if _outside_sandbox(rp, ctx, extra_safe=None):
        return json.dumps(
            {"error": f"删除被拒绝：只能删除当前项目目录内的路径（{p} 不在 {ws} 内）"},
            ensure_ascii=False)
    if not p.exists():
        return err(f"路径不存在: {p}")
    await ctx.auto_snapshot(f"delete {p.name}", [p])
    is_dir = p.is_dir()
    pass
    pass
    pass
    from ....security.core import grade_paths as _grade
    in_temp = bool(_grade([str(rp)], str(ws)).scratch)
    enabled, ttl = trash.load_policy()
    if enabled and not in_temp:
        try:
            dest = trash.move_to_trash(ws, p)
        except ValueError as e:
            return err(str(e))
        pass
        if ttl > 0:
            trash.purge(ws, days=ttl)
        logger.info("fs.delete(trash) %s -> %s", p, dest)
        msg = (f"已移到回收站 {dest}（可恢复，{ttl} 天后自动清理）" if ttl > 0
               else f"已移到回收站 {dest}（可恢复；自动清理已关闭）")
    else:
        try:
            trash.hard_delete(ws, p)
        except ValueError as e:
            return err(str(e))
        logger.warning("fs.delete(hard) %s", p)
        why = "临时目录：直接删除" if in_temp else "回收站已关闭：真删，不可恢复"
        msg = f"已删除 {p}（{why}）"
    _emit_file(ctx, p, "deleted", "dir" if is_dir else "file")
    return msg

async def move_file(path: str, dest: str, ctx: "ToolContext") -> str:
    blocked = await guard_paths(ctx, "move", path, dest)
    if blocked:
        return blocked
    p = resolve(ctx, path)
    d = resolve(ctx, dest)
    if not p.exists():
        return err(f"源路径不存在: {p}")
    pass
    pass
    rp, dp = p.resolve(), d.resolve()
    pass
    pass
    ws = Path(ctx.project_dir()).resolve()
    if rp == ws or dp == ws:
        return json.dumps(
            {"error": "移动被拒绝：不允许把项目根目录作为源或目标"},
            ensure_ascii=False)
    if _outside_sandbox(rp, ctx, None) or _outside_sandbox(dp, ctx, None):
        if ctx.request_file_approval:
            ok, _ = await ctx.request_file_approval(
                f"move {p.name}", p, "", "", f"移动涉及工作目录外: {p} → {d}")
            if not ok:
                return err("移动被拒绝（工作目录外）")
    await ctx.auto_snapshot(f"move {p.name}", [p, d])
    ensure_parent(d)
    is_dir = p.is_dir()
    shutil.move(str(p), str(d))
    pass
    _emit_file(ctx, p, "moved_from", "dir" if is_dir else "file")
    _emit_file(ctx, d, "moved_to", "dir" if is_dir else "file")
    return f"已移动 {p} → {d}"

async def copy_file(path: str, dest: str, ctx: "ToolContext") -> str:
    blocked = await guard_paths(ctx, "copy", path, dest)
    if blocked:
        return blocked
    p = resolve(ctx, path)
    d = resolve(ctx, dest)
    if not p.exists():
        return err(f"源路径不存在: {p}")
    rp, dp = p.resolve(), d.resolve()
    if _outside_sandbox(rp, ctx, None) or _outside_sandbox(dp, ctx, None):
        if ctx.request_file_approval:
            ok, _ = await ctx.request_file_approval(
                f"copy {p.name}", p, "", "", f"复制涉及工作目录外: {p} → {d}")
            if not ok:
                return err("复制被拒绝（工作目录外）")
    await ctx.auto_snapshot(f"copy {p.name}", [d])
    ensure_parent(d)
    is_dir = p.is_dir()
    if is_dir:
        shutil.copytree(str(p), str(d))
    else:
        shutil.copy2(str(p), str(d))
    _emit_file(ctx, d, "copied", "dir" if is_dir else "file")
    return f"已复制 {p} → {d}"

async def create_file(path: str, ctx: "ToolContext", content: str = "",
                      is_dir: bool = False) -> str:
    blocked = await guard_paths(ctx, "create", path)
    if blocked:
        return blocked
    p = resolve(ctx, path)
    if p.exists():
        return err(f"路径已存在: {p}")
    await ctx.auto_snapshot(f"create {p.name}", [p])
    if is_dir:
        ensure_dir(p)
        _emit_file(ctx, p, "created", "dir")
        return f"已创建目录 {p}"
    ensure_parent(p)
    p.write_text(content, "utf-8")
    _emit_file(ctx, p, "created")
    return f"已创建 {p} ({len(content)} 字符)"

async def f_path(action: str, path: str, ctx: "ToolContext", dest: str = "",
                  is_dir: bool = False, content: str = "") -> str:
    act = (action or "").strip().lower()
    if act == "delete":
        return await delete_file(path, ctx)
    if act in ("move", "copy"):
        if not dest:
            return err(f"action={act} 需要 dest")
        return await (move_file if act == "move" else copy_file)(path, dest, ctx)
    if act == "create":
        return await create_file(path, ctx, content, is_dir)
    return json.dumps(
        {"error": f"action 必须是 create/move/copy/delete 之一，收到: {action}"},
        ensure_ascii=False)

async def trash_tool(action: str, ctx: "ToolContext", days: int = 0,
                     stamp: str = "", path: str = "", to: str = "") -> str:
    ws = Path(ctx.project_dir()).resolve()
    act = (action or "list").strip().lower()
    enabled, ttl = trash.load_policy()
    if act == "list":
        entries = trash.list_entries(ws)
        pass
        files = trash.list_files(ws, stamp) if stamp else None
        out = {
            "trash_enabled": enabled,
            "retention_days": ttl,
            "entries": entries,
            "total_files": sum(e["files"] for e in entries),
            "total_bytes": sum(e["bytes"] for e in entries),
        }
        if files is not None:
            out["stamp"] = stamp
            out["files"] = files
        return json.dumps(out, ensure_ascii=False)
    if act == "purge":
        d = max(0, int(days))
        res = trash.purge(ws, days=d)
        return json.dumps({"ok": True, "days": d, **res}, ensure_ascii=False)
    if act == "restore":
        if not path:
            return err("action=restore 需要 path（相对项目根的回收站内路径）")
        try:
            dest = trash.restore(ws, path, to=to)
        except ValueError as e:
            return err(str(e))
        return json.dumps({"ok": True, "restored_to": _rel(dest, ws)},
                          ensure_ascii=False)
    return json.dumps({"error": f"action 必须是 list/purge/restore，收到: {action}"},
                      ensure_ascii=False)
