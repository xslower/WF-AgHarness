from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from ....util.jsonx import err
from ...text_limit import MAX_OUTPUT, truncate as _truncate
from .channels import fetch_doc
from .extract import _html_to_md
from .interact import interact_page

if TYPE_CHECKING:
    from ... import ToolContext

pass
THIN_CONTENT = 200
pass
_DEFAULT_DEBUG = {"screen": "page", "shots": [], "wait_ms": 0,
                  "all_requests": False, "viewport": ""}


def is_url(q: str) -> bool:
    return (q or "").strip().lower().startswith(("http://", "https://", "file://"))


def _looks_broken(status: int, content_type: str, text: str) -> bool:
    if status >= 400:
        return True
    return "html" in (content_type or "") and len((text or "").strip()) < THIN_CONTENT


def _pick(d: dict, *names):
    for n in names:
        v = d.get(n)
        if v not in (None, ""):
            return v
    low = {str(k).lower(): v for k, v in d.items()}
    for n in names:
        v = low.get(n.lower())
        if v not in (None, ""):
            return v
    return None


def _as_bool(v: Any, default: bool = False) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    s = str(v or "").strip().lower()
    if s in ("true", "1", "yes", "on", "all", "y", "是"):
        return True
    if s in ("false", "0", "no", "off", "none", "否"):
        return False
    return default


def _as_ms(v: Any, default: int = 0) -> int:
    if isinstance(v, (int, float)):
        return max(0, min(int(v), 10_000))
    m = re.match(r"^([\d.]+)\s*(ms|s|毫秒|秒)?$", str(v or "").strip().lower())
    if not m:
        return default
    n = float(m.group(1))
    unit = m.group(2)
    return max(0, min(int(n * (1000 if unit in ("s", "秒") else 1)), 10_000))


def _as_at(v: Any) -> str:
    if isinstance(v, (list, tuple)) and len(v) == 4:
        return ",".join(str(n) for n in v)
    if isinstance(v, dict):
        n = [_pick(v, "x", "left"), _pick(v, "y", "top"),
             _pick(v, "w", "width"), _pick(v, "h", "height")]
        if all(x is not None for x in n):
            return ",".join(str(x) for x in n)
    return str(v)


def _as_shots(v: Any) -> list[dict]:
    if v is None or v is False or v == "":
        return []
    if isinstance(v, str):
        s = v.strip()
        try:
            parsed = json.loads(s) if s.startswith(("[", "{")) else None
        except ValueError:
            parsed = None
        if isinstance(parsed, dict):
            v = [parsed]
        elif isinstance(parsed, list):
            v = parsed
        elif re.match(r"^[\d.,\s]+$", s):
            v = [{"at": s}]
        elif s.startswith((".", "#", "[", "body", "div", "h1", "h2", "h3")):
            v = [{"selector": s}]
        else:
            return []
    if isinstance(v, dict):
        v = [v]
    if not isinstance(v, list):
        return []
    out: list[dict] = []
    for item in v[:8]:
        if isinstance(item, str):
            t = item.strip()
            item = ({"at": t} if re.match(r"^[\d.,\s]+$", t)
                    else {"selector": t})
        if not isinstance(item, dict):
            continue
        sel = _pick(item, "selector", "css", "sel", "xpath", "元素", "选择器")
        at = _pick(item, "at", "rect", "box", "area", "coords", "position", "坐标")
        if sel is not None:
            out.append({"selector": str(sel).strip()})
        elif at is not None:
            out.append({"at": _as_at(at)})
        else:
            n = [_pick(item, "x", "left"), _pick(item, "y", "top"),
                 _pick(item, "w", "width"), _pick(item, "h", "height")]
            if all(x is not None for x in n):
                out.append({"at": ",".join(str(x) for x in n)})
    return out


def _as_viewport(v: Any) -> str:
    if isinstance(v, dict):
        return f"{_pick(v, 'width', 'w') or 1280}x{_pick(v, 'height', 'h') or 720}"
    if isinstance(v, (list, tuple)) and len(v) == 2:
        return f"{v[0]}x{v[1]}"
    return str(v or "").strip()


def _debug_opts(debug: Any) -> dict | None:
    if debug is None or debug is False or debug == 0 or debug == "":
        return None
    if isinstance(debug, str):
        s = debug.strip().lower()
        if s in ("false", "0", "no", "off", "none", "normal", "轻量"):
            return None
        if s.startswith("{"):
            try:
                debug = json.loads(debug)
            except ValueError:
                return dict(_DEFAULT_DEBUG)
        elif s.startswith("["):
            return {**_DEFAULT_DEBUG, "shots": _as_shots(debug)}
        else:
            return dict(_DEFAULT_DEBUG)
    if isinstance(debug, (bool, int, float)):
        return dict(_DEFAULT_DEBUG)
    if isinstance(debug, list):
        return {**_DEFAULT_DEBUG, "shots": _as_shots(debug)}
    if not isinstance(debug, dict):
        return dict(_DEFAULT_DEBUG)
    screen = str(_pick(debug, "screen", "mode", "type", "capture", "截图", "模式")
                 or "page").strip().lower()
    if screen not in ("viewport", "视口", "screen", "first", "当前屏", "visible"):
        screen = "page"
    else:
        screen = "viewport"
    return {"screen": screen,
            "shots": _as_shots(_pick(debug, "shots", "screens", "regions",
                                     "areas", "positions", "截图", "局部")),
            "wait_ms": _as_ms(_pick(debug, "wait_ms", "wait", "delay", "settle",
                                    "waitfor", "等待")),
            "all_requests": _as_bool(_pick(debug, "all_requests", "all",
                                           "network", "requests", "全部请求")),
            "viewport": _as_viewport(_pick(debug, "viewport", "size", "window",
                                           "resolution", "分辨率", "视口尺寸"))}


def _as_steps(v: Any) -> list[dict]:
    if v is None or v is False or v == "":
        return []
    if isinstance(v, str):
        try:
            v = json.loads(v.strip())
        except ValueError:
            return []
    if isinstance(v, dict):
        v = [v]
    return [x for x in v if isinstance(x, dict)] if isinstance(v, list) else []


def _format_doc(doc: dict, target: str, text: str | None = None) -> str:
    ct = doc.get("content_type") or ""
    if text is None:
        raw = doc.get("text") or ""
        text = _html_to_md(raw) if "html" in ct else raw
    head = f"[{doc.get('status', '?')} {ct}]\n"
    final = doc.get("final_url") or ""
    if final and final.rstrip("/") != (target or "").rstrip("/"):
        head += f"最终地址: {final}\n"
    return _truncate(head + text, MAX_OUTPUT)


async def web_fetch(url: str, ctx: "ToolContext") -> str:
    try:
        doc = await fetch_doc(url)
    except Exception as e:
        return err(f"请求失败: {e}")
    return _format_doc(doc, url)


async def _fast_fetch(target: str, ctx: "ToolContext") -> str | None:
    try:
        doc = await fetch_doc(target)
    except Exception:
        return None
    ct = doc.get("content_type") or ""
    raw = doc.get("text") or ""
    text = _html_to_md(raw) if "html" in ct else raw
    if _looks_broken(int(doc.get("status") or 0), ct, text):
        return None
    return _format_doc(doc, target, text)


async def _browser_open(target: str, ctx: "ToolContext", *, steps: list[dict],
                        opts: dict | None) -> str:
    o = opts or {}
    raw = await interact_page(
        target, ctx, steps=steps,
        screenshot=opts is not None,
        wait_ms=o.get("wait_ms", 0), viewport=o.get("viewport", ""),
        all_requests=o.get("all_requests", False),
        opts={**o, "with_logs": opts is not None, "want_content": True})
    pass
    pass
    if opts is None and not steps:
        try:
            doc = json.loads(raw)
        except (ValueError, TypeError):
            return raw
        if doc.get("error") or not doc.get("content"):
            return raw
        final = doc.get("final_url") or ""
        head = (f"最终地址: {final}\n"
                if final and final.rstrip("/") != target.rstrip("/") else "")
        return _truncate(head + doc["content"], MAX_OUTPUT)
    return raw


async def open_page(query: str, ctx: "ToolContext", *, steps: Any = None,
                    debug: Any = None) -> str:
    target = (query or "").strip()
    if not is_url(target):
        return err("url 必须是 http(s):// 或 file:// 地址")
    opts = _debug_opts(debug)
    clean = _as_steps(steps)
    if not clean and opts is None:
        fast = await _fast_fetch(target, ctx)
        if fast is not None:
            return fast
    return await _browser_open(target, ctx, steps=clean, opts=opts)
