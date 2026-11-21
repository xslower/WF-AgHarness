from __future__ import annotations

import io
import json
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ....chat.recent import publish_file_changed
from ...text_limit import MAX_OUTPUT

if TYPE_CHECKING:
    from ... import ToolContext

logger = logging.getLogger("harness.tools.web.inspect")

pass
MAX_ITEMS = 40
pass
MAX_COLLECT = 2000
pass
MAX_LINE = 300
NAV_TIMEOUT_MS = 20_000
SETTLE_MS = 800
MAX_SETTLE_MS = 10_000
BROWSER_TIMEOUT_MS = 45_000
pass
MAX_SCREENS = 8
pass
MAX_SHOTS = 8

_BAD_CONSOLE = {"error", "warning", "pageerror", "assert"}


def _clip(s: str) -> str:
    s = (s or "").replace("\n", " ").strip()
    return s[:MAX_LINE] + ("…" if len(s) > MAX_LINE else "")


def _tail(rows: list[dict], what: str) -> list[dict]:
    if len(rows) <= MAX_ITEMS:
        return rows
    head = MAX_ITEMS * 2 // 3
    return (rows[:head] + [{"...": f"中间省略 {len(rows) - MAX_ITEMS} 条 {what}"}]
            + rows[-(MAX_ITEMS - head):])


class Recorder:

    def __init__(self) -> None:
        self.console: list[dict] = []
        self.requests: list[dict] = []
        self.problems: list[dict] = []
        self._levels: dict[str, int] = {}

    def attach(self, page) -> None:
        page.on("console", self._on_console)
        page.on("pageerror", self._on_pageerror)
        page.on("request", self._on_request)
        page.on("requestfailed", self._on_failed)
        page.on("response", self._on_response)

    def _on_console(self, m) -> None:
        self._log(m.type, m.text)

    def _on_pageerror(self, e) -> None:
        self._log("pageerror", str(e))

    def _log(self, level: str, text: str) -> None:
        if len(self.console) < MAX_COLLECT:
            self.console.append({"level": level, "text": _clip(text)})
        self._levels[level] = self._levels.get(level, 0) + 1

    def _on_request(self, r) -> None:
        if len(self.requests) < MAX_COLLECT:
            self.requests.append({"method": r.method, "url": _clip(r.url),
                                 "type": r.resource_type})

    def _on_failed(self, r) -> None:
        self._problem({"method": r.method, "url": _clip(r.url),
                       "type": r.resource_type,
                       "error": _clip(str(r.failure or ""))})

    def _on_response(self, r) -> None:
        if r.status >= 400:
            self._problem({"method": r.request.method, "url": _clip(r.url),
                           "status": r.status, "error": f"HTTP {r.status}"})

    def _problem(self, row: dict) -> None:
        if len(self.problems) < MAX_COLLECT:
            self.problems.append(row)

    def result(self, all_requests: bool) -> dict:
        bad = [c for c in self.console if c["level"] in _BAD_CONSOLE]
        rows = self.requests if all_requests else self.problems
        shown = _tail(rows, "network")
        return {
            "console": {"total": len(self.console), "errors": len(bad),
                        "levels": self._levels,
                        "messages": _tail(bad, "console")},
            "network": {"total": len(self.requests),
                        "failed": len(self.problems),
                        "shown": len(shown), "requests": shown},
        }


def _parse_viewport(viewport: str) -> dict | None:
    if not viewport:
        return None
    try:
        w, h = viewport.lower().split("x", 1)
        return {"width": max(320, min(int(w), 3840)),
                "height": max(240, min(int(h), 2160))}
    except (ValueError, TypeError):
        return None


def _shot_dir(ctx: "ToolContext", name: str = "web_inspect") -> Path:
    cwd = Path(getattr(ctx, "cwd", "") or ".").resolve()
    d = cwd / "runs" / f"{name}_{int(time.time() * 1000)}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _rel(ctx: "ToolContext", p: Path) -> str:
    root = Path(getattr(ctx, "cwd", "") or ".").resolve()
    try:
        return str(p.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(p)


def _publish(ctx: "ToolContext", p: Path) -> None:
    try:
        report = getattr(ctx, "report_file", None)
        if report is not None:
            report(str(p))
    except Exception:
        logger.debug("inspect: report_file 失败", exc_info=True)
    publish_file_changed(str(getattr(ctx, "cwd", "") or ""), p, "created")


async def _full_image(page) -> tuple | None:
    from PIL import Image
    try:
        raw = await page.screenshot(full_page=True)
        width = int(await page.evaluate("innerWidth"))
        height = int(await page.evaluate("innerHeight"))
        im = Image.open(io.BytesIO(raw)).convert("RGB")
        return im, (width, height)
    except Exception:
        logger.debug("inspect: 长图截图失败", exc_info=True)
        return None


def _crop_save(im, box: tuple[int, int, int, int], p: Path) -> bool:
    try:
        x0, y0, x1, y1 = box
        x0, y0 = max(0, int(x0)), max(0, int(y0))
        x1, y1 = min(im.width, int(x1)), min(im.height, int(y1))
        if x1 <= x0 or y1 <= y0:
            return False
        im.crop((x0, y0, x1, y1)).save(p, "PNG")
        return p.exists() and p.stat().st_size > 0
    except Exception:
        logger.debug("inspect: 裁图失败 %s", p.name, exc_info=True)
        return False


def _screens(im, vp: tuple, ctx: "ToolContext", out_dir: Path) -> list[dict]:
    _, vh = vp
    count = max(1, min(MAX_SCREENS, -(-im.height // max(1, vh))))
    out: list[dict] = []
    for i in range(count):
        top = i * vh
        p = out_dir / f"screen_{i + 1:02d}.png"
        if not _crop_save(im, (0, top, im.width, top + vh), p):
            continue
        _publish(ctx, p)
        out.append({"path": _rel(ctx, p), "scrollY": top,
                    "page_y": [top, min(top + vh, im.height)]})
    return out


def _parse_at(at: str) -> dict | None:
    try:
        parts = [float(v) for v in str(at).replace(" ", "").split(",")]
        if len(parts) != 4:
            return None
        x, y, w, h = parts
        if w <= 0 or h <= 0:
            return None
        return {"x": x, "y": y, "width": w, "height": h}
    except (ValueError, TypeError):
        return None


async def _locate_shots(page, im, ctx: "ToolContext", out_dir: Path,
                        shots: list) -> list[dict]:
    out: list[dict] = []
    for i, item in enumerate(shots[:MAX_SHOTS]):
        if not isinstance(item, dict):
            continue
        p = out_dir / f"shot_{i + 1:02d}.png"
        row: dict[str, Any] = {"index": i + 1}
        sel = str(item.get("selector") or "").strip()
        if sel:
            rect = await _element_rect(page, sel)
        else:
            rect = _parse_at(str(item.get("at") or ""))
        if rect is None:
            row.update({"ok": False, "selector": sel or None,
                        "error": '需要 at:"x,y,w,h" 或可定位的 selector'})
        else:
            box = (rect["x"], rect["y"],
                   rect["x"] + rect["width"], rect["y"] + rect["height"])
            ok = _crop_save(im, box, p)
            row.update({"ok": ok, "bbox": rect,
                        "error": None if ok else "区域超出长图范围或裁图失败"})
            if sel:
                row["selector"] = sel
            else:
                row["at"] = str(item.get("at"))
        row["path"] = _rel(ctx, p) if row.get("ok") else None
        if row.get("ok"):
            _publish(ctx, p)
        out.append(row)
    return out


async def _element_rect(page, sel: str) -> dict | None:
    try:
        loc = page.locator(sel).first
        await loc.wait_for(state="attached", timeout=3000)
        box = await loc.bounding_box()
        if not box:
            return None
        sy = await page.evaluate("window.scrollY")
        return {"x": round(box["x"], 1), "y": round(box["y"] + sy, 1),
                "width": round(box["width"], 1),
                "height": round(box["height"], 1)}
    except Exception:
        logger.debug("inspect: 元素定位失败 %s", sel, exc_info=True)
        return None


async def _page_meta(page) -> dict:
    try:
        return {"title": _clip(await page.title()), "final_url": page.url}
    except Exception:
        logger.debug("inspect: 取标题/地址失败", exc_info=True)
        return {"title": "", "final_url": ""}


def _clip_json(obj: dict) -> str:
    text = json.dumps(obj, ensure_ascii=False)
    if len(text) > MAX_OUTPUT:
        net = obj.get("network", {})
        if isinstance(net, dict) and net.get("requests"):
            net["requests"] = net["requests"][:10]
            net["shown"] = len(net["requests"])
            net["truncated"] = True
        text = json.dumps(obj, ensure_ascii=False)
    return (text if len(text) <= MAX_OUTPUT
            else text[:MAX_OUTPUT] + f"\n...[截断，共 {len(text)} 字符]")
