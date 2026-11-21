from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable, Optional

logger = logging.getLogger("harness.github")

pass
_SETTINGS: Optional[Callable[[], object]] = None

API = "https://api.github.com"
pass
TIMEOUT = 15
pass
CACHE_TTL = 60
pass
_CACHE_MAX = 200

_UA = {"User-Agent": "Harness-GitHub/1.0",
       "Accept": "application/vnd.github+json",
       "X-GitHub-Api-Version": "2022-11-28"}

pass
_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_LOCK = threading.Lock()


class GitHubError(RuntimeError):

    def __init__(self, message: str, status_code: int = 0) -> None:
        super().__init__(message)
        self.status_code = status_code

    @property
    def rate_limited(self) -> bool:
        return self.status_code in (403, 429)


def bind_settings(getter: Optional[Callable[[], object]] = None) -> None:
    global _SETTINGS
    _SETTINGS = getter


def _setting_token() -> str:
    if _SETTINGS is None:
        return ""
    try:
        return (getattr(_SETTINGS(), "githubToken", "") or "").strip()
    except Exception:
        return ""


def token() -> str:
    v = _setting_token()
    if v:
        return v
    for name in ("GITHUB_TOKEN", "GITHUB_PERSONAL_ACCESS_TOKEN"):
        v = (os.environ.get(name) or "").strip()
        if v:
            return v
    return ""


def status() -> dict:
    t = token()
    return {"configured": bool(t),
            "hint": f"…{t[-4:]}" if len(t) >= 8 else "",
            "source": _source()}


def _source() -> str:
    if _setting_token():
        return "settings"
    for name in ("GITHUB_TOKEN", "GITHUB_PERSONAL_ACCESS_TOKEN"):
        if (os.environ.get(name) or "").strip():
            return f"env:{name}"
    return ""


def _headers() -> dict:
    h = dict(_UA)
    t = token()
    if t:
        h["Authorization"] = f"Bearer {t}"
    return h


def api_get(path: str, params: dict | None = None,
            cache: bool = True) -> dict:
    url = API + path
    if params:
        clean = {k: str(v) for k, v in params.items() if v not in (None, "")}
        url += "?" + urllib.parse.urlencode(clean, quote_via=urllib.parse.quote)
    if cache:
        hit = _cache_get(url)
        if hit is not None:
            return hit
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        raise GitHubError(_explain(e.code, body), e.code) from e
    except Exception as e:
        raise GitHubError(f"GitHub 请求失败: {e}") from e
    if not isinstance(data, dict):
        data = {"items": data}
    if cache:
        _cache_put(url, data)
    return data


def _explain(code: int, body: str) -> str:
    if code == 401:
        return ("GitHub 认证失败：未配置 token 或 token 无效"
                "（匿名只能做部分搜索，code search 必须带 token）")
    if code == 403:
        return f"GitHub 拒绝访问（多半是配额用尽，稍后再试）: {body}"
    if code == 404:
        return "GitHub 资源不存在"
    if code == 422:
        return f"GitHub 查询语法不合法: {body}"
    return f"GitHub API 错误 {code}: {body}"


def whoami() -> dict:
    data = api_get("/user", cache=False)
    return {"login": data.get("login", ""), "name": data.get("name", ""),
            "scopes": ""}


def _cache_get(url: str) -> dict | None:
    with _CACHE_LOCK:
        row = _CACHE.get(url)
        if row is None:
            return None
        ts, data = row
        if time.time() - ts > CACHE_TTL:
            _CACHE.pop(url, None)
            return None
        return data


def _cache_put(url: str, data: dict) -> None:
    with _CACHE_LOCK:
        if len(_CACHE) >= _CACHE_MAX:
            pass
            for k in sorted(_CACHE, key=lambda k: _CACHE[k][0])[: _CACHE_MAX // 2]:
                _CACHE.pop(k, None)
        _CACHE[url] = (time.time(), data)


def clear_cache() -> None:
    with _CACHE_LOCK:
        _CACHE.clear()
