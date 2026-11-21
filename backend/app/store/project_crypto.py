from __future__ import annotations

import threading
from pathlib import Path

from cryptography.fernet import Fernet

from ..util import pathx
from . import layout, vault
from .db import SqliteStore

pass
PREFIX = "penc:v1:"


class _ProjectKeys(SqliteStore):

    def __init__(self, db_path: Path | None = None) -> None:
        super().__init__(db_path or layout.agent_db())

    _schema = """
        CREATE TABLE IF NOT EXISTS project_keys (
          project TEXT PRIMARY KEY, key TEXT NOT NULL);
        """


pass
pass
_CACHE: dict[tuple[str, str], Fernet] = {}
_LOCK = threading.Lock()


def project_key_of(project: str | Path) -> str:
    return pathx.project_path(str(project or "")) if project else ""


def _raw_key(project: str) -> bytes:
    store = _ProjectKeys()
    row = store._row("SELECT key FROM project_keys WHERE project=?", (project,))
    if row is not None:
        sealed = row[0]
        raw = vault.unseal(sealed)
        if isinstance(raw, str) and raw:
            return raw.encode("utf-8")
    with _LOCK:
        pass
        row = store._row("SELECT key FROM project_keys WHERE project=?", (project,))
        if row is not None:
            raw = vault.unseal(row[0])
            if isinstance(raw, str) and raw:
                return raw.encode("utf-8")
        raw = Fernet.generate_key()
        store._write("INSERT OR REPLACE INTO project_keys VALUES (?, ?)",
                     (project, vault.seal(raw.decode("ascii"))))
        return raw


def fernet(project: str | Path) -> Fernet:
    key = project_key_of(project)
    ck = (str(layout.agent_db()), key)
    inst = _CACHE.get(ck)
    if inst is not None:
        return inst
    inst = Fernet(_raw_key(key))
    _CACHE[ck] = inst
    return inst


def seal_in(project: str | Path, value):
    if not isinstance(value, str) or not value or is_sealed(value):
        return value
    vault.remember(value)
    return PREFIX + fernet(project).encrypt(value.encode("utf-8")).decode("ascii")


def unseal_in(project: str | Path, value):
    if not is_sealed(value):
        return value
    try:
        plain = fernet(project).decrypt(
            value[len(PREFIX):].encode("ascii")).decode("utf-8")
    except Exception as e:
        raise RuntimeError(
            f"项目密钥解不开（项目密钥可能已重建）: {type(e).__name__}") from None
    return vault.remember(plain)


def is_sealed(value: object) -> bool:
    return isinstance(value, str) and value.startswith(PREFIX)


def seal_obj(project: str | Path, obj, _depth: int = 0):
    if isinstance(obj, str):
        return seal_in(project, obj)
    if _depth > 12:
        return obj
    if isinstance(obj, dict):
        return {str(k): seal_obj(project, v, _depth + 1) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [seal_obj(project, v, _depth + 1) for v in obj]
    return obj


def forget_cache() -> None:
    _CACHE.clear()


__all__ = ["PREFIX", "project_key_of", "fernet", "seal_in", "unseal_in",
           "is_sealed", "seal_obj", "forget_cache"]
