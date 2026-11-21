from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path
from typing import Optional

from ....util.fsx import ensure_parent, is_inside
from ....util.jsonx import read_json
from ....util import vtree
from ....store import layout
from ....checkpoints import SNAP_DIR, purge_snapshots
logger = logging.getLogger("harness.trash")

BIN_DIR = "bin"
INDEX_NAME = vtree.INDEX_NAME
TRASH_NAME = ".trash"
DEFAULT_RETENTION_DAYS = 7
STAMP_FMT = vtree.STAMP_FMT


def bin_root(project_root: str | Path) -> Path:
    return Path(project_root).resolve() / TRASH_NAME / BIN_DIR


pass
def load_policy() -> tuple[bool, int]:
    try:
        raw = read_json(layout.config_json()) or {}
        s = raw.get("settings") or {}
        return bool(s.get("trashEnabled", True)), int(s.get("trashRetentionDays",
                                                            DEFAULT_RETENTION_DAYS))
    except Exception:
        return True, DEFAULT_RETENTION_DAYS


pass
def trash_root(project_root: str | Path) -> Path:
    return Path(project_root).resolve() / TRASH_NAME


def _unique(base: Path) -> Path:
    dest, i = base, 1
    while dest.exists():
        dest = base.with_name(f"{base.name}-{i}")
        i += 1
    return dest


pass
def move_to_trash(project_root: str | Path, target: str | Path,
                  stamp: Optional[str] = None) -> Path:
    root = Path(project_root).resolve()
    src = Path(target).resolve()
    if src == root:
        raise ValueError("不允许把项目根目录移入回收站")
    if not is_inside(src, root):
        raise ValueError(f"路径不在项目内，已拒绝: {target}")
    rel = src.relative_to(root)
    if rel.parts and rel.parts[0] == TRASH_NAME:
        raise ValueError("已在回收站内的路径不再处理")
    binry = bin_root(root)
    idx = vtree.read_index(binry)
    stamp = stamp or vtree.new_stamp(idx)
    dest = _unique(vtree.version_path(binry, rel, stamp))
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dest))
    idx.setdefault(stamp, {"ts": vtree.stamp_ts(stamp, dest), "paths": []})[
        "paths"].append(rel.as_posix())
    vtree.write_index(binry, idx)
    logger.info("trash in: %s -> %s", src, dest)
    return dest


def restore(project_root: str | Path, rel_in_trash: str | Path,
            to: str | Path = "") -> Path:
    root = Path(project_root).resolve()
    src = (trash_root(root) / rel_in_trash).resolve()
    if not is_inside(src, trash_root(root)) or src == trash_root(root):
        raise ValueError(f"不是回收站内的路径: {rel_in_trash}")
    if not src.exists():
        src = _resolve_latest(bin_root(root), src) or src
    if not src.exists():
        raise ValueError(f"回收站里没有这一项: {rel_in_trash}")
    if to:
        dest = Path(to)
        dest = dest if dest.is_absolute() else root / dest
        dest = dest.resolve()
        if not is_inside(dest, root) or dest == root:
            raise ValueError(f"恢复目标必须在项目内: {to}")
    else:
        dest = (root / _rel_of_entry(bin_root(root), src)).resolve()
    dest = _unique(dest)
    ensure_parent(dest)
    shutil.move(str(src), str(dest))
    logger.info("trash out: %s -> %s", src, dest)
    return dest


def _resolve_latest(binry: Path, want: Path) -> Path | None:
    if not is_inside(want, binry):
        return None
    rel = want.relative_to(binry)
    vers = vtree.version_of(binry, rel)
    return vers[-1][1] if vers else None


def _rel_of_entry(binry: Path, item: Path) -> Path:
    rel = item.relative_to(binry)
    base, stamp = vtree.split_stamp(rel.name)
    if stamp:
        rel = rel.with_name(base)
    return rel


def hard_delete(project_root: str | Path, target: str | Path) -> None:
    root = Path(project_root).resolve()
    src = Path(target).resolve()
    if src == root:
        raise ValueError("不允许删除项目根目录")
    if not is_inside(src, root):
        from ....security.core import grade_paths
        if not grade_paths([str(src)], str(root)).scratch:
            raise ValueError(f"路径不在项目内，已拒绝: {target}")
    if src.is_dir():
        shutil.rmtree(src)
    else:
        src.unlink()
    logger.warning("hard delete: %s", src)


pass
def _created_at(d: Path) -> float:
    return vtree.stamp_ts(d.name, d)


def _legacy_dirs(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return sorted(d for d in root.iterdir()
                  if d.is_dir() and d.name not in (SNAP_DIR, BIN_DIR)
                  and vtree.STAMP_RE.match(d.name))


def list_entries(project_root: str | Path, now: Optional[float] = None) -> list[dict]:
    binry = bin_root(project_root)
    if not binry.is_dir():
        return []
    now = time.time() if now is None else now
    groups: dict[str, list[Path]] = {}
    for _rel, stamp, item in vtree.iter_versions(binry):
        groups.setdefault(stamp, []).append(item)
    out = []
    for stamp, items in groups.items():
        out.append({
            "stamp": stamp,
            "age_days": round((now - vtree.stamp_ts(stamp, items[0])) / 86400, 1),
            # 目录条目里面的文件也算上，否则「删了一个目录」会显示 0 个文件
            "files": sum(1 if it.is_file()
                         else len([f for f in it.rglob("*") if f.is_file()])
                         for it in items),
            "bytes": sum(vtree.size_of(it) for it in items),
        })
    out.sort(key=lambda e: e["stamp"], reverse=True)
    return out


def list_files(project_root: str | Path, stamp: str = "") -> list[dict]:
    binry = bin_root(project_root)
    if not binry.is_dir():
        return []
    return [{"path": str(item.relative_to(binry.parent)).replace("\\", "/"),
             "bytes": vtree.size_of(item)}
            for _rel, s, item in vtree.iter_versions(binry)
            if not stamp or s == stamp]


pass
def purge(project_root: str | Path, days: Optional[int] = None,
          now: Optional[float] = None) -> dict:
    root = trash_root(project_root)
    if not root.is_dir():
        return {"removed": 0, "freed_bytes": 0, "kept": 0}
    keep_days = DEFAULT_RETENTION_DAYS if days is None else int(days)
    now = time.time() if now is None else now
    cutoff = now - keep_days * 86400
    res = purge_snapshots(project_root, days=keep_days, now=now)
    removed, freed = res["removed"], res["freed_bytes"]
    binres = vtree.purge(bin_root(project_root), cutoff, all_=keep_days == 0)
    removed += binres["removed"]
    freed += binres["freed_bytes"]
    kept = 0
    for d in _legacy_dirs(root):
        if not is_inside(d, root):
            kept += 1
            continue
        if keep_days == 0 or _created_at(d) < cutoff:
            freed += vtree.size_of(d)
            shutil.rmtree(d, ignore_errors=True)
            removed += 1
        else:
            kept += 1
    if removed:
        logger.info("trash purge: removed=%d freed=%dB kept=%d (days=%d)",
                    removed, freed, kept, keep_days)
    return {"removed": removed, "freed_bytes": freed, "kept": kept}


def purge_tree(tree: dict, days: int) -> dict:
    out: dict = {}

    def walk(node: dict) -> None:
        if not node:
            return
        p = node.get("path")
        if p:
            try:
                res = purge(p, days=days)
                if res["removed"]:
                    out[p] = res
            except Exception:
                logger.debug("purge failed: %s", p, exc_info=True)
        for ch in node.get("children") or []:
            walk(ch)

    walk(tree or {})
    return out
