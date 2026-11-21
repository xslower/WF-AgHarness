from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

pass
SHARE_ROOT = str(Path("~/share").expanduser())

pass
_SHARE_MARKER = "/share/share/"
pass
_OLD_SINGLE_SHARE = ("/media/swf/MyDisk/share/", "/media/swf/MyDisk1/share/")


pass
def syntax_path(path: str | os.PathLike | None) -> str:
    s = str(path or "").strip().replace("\\", "/")
    if not s:
        return s
    if s.startswith("~/"):
        s = str(Path(s).expanduser())
    if s == SHARE_ROOT:
        return s
    if s.startswith(SHARE_ROOT + "/"):
        return s.rstrip("/")
    pass
    i = s.rfind(_SHARE_MARKER)
    if i >= 0:
        return (SHARE_ROOT + s[i + len(_SHARE_MARKER) - 1:]).rstrip("/")
    for old in _OLD_SINGLE_SHARE:
        if s.startswith(old):
            return (SHARE_ROOT + "/" + s[len(old):]).rstrip("/")
    return s.rstrip("/")


pass
@lru_cache(maxsize=8)
def _alias_table(share_root: str) -> tuple[tuple[str, str], ...]:
    table: list[tuple[str, str]] = [(share_root, "")]
    try:
        real = os.path.realpath(share_root)
    except (OSError, ValueError):
        real = ""
    if real and real != share_root:
        table.append((real, ""))
    home = os.path.dirname(share_root)
    try:
        names = sorted(os.listdir(home))
    except OSError:
        names = []
    for name in names:
        link = os.path.join(home, name)
        try:
            if not os.path.islink(link):
                continue
            target = os.path.realpath(link)
        except (OSError, ValueError):
            continue
        if not real or not target:
            continue
        if target == real:
            table.append((link, ""))
        elif target.startswith(real + "/"):
            table.append((link, target[len(real) + 1:]))
    table.sort(key=lambda kv: len(kv[0]), reverse=True)
    return tuple(table)


def share_aliases() -> list[tuple[str, str]]:
    return list(_alias_table(SHARE_ROOT))


def invalidate_alias_cache() -> None:
    _alias_table.cache_clear()
    _physical_cached.cache_clear()


def _rel_from_alias(s: str) -> str | None:
    for prefix, rel in _alias_table(SHARE_ROOT):
        if not prefix or not s.startswith(prefix):
            continue
        rest = s[len(prefix):]
        if rest and not rest.startswith("/"):
            continue
        rest = rest.strip("/")
        return f"{rel}/{rest}" if rel and rest else (rel or rest)
    return None


pass
@lru_cache(maxsize=4096)
def _physical_cached(s: str) -> str:
    try:
        return os.path.realpath(os.path.abspath(os.path.expanduser(s)))
    except (OSError, ValueError):
        return os.path.abspath(os.path.expanduser(s))


def physical(path: str | os.PathLike | None) -> str:
    s = str(path or "")
    return _physical_cached(s) if s else ""


def same_path(a: str | os.PathLike | None,
              b: str | os.PathLike | None) -> bool:
    pa, pb = physical(a), physical(b)
    return bool(pa) and pa == pb


def rel_inside(path: str | os.PathLike | None,
               root: str | os.PathLike | None) -> str | None:
    p, r = physical(path), physical(root)
    if not p or not r:
        return None
    if p == r:
        return ""
    if p.startswith(r.rstrip("/") + "/"):
        return p[len(r.rstrip("/")) + 1:]
    return None


def is_within(path: str | os.PathLike | None,
              root: str | os.PathLike | None) -> bool:
    return rel_inside(path, root) is not None


pass
def project_path(path: str | os.PathLike | None) -> str:
    s = syntax_path(path)
    if not s or not s.startswith("/"):
        return s
    rel = _rel_from_alias(s)
    if rel is None:
        pass
        pass
        real = physical(s)
        rel = _rel_from_alias(real) if real != s else None
    if rel is None:
        return s
    return (SHARE_ROOT + "/" + rel).rstrip("/") if rel else SHARE_ROOT


def project_dir(path: str | os.PathLike | None) -> Path:
    return Path(project_path(str(Path(path or "").expanduser())))


def normalize_key(prefix: str, path: str) -> str:
    return prefix + project_path(path)


__all__ = [
    "SHARE_ROOT",
    "syntax_path", "project_path", "project_dir", "normalize_key",
    "physical", "same_path", "rel_inside", "is_within",
    "share_aliases", "invalidate_alias_cache",
]
