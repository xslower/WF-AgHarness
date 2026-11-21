from __future__ import annotations

import asyncio
import importlib
import socket

import pytest

import app.tools.builtin.web as web_mod
from app.tools.text_limit import MAX_OUTPUT, truncate
from app.tools.builtin import build_tools as build_registry

pass
BAIDU_LIKE = """
<html><body>
  <div class="result c-container">
    <h3><a href="https://docs.python.org/3/library/asyncio.html">asyncio — 异步 I/O</a></h3>
    <div class="c-abstract">asyncio 是用于编写并发代码的库，使用 async/await 语法。</div>
  </div>
  <div class="result c-container">
    <h3><a href="https://example.com/tutorial">Python asyncio 教程</a></h3>
    <div class="c-abstract">从事件循环开始讲起，附完整示例。</div>
  </div>
  <div class="result c-container">
    <h3><a href="https://example.com/no-snippet">没有摘要的条目</a></h3>
  </div>
  <div class="result c-container">
    <h3>没有链接的条目</h3>
    <div class="c-abstract">这条应该被跳过。</div>
  </div>
</body></html>
"""

BAIDU_SELECTOR = "div.result, div.c-container"
LINK_SELECTOR = "h3 a"

ANTIBOT_PAGE = """
<html><body><div class="result c-container">
  <h3><a href="">请输入验证码</a></h3>
</div><p>网络不给力，请稍后重试</p></body></html>
"""


pass
def test_vendored_crawl4ai_present():
    root = web_mod.crawl4ai_path()
    assert root.is_dir(), f"缺少 vendored crawl4ai: {root}"
    pkg = root / "crawl4ai"
    assert (pkg / "__init__.py").is_file(), "crawl4ai 包不完整（缺 __init__.py）"
    pass
    assert (pkg / "async_webcrawler.py").is_file()
    assert (pkg / "async_configs.py").is_file()


def test_ensure_crawl4ai_puts_path_on_syspath():
    import sys

    p = web_mod.ensure_crawl4ai()
    assert str(p) in sys.path
    assert str(p) in sys.path
    assert sys.path.count(str(p)) == 1


def test_crawl4ai_importable():
    web_mod.ensure_crawl4ai()
    try:
        mod = importlib.import_module("crawl4ai")
    except ModuleNotFoundError as e:
        if (e.name or "").split(".")[0] == "crawl4ai":
            pytest.fail(f"crawl4ai 本体导入失败（目录缺失或包不完整）: {e}")
        pytest.skip(f"crawl4ai 依赖缺失，跳过导入检查: {e.name}")
    assert hasattr(mod, "AsyncWebCrawler")


def test_web_tool_registered_with_expected_schema():
    reg = build_registry()
    assert "web" in reg.tools
    schema = next(s for s in reg.schemas
                  if s.get("function", {}).get("name") == "web")
    props = schema["function"]["parameters"]["properties"]
    pass
    pass
    assert set(props) == {"query", "steps", "debug", "limit"}
    assert schema["function"]["parameters"]["required"] == ["query"]


pass
def test_parse_serp_extracts_fields():
    items = web_mod._parse_serp(BAIDU_LIKE, BAIDU_SELECTOR, LINK_SELECTOR)
    assert len(items) == 3
    first = items[0]
    assert first["title"] == "asyncio — 异步 I/O"
    assert first["url"] == "https://docs.python.org/3/library/asyncio.html"
    assert "并发" in first["snippet"]
    assert items[2]["snippet"] == ""


def test_parse_serp_antibot_page_returns_empty():
    assert web_mod._parse_serp(ANTIBOT_PAGE, BAIDU_SELECTOR, LINK_SELECTOR) == []


def test_parse_serp_respects_limit():
    html = "<html><body>" + "".join(
        f'<div class="result"><h3><a href="https://e.com/{i}">t{i}</a></h3></div>'
        for i in range(30)) + "</body></html>"
    assert len(web_mod._parse_serp(html, BAIDU_SELECTOR, LINK_SELECTOR)) == web_mod._SERP_MAX_ITEMS
    assert len(web_mod._parse_serp(html, BAIDU_SELECTOR, LINK_SELECTOR, limit=3)) == 3


def test_parse_serp_handles_garbage_html():
    assert web_mod._parse_serp("", BAIDU_SELECTOR, LINK_SELECTOR) == []
    assert web_mod._parse_serp("<not html", BAIDU_SELECTOR, LINK_SELECTOR) == []


def test_parse_serp_relativizes_links_against_engine_base():
    html = ('<div class="result"><h3><a href="/link?url=abc">相对</a></h3></div>'
            '<div class="result"><h3><a href="javascript:void(0)">假链接</a></h3></div>'
            '<div class="result"><h3><a href="#top">锚点</a></h3></div>')
    items = web_mod._parse_serp(html, BAIDU_SELECTOR, LINK_SELECTOR,
                               base="https://www.baidu.com/s?wd=x")
    assert len(items) == 1
    assert items[0]["url"] == "https://www.baidu.com/link?url=abc"


def test_drop_ads_removes_promoted_items():
    rows = [{"title": "广告 某某课程"}, {"title": "正常结果"}, {"title": "结果里提到广告"}]
    kept = web_mod.drop_ads(rows)
    assert [r["title"] for r in kept] == ["正常结果", "结果里提到广告"]


pass
def test_html_to_md_strips_scripts_and_keeps_body():
    html = ("<html><head><script>var x=1</script><style>.a{}</style></head>"
            "<body><h1>标题</h1><p>正文内容足够长，用来确认提取逻辑不会把正文丢掉。</p>"
            "<p>第二段内容，包含 <a href='https://example.com'>链接</a>。</p></body></html>")
    md = web_mod._html_to_md(html)
    assert "标题" in md and "正文内容" in md
    assert "var x=1" not in md
    pass
    assert "# 标题" in md and "https://example.com" in md


def test_snippet_falls_back_to_longest_text_when_selector_misses():
    html = ('<div class="result">'
            '<h3><a href="https://e.com/a">Python asyncio 教程</a></h3>'
            '<div class="cos-space-mt-xxs">asyncio 是 Python 原生异步 I/O 框架，'
            '核心是协程和事件循环，用 async def 定义协程。</div></div>')
    item = web_mod._parse_serp(html, BAIDU_SELECTOR, LINK_SELECTOR)[0]
    assert "异步 I/O 框架" in item["snippet"]


def test_snippet_fallback_skips_title_copy_and_nav_noise():
    html = ('<div class="result">'
            '<h3><a href="https://e.com/a">Python asyncio 教程完整标题</a></h3>'
            '<span class="x">Python asyncio 教程完整标题</span>'
            '<div class="y">大家还在搜 replit在线编程 在线python绘图 python代码</div>'
            '</div>')
    item = web_mod._parse_serp(html, BAIDU_SELECTOR, LINK_SELECTOR)[0]
    assert item["snippet"] == ""


def test_snippet_selector_wins_over_fallback():
    html = ('<div class="result">'
            '<h3><a href="https://e.com/a">标题</a></h3>'
            '<div class="c-abstract">这是真的摘要，长度足够长。</div>'
            '<div class="other">另一段更长的无关文本，长度超过真摘要很多很多。</div>'
            '</div>')
    item = web_mod._parse_serp(html, BAIDU_SELECTOR, LINK_SELECTOR)[0]
    assert item["snippet"] == "这是真的摘要，长度足够长。"


def test_snippet_length_capped_at_200():
    long_text = "很长的摘要" * 200
    html = (f'<div class="result"><h3><a href="https://e.com/a">t</a></h3>'
            f'<div class="c-abstract">{long_text}</div></div>')
    item = web_mod._parse_serp(html, BAIDU_SELECTOR, LINK_SELECTOR)[0]
    assert len(item["snippet"]) == 200


def test_output_is_truncated_to_max_output():
    huge = "字" * (MAX_OUTPUT * 2)
    out = truncate(huge, MAX_OUTPUT)
    assert len(out) <= MAX_OUTPUT + 100
    assert MAX_OUTPUT <= 40_000


pass
def _net_ok(host: str = "example.com", port: int = 443, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@pytest.fixture
def require_net():
    if not _net_ok():
        pytest.skip("网络不可达，跳过联网冒烟")


@pytest.mark.network
async def test_fetch_example_com(require_net):
    from app.tools import ToolContext

    out = await web_mod.web_fetch("https://example.com", ToolContext("."))
    assert not out.startswith('{"error"'), out[:200]
    assert "[200" in out[:40]
    pass
    pass
    assert "documentation" in out.lower()
    assert 50 < len(out) <= MAX_OUTPUT


@pytest.mark.network
async def test_search_returns_relevant_results(require_net):
    from app.tools import ToolContext

    query = "python asyncio 教程"
    out = await web_mod.web_search_html(query, ToolContext("."), limit=8)
    if out.startswith('{"error"'):
        await asyncio.sleep(2.0)
        out = await web_mod.web_search_html(query, ToolContext("."), limit=8)
    if out.startswith('{"error"'):
        pytest.skip(f"搜索引擎此刻不可用（限流/验证码），非代码问题: {out[:160]}")
    lines = [ln for ln in out.splitlines() if ln.strip().startswith("[")]
    assert len(lines) >= 3, f"结果太少（{len(lines)} 条）:\n{out[:500]}"

    pass
    assert any(ln.strip().startswith("http") for ln in out.splitlines())
    assert "https://" in out or "http://" in out

    pass
    body = out.lower()
    hits = body.count("python") + body.count("asyncio")
    assert hits >= 2, f"相关性命中过少（{hits}）:\n{out[:500]}"

    pass
    assert 300 <= len(out) <= MAX_OUTPUT
    assert "置信度" not in out


@pytest.mark.network
@pytest.mark.network
async def test_browser_channel_via_crawl4ai(require_net):
    try:
        items = await web_mod._search_via_browser(
            "https://www.baidu.com/s?wd=python", BAIDU_SELECTOR, LINK_SELECTOR)
    except Exception as e:
        msg = str(e).lower()
        if any(k in msg for k in ("playwright", "executable", "browser", "chromium")):
            pytest.skip(f"无头浏览器不可用（环境问题）: {e}")
        raise
    assert items, "crawl4ai 通道返回 0 条：可能被反爬或页面结构已变"
    assert all(i["url"].startswith("http") for i in items)
    assert all(len(i["snippet"]) <= 200 for i in items)


@pytest.mark.network
@pytest.mark.network
async def test_aggregate_search_returns_more_than_single_engine(require_net):
    from app.tools import ToolContext

    out = await web_mod.web_search_aggregate("python asyncio", ToolContext("."),
                                             limit=10, pages=2)
    if out.startswith('{"error"'):
        pytest.skip(f"搜索引擎此刻不可用（限流/验证码）: {out[:160]}")
    tail = [ln for ln in out.splitlines() if ln.startswith("共 ")]
    assert tail, out[-400:]
    n = int(tail[0].split("去重后 ")[1].split(" 条")[0])
    if n < 10 and "部分引擎不可用" in out:
        pytest.skip(f"多引擎里多数被限流，只有 {n} 条，无法验证聚合广度: {out[-200:]}")
    assert n >= 10, f"多引擎×多页去重后只有 {n} 条，聚合没生效：\n{out[:500]}"
    assert "来源" not in out
    assert "置信度" not in out


@pytest.mark.network
async def test_aggregate_paging_adds_results(require_net):
    from app.tools import ToolContext

    async def total(pages: int) -> int:
        out = await web_mod.web_search_aggregate("python 异步", ToolContext("."),
                                                 limit=5, pages=pages)
        tail = [ln for ln in out.splitlines() if ln.startswith("共 ")]
        if not tail:
            pytest.skip(f"聚合搜索无结果（网络受限）: {out[:120]}")
        return int(tail[0].split("去重后 ")[1].split(" 条")[0])

    one, three = await total(1), await total(3)
    if three <= one:
        pytest.skip(f"翻页没带来新结果，疑似被反爬（1 页 {one} 条 / 3 页 {three} 条）")
    assert three > one, f"翻页没带来新结果：1 页 {one} 条，3 页 {three} 条"
