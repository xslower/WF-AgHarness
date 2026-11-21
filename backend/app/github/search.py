from __future__ import annotations

import logging

from .client import GitHubError, api_get, token

logger = logging.getLogger("harness.github")

pass
MAX_TOTAL = 1000
pass
_CODE_PAGE = 100


def search_skill_repos(q: str, page: int = 1, size: int = 12) -> dict:
    page = max(1, page)
    size = min(50, max(5, size))
    if token():
        try:
            return _by_code_search(q, page, size)
        except GitHubError as e:
            pass
            logger.warning("GitHub code search 失败，降级仓库搜索: %s", e)
            out = _by_repo_search(q, page, size)
            out["degraded"] = True
            out["note"] = f"代码搜索不可用（{e}），已降级为仓库搜索"
            return out
    out = _by_repo_search(q, page, size)
    out["degraded"] = True
    out["note"] = "未配置 GitHub Token，已降级为仓库搜索（精度受限，在设置页 MCP 里填 token）"
    return out


def _by_code_search(q: str, page: int, size: int) -> dict:
    query = "filename:SKILL.md" + (f" {q.strip()}" if q.strip() else "")
    raw = api_get("/search/code", {"q": query, "per_page": _CODE_PAGE,
                                   "page": page})
    repos: list[str] = []
    for item in raw.get("items", []):
        full = ((item.get("repository") or {}).get("full_name") or "")
        if full and full not in repos:
            repos.append(full)
    items = [_hydrate(r) for r in repos[:size]]
    total = min(int(raw.get("total_count", 0) or 0), MAX_TOTAL)
    return {"items": items, "total": total, "page": page, "size": size,
            "hasMore": len(repos) >= _CODE_PAGE and page * size < total,
            "degraded": False}


def _hydrate(full_name: str) -> dict:
    try:
        return _repo_item(full_name, api_get(f"/repos/{full_name}"))
    except GitHubError as e:
        logger.debug("补仓库元数据失败 %s: %s", full_name, e)
        return _repo_item(full_name)


def _by_repo_search(q: str, page: int, size: int) -> dict:
    parts = ["SKILL.md", "in:readme"]
    if q.strip():
        parts.append(q.strip())
    raw = api_get("/search/repositories", {
        "q": " ".join(parts), "sort": "stars", "order": "desc",
        "per_page": size, "page": page})
    items = [_repo_item(r.get("full_name", ""), r) for r in raw.get("items", [])]
    total = min(int(raw.get("total_count", 0) or 0), MAX_TOTAL)
    return {"items": items, "total": total, "page": page, "size": size,
            "hasMore": len(items) == size and page * size < total,
            "degraded": False}


def _repo_item(full_name: str, raw: dict | None = None) -> dict:
    raw = raw or {}
    owner = (raw.get("owner") or {}).get("login") or full_name.split("/")[0]
    branch = raw.get("default_branch", "main")
    return {
        "fullName": full_name,
        "description": (raw.get("description") or "")[:200],
        "stars": int(raw.get("stargazers_count", 0) or 0),
        "url": raw.get("html_url") or f"https://github.com/{full_name}",
        "rawUrl": (f"https://raw.githubusercontent.com/{full_name}/"
                   f"{branch}/SKILL.md"),
        "owner": owner,
        "topics": (raw.get("topics") or [])[:8],
    }
