from __future__ import annotations

import asyncio
import json

import pytest

import app.tools.builtin.web as web_mod
import app.tools.builtin.web.channels as web_ch
from app.tools import ToolContext


@pytest.fixture(autouse=True)
def _no_browser(monkeypatch):
        async def _boom():
            raise RuntimeError("测试环境不启浏览器")

        monkeypatch.setattr(web_ch, "browser_session", _boom)


@pytest.mark.parametrize("html,status,expect", [
    ("", 403, "限流"),
    ("", 429, "限流"),
    ("<html>请输入验证码</html>", 200, "反爬验证"),
    ("x" * 100, 200, "过短"),
    ("<html>网络不给力，请稍后重试</html>", 200, "反爬"),
])
def test_detect_antibot_recognises_block_pages(html, status, expect):
    assert expect in web_mod.detect_antibot(html, status)


def test_detect_antibot_passes_normal_page():
    normal = "<html><body>" + "".join(
        f'<div class="result"><h3><a href="https://e.com/{i}">t{i}</a></h3>'
        f'<div class="c-abstract">摘要{i}</div></div>' for i in range(20)) + "</body></html>"
    assert web_mod.detect_antibot(normal, 200) == ""


def test_blocked_engine_raises_with_reason(monkeypatch):
    async def fake_fetch(url, timeout=8.0):
        return 200, "<html>请输入验证码</html>"

    monkeypatch.setattr(web_ch, "_fetch_html", fake_fetch)
    with pytest.raises(RuntimeError) as e:
        asyncio.run(web_ch.search_one_page(web_mod.BAIDU, "q", 1, False))
    assert "反爬" in str(e.value)


def test_all_blocked_error_tells_user_to_wait(monkeypatch):
    async def fake_page(engine, query, page, use_browser, timeout=8.0, crawler=None):
        raise RuntimeError("触发了反爬验证（请稍后重试）")

    monkeypatch.setattr(web_ch, "search_one_page", fake_page)
    out = asyncio.run(web_mod.web_search_aggregate("q", ToolContext("."), limit=5))
    payload = json.loads(out)
    assert "反爬" in payload["error"]
    assert "几分钟" in payload["error"]
    assert "deepseek" not in payload["error"], "不该再推荐有账号风险的网页版通道"


def test_structure_error_keeps_original_wording(monkeypatch):
    async def fake_page(engine, query, page, use_browser, timeout=8.0, crawler=None):
        return []

    monkeypatch.setattr(web_ch, "search_one_page", fake_page)
    out = asyncio.run(web_mod.web_search_aggregate("q", ToolContext("."), limit=5))
    payload = json.loads(out)
    assert "页面结构可能已变" in payload["error"]
    assert "deepseek" not in payload["error"]


def test_browser_fallback_skipped_for_sogou_so360(monkeypatch):
    calls = []

    async def fake_fetch(url, timeout=8.0):
        return 200, "<html>请输入验证码</html>"

    async def fake_browser(*a, **kw):
        calls.append(1)
        return []

    monkeypatch.setattr(web_ch, "_fetch_html", fake_fetch)
    monkeypatch.setattr(web_ch, "_search_via_browser", fake_browser)
    for e in (web_mod.SOGOU, web_mod.SO360):
        with pytest.raises(RuntimeError) as ex:
            asyncio.run(web_ch.search_one_page(e, "q", 1, True))
        assert "反爬" in str(ex.value)
    assert calls == []
    with pytest.raises(RuntimeError):
        asyncio.run(web_ch.search_one_page(web_mod.BAIDU, "q", 1, True))
    assert calls == [1], "百度/Bing 的浏览器兜底必须保留"
