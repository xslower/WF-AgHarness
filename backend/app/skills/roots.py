from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable


from ..store import layout
from ..project.scope import current_project
from . import index

logger = logging.getLogger("harness.skills")

pass
SKILLS_DIR = layout.SOURCE_ROOT / "data" / "skills"

pass
_PLUGINMAN = None


def bind_pluginman(pm) -> None:
    global _PLUGINMAN
    _PLUGINMAN = pm


def skill_roots() -> list[Path]:
    roots = [Path(SKILLS_DIR)]

    pm = _PLUGINMAN
    if pm is None:
        return roots
    try:
        pass
        pass
        pass
        registered = getattr(pm, "project_skill_dirs", None)
        if registered is not None:
            for d in registered(current_project()):
                p = Path(d)
                if p not in roots:
                    roots.append(p)
    except Exception:
        logger.debug("skill 根解析失败（项目插件），继续用内置根", exc_info=True)
    return roots


def list_skills() -> list[str]:
    return index.list_skills(skill_roots())


def skill_index_of(project: str) -> dict[str, Path]:
    from ..project.scope import project_scope

    with project_scope(str(project)):
        return index.skill_index(skill_roots())


def list_skills_of(project: str) -> list[str]:
    return sorted(skill_index_of(project))


def catalog_text(limit: int = 15) -> str:
    index_ = index.skill_index(skill_roots())
    if not index_:
        return ""
    names = sorted(index_)
    lines = []
    for n in names[:limit]:
        desc = index.skill_meta(index_[n])["desc"]
        lines.append(f"  {n} — {desc}" if desc else f"  {n}")
    rest = len(names) - len(lines)
    text = "\n".join(lines)
    if rest > 0:
        text += f"\n  ...另有 {rest} 个，用 action=search 检索"
    return text

