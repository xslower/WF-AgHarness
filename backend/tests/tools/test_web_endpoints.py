from __future__ import annotations

import asyncio

import app.tools.builtin.web.channels as ch
from app.tools.builtin.web.engines import SO360, SOGOU


def _html(sel: str, cls: str, title: str) -> str:
    link = (f"<h3><a href='https://x.test/1'>{title}</a></h3>"
            if sel == "h3 a" else
            f"<a class='alink' href='https://x.test/1'><h3>{title}</h3></a>")
    pass
    return f"<li class='{cls}'>{link}<p>摘要</p></li>" + "<!-- padding -->" * 120


def test_sogou_has_weixin_fallback_with_own_selectors():
    assert len(SOGOU.alts) == 1
    alt = SOGOU.alts[0]
    assert alt.id == "sogou"
    assert "weixin.sogou.com" in alt.url
    assert alt.sel == "ul.news-list li" and alt.link_sel == "h3 a"
    assert SOGOU.sel == "div.vrwrap, div.rb"


def test_so360_default_is_desktop_with_mobile_fallback():
    assert SO360.url.startswith("https://www.so.com/s")
    assert SO360.sel == "li.res-list" and SO360.link_sel == "h3 a"
    mobile = SO360.alts[0]
    assert mobile.url.startswith("https://m.so.com/s")
    assert mobile.sel == "div.res-list" and mobile.link_sel == "a.alink"


def test_page_url_paging_still_works_on_desktop():
    assert "pn=2" in SO360.page_url("q", 2)
    assert "pn=3" in SO360.page_url("q", 3)


def test_fallback_uses_primary_result_when_available(monkeypatch):
    html = _html("h3 a", "res-list", "Python asyncio 教程")
    calls = []

    async def fake(url, timeout=8.0):
        calls.append(url)
        return 200, html

    monkeypatch.setattr(ch, "_fetch_html", fake)
    got = asyncio.run(ch.search_one_page(SO360, "python asyncio 教程", 1, False))
    assert len(got) == 1 and got[0]["title"] == "Python asyncio 教程"
    assert len(calls) == 1 and "www.so.com" in calls[0]


def test_fallback_switches_when_primary_is_blocked(monkeypatch):
    calls = []

    async def fake(url, timeout=8.0):
        calls.append(url)
        if "www.so.com" in url:
            return 200, "<html>请输入验证码</html>"
        return 200, ("<div class='res-list'>"
                     "<a class='alink' href='https://x.test/1'>"
                     "<h3>Python asyncio 教程 移动版</h3></a><p>摘要</p></div>"
                     + "<!-- padding -->" * 120)

    monkeypatch.setattr(ch, "_fetch_html", fake)
    got = asyncio.run(ch.search_one_page(SO360, "python asyncio 教程", 1, False))
    assert len(got) == 1 and "移动版" in got[0]["title"]
    assert len(calls) == 2 and "m.so.com" in calls[1]


def test_all_endpoints_blocked_raises_antibot_reason(monkeypatch):
    async def fake(url, timeout=8.0):
        return 200, "<html>请输入验证码</html>"

    monkeypatch.setattr(ch, "_fetch_html", fake)
    try:
        asyncio.run(ch.search_one_page(SOGOU, "python asyncio 教程", 1, False))
        raise AssertionError("应当抛出反爬错误")
    except RuntimeError as e:
        assert "反爬" in str(e) or "验证" in str(e)
