from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from urllib.parse import quote_plus
from typing import TYPE_CHECKING

from ....store import layout
from ....util.jsonx import err
from ...text_limit import MAX_OUTPUT, truncate as _truncate
from ... import cascade
from .extract import _html_to_md

logger = logging.getLogger("harness.tools.web")
from .engines import BAIDU, SOGOU, SO360, parse_wiki_json, select_engines
from .pagekind import is_blocked
from .merge import merge_results, rank_results, select_top
from .resolve import enrich, remerge_by_real_url, resolve_many
from .trust import annotate as _annotate

if TYPE_CHECKING:
    from ... import ToolContext, ToolRegistry

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

pass
pass
_SERP_SNIPPET_SEL = (".c-abstract, [class*=abstract], [class*=str_info], "
                     "[class*=content-right], p")
_SERP_MAX_ITEMS = 15

pass
pass
_DEFAULT_PAGES = 2
pass
_MAX_PAGES = 5


def crawl4ai_path() -> Path:
    return layout.BACKEND_ROOT / "vendor" / "crawl4ai-src"


def ensure_crawl4ai() -> Path:
    p = crawl4ai_path()
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
    return p


pass
_SNIPPET_NAV = ("大家还在搜", "相关搜索", "查看更多", "展开", "广告")


def _fallback_snippet(li, title: str) -> str:
    best = ""
    for d in li.find_all(["div", "span", "p", "em"]):
        t = d.get_text(" ", strip=True)
        if not (30 <= len(t) <= 300):
            continue
        pass
        if title and (title in t or t in title):
            continue
        if any(k in t for k in _SNIPPET_NAV) or t.startswith(("http", "www")):
            continue
        if len(t) > len(best):
            best = t
    return best[:200]


def _parse_serp(html: str, sel: str, link_sel: str,
                limit: int = _SERP_MAX_ITEMS, base: str = "",
                title_sel: str = "") -> list[dict]:
    from urllib.parse import urljoin

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html or "", "lxml")
    out: list[dict] = []
    for li in soup.select(sel)[:limit]:
        a = li.select_one(link_sel)
        href = (a.get("href") if a is not None else None) or ""
        href = href.strip()
        if not href or href.startswith("#") or href.lower().startswith("javascript:"):
            continue
        href = urljoin(base, href) if base else href
        if not href.lower().startswith(("http://", "https://")):
            continue
        sn = li.select_one(_SERP_SNIPPET_SEL)
        if title_sel:
            tnode = li.select_one(title_sel)
            title = tnode.get_text(" ", strip=True) if tnode is not None else ""
        else:
            title = a.get_text(strip=True)
        snippet = sn.get_text(" ", strip=True) if sn is not None else ""
        if len(snippet) < 10:
            pass
            pass
            snippet = _fallback_snippet(li, title)
        item = {
            "title": title,
            "url": href,
            "snippet": snippet[:200],
        }
        pass
        pass
        real = (li.get("data-pcurl") or "").strip() if hasattr(li, "get") else ""
        if real.startswith(("http://", "https://")):
            item["via"] = href
            item["url"] = real
        out.append(item)
    return out



pass
pass
from .channels import (LazyBrowser, _fetch_html, browser_session, detect_antibot,
                       search_one_engine, search_one_page)



def drop_ads(results: list[dict]) -> list[dict]:
    return [x for x in results if "广告" not in (x.get("title") or "")[:4]]


def _is_tool_error(result: str) -> bool:
    s = (result or "").lstrip()
    if not s.startswith("{"):
        return False
    try:
        obj = json.loads(s)
    except ValueError:
        return False
    return isinstance(obj, dict) and "error" in obj


async def _fetch_all(picked: list, query: str, pages: int, use_browser: bool,
                     timeout: float, crawler,
                     first_page: int = 1) -> tuple[list[list[dict]], dict[str, str]]:
    groups: list[list[dict]] = []
    errors: dict[str, str] = {}
    for e in picked:
        pass
        items, one_err = await search_one_engine(
            e, query, pages, use_browser,
            3.0 if e.kind == "wiki" else timeout, crawler=crawler,
            first_page=first_page)
        groups.append(items)
        if one_err:
            errors[e.id] = one_err
    return groups, errors


def _label_sources(merged: list[dict], picked: list) -> None:
    for r in merged:
        r["sources"] = [picked[i].label for i in r["sources"] if i < len(picked)]


def _empty_result(errors: dict[str, str], note: str = "") -> str:
    detail = ("；".join(f"{k}: {v}" for k, v in errors.items())
              or "页面结构可能已变")
    pass
    pass
    blocked = any(k in detail for k in ("反爬", "验证", "限流", "拦截页"))
    hint = ("\n几个引擎都被拦了：**过几分钟再搜**（短时间内重复搜索会触发反爬，"
            "等一两分钟通常就恢复）。这不是页面结构问题，不用改选择器。"
            if blocked else "")
    msg = note or f"未解析到搜索结果（{detail}）{hint}"
    return json.dumps({"error": msg}, ensure_ascii=False)


pass
_SPARSE_RESULTS = 3


def _trust_note(top: list[dict], merged_len: int) -> str:
    if not top or len(top) > _SPARSE_RESULTS or merged_len > _SPARSE_RESULTS:
        return ""
    if any(x.get("trust") != "low" for x in top):
        return ""
    return ("\n注意：本次只搜到这几条且置信度都低（疑似水文/软文），"
            "仅作线索，建议换个更具体的搜索词再确认。")


def _row_text(idx: int, x: dict) -> str:
    head = f"[{idx}] {x['title']}\n    {x['url']}"
    sn = (x.get("snippet") or "").strip()
    return f"{head}\n    {sn}" if sn else head


def _format_rows(top: list[dict], merged_len: int, picked: list, pages: int,
                 mapping: dict, errors: dict[str, str], want: int = 0) -> str:
    lines = [_row_text(i + 1, x) for i, x in enumerate(top)]
    got = len(top)
    if want and got > want:
        pass
        note = (f"\n\n共 {len(picked)} 个引擎 × {pages} 页，去重后 {merged_len} 条。"
                f"前 {got} 条都相关度高（你要 {want} 条，多给的是同级高相关结果）。")
    else:
        note = (f"\n\n共 {len(picked)} 个引擎 × {pages} 页，去重后 {merged_len} 条，"
                f"取前 {got} 条。")
    if mapping:
        note += (f"\n其中 {len(mapping)} 条已还原为真实地址"
                 f"（其余是引擎跳转链接，仍可直接 fetch，会自动跟随）。")
    if errors:
        note += "\n部分引擎不可用：" + "；".join(f"{k}({v[:40]})" for k, v in errors.items())
    return _truncate("\n".join(lines) + note + _trust_note(top, merged_len), MAX_OUTPUT)


async def web_search_aggregate(query: str, ctx: "ToolContext", limit: int = 10,
                               pages: int = 1, engines: list[str] | None = None,
                               use_browser: bool = True,
                               timeout: float = 8.0) -> str:
    picked = select_engines(engines)
    pass
    pass
    pages = max(_DEFAULT_PAGES, min(int(pages or 1), _MAX_PAGES))
    limit = max(1, int(limit or 10))
    pass
    pass
    need_browser = use_browser and any(
        getattr(e, "browser_ok", True) for e in picked)
    crawler = LazyBrowser(need_browser)
    try:
        groups, errors = await _fetch_all(picked, query, pages, need_browser,
                                          timeout, crawler)
        merged = merge_results(groups)
        pass
        pass
        pass
        if merged and len(merged) < limit and pages < _MAX_PAGES:
            more, more_err = await _fetch_all(
                picked, query, 1, need_browser, timeout, crawler,
                first_page=pages + 1)
            groups = [a + b for a, b in zip(groups, more)]
            for k, v in more_err.items():
                errors.setdefault(k, v)
            merged = merge_results(groups)
    finally:
        await crawler.close()

    pass
    pass
    from .health import log_sources, observe
    observe(groups, picked, query, errors)
    _label_sources(merged, picked)
    merged = drop_ads(_annotate(merged))
    if not merged:
        return _empty_result(errors)
    pass
    pass
    rank_results(merged, query)
    pass
    pass
    top = select_top(merged, limit)
    pass
    pass
    mapping = await resolve_many([x.get("url") or "" for x in top],
                                 timeout=4.0, limit=len(top))
    if mapping:
        enrich(top, mapping)
        pass
        pass
        pass
        seen = {id(x) for x in top}
        top = remerge_by_real_url(top)
        pass
        pass
        pass
        pass
        top = [x for x in top if not is_blocked(x.get("url") or "")]
        want = len(top)
        for x in merged:
            if len(top) >= want:
                break
            if id(x) not in seen and all(
                    x.get("url") != y.get("url") for y in top):
                top.append(x)
    pass
    log_sources(query, top)
    return _format_rows(top, len(merged), picked, pages, mapping, errors,
                        want=limit)
async def web_search_html(query: str, ctx: "ToolContext", limit: int = 8) -> str:
    for e in (BAIDU, SOGOU, SO360):
        try:
            items = await search_one_page(e, query, 1, use_browser=False)
        except Exception:
            items = []
        items = drop_ads(items)
        if items:
            items = _annotate(items)[:limit]
            lines = [f"[{i+1}] {x['title']}\n"
                     f"    {x['url']}\n    {x['snippet']}"
                     for i, x in enumerate(items)]
            return _truncate("\n".join(lines) + _trust_note(items, len(items)),
                             MAX_OUTPUT)
    return json.dumps({"error": "未解析到搜索结果（可能被反爬或页面结构变化）"},
                      ensure_ascii=False)


pass
pass
pass
pass
WEB_SCHEMA: dict = {
    # 签名每轮都进上下文，压到最短：只写「怎么选路由 + 去哪里看细节」。
    # 14 种 step 动作只在 steps 参数里列一次；debug 的宽松写法交给实现容错，
    # 不在 schema 里教模型写错格式（实测模型会照抄示例，越写越乱）。
    "desc": (
        "联网：query 给搜索词→多引擎聚合搜索（去重、按相关度排序、标来源）；"
        "query 给 http(s):// 或 file:// 网址→打开网页，默认只返正文 Markdown，"
        "抓不到或需要 JS 时自动升级无头浏览器。"
        "网页上的点击/填表/翻页用 steps 一次给完整序列（拆开调用会丢表单状态）。"
        "要给截图/控制台报错/失败请求时才传 debug。limit 是想要的搜索条数（默认 8）。"
        "典型流程：先搜词拿网址，再把网址放进 query 读原文；页面白屏才加 debug。"
    ),
    "params": {
        "query": {"type": "string",
                  "description": "搜索词，或要打开的网页地址（http(s):// 或 file://）。两者都放这一个参数"},
        "steps": {"type": "array", "items": {"type": "object"},
                  "description": "网址模式：按序执行的交互步骤，一步失败即停（可加 optional:true 跳过）。"
                                 "每项含 act + 参数，act 可取："
                                 "goto(url)/click(sel)/fill(sel,value)/type(sel,value)/press(key)/"
                                 "select(sel,value)/check(sel)/uncheck(sel)/scroll(value)/"
                                 "wait(sel 或 ms)/text(sel)/value(sel)/attr(sel,name)/screenshot(sel)。"
                                 "另可给 timeout_ms。sel=CSS 选择器"},
        "debug": {"type": "object",
                  "description": "网址模式：传了才追加截图+控制台报错+失败请求（默认不采，只返正文）。"
                                 "{} 用默认档；可选 screen:'page'|'viewport'、shots:[{at}|{selector}]、"
                                 "wait_ms、all_requests、viewport"},
        "limit": {"type": "integer",
                  "description": "搜索模式：想要的结果条数（默认 8）。每个引擎默认翻 2 页，不够会再补 1 页"},
    },
    "required": ["query"],
}


def register(reg: "ToolRegistry") -> None:
    from .open import is_url, open_page

    async def web(ctx: "ToolContext", query: str = "", steps: list | None = None,
                  debug: dict | None = None, limit: int = 8) -> str:
        q = (query or "").strip()
        if not q:
            return err("query 必填：给搜索词或网页地址")
        from .health import log_usage
        log_usage(q, is_url(q), steps, debug, limit)
        if is_url(q):
            return await open_page(q, ctx, steps=steps, debug=debug)
        n = max(1, int(limit or 8))
        pass
        pass
        pages = _DEFAULT_PAGES

        async def system() -> str:
            return await web_search_aggregate(q, ctx, limit=n, pages=pages)
        pass
        return await cascade.run("web", {"query": q, "limit": n}, ctx, system)

    reg.register("web", WEB_SCHEMA["desc"], WEB_SCHEMA["params"], web,
                 WEB_SCHEMA["required"])
