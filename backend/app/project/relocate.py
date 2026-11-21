from __future__ import annotations

import shutil
import logging
from pathlib import Path

from ..store import layout
from ..store.db import open_ro
from ..util import pathx

logger = logging.getLogger("harness.project.relocate")


class RelocateError(Exception):
    pass


def _resolve(pm, path: str) -> Path:
    if not path:
        raise RelocateError("路径为空")
    return pathx.project_dir(path)


def _depth(path: Path, known: set[str]) -> int:
    d, cur = 1, path.parent
    while True:
        if str(cur) in known:
            return d + 1
        if cur == cur.parent:
            return d
        cur = cur.parent


def _validate(pm, src: Path, parent: Path) -> tuple[Path, set[str], int]:
    pass
    known = {str(pathx.project_dir(p)) for p in pm.registered_paths()}
    if str(src) not in known:
        raise RelocateError(f"项目未注册: {src}")
    if not src.is_dir():
        raise RelocateError(f"项目目录不存在: {src}")
    if parent != pm.ensure_root() and str(parent) not in known:
        raise RelocateError(f"目标项目未注册: {parent}")
    if str(parent) != str(pm.ensure_root()) and (
            parent == src or str(parent).startswith(str(src) + "/")):
        raise RelocateError("不能把项目移动到自己或自己的后代下面")
    dest = parent / src.name
    if dest.exists():
        raise RelocateError(f"目标目录已存在: {dest}")
    pass
    base_depth = _depth(parent, known) if str(parent) in known else 1
    subtree = 1 + max((_depth(Path(p), known) - _depth(src, known)
                       for p in known if p.startswith(str(src) + "/")), default=0)
    if base_depth + subtree > 3:
        raise RelocateError("层级超过 3 层")
    return dest, known, base_depth + subtree


def _empty_chat_db(path: Path) -> bool:
    if not path.is_file() or not path.name.startswith("chat.") or not path.name.endswith(".db"):
        return False
    conn = None
    try:
        conn = open_ro(path)
        row = conn.execute("SELECT COUNT(*) FROM messages").fetchone()
        return bool(row and row[0] == 0)
    except Exception:
        return False
    finally:
        if conn is not None:
            conn.close()


def _merge_dir(old: Path, new: Path) -> int:
    if not old.is_dir():
        return 0
    new.mkdir(parents=True, exist_ok=True)
    moved = 0
    for item in sorted(old.iterdir()):
        dst = new / item.name
        if dst.exists():
            if (item.is_file() and dst.is_file()
                    and _empty_chat_db(dst) and not _empty_chat_db(item)):
                for suffix in ("", "-wal", "-shm"):
                    side = Path(str(dst) + suffix)
                    if side.is_file():
                        side.unlink()
            elif item.is_dir() and dst.is_dir():
                moved += _merge_dir(item, dst)
                continue
            else:
                continue
        if dst.exists():
            continue
        shutil.move(str(item), str(dst))
        moved += 1
    try:
        old.rmdir()
    except OSError:
        pass
    return moved


def _runtime_dirs(old: str, new: str) -> tuple[Path | None, Path | None]:
    a, b = layout.runtime_project_dir(old), layout.runtime_project_dir(new)
    if a is None or b is None or a == b:
        return None, None
    return a, b


def _rewire(pm, sessions, old: str, new: str, rt_dirs=None,
            keys=None, stores=None) -> dict:
    from ..chat.session_recovery import recover_sessions, retarget_sessions

    old = str(pathx.project_dir(old))
    new = str(pathx.project_dir(new))
    rt_old, rt_new = rt_dirs if rt_dirs is not None else _runtime_dirs(old, new)
    key_old, key_new = keys if keys is not None else _recent_keys(old, new)
    rt_moved = _merge_dir(rt_old, rt_new) if rt_old else 0
    reg_moved = pm.retarget(old, new)
    sess_moved = retarget_sessions(sessions, old, new)
    extra = _retarget_stores(old, new, key_old, key_new, stores)
    stats = recover_sessions(sessions, new)
    out = {"path": new, "from": old, "runtime_moved": rt_moved,
           "registry_moved": reg_moved, "sessions_moved": sess_moved,
           "recovered": stats}
    out.update(extra)
    return out


def _recent_keys(old: str, new: str) -> tuple[str, str]:
    if layout.runtime_root() is None:
        return "", ""
    try:
        return layout.project_key(old), layout.project_key(new)
    except Exception:
        return "", ""


def _default_stores() -> dict:
    from ..chat.recent import RecentStore
    from ..store.plugin_config import PluginConfigStore
    return {"plugin_config": PluginConfigStore(), "recent": RecentStore()}


def _retarget_stores(old: str, new: str, key_old: str, key_new: str,
                     stores) -> dict:
    from ..security import project_mode

    st = dict(_default_stores())
    st.update(stores or {})

    def safe(fn, *args) -> int:
        if fn is None:
            return 0
        try:
            return int(fn(*args) or 0)
        except Exception:
            logger.warning("项目迁移：%s 改绑失败", getattr(fn, "__qualname__", fn),
                           exc_info=True)
            return 0

    installs = st.get("installs")
    return {
        "plugins_moved": safe(getattr(installs, "retarget", None), old, new),
        "configs_moved": safe(st["plugin_config"].retarget, old, new),
        "policy_moved": safe(project_mode.retarget, old, new),
        "recent_moved": safe(st["recent"].retarget_keys, key_old, key_new),
    }


def relocate(pm, sessions, src_path: str, parent_path: str, stores=None) -> dict:
    src = _resolve(pm, src_path)
    parent = _resolve(pm, parent_path) if parent_path else pm.ensure_root()
    dest, known, _ = _validate(pm, src, parent)
    pass
    rt_dirs = _runtime_dirs(str(src), str(dest))
    keys = _recent_keys(str(src), str(dest))
    pass
    parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dest))
    return _rewire(pm, sessions, str(src), str(dest), rt_dirs,
                   keys=keys, stores=stores)
def migrate_orphan(pm, sessions, old_path: str, new_path: str, stores=None) -> dict:
    old = _resolve(pm, old_path)
    new = _resolve(pm, new_path)
    if old == new:
        raise RelocateError("新旧路径相同")
    if old.is_dir():
        raise RelocateError(f"旧项目目录仍在，无需迁移: {old}")
    if not new.is_dir():
        raise RelocateError(f"新项目目录不存在: {new}")
    if old.name != new.name:
        raise RelocateError("名称对不上，拒绝自动迁移")
    if str(old) not in {str(pathx.project_dir(p)) for p in pm.registered_paths()}:
        raise RelocateError(f"旧项目未注册: {old}")
    pass
    pass
    pass
    rt_dirs = _runtime_dirs(str(old), str(new))
    keys = _recent_keys(str(old), str(new))
    return _rewire(pm, sessions, str(old), str(new), rt_dirs,
                   keys=keys, stores=stores)
