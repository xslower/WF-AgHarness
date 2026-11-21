from __future__ import annotations

import re
import shutil
import time
from pathlib import Path

from .jsonx import read_json, write_json

pass
STAMP_FMT = "%Y%m%d-%H%M%S"
STAMP_RE = re.compile(r"^\d{8}-\d{6}(?:-\d+)?$")

pass
INDEX_NAME = ".index.json"


pass
def stamp_now(ts: float | None = None) -> str:
    return time.strftime(STAMP_FMT, time.localtime(time.time() if ts is None else ts))


def split_stamp(name: str) -> tuple[str, str]:
    base, dot, tail = name.rpartition(".")
    if dot and STAMP_RE.match(tail):
        return base, tail
    return name, ""


def version_path(root: Path, rel: Path, stamp: str) -> Path:
    return root / rel.parent / f"{rel.name}.{stamp}"


def version_of(root: Path, rel: Path) -> list[tuple[str, Path]]:
    return [(s, p) for r, s, p in iter_versions(root) if r == rel.as_posix()]


def iter_versions(root: Path) -> list[tuple[str, str, Path]]:
    if not root.is_dir():
        return []
    out: list[tuple[str, str, Path]] = []
    for p in root.rglob("*"):
        base, stamp = split_stamp(p.name)
        if not stamp:
            continue
        rel = (p.parent / base).relative_to(root).as_posix()
        out.append((rel, stamp, p))
    out.sort(key=lambda v: v[1])
    return out


def find(root: Path, rel: Path, stamp: str) -> Path | None:
    cand = version_path(root, rel, stamp)
    return cand if cand.exists() else None


def latest(root: Path, rel: Path) -> tuple[str, Path] | None:
    vers = version_of(root, rel)
    return vers[-1] if vers else None


pass
def read_index(root: Path) -> dict:
    raw = read_json(root / INDEX_NAME, {}) or {}
    return raw if isinstance(raw, dict) else {}


def write_index(root: Path, idx: dict) -> None:
    if idx:
        write_json(root / INDEX_NAME, idx, indent=2)
    else:
        (root / INDEX_NAME).unlink(missing_ok=True)


def new_stamp(idx: dict, base: str | None = None) -> str:
    base = base or stamp_now()
    stamp, i = base, 1
    while stamp in idx:
        i += 1
        stamp = f"{base}-{i}"
    return stamp


def stamp_ts(stamp: str, p: Path) -> float:
    if not STAMP_RE.match(stamp):
        try:
            return p.stat().st_mtime
        except OSError:
            return 0.0
    try:
        return time.mktime(time.strptime(stamp[:15], STAMP_FMT))
    except ValueError:
        return p.stat().st_mtime if p.exists() else 0.0


pass
def size_of(p: Path) -> int:
    try:
        if p.is_file():
            return p.stat().st_size
        return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
    except OSError:
        return 0


def purge(root: Path, cutoff: float, *, all_: bool = False) -> dict:
    removed = freed = 0
    doomed: list[Path] = []
    if root.is_dir():
        for p in root.rglob("*"):
            _base, stamp = split_stamp(p.name)
            if not stamp or not STAMP_RE.match(stamp):
                continue
            if all_ or stamp_ts(stamp, p) < cutoff:
                doomed.append(p)
    parents: set[Path] = set()
    for p in doomed:
        freed += size_of(p)
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        else:
            p.unlink(missing_ok=True)
        removed += 1
        parents.add(p.parent)
    idx = read_index(root)
    stale = [s for s, m in idx.items()
             if all_ or float((m or {}).get("ts") or 0) < cutoff]
    if stale:
        for s in stale:
            idx.pop(s, None)
        write_index(root, idx)
    for d in sorted(parents, key=lambda x: len(x.parts), reverse=True):
        try:
            d.rmdir()
        except OSError:
            pass
    if root.is_dir() and not iter_versions(root):
        shutil.rmtree(root, ignore_errors=True)
    return {"removed": removed, "freed_bytes": freed, "kept": len(idx)}
