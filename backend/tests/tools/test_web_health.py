from __future__ import annotations

import json

import app.tools.builtin.web.health as H
from app.tools.builtin.web.engines import BAIDU, BING
from app.tools.builtin.web.paths import logs_dir


def _read():
    from app.util.jsonx import read_jsonl
    return read_jsonl(logs_dir() / "web_engine_health.jsonl")


pass
class TestObserveIsLogOnly:
    def test_observe_returns_rows_not_alerts(self):
        rows = H.observe([[], []], [BAIDU, BING], "q", {})
        assert len(rows) == 2
        assert [r["engine"] for r in rows] == ["baidu", "bing"]
        assert all("ratio" in r for r in rows)

    def test_every_engine_is_logged(self):
        H.observe([[], []], [BAIDU, BING], "q", {})
        assert len(_read()) == 2

    def test_low_ratio_still_logged_without_side_effect(self):
        bad = [{"title": "豆包AI助手", "url": f"https://a.com/{i}",
                "snippet": "广告"} for i in range(10)]
        for _ in range(5):
            H.observe([bad], [BAIDU], "python asyncio 教程", {})
        rows = _read()
        assert len(rows) == 5
        assert all(r["ratio"] == 0.0 for r in rows)
        pass
        assert not hasattr(H, "disabled_engines")
        assert not hasattr(H, "record")

    def test_blocked_flag_recorded(self):
        rows = H.observe([[]], [BAIDU], "q", {"baidu": "触发了反爬验证"})
        assert rows[0]["blocked"] is True
        assert _read()[0]["blocked"] is True

    def test_not_blocked_when_has_items(self):
        items = [{"title": "t", "url": "https://a.com/1", "snippet": "s"}]
        rows = H.observe([items], [BAIDU], "q", {"baidu": "某个错误"})
        assert rows[0]["blocked"] is False

    def test_logs_entities_and_topics(self):
        H.observe([[]], [BAIDU], "trae checkin_credits 签到", {})
        row = _read()[0]
        assert "trae" in row["entities"]
        assert "签到" in row["topics"]

    def test_engine_scored_separately(self):
        good = [{"title": f"trae 自动签到 {i}", "url": f"https://b.com/{i}",
                 "snippet": "签到 脚本"} for i in range(8)]
        bad = [{"title": "豆包AI编程助手", "url": f"https://a.com/{i}",
                "snippet": "广告"} for i in range(8)]
        rows = H.observe([bad, good], [BAIDU, BING], "trae 签到 脚本", {})
        assert rows[0]["ratio"] < rows[1]["ratio"]


pass
class TestNoAlertInOutput:
    def test_no_report_function(self):
        assert not hasattr(H, "report")

    def test_error_json_is_plain(self, monkeypatch):
        import asyncio

        import app.tools.builtin.web as web_mod
        import app.tools.builtin.web.channels as web_ch

        async def boom(engine, query, page, use_browser, timeout=8.0, crawler=None):
            raise RuntimeError("触发了反爬验证（请稍后重试）")

        monkeypatch.setattr(web_ch, "search_one_page", boom)
        out = asyncio.run(web_mod.web_search_aggregate("q", None, limit=5))
        data = json.loads(out)
        assert "error" in data
        assert "health" not in data

    def test_low_ratio_does_not_change_output(self, monkeypatch):
        import asyncio

        import app.tools.builtin.web as web_mod
        import app.tools.builtin.web.channels as web_ch

        async def fake(engine, query, page, use_browser, timeout=8.0, crawler=None):
            return [{"title": f"trae 自动签到 实现 {engine.id}-{i}",
                     "url": f"https://a.com/{engine.id}/{i}",
                     "snippet": "签到 脚本"} for i in range(5)]

        monkeypatch.setattr(web_ch, "search_one_page", fake)
        outs = [asyncio.run(web_mod.web_search_aggregate("trae 签到 脚本", None, limit=5))
                for _ in range(4)]
        pass
        assert all("error" not in o for o in outs)
        assert all("trae" in o for o in outs)


pass
class TestUsageAndSchema:
    def test_web_signature_is_compact(self):
        from app.tools.builtin.web.tool import WEB_SCHEMA
        desc = WEB_SCHEMA["desc"]
        whole = json.dumps(WEB_SCHEMA, ensure_ascii=False)
        assert len(desc) < 260, len(desc)
        assert whole.count("goto(url)") == 1
        assert len(whole) < 1000, len(whole)

    def test_log_usage_records_shape_only(self):
        from app.util.jsonx import read_jsonl
        H.log_usage("python asyncio 教程", False, [{"act": "click", "selector": "#go"}],
                    {"screen": "page"}, 8)
        rows = read_jsonl(logs_dir() / "web_usage.jsonl")
        assert rows[0]["acts"] == ["click"] and rows[0]["debug_type"] == "dict"
        assert rows[0]["q"] == "python asyncio 教程" and rows[0]["limit"] == 8
