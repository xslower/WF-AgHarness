from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ....util.jsonx import err
from .crawl import _import_crawl4ai
from .extract import _html_to_md
from .inspect import (
    BROWSER_TIMEOUT_MS, MAX_SETTLE_MS, NAV_TIMEOUT_MS, SETTLE_MS,
    Recorder, _clip, _clip_json, _crop_save, _full_image, _locate_shots,
    _page_meta, _parse_viewport, _publish, _rel, _screens, _shot_dir,
)

if TYPE_CHECKING:
    from ... import ToolContext

logger = logging.getLogger("harness.tools.web.interact")

pass
MAX_STEPS = 40
pass
STEP_TIMEOUT_MS = 15_000
pass
DIR_NAME = "web_interact"
pass
CONTENT_MAX = 8000
pass
_HANDLERS: dict[str, Any] = {}
pass
SID = "harness-web-interact"


def _timeout(step: dict) -> int:
    try:
        t = int(step.get("timeout_ms") or STEP_TIMEOUT_MS)
    except (TypeError, ValueError):
        t = STEP_TIMEOUT_MS
    return max(1_000, min(t, BROWSER_TIMEOUT_MS))


def _handler(*acts: str):
    def deco(fn):
        for a in acts:
            _HANDLERS[a] = fn
        return fn
    return deco


def _loc(page, step: dict):
    return page.locator(step["selector"]).first


@_handler("goto")
async def _h_goto(page, step: dict, ctx, out_dir) -> dict:
    resp = await page.goto(str(step["url"]).strip(), wait_until="load",
                           timeout=_timeout(step))
    return {"status": resp.status if resp is not None else None}


@_handler("click")
async def _h_click(page, step: dict, ctx, out_dir) -> dict:
    await _loc(page, step).click(timeout=_timeout(step))
    return {}


@_handler("fill")
async def _h_fill(page, step: dict, ctx, out_dir) -> dict:
    await _loc(page, step).fill(str(step.get("value", "")), timeout=_timeout(step))
    return {}


@_handler("type")
async def _h_type(page, step: dict, ctx, out_dir) -> dict:
    try:
        delay = max(0, int(step.get("delay") or 30))
    except (TypeError, ValueError):
        delay = 30
    await _loc(page, step).press_sequentially(str(step.get("value", "")),
                                              delay=delay, timeout=_timeout(step))
    return {}


@_handler("press")
async def _h_press(page, step: dict, ctx, out_dir) -> dict:
    key = str(step.get("key") or step.get("value") or "").strip()
    if step["selector"]:
        await _loc(page, step).press(key, timeout=_timeout(step))
    else:
        await page.keyboard.press(key)
    return {}


@_handler("select")
async def _h_select(page, step: dict, ctx, out_dir) -> dict:
    values = step.get("values")
    if values is None:
        values = [step.get("value", "")]
    if not isinstance(values, list) or not values:
        raise ValueError("select 需要 value 或 values 数组")
    chosen = await _loc(page, step).select_option([str(v) for v in values],
                                                  timeout=_timeout(step))
    return {"selected": [str(c) for c in chosen]}


@_handler("check", "uncheck")
async def _h_check(page, step: dict, ctx, out_dir) -> dict:
    off = str(step.get("value", "")).strip().lower() in {"false", "0", "no", "off"}
    loc = _loc(page, step)
    if off or step["act"] == "uncheck":
        await loc.uncheck(timeout=_timeout(step))
    else:
        await loc.check(timeout=_timeout(step))
    return {}


@_handler("scroll")
async def _h_scroll(page, step: dict, ctx, out_dir) -> dict:
    amount = step.get("value", "bottom")
    low = str(amount).strip().lower()
    if low == "top":
        await page.evaluate("window.scrollTo(0, 0)")
    elif low == "bottom":
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    else:
        try:
            dy = int(amount)
        except (TypeError, ValueError):
            raise ValueError(f"scroll 的 value 应为 top/bottom 或像素数，收到 {amount!r}")
        await page.evaluate(f"window.scrollBy(0, {dy})")
    return {}


@_handler("wait")
async def _h_wait(page, step: dict, ctx, out_dir) -> dict:
    if step["selector"]:
        await _loc(page, step).wait_for(state="visible", timeout=_timeout(step))
        return {}
    try:
        ms = int(step.get("value") if step.get("value") is not None
                 else step.get("ms") or 0)
    except (TypeError, ValueError):
        ms = 0
    await page.wait_for_timeout(max(0, min(ms, MAX_SETTLE_MS)))
    return {}


@_handler("text")
async def _h_text(page, step: dict, ctx, out_dir) -> dict:
    text = await _loc(page, step).inner_text(timeout=_timeout(step))
    return {"text": _clip(str(text))}


@_handler("value")
async def _h_value(page, step: dict, ctx, out_dir) -> dict:
    val = await _loc(page, step).input_value(timeout=_timeout(step))
    return {"value": _clip(str(val))}


@_handler("attr")
async def _h_attr(page, step: dict, ctx, out_dir) -> dict:
    name = str(step.get("name") or "").strip()
    val = await _loc(page, step).get_attribute(name, timeout=_timeout(step))
    return {"attr": {name: val}}


@_handler("screenshot")
async def _h_screenshot(page, step: dict, ctx, out_dir) -> dict:
    p = out_dir / f"step_{step['_no']:02d}.png"
    if step["selector"]:
        await _loc(page, step).screenshot(path=str(p), timeout=_timeout(step))
    else:
        await page.screenshot(path=str(p))
    if not (p.exists() and p.stat().st_size > 0):
        raise RuntimeError("截图写入失败")
    _publish(ctx, p)
    return {"screenshot": _rel(ctx, p)}


pass
_NEEDS_SEL = {"click", "fill", "type", "select", "check", "uncheck",
              "text", "value", "attr"}


def _compile_steps(raw_steps: list) -> list[dict]:
    if len(raw_steps) > MAX_STEPS:
        raise ValueError(f"steps 最多 {MAX_STEPS} 步，收到 {len(raw_steps)}")
    plan: list[dict] = []
    for no, raw in enumerate(raw_steps, 1):
        step = dict(raw)
        act = str(step.get("act") or step.get("action") or "").strip().lower()
        if act not in _HANDLERS:
            raise ValueError(f"第 {no} 步 act 无效: {act!r}"
                             f"（可选：{'/'.join(sorted(_HANDLERS))}）")
        step["act"] = act
        step["_no"] = no
        step["selector"] = str(step.get("selector") or "").strip()
        if act in _NEEDS_SEL and not step["selector"]:
            raise ValueError(f"第 {no} 步 {act} 需要 selector")
        if act == "goto" and not str(step.get("url") or "").strip():
            raise ValueError(f"第 {no} 步 goto 需要 url")
        if act == "press" and not str(step.get("key") or step.get("value") or "").strip():
            raise ValueError(f"第 {no} 步 press 需要 key（如 Enter）")
        if act == "attr" and not str(step.get("name") or "").strip():
            raise ValueError(f"第 {no} 步 attr 需要 name（属性名，如 href）")
        plan.append(step)
    pass
    return plan


async def _run_steps(page, plan: list[dict], ctx: "ToolContext",
                     out_dir: Path | None) -> tuple[list[dict], str]:
    results: list[dict] = []
    fatal: str = ""
    for step in plan:
        row: dict[str, Any] = {"step": step["_no"], "act": step["act"]}
        results.append(row)
        if fatal:
            row["skipped"] = True
            continue
        try:
            row.update(await _HANDLERS[step["act"]](page, step, ctx, out_dir))
            row["ok"] = True
        except Exception as e:
            row["ok"] = False
            msg = f"{type(e).__name__}: {_clip(str(e))}"
            if step.get("optional"):
                row["warning"] = msg
            else:
                row["error"] = msg
                fatal = (f"第 {step['_no']} 步({step['act']}) 失败: {msg}，"
                         f"后续 {len(plan) - step['_no']} 步已跳过")
    return results, fatal


async def _collect_content(page, out: dict) -> None:
    try:
        md = _html_to_md(await page.content())
    except Exception:
        logger.debug("interact: 提取正文失败", exc_info=True)
        return
    out["content"] = md[:CONTENT_MAX]
    out["content_len"] = len(md)
    if len(md) > CONTENT_MAX:
        out["content_truncated"] = True


async def _collect_shots(page, out: dict, ctx: "ToolContext", out_dir: Path,
                         screenshot: bool, o: dict) -> None:
    shots = o.get("shots") or []
    image = await _full_image(page)
    if image is None:
        out["screenshot_error"] = "长图截图失败（console/network 仍有效）"
        return
    im, (vpw, vph) = image
    out["page_size"] = [im.width, im.height]
    if o.get("screen") == "viewport":
        p = out_dir / "viewport.png"
        if _crop_save(im, (0, 0, im.width, vph), p):
            _publish(ctx, p)
            out["screens"] = [{"path": _rel(ctx, p), "mode": "viewport",
                               "page_y": [0, vph]}]
    elif screenshot:
        out["screens"] = _screens(im, (vpw, vph), ctx, out_dir)
    if shots:
        out["shots"] = await _locate_shots(page, im, ctx, out_dir, shots)


def _browser_cfg(BrowserConfig, viewport: str):
    vp = _parse_viewport(viewport) or {"width": 1280, "height": 720}
    return BrowserConfig(headless=True, verbose=False, enable_stealth=True,
                         viewport_width=vp["width"], viewport_height=vp["height"])


async def _interact_core(crawler, target: str, plan: list[dict],
                         ctx: "ToolContext", *, check_robots: bool,
                         screenshot: bool, settle: int,
                         o: dict) -> tuple[dict, Recorder, bool]:
    rec = Recorder()
    if check_robots and not await crawler.robots_parser.can_fetch(
            target, crawler.browser_config.user_agent or "*"):
        return {"error": f"robots.txt 不允许交互该地址: {target}"}, rec, True
    page, _context = await crawler.crawler_strategy.browser_manager.get_page(
        CrawlerRunConfig(session_id=SID))
    rec.attach(page)
    page.set_default_timeout(BROWSER_TIMEOUT_MS)
    page.set_default_navigation_timeout(NAV_TIMEOUT_MS)
    resp = await page.goto(target, wait_until="load", timeout=NAV_TIMEOUT_MS)
    status = resp.status if resp is not None else None
    if status is not None and status >= 400:
        return {"status_code": status,
                "error": f"页面加载失败: HTTP {status}"}, rec, True
    out: dict[str, Any] = dict(await _page_meta(page))
    shots = o.get("shots") or []
    want_shots = screenshot or shots or any(s["act"] == "screenshot" for s in plan)
    out_dir = _shot_dir(ctx, DIR_NAME) if want_shots else None
    if out_dir is not None:
        out["shot_dir"] = _rel(ctx, out_dir)
    if plan:
        out["steps"], fatal = await _run_steps(page, plan, ctx, out_dir)
        if fatal:
            out["error"] = fatal
    await page.wait_for_timeout(settle)
    out.update(await _page_meta(page))
    if o.get("want_content", False):
        await _collect_content(page, out)
    if out_dir is not None:
        await _collect_shots(page, out, ctx, out_dir, screenshot, o)
    return out, rec, False


async def interact_page(url: str, ctx: "ToolContext", *,
                        steps: list | None = None, screenshot: bool = True,
                        wait_ms: int = 0, viewport: str = "",
                        all_requests: bool = False, opts: dict | None = None,
                        respect_robots: bool = True) -> str:
    target = (url or "").strip()
    if not target:
        return err("需要 url")
    if not target.lower().startswith(("http://", "https://", "file://")):
        return err("url 必须是 http(s):// 或 file:// 地址")
    try:
        plan = _compile_steps([s for s in (steps or []) if isinstance(s, dict)])
    except ValueError as e:
        return err(f"steps 无效: {e}")
    try:
        AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, _CacheMode = _import_crawl4ai()
        pass
        pass
        globals()["CrawlerRunConfig"] = CrawlerRunConfig
    except RuntimeError as e:
        return err(str(e))

    o = opts or {}
    pass
    check_robots = bool(respect_robots) and target.lower().startswith(("http://", "https://"))
    settle = SETTLE_MS + max(0, min(int(wait_ms or 0), MAX_SETTLE_MS))
    out: dict[str, Any] = {"url": target}
    try:
        async with AsyncWebCrawler(config=_browser_cfg(BrowserConfig, viewport)) as crawler:
            core, rec, aborted = await _interact_core(
                crawler, target, plan, ctx, check_robots=check_robots,
                screenshot=screenshot, settle=settle, o=o)
            out.update(core)
            if aborted:
                return _clip_json(out)
    except Exception as e:
        return err(f"浏览器交互失败: {type(e).__name__}: {_clip(str(e))}"
                   "（提示：playwright install chromium）")
    if o.get("with_logs", True):
        out.update(rec.result(all_requests))
    return _clip_json(out)
