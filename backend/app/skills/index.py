from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ..tools.text_limit import MAX_READ, truncate as _truncate
from ..util import jsonx



def _iter_skill_dirs(roots: Iterable[Path]):
    for root in roots:
        root = Path(root)
        if not root.is_dir():
            continue
        if (root / "SKILL.md").is_file():
            yield root
        try:
            children = sorted(root.iterdir())
        except OSError:
            continue
        for sub in children:
            if sub.is_dir() and (sub / "SKILL.md").is_file():
                yield sub


pass
pass
PREFIX = "skill__"


def qualify(name: str) -> str:
    n = (name or "").strip()
    return n if n.startswith(PREFIX) else PREFIX + n


def unqualify(name: str) -> str:
    n = (name or "").strip()
    return n[len(PREFIX):] if n.startswith(PREFIX) else n


def skill_index(roots: Iterable[Path]) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for d in _iter_skill_dirs(roots):
        index.setdefault(qualify(d.name), d)
    return index


def list_skills(roots: Iterable[Path]) -> list[str]:
    return sorted(skill_index(roots))


def _desc_of(body: str) -> str:
    for line in body.splitlines():
        s = line.strip().lstrip("#").strip()
        if s:
            return s[:80]
    return ""


def _tags_of(body: str) -> list[str]:
    for line in body.splitlines()[:30]:
        s = line.strip().lower()
        if s.startswith("tags:") or s.startswith("标签:"):
            return [t.strip() for t in s.split(":", 1)[1].split(",") if t.strip()]
    return []


def skill_meta(path: Path) -> dict:
    p = Path(path) / "SKILL.md"
    try:
        body = p.read_text("utf-8", errors="replace")
    except OSError:
        return {"desc": "", "tags": [], "lines": 0}
    return {"desc": _desc_of(body), "tags": _tags_of(body),
            "lines": len(body.splitlines())}



def match_skills(query: str, roots: Iterable[Path], limit: int = 5) -> list[dict]:
    q = (query or "").strip().lower()
    if not q:
        return []
    terms = q.split()
    scored: list[tuple[int, dict]] = []
    for n, d in skill_index(roots).items():
        try:
            body = (d / "SKILL.md").read_text("utf-8", errors="replace")
        except OSError:
            continue
        low = body.lower()
        desc = _desc_of(body)
        tags = _tags_of(body)
        low_tags = [t.lower() for t in tags]
        score = 0
        if all(t in n.lower() for t in terms):
            score += 10
        score += sum(3 for t in terms if t in n.lower())
        score += sum(2 for t in terms if t in desc.lower())
        score += sum(6 for t in terms if any(t == tg or t in tg for tg in low_tags))
        score += low.count(q)
        if score > 0:
            scored.append((score, {"name": n, "desc": desc, "tags": tags,
                                   "score": score}))
    scored.sort(key=lambda x: -x[0])
    return [hit for _, hit in scored[:limit]]



def use_skill(name: str, roots: Iterable[Path]) -> str:
    index = skill_index(roots)
    d = index.get(qualify(name))
    if d is None:
        avail = ", ".join(sorted(index)) or "（无）"
        return jsonx.dumps(
            {"error": f"skill 不存在: {name}。可用: {avail}"
                      "（也可用 tool(action=search) 按关键词查）"})
    return _truncate((d / "SKILL.md").read_text("utf-8", errors="replace"), MAX_READ)
