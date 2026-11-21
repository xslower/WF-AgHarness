from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Sequence

from .util import vtree

DEFAULT_IGNORE = """# Agent Harness 自动生成，可自行修改
*.db
*.sqlite
node_modules/
.venv/
venv/
.env
*.log
logs/
cache/
.cache/
dist/
build/
# 大媒体文件
*.png
*.jpg
*.jpeg
*.gif
*.bmp
*.webp
*.mp3
*.wav
*.mp4
*.mkv
*.avi
*.mov
*.zip
*.tar.gz
*.7z
"""


pass
pass
pass
GIT_TIMEOUT = 30


def _git(ws: Path, *args: str, check: bool = True,
         timeout: float | None = GIT_TIMEOUT) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(ws), *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace",
                          check=check, timeout=timeout)


def ensure_repo(ws: str) -> None:
    p = Path(ws)
    if not p.exists():
        p.mkdir(parents=True, exist_ok=True)
    if not (p / ".git").exists():
        _git(p, "init", "-q")
        _git(p, "config", "user.email", "agent@local")
        _git(p, "config", "user.name", "Agent Harness")
        _git(p, "config", "core.autocrlf", "false")
    gi = p / ".gitignore"
    if not gi.exists():
        gi.write_text(DEFAULT_IGNORE, "utf-8")


pass
pass
SNAP_DIR = "snap"
pass
SNAP_INDEX = vtree.INDEX_NAME
_TRASH_NAME = ".trash"

pass
pass
_DEEP_FP_MAX = 4 * 1024 * 1024


def snapshot(ws: str, message: str,
             paths: "Sequence[str | Path] | None" = None) -> str | None:
    from .project.git_mode import git_enabled
    if git_enabled(ws):
        return _git_snapshot(ws, message)
    return _trash_snapshot(ws, message, paths)


def list_checkpoints(ws: str, limit: int = 50) -> list[dict]:
    from .project.git_mode import git_enabled
    if git_enabled(ws):
        return _git_list(ws, limit)
    return _trash_list(ws, limit)


def restore(ws: str, sha: str) -> None:
    if vtree.STAMP_RE.match(sha):
        _trash_restore(ws, sha)
    else:
        _git_restore(ws, sha)


def _git_snapshot(ws: str, message: str) -> str | None:
    p = Path(ws)
    try:
        ensure_repo(ws)
        _git(p, "add", "-A")
        r = _git(p, "status", "--porcelain")
        if not r.stdout.strip():
            return None
        _git(p, "commit", "-q", "-m", message, "--no-verify")
        return _git(p, "rev-parse", "--short", "HEAD").stdout.strip()
    except Exception:
        return None


def _git_list(ws: str, limit: int) -> list[dict]:
    p = Path(ws)
    if not (p / ".git").exists():
        return []
    r = _git(p, "log", "--oneline", f"-{limit}", "--pretty=format:%h\t%at\t%s",
             check=False)
    out = []
    for line in r.stdout.splitlines():
        sha, ts, msg = line.split("\t", 2)
        if msg.startswith("agent:"):
            out.append({"sha": sha, "ts": float(ts), "message": msg[6:]})
    return out


def _git_restore(ws: str, sha: str) -> None:
    p = Path(ws)
    _git(p, "reset", "--hard", sha)
    _git(p, "clean", "-fdq")


pass
pass
_LEGACY_PREFIX = "snap-"


def _trash_root(ws: str) -> Path:
    return Path(ws) / _TRASH_NAME


def _snap_root(ws: str) -> Path:
    return _trash_root(ws) / SNAP_DIR


def _rels_of(ws: str, paths: "Sequence[str | Path]") -> list[str]:
    root = os.path.normpath(str(ws))
    out: list[str] = []
    for raw in paths:
        p = os.path.normpath(os.path.join(root, str(raw)))
        rel = os.path.relpath(p, root)
        if rel == "." or rel.startswith(".."):
            continue
        rel = rel.replace(os.sep, "/")
        if rel not in out:
            out.append(rel)
    return out


def _same_content(a: Path, b: Path) -> bool:
    try:
        if a.stat().st_size != b.stat().st_size:
            return False
        if a.stat().st_size > _DEEP_FP_MAX:
            return False
        return a.read_bytes() == b.read_bytes()
    except OSError:
        return False


def _display_message(meta: dict) -> str:
    raw = str(meta.get("message") or "自动备份")
    return raw[6:] if raw.startswith("agent:") else raw


def _trash_snapshot(ws: str, message: str,
                    paths: "Sequence[str | Path] | None" = None) -> str | None:
    if paths is None:
        raise ValueError(
            "该目录不是 git 项目，无法整项目快照（没有基线可比）；"
            "请用 git 管理这个项目，或只对具体文件做写前快照")
    root = Path(ws)
    rels = _rels_of(ws, paths)
    if not rels:
        return None
    todo: list[tuple[Path, Path]] = []
    for raw in rels:
        rel = Path(raw)
        src = root / rel
        if not src.is_file():
            continue
        prev = vtree.latest(_snap_root(ws), rel)
        if prev and _same_content(src, prev[1]):
            continue
        todo.append((rel, src))
    if not todo:
        return None
    snap = _snap_root(ws)
    idx = vtree.read_index(snap)
    stamp = vtree.new_stamp(idx)
    wrote: list[Path] = []
    try:
        for rel, src in todo:
            dest = vtree.version_path(snap, rel, stamp)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            wrote.append(dest)
    except OSError:
        for d in wrote:
            d.unlink(missing_ok=True)
        return None
    idx[stamp] = {"ts": time.time(), "message": message, "paths": rels}
    vtree.write_index(snap, idx)
    return stamp


def _trash_entries(ws: str) -> list[dict]:
    out = [{"sha": stamp, "ts": float(meta.get("ts") or 0),
            "message": _display_message(meta),
            "paths": meta.get("paths") or None}
           for stamp, meta in vtree.read_index(_snap_root(ws)).items()]
    out.sort(key=lambda b: b["ts"], reverse=True)
    return out


def _trash_list(ws: str, limit: int) -> list[dict]:
    return [{"sha": b["sha"], "ts": b["ts"], "message": b["message"]}
            for b in _trash_entries(ws)[:limit]]


def _trash_restore(ws: str, sha: str) -> None:
    snap = _snap_root(ws)
    idx = vtree.read_index(snap)
    if not vtree.STAMP_RE.match(sha) or sha not in idx:
        raise ValueError(f"没有备份: {sha}")
    root = Path(ws)
    scope = list(idx[sha].get("paths") or [])
    keep: set[str] = set()
    for rel in scope:
        for stamp, f in vtree.version_of(snap, Path(rel)):
            if stamp != sha:
                continue
            keep.add(rel)
            dest = root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)
            break
    for rel in scope:
        p = root / rel
        if rel not in keep and p.is_file():
            p.unlink()


def purge_snapshots(project_root: str | Path, days: int,
                    now: float | None = None) -> dict:
    ws = str(project_root)
    cutoff = (time.time() if now is None else now) - days * 86400
    res = vtree.purge(_snap_root(ws), cutoff, all_=days == 0)
    removed, freed = res["removed"], res["freed_bytes"]
    if not vtree.read_index(_snap_root(ws)):
        for d in sorted((p for p in _snap_root(ws).rglob("*") if p.is_dir()),
                        key=lambda x: len(x.parts), reverse=True):
            try:
                d.rmdir()
            except OSError:
                pass
    trash = _trash_root(ws)
    if trash.is_dir():
        for d in list(trash.iterdir()):
            if d.is_dir() and d.name.startswith(_LEGACY_PREFIX):
                freed += vtree.size_of(d)
                shutil.rmtree(d, ignore_errors=True)
                removed += 1
    return {"removed": removed, "freed_bytes": freed}
