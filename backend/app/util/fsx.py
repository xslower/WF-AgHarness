from __future__ import annotations

from pathlib import Path

from . import pathx


def rel_to(path: str | Path, root: str | Path) -> Path | None:
    rel = pathx.rel_inside(path, root)
    return None if rel is None else Path(rel or ".")


def is_inside(path: str | Path, root: str | Path) -> bool:
    return pathx.is_within(path, root)



def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def ensure_parent(file_path: str | Path) -> Path:
    p = Path(file_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def write_text(file_path: str | Path, text: str, encoding: str = "utf-8") -> Path:
    p = ensure_parent(file_path)
    tmp = p.with_name(f".{p.name}.tmp")
    tmp.write_text(text, encoding)
    tmp.replace(p)
    return p
