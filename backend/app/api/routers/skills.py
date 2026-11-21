from __future__ import annotations

import re
import urllib.request
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..errors import bad_gateway, bad_request, conflict, not_found
from ...store import layout
from ...util import pathx
from ..deps import Container, get_container
from ...skills import skill_meta, unqualify
from ...util.fsx import rel_to

router = APIRouter()

_UA = {"User-Agent": "Harness-SkillHub/1.0"}


def _skill_dir() -> Path:
    from ...skills import roots as skill_roots
    return skill_roots.SKILLS_DIR


def _skill_path(name: str) -> Path:
    dirname = (name or "").strip()
    if (not dirname or dirname in (".", "..")
            or "/" in dirname or "\\" in dirname or ":" in dirname):
        raise bad_request(f"非法的 skill 名称: {name}")
    root = _skill_dir().resolve()
    target = (root / dirname).resolve()
    if target.parent != root:
        raise bad_request(f"skill 目录越界，已拒绝: {name}")
    return target


def _project_skill_path(project: str, name: str) -> Path | None:
    p = pathx.project_dir(project)
    if not layout.is_project(p):
        return None
    root = layout.project_skills_dir(p).resolve()
    rel = rel_to((root / (name or "").strip()).resolve(), root)
    if rel is None or not rel.parts:
        return None
    target = root / rel
    return target if (target / "SKILL.md").is_file() else None


def _skill_index_for(project: str) -> tuple[Path, dict[str, Path]]:
    from ...skills import roots as skill_roots

    return _skill_dir().resolve(), skill_roots.skill_index_of(project)


@router.get("/api/skills")
def skills_list(project: str = ""):
    _, index = _skill_index_for(project)
    return {"skills": sorted(index)}

@router.get("/api/skills/detail")
def skills_detail(project: str = ""):
    builtin, index = _skill_index_for(project)
    items: list[dict] = []
    for name, path in sorted(index.items()):
        pass
        meta = skill_meta(path)
        pass
        pass
        pass
        src = "builtin" if Path(path).resolve().is_relative_to(builtin) else "project"
        items.append({"name": name, "display": unqualify(name),
                      "desc": meta["desc"], "tags": meta["tags"],
                      "lines": meta["lines"], "source": src})
    return {"skills": items}


@router.get("/api/skills/explore")
def skills_explore(q: str = "", page: int = 1, size: int = 12):
    from ...github import GitHubError, search_skill_repos

    try:
        return search_skill_repos(q, page=page, size=size)
    except GitHubError as e:
        raise bad_gateway(str(e))


class SkillInstallIn(BaseModel):
    url: str = ""
    name: str = ""
    project: str = ""


def _project_skill_target(project: str, name: str) -> Path:
    p = pathx.project_dir(project)
    if not layout.is_project(p):
        raise bad_request(f"不是项目目录: {project}")
    root = layout.project_skills_dir(p).resolve()
    sub = (name or "").strip().strip("/")
    if not sub or "\\" in sub or sub.split("/")[0] in (".", ".."):
        raise bad_request(f"非法的 skill 名称: {name}")
    target = (root / sub).resolve()
    rel = rel_to(target, root)
    if rel is None or not rel.parts:
        raise bad_request(f"skill 目录越界，已拒绝: {name}")
    return target


@router.post("/api/skills/install")
def skills_install(body: SkillInstallIn, c: Container = Depends(get_container)):
    url = (body.url or "").strip()
    if not url:
        raise bad_request("请提供 skill 的 URL")
    name = (body.name or "").strip()
    if not name:
        seg = url.rstrip("/").rsplit("/", 1)[-1]
        name = re.sub(r"\.(md|json|txt|yml|yaml)$", "", seg, flags=re.IGNORECASE)
    if not name or name.lower() == "skill":
        raise bad_request(f"无法推导 skill 名: {name}")
    pass
    if body.project:
        target = _project_skill_target(body.project, name)
    else:
        target = _skill_path(name)
    if target.exists():
        raise conflict(f"Skill {name} 已存在")
    try:
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        raise bad_gateway(f"无法获取 URL: {e}")
    if not content.strip():
        raise bad_request("获取到的内容为空")
    target.mkdir(parents=True, exist_ok=True)
    (target / "SKILL.md").write_text(content, "utf-8")
    pass
    if body.project:
        from ...plugins.adopt import adopt_skill
        try:
            adopt_skill(body.project, name, installs=c.installs)
        except ValueError:
            pass
    return {"ok": True, "name": name, "lines": len(content.splitlines())}


@router.delete("/api/skills/{name}")
def skills_delete(name: str, project: str = "",
                  c: Container = Depends(get_container)):
    import shutil

    plain = unqualify(name)
    pass
    target = _project_skill_path(project, plain)
    if target is not None:
        shutil.rmtree(target, ignore_errors=True)
        _unregister_skill(c, project, plain)
        return {"ok": True, "removed": str(target)}
    pass
    from ...plugins.adopt import registered_skill_dirs
    for d in registered_skill_dirs(c.installs, project):
        if d.name == plain:
            raise bad_request(f"skill {plain} 随插件登记，请卸载对应插件")
    pass
    target = _skill_path(plain)
    if not target.is_dir():
        raise not_found(f"Skill 不存在: {name}")
    shutil.rmtree(target)
    return {"ok": True, "removed": str(target)}

def _unregister_skill(c: Container, project: str, name: str) -> None:
    from ...plugins import location
    p = pathx.project_dir(project) if project else None
    if p is None or not layout.is_project(p):
        return
    try:
        c.installs.remove_plugin(f"{location.SKILL_PID_PREFIX}{name}", str(p))
    except Exception:
        pass
