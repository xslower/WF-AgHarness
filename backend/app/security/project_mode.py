from __future__ import annotations

import logging
from pathlib import Path

from ..store import layout
from ..store.kv import KVStore
from ..util import pathx
from .core import MODES

logger = logging.getLogger("harness.policy")

pass
pass
DEFAULT_MODE = "workspace"

pass
pass
pass
pass

PREFIX = "project_policy:"


def _kv() -> KVStore:
    return KVStore()


def _key(project: str) -> str:
    return PREFIX + pathx.project_path(project)


def _top(project: str) -> str:
    top = layout.top_project(project)
    return (pathx.project_path(str(top)) if top is not None
            else pathx.project_path(project))


def _ancestors(path: str) -> list[str]:
    cur = Path(pathx.project_path(path))
    out: list[str] = []
    while True:
        out.append(str(cur))
        parent = cur.parent
        if parent == cur:
            break
        cur = parent
    return out


def get_mode(project: str) -> str:
    if not project:
        return DEFAULT_MODE
    try:
        kv = _kv()
        candidates: list[str] = [project]
        top = _top(project)
        if top != project:
            candidates.append(top)
        for anc in _ancestors(project):
            if anc not in candidates:
                candidates.append(anc)
        for cand in candidates:
            v = kv.get_json(_key(cand))
            if v in MODES:
                return str(v)
    except Exception:
        logger.debug("读取项目安全级别失败: %s", project, exc_info=True)
    return DEFAULT_MODE


def set_mode(project: str, mode: str) -> str:
    if mode not in MODES:
        raise ValueError(f"mode 必须是 {list(MODES)} 之一，收到: {mode}")
    if not project:
        raise ValueError("project 不能为空")
    _kv().set_json(_key(project), mode)
    return mode


def clear_mode(project: str) -> bool:
    return _kv().delete(_key(project))


def mode_for_cwd(cwd: str) -> str:
    if not cwd:
        return DEFAULT_MODE
    return get_mode(cwd)


def retarget(old: str, new: str) -> int:
    from ..store.retarget import in_scope, project_scope_key, rebase

    old_key = project_scope_key(old)
    new_key = project_scope_key(new)
    if not old_key or old_key == new_key:
        return 0
    kv = _kv()
    moved = 0
    for key in kv.keys(PREFIX):
        cur = project_scope_key(key[len(PREFIX):])
        if not in_scope(cur, old_key):
            continue
        target = PREFIX + rebase(cur, old_key, new_key)
        if target == key:
            continue
        kv.set_json(target, kv.get_json(key))
        kv.delete(key)
        moved += 1
    return moved
