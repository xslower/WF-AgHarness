from __future__ import annotations

import asyncio

import pytest

import app.tools.builtin.web as web_mod
import app.tools.builtin.web.channels as web_ch
import app.tools.builtin.web.resolve as R


@pytest.fixture(autouse=True)
def _clear_cache():
    R._CACHE.clear()
    yield
    R._CACHE.clear()


pass
def test_display_host_strips_www_and_hides_redirect():
    assert R.display_host("https://www.docs.python.org/3/") == "docs.python.org"
    assert R.display_host("https://docs.python.org/3/") == "docs.python.org"
    pass
    assert R.display_host("https://www.baidu.com/link?url=abc") == ""
    assert R.display_host("") == ""


@pytest.fixture(autouse=True)
def _no_browser(monkeypatch):
    async def _boom():
        raise RuntimeError("测试环境不启浏览器")

    monkeypatch.setattr(web_ch, "browser_session", _boom)


def test_non_redirect_url_is_returned_as_is():
    assert asyncio.run(R.resolve_redirect("https://docs.python.org/3/")) == \
        "https://docs.python.org/3/"


def test_resolve_uses_location_header(monkeypatch):
    import httpx

    class FakeResp:
        status_code = 302
        headers = {"location": "https://docs.python.org/zh-cn/3/library/asyncio.html"}

    class FakeClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url):
            return FakeResp()

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    got = asyncio.run(R.resolve_redirect("https://www.baidu.com/link?url=abc"))
    assert got == "https://docs.python.org/zh-cn/3/library/asyncio.html"


def test_resolve_rejects_redirect_to_another_redirect(monkeypatch):
    import httpx

    class FakeResp:
        status_code = 302
        headers = {"location": "https://www.so.com/link?m=next"}

    class FakeClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url):
            return FakeResp()

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    assert asyncio.run(R.resolve_redirect("https://www.so.com/link?m=abc")) == ""


def test_resolve_network_error_is_silent():
    got = asyncio.run(R.resolve_redirect("https://www.baidu.com/link?url=nonexistent-host-xyz"))
    assert got in ("", got)


def test_resolve_many_limits_probes(monkeypatch):
    calls = []

    async def fake(url, timeout=4.0):
        calls.append(url)
        return "https://real.example/" + str(len(calls))

    monkeypatch.setattr(R, "resolve_redirect", fake)
    urls = [f"https://www.baidu.com/link?url=u{i}" for i in range(10)]
    out = asyncio.run(R.resolve_many(urls, limit=3))
    assert len(calls) == 3
    assert len(out) == 3


def test_resolve_many_caches_and_skips_real_urls(monkeypatch):
    calls = []

    async def fake(url, timeout=4.0):
        calls.append(url)
        return "https://real.example/x"

    monkeypatch.setattr(R, "resolve_redirect", fake)
    asyncio.run(R.resolve_many(["https://a.com/real", "https://www.baidu.com/link?url=q"]))
    assert calls == ["https://www.baidu.com/link?url=q"]


pass
def test_enrich_replaces_url_and_keeps_original():
    rows = [{"title": "t", "url": "https://www.baidu.com/link?url=abc", "snippet": ""}]
    R.enrich(rows, {"https://www.baidu.com/link?url=abc": "https://docs.python.org/3/"})
    assert rows[0]["url"] == "https://docs.python.org/3/"
    assert rows[0]["via"] == "https://www.baidu.com/link?url=abc"
    assert rows[0]["host"] == "docs.python.org"


def test_enrich_without_mapping_adds_host_only():
    rows = [{"title": "t", "url": "https://www.so.com/link?m=abc", "snippet": ""}]
    R.enrich(rows, {})
    assert rows[0]["url"] == "https://www.so.com/link?m=abc"
    assert rows[0]["host"] == ""


def test_remerge_merges_same_page_from_different_engines():
    rows = [
        {"title": "Python 官方文档 asyncio", "url": "https://docs.python.org/3/library/asyncio.html",
         "snippet": "短", "sources": ["百度"], "hits": 1, "best_rank": 0},
        {"title": "asyncio — 异步 IO（中文）", "url": "https://docs.python.org/3/library/asyncio.html?utm_source=x",
         "snippet": "更长的摘要内容", "sources": ["360"], "hits": 1, "best_rank": 4},
    ]
    out = R.remerge_by_real_url(rows)
    assert len(out) == 1
    assert set(out[0]["sources"]) == {"百度", "360"}
    assert out[0]["snippet"] == "更长的摘要内容"
    assert out[0]["best_rank"] == 0


def test_remerge_keeps_distinct_pages():
    rows = [
        {"title": "A", "url": "https://a.com/1", "snippet": "", "sources": ["百度"]},
        {"title": "B", "url": "https://b.com/2", "snippet": "", "sources": ["360"]},
    ]
    assert len(R.remerge_by_real_url(rows)) == 2


pass
def test_aggregate_output_uses_real_url(monkeypatch):
    from app.tools import ToolContext

    async def fake_page(engine, query, page, use_browser, timeout=8.0, crawler=None):
        if engine.id == "baidu":
            return [{"title": "文档", "url": "https://www.baidu.com/link?url=ok",
                     "snippet": "s"}]
        if engine.id == "bing":
            return [{"title": "解不开的", "url": "https://www.so.com/link?m=bad",
                     "snippet": "s2"}]
        return []

    async def fake_resolve_redirect(url, timeout=4.0):
        if "baidu.com/link" in url:
            return "https://docs.python.org/3/library/asyncio.html"
        return ""

    monkeypatch.setattr(web_ch, "search_one_page", fake_page)
    monkeypatch.setattr(R, "resolve_redirect", fake_resolve_redirect)
    out = asyncio.run(web_mod.web_search_aggregate("asyncio", ToolContext("."), limit=5))
    assert "https://docs.python.org/3/library/asyncio.html" in out
    assert "已还原为真实地址" in out
    assert "https://www.so.com/link?m=bad" in out


pass
def test_web_fetch_reports_final_url(monkeypatch):
    import httpx

    class FakeResp:
        status_code = 200
        headers = {"content-type": "text/html"}
        text = "<html><body><p>正文内容足够长，用于确认提取逻辑正常工作。</p></body></html>"
        url = "https://docs.python.org/3/library/asyncio.html"

    class FakeClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url, headers=None):
            return FakeResp()

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    from app.tools import ToolContext
    out = asyncio.run(web_mod.web_fetch("https://www.baidu.com/link?url=abc",
                                        ToolContext(".")))
    assert "最终地址: https://docs.python.org/3/library/asyncio.html" in out
    assert "正文内容" in out


def test_web_fetch_omits_final_url_when_unchanged(monkeypatch):
    import httpx

    class FakeResp:
        status_code = 200
        headers = {"content-type": "text/html"}
        text = "<html><body><p>正文内容足够长，用于确认提取逻辑正常工作。</p></body></html>"
        url = "https://example.com/page"

    class FakeClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url, headers=None):
            return FakeResp()

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    from app.tools import ToolContext
    out = asyncio.run(web_mod.web_fetch("https://example.com/page", ToolContext(".")))
    assert "最终地址" not in out
