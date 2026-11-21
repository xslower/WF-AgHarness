from __future__ import annotations

import asyncio
import json

import pytest

import app.tools.builtin.web as web_mod
import app.tools.builtin.web.engines as E
import app.tools.builtin.web.merge as M
import app.tools.builtin.web.trust as T


class _Ctx:
    pass


pass
@pytest.mark.parametrize("text,is_err", [
    ('{"error": "未解析到搜索结果"}', True),
    ('{"ok": 1, "error": "x"}', True),
    # 成功结果，摘要里恰好提到错误对象 —— 老实现会误判
    ('[1] 某教程\n    https://x.com\n    代码里写 {"error": "bad"} 这样', False),
    ('[1] 某教程\n    https://x.com\n    正常摘要', False),
    # 不是 JSON 对象（列表/纯文本）一律不算错误对象
    ('[{"error": "x"}]', False),
    ('error: something', False),
])
def test_is_tool_error_only_for_error_objects(text, is_err):
    assert web_mod._is_tool_error(text) is is_err


def test_success_result_does_not_fall_back_to_api_client():
    calls: list[str] = []

    class _Client:
        async def search(self, q, limit):
            calls.append(q)
            return "API_FALLBACK_CALLED"

    class _Reg:
        def register(self, name, desc, schema, fn, required=None):
            self.fn = fn

    async def fake_aggregate(q, ctx, **kw):
        return '[1] 标题\n    https://x.com\n    示例代码 {"error": "bad"}'

    reg = _Reg()
    web_mod.register(reg)
    pass
    import app.tools.builtin.web.tool as web_tool
    orig = web_tool.web_search_aggregate
    web_tool.web_search_aggregate = fake_aggregate
    try:
        out = asyncio.run(reg.fn(_Ctx(), query="x"))
    finally:
        web_tool.web_search_aggregate = orig

    assert calls == [], "成功结果不该走 API 兜底"
    assert out.startswith("[1]")


def test_aggregate_failure_is_returned_not_swallowed(monkeypatch):
    class _Reg:
        def register(self, name, desc, schema, fn, required=None):
            self.fn = fn

    err = json.dumps({"error": "全挂了"}, ensure_ascii=False)

    async def fake_aggregate(q, ctx, **kw):
        return err

    reg = _Reg()
    web_mod.register(reg)
    import app.tools.builtin.web.tool as web_tool
    monkeypatch.setattr(web_tool, "web_search_aggregate", fake_aggregate)
    out = asyncio.run(reg.fn(_Ctx(), query="x"))
    assert out == err


pass
def test_wiki_page_url_advances_offset():
    e = E.select_engines(["wiki"])[0]
    urls = [e.page_url("测试", p) for p in (1, 2, 3)]
    assert len(set(urls)) == 3, "wiki 每一页都必须是不同 URL"
    offsets = [int(u.split("gsroffset=")[1].split("&")[0]) for u in urls]
    assert offsets == [0, E.WIKI_PAGE_SIZE, E.WIKI_PAGE_SIZE * 2]


def test_wiki_pages_do_not_refetch_same_url():
    import app.tools.builtin.web.channels as web_ch

    seen: list[str] = []

    async def fake_fetch(url, timeout=8.0):
        seen.append(url)
        return 500, ""

    async def _no_browser():
        raise RuntimeError("测试环境不启浏览器")

    orig_fetch = web_ch._fetch_html
    orig_browser = web_ch.browser_session
    web_ch._fetch_html = fake_fetch
    web_ch.browser_session = _no_browser
    try:
        import app.tools.builtin.web.tool as web_tool
        asyncio.run(web_tool.web_search_aggregate(
            "x", _Ctx(), pages=3, engines=["wiki"], timeout=0.1))
    finally:
        web_ch._fetch_html = orig_fetch
        web_ch.browser_session = orig_browser

    assert len(seen) == 3
    assert len(set(seen)) == 3, f"同一 URL 被重复请求：{seen}"


pass
def test_trust_overrides_path_is_data_dir(tmp_path, monkeypatch):
    from app import config as config_mod

    monkeypatch.setattr(config_mod, "DATA_DIR", tmp_path)
    assert T._overrides_path() == tmp_path / "web/logs/web_trust.json"


def test_trust_overrides_actually_take_effect(tmp_path, monkeypatch):
    from app import config as config_mod

    monkeypatch.setattr(config_mod, "DATA_DIR", tmp_path)
    p = tmp_path / "web/logs/web_trust.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "blacklist": ["blocked.example.com"],
        "tier1": ["trusted.example.com"],
    }), "utf-8")

    assert T.trust_tier("https://blocked.example.com/a") == -1
    assert T.trust_tier("https://sub.blocked.example.com/a") == -1
    assert T.trust_tier("https://trusted.example.com/a") == 2
    pass
    assert T.trust_tier("https://docs.python.org/x") == 2


pass
def test_merge_fills_missing_title_from_later_item():
    groups = [[
        {"title": "", "url": "https://a.com/x", "snippet": "短"},
        {"title": "真正的标题", "url": "https://a.com/x", "snippet": "更长的摘要内容"},
    ]]
    merged = M.merge_results(groups)
    assert len(merged) == 1
    assert merged[0]["title"] == "真正的标题"
    assert merged[0]["snippet"] == "更长的摘要内容"
    assert merged[0]["hits"] == 2


def test_merge_registers_title_key_even_when_matched_by_url():
    groups = [
        [{"title": "同一条", "url": "https://a.com/x", "snippet": "a"}],
        # 另一引擎没有可用 URL（跳转链接）→ 只能靠标题，须能合并到同一条
        [{"title": "同一条 - CSDN博客", "url": "https://www.baidu.com/link?url=z",
          "snippet": "更长的摘要"}],
    ]
    merged = M.merge_results(groups)
    assert len(merged) == 1
    assert merged[0]["sources"] == [0, 1]
    assert merged[0]["hits"] == 2


pass
def test_limit_is_target_count_and_pages_default_two():
    captured: dict = {}

    class _Reg:
        def register(self, name, desc, schema, fn, required=None):
            self.desc = desc
            self.fn = fn

    async def fake_aggregate(q, ctx, **kw):
        captured.update(kw)
        return "[1] x"

    reg = _Reg()
    web_mod.register(reg)
    import app.tools.builtin.web.tool as web_tool
    orig = web_tool.web_search_aggregate
    web_tool.web_search_aggregate = fake_aggregate
    try:
        asyncio.run(reg.fn(_Ctx(), query="q", limit=20))
        assert captured["limit"] == 20
        assert captured["pages"] == 2
        asyncio.run(reg.fn(_Ctx(), query="q", limit=100))
        assert captured["pages"] == 2
    finally:
        web_tool.web_search_aggregate = orig
    for gone in ("action", "engine", "engines", "pages", "render"):
        assert gone not in reg.desc
    assert "默认集合" not in reg.desc
