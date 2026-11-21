from __future__ import annotations

import asyncio
import json

import pytest

import app.tools.builtin.web as web_mod
import app.tools.builtin.web.channels as web_ch
import app.tools.builtin.web.engines as E
import app.tools.builtin.web.merge as M
from app.tools.builtin import build_tools as build_registry


pass
def test_normalize_title_strips_site_suffix():
    assert M.normalize_title("Python asyncio 教程 - CSDN博客") == "python asyncio 教程"
    assert M.normalize_title("Python asyncio模块 | 菜鸟教程") == "python asyncio模块"
    assert M.normalize_title("python异步编程库asyncio使用教程_知乎") == "python异步编程库asyncio使用教程"


def test_normalize_title_handles_entities_width_and_tags():
    got = M.normalize_title("Python\u200b  asyncio\u3000教程 &amp; <em>示例</em>")
    assert "\u200b" not in got and "\u3000" not in got and "<em>" not in got
    assert "&" in got and "  " not in got


def test_normalize_title_keeps_short_titles_intact():
    assert M.normalize_title("C++ - 维基百科") != ""
    assert M.normalize_title("Rust") == "rust"


def test_redirect_urls_are_detected():
    assert M.is_redirect_url("https://www.baidu.com/link?url=abc")
    assert M.is_redirect_url("https://www.sogou.com/link?url=abc")
    assert M.is_redirect_url("https://www.so.com/link?m=abc")
    assert M.is_redirect_url("https://www.bing.com/ck/a?u=abc")
    assert not M.is_redirect_url("https://docs.python.org/3/library/asyncio.html")


def test_canonical_url_drops_tracking_and_fragment():
    a = M.canonical_url("https://Docs.Python.org/3/library/asyncio.html?utm_source=x#top")
    b = M.canonical_url("https://docs.python.org/3/library/asyncio.html")
    assert a == b


def test_canonical_url_keeps_meaningful_query():
    assert "v=abc" in M.canonical_url("https://y.com/watch?v=abc")
    assert "page=2" in M.canonical_url("https://x.com/list?page=2")


pass
def test_merge_dedupes_same_title_across_engines():
    groups = [
        [{"title": "Python asyncio 教程 - CSDN博客", "url": "https://www.baidu.com/link?url=a",
          "snippet": "短"}],
        [{"title": "Python asyncio 教程 | 菜鸟教程", "url": "https://www.sogou.com/link?url=b",
          "snippet": "更长的摘要更长的摘要"}],
        [{"title": "Python asyncio 教程_知乎", "url": "https://x.com/real",
          "snippet": ""}],
    ]
    merged = M.merge_results(groups)
    assert len(merged) == 1
    assert merged[0]["sources"] == [0, 1, 2]
    assert merged[0]["hits"] == 3
    assert merged[0]["snippet"] == "更长的摘要更长的摘要"


def test_merge_dedupes_by_real_url_when_available():
    groups = [
        [{"title": "标题甲", "url": "https://x.com/a?utm_source=1", "snippet": ""}],
        [{"title": "完全不同的标题乙", "url": "https://x.com/a", "snippet": ""}],
    ]
    assert len(M.merge_results(groups)) == 1


def test_merge_keeps_distinct_results():
    groups = [
        [{"title": "结果一", "url": "https://a.com/1", "snippet": ""}],
        [{"title": "结果二", "url": "https://b.com/2", "snippet": ""}],
    ]
    assert len(M.merge_results(groups)) == 2


def test_merge_records_best_rank():
    groups = [
        [{"title": "x", "url": "https://a.com/1", "snippet": ""}],
        [{"title": "无关", "url": "https://b.com/2", "snippet": ""},
         {"title": "x", "url": "https://a.com/1", "snippet": ""}],
    ]
    merged = M.merge_results(groups)
    row = next(r for r in merged if r["url"].endswith("/1"))
    assert row["best_rank"] == 0


pass
def test_rank_prefers_multi_engine_hits():
    rows = [
        {"title": "只在一个引擎出现", "url": "https://a.com", "snippet": "",
         "sources": ["百度"], "best_rank": 0},
        {"title": "两个引擎都命中", "url": "https://b.com", "snippet": "",
         "sources": ["百度", "搜狗"], "best_rank": 5},
    ]
    M.rank_results(rows, "查询")
    assert rows[0]["title"] == "两个引擎都命中"


def test_rank_then_prefers_query_overlap():
    pass
    pass
    rows = [
        {"title": "完全无关的内容", "url": "https://a.com", "snippet": "",
         "sources": ["百度"], "best_rank": 0},
        {"title": "python asyncio 教程", "url": "https://b.com", "snippet": "",
         "sources": ["百度"], "best_rank": 3},
    ] + [{"title": f"云计算 容器 部署 实践 {i}", "url": f"https://n.com/{i}",
          "snippet": "运维 监控 日志", "sources": ["百度"], "best_rank": i}
         for i in range(8)]
    M.rank_results(rows, "python asyncio 教程")
    assert rows[0]["title"] == "python asyncio 教程"


def test_rank_uses_bm25_not_raw_substring_count():
    rows = [
        {"title": "Python事件循环教程:如何使用asyncio事件循环",
         "url": "https://a.com", "snippet": "asyncio 并发编程指南 事件循环",
         "sources": ["百度"], "best_rank": 0},
        {"title": "python asyncio 教程", "url": "https://b.com",
         "snippet": "从事件循环开始讲起", "sources": ["百度"], "best_rank": 3},
    ] + [{"title": f"云计算 容器 部署 实践 {i}", "url": f"https://n.com/{i}",
          "snippet": "运维 监控 日志", "sources": ["百度"], "best_rank": i}
         for i in range(8)]
    M.rank_results(rows, "python asyncio 教程")
    assert rows[0]["title"] == "python asyncio 教程"


def test_relevance_scores_title_higher_than_snippet():
    from app.tools.builtin.web.relevance import score_items
    rows = [
        {"title": "python asyncio 教程", "snippet": ""},
        {"title": "随笔", "snippet": "偶尔提到 python asyncio 教程 这几个字"},
    ] + [{"title": f"云计算 容器 部署 实践 {i}", "snippet": "运维 监控 日志"}
         for i in range(18)]
    s = score_items("python asyncio 教程", rows)
    assert s[0] > s[1]


def test_is_blocked_catches_antispider_pages():
    from app.tools.builtin.web.pagekind import is_blocked, is_noise
    assert is_blocked("https://weixin.sogou.com/antispider/?from=%2Flink%3Furl%3Dx")
    assert is_blocked("https://x.com/captcha?y=1")
    assert not is_blocked("https://docs.python.org/3/library/asyncio.html")
    assert is_noise("https://weixin.sogou.com/antispider/", "Python异步教程:Asyncio")


def test_is_noise_still_allows_real_content_pages():
    from app.tools.builtin.web.pagekind import is_noise
    assert not is_noise("https://blog.csdn.net/x/article/details/123",
                        "Python异步编程教程:asyncio协程基础实践")
    assert not is_noise("https://zhuanlan.zhihu.com/p/673630796",
                        "python异步编程库asyncio使用教程")


def test_pagekind_verification_url_is_noise():
    from app.tools.builtin.web.pagekind import is_blocked
    assert is_blocked("https://www.so.com/s?q=x&verify=1")
    assert is_blocked("https://example.com/unusual_traffic")


pass
def test_content_key_ignores_punctuation_and_space():
    a = {"snippet": "Python 的 asyncio 模块提供事件循环，用于编写并发代码。"}
    b = {"snippet": "Python的asyncio模块提供事件循环,用于编写并发代码!"}
    assert M.content_key(a) == M.content_key(b)


def test_content_key_skips_short_snippet():
    assert M.content_key({"snippet": "查看更多"}) == ""
    assert M.content_key({"snippet": ""}) == ""


def test_merge_dedupes_reposted_content_with_different_title_and_url():
    body = """Python 的 asyncio 模块提供了事件循环、协程、任务等基础能力，
用于编写单线程并发代码，是 Python 异步编程的核心基础设施。"""
    groups = [
        [{"title": "asyncio 入门 - 知乎", "url": "https://zhuanlan.zhihu.com/p/1",
          "snippet": body}],
        [{"title": "Python异步编程详解 | CSDN", "url": "https://blog.csdn.net/x/2",
          "snippet": body.replace("，", ",")}],
    ]
    merged = M.merge_results(groups)
    assert len(merged) == 1
    assert merged[0]["sources"] == [0, 1]


def test_merge_keeps_different_content_same_title_prefix():
    groups = [
        [{"title": "asyncio 教程", "url": "https://a.com/1",
          "snippet": "讲事件循环的调度机制、回调队列与协程的挂起恢复原理，配代码示例。"}],
        [{"title": "asyncio 教程（二）", "url": "https://b.com/2",
          "snippet": "讲 Task 与 Future 的关系、取消传播、超时控制与异常聚合处理方式。"}],
    ]
    assert len(M.merge_results(groups)) == 2


pass
def _rows(grades: list[str]) -> list[dict]:
    return [{"title": f"t{i}", "url": f"https://a.com/{i}", "snippet": "",
             "sources": ["百度"], "best_rank": i, "_g": g}
            for i, g in enumerate(grades)]


def test_select_top_gives_more_when_still_highly_relevant():
    rows = _rows(["A"] * 15 + ["B"] * 5)
    assert len(M.select_top(rows, 8)) == 15


def test_select_top_stops_at_first_non_a():
    rows = _rows(["A"] * 3 + ["B"] + ["A"] * 10)
    assert len(M.select_top(rows, 2)) == 3


def test_select_top_respects_hard_cap():
    rows = _rows(["A"] * 40)
    assert len(M.select_top(rows, 8)) == M.MAX_ROWS


def test_select_top_returns_at_least_limit_when_available():
    rows = _rows(["B"] * 10)
    assert len(M.select_top(rows, 5)) == 5


pass
def test_baidu_paging_uses_pn_step_10():
    assert "pn=0" not in E.BAIDU.page_url("q", 1)
    assert "pn=10" in E.BAIDU.page_url("q", 2)
    assert "pn=20" in E.BAIDU.page_url("q", 3)


def test_sogou_paging_uses_page_1based():
    assert "page=1" not in E.SOGOU.page_url("q", 1)
    assert "page=2" in E.SOGOU.page_url("q", 2)


def test_so360_paging_uses_pn_1based():
    assert "pn=2" in E.SO360.page_url("q", 2)
    assert "pn=3" in E.SO360.page_url("q", 3)


def test_page_url_quotes_query():
    url = E.BAIDU.page_url("python asyncio", 1)
    assert "python+asyncio" in url


def test_select_engines_defaults_and_unknown():
    default = ["baidu", "bing", "sogou", "so360"]
    assert [e.id for e in E.select_engines(None)] == default
    assert [e.id for e in E.select_engines(["baidu"])] == ["baidu"]
    assert [e.id for e in E.select_engines(["nope"])] == default
    assert [e.id for e in E.select_engines(["baidu", "baidu"])] == ["baidu"]
    pass
    assert [e.id for e in E.select_engines(["wiki"])] == ["wiki"]


def test_sogou_so360_browser_fallback_disabled():
    assert E.SOGOU.browser_ok is False
    assert E.SO360.browser_ok is False
    assert E.BAIDU.browser_ok is True and E.BING.browser_ok is True


pass
WIKI_JSON = json.dumps({"query": {"pages": {
    "1": {"index": 2, "title": "异步IO", "extract": "第二条\n内容"},
    "2": {"index": 1, "title": "Asyncio", "extract": "第一条内容"},
    "3": {"index": 3, "title": "", "extract": "无标题应丢弃"},
}}}, ensure_ascii=False)


def test_parse_wiki_json_orders_by_index_and_builds_url():
    rows = E.parse_wiki_json(WIKI_JSON)
    assert [r["title"] for r in rows] == ["Asyncio", "异步IO"]
    assert rows[0]["url"].startswith("https://zh.wikipedia.org/wiki/")
    assert "\n" not in rows[0]["snippet"]


def test_parse_wiki_json_bad_input_returns_empty():
    assert E.parse_wiki_json("") == []
    assert E.parse_wiki_json("not json") == []
    assert E.parse_wiki_json("{}") == []


pass
@pytest.fixture(autouse=True)
def _no_browser(monkeypatch):
    async def _boom():
        raise RuntimeError("测试环境不启浏览器")

    import app.tools.builtin.web.channels as web_ch
    monkeypatch.setattr(web_ch, "browser_session", _boom)


def _patch_engines(monkeypatch, mapping: dict[str, list[dict] | Exception]):
    async def fake(engine, query, page, use_browser, timeout=8.0, crawler=None,
                   first_page=1):
        val = mapping.get(engine.id)
        if isinstance(val, Exception):
            raise val
        if isinstance(val, dict):
            val = val.get(page, [])
        return val or []

    monkeypatch.setattr(web_ch, "search_one_page", fake)


@pytest.fixture()
def ctx():
    from app.tools import ToolContext
    return ToolContext(".")


def test_aggregate_dedupes_across_engines(monkeypatch, ctx):
    same = [
        {"title": "Python asyncio 教程 - CSDN博客", "url": "https://www.baidu.com/link?url=a",
         "snippet": "a"},
        {"title": "另一篇", "url": "https://www.baidu.com/link?url=b", "snippet": "b"},
    ]
    other = [
        {"title": "Python asyncio 教程 | 菜鸟教程", "url": "https://www.sogou.com/link?url=a",
         "snippet": "a 更长一点的摘要"},
        {"title": "另一篇_知乎", "url": "https://www.sogou.com/link?url=b", "snippet": "b"},
    ]
    _patch_engines(monkeypatch, {"baidu": same, "bing": other})
    out = asyncio.run(web_mod.web_search_aggregate("python asyncio", ctx, limit=10))
    tail = [l for l in out.splitlines() if l.startswith("共 ")]
    assert tail and "去重后 2 条" in tail[0], out[:400]
    assert "来源" not in out
    assert "去重后 2 条" in out


def test_aggregate_one_engine_failure_does_not_kill_search(monkeypatch, ctx):
    _patch_engines(monkeypatch, {
        "baidu": [{"title": "正常结果", "url": "https://a.com/1", "snippet": "s"}],
        "bing": RuntimeError("Bing 不可达: ConnectError"),
    })
    out = asyncio.run(web_mod.web_search_aggregate("q", ctx, limit=5))
    assert "正常结果" in out
    assert "部分引擎不可用" in out and "bing" in out


def test_aggregate_all_engines_fail_returns_error(monkeypatch, ctx):
    _patch_engines(monkeypatch, {k: RuntimeError("boom") for k in
                                 ("baidu", "bing")})
    out = asyncio.run(web_mod.web_search_aggregate("q", ctx, limit=5))
    assert json.loads(out)["error"].startswith("未解析到搜索结果")


def test_aggregate_pages_multiplies_results(monkeypatch, ctx):
    per_page = {
        1: [{"title": "第一页", "url": "https://a.com/1", "snippet": ""}],
        2: [{"title": "第二页", "url": "https://a.com/2", "snippet": ""}],
        3: [{"title": "第三页", "url": "https://a.com/3", "snippet": ""}],
    }
    _patch_engines(monkeypatch, {"baidu": per_page, "bing": []})
    out = asyncio.run(web_mod.web_search_aggregate("q", ctx, limit=10, pages=3))
    assert "去重后 3 条" in out
    for t in ("第一页", "第二页", "第三页"):
        assert t in out


def test_aggregate_pages_capped(monkeypatch, ctx):
    seen = []

    async def fake(engine, query, page, use_browser, timeout=8.0, crawler=None):
        seen.append(page)
        return []

    monkeypatch.setattr(web_ch, "search_one_page", fake)
    asyncio.run(web_mod.web_search_aggregate("q", ctx, pages=99))
    assert max(seen) <= 5


def test_aggregate_drops_blacklist(monkeypatch, ctx):
    _patch_engines(monkeypatch, {
        "baidu": [{"title": "采集站内容", "url": "https://www.360doc.com/x", "snippet": ""},
                  {"title": "正常", "url": "https://docs.python.org/3/", "snippet": ""}],
        "bing": [],
    })
    out = asyncio.run(web_mod.web_search_aggregate("q", ctx, limit=10))
    assert "采集站内容" not in out
    assert "正常" in out


pass
def test_web_schema_is_single_entry_four_params():
    reg = build_registry()
    params = next(s["function"]["parameters"] for s in reg.schemas
                  if s["function"]["name"] == "web")
    assert set(params["properties"]) == {"query", "steps", "debug", "limit"}
    assert params["required"] == ["query"]
    for gone in ("action", "engine", "engines", "pages", "render", "url"):
        assert gone not in params["properties"]
