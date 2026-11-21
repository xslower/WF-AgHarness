from __future__ import annotations

import pytest

from app.tools.builtin.web.query import split
from app.tools.builtin.web.relevance import grade, judge, score_items, terms


class TestGrade:

    def test_entity_plus_topic_is_A(self):
        item = {"title": "Trae 自动签到脚本", "url": "https://blog.csdn.net/a/1",
                "snippet": "实现签到功能"}
        assert grade(item, *split("trae 签到")) == "A"

    def test_entity_only_is_B(self):
        item = {"title": "Trae 是什么", "url": "https://blog.csdn.net/a/1",
                "snippet": "一个编辑器"}
        assert grade(item, *split("trae 签到 积分")) == "B"

    def test_topic_only_is_C(self):
        item = {"title": "Python 实现自动签到脚本",
                "url": "https://blog.csdn.net/a/1", "snippet": "签到 积分"}
        assert grade(item, *split("trae 签到 积分")) == "C"

    def test_nothing_hit_is_X(self):
        item = {"title": "今天天气不错", "url": "https://blog.csdn.net/a/1",
                "snippet": "阳光明媚"}
        assert grade(item, *split("trae 签到")) == "X"

    def test_nav_page_is_X_even_if_hit(self):
        item = {"title": "GitHub", "url": "https://github.com/", "snippet": ""}
        assert grade(item, *split("trae 签到")) == "X"

    def test_dict_page_is_X(self):
        item = {"title": "refresh_token - 百度百科",
                "url": "https://baike.baidu.com/item/x", "snippet": ""}
        assert grade(item, *split("trae refresh_token 签到")) == "X"

    def test_real_case_seq64_zhihu_is_A(self):
        item = {"title": "Trae不开机每天自动签到免费领积分- 知乎",
                "url": "https://zhuanlan.zhihu.com/p/2100883405793772030",
                "snippet": "workbuddy 自动 签到 领积分 Trae"}
        assert grade(item, *split("trae-proxy 签到 checkin_credits 领积分 github")) == "A"

    def test_real_case_github_repo_is_not_A(self):
        item = {"title": "GitHub - slinloving/Gladoscheckin: Glados自动签到",
                "url": "https://github.com/slinloving/Gladoscheckin",
                "snippet": "glados 自动签到"}
        assert grade(item, *split("trae-proxy 签到 checkin_credits 领积分 github")) != "A"


class TestScoreItems:

    def test_full_hit_ranks_above_partial(self):
        items = [{"title": "随便写点什么", "snippet": "无关内容"}]
        items += [{"title": f"无关噪声条目 {i}", "snippet": "闲聊内容"}
                  for i in range(20)]
        items.append({"title": "python asyncio 教程 入门", "snippet": "异步 教程"})
        scores = score_items("python asyncio 教程", items)
        assert scores[-1] > scores[0]

    def test_empty_safe(self):
        assert score_items("", [{"title": "a"}]) == [0.0]
        assert score_items("q", []) == []

    def test_returns_same_length(self):
        items = [{"title": f"t{i}", "snippet": "s"} for i in range(5)]
        assert len(score_items("q", items)) == 5


class TestJudgeIsObservationOnly:

    def test_counts_A_grade(self):
        items = [
            {"title": "Trae 自动签到脚本", "url": "https://b.com/1", "snippet": "签到"},
            {"title": "无关内容", "url": "https://b.com/2", "snippet": "闲聊"},
        ]
        r = judge("trae 签到", items)
        assert r["total"] == 2 and r["relevant"] == 1
        assert r["ratio"] == 0.5

    def test_no_kept_field(self):
        r = judge("trae 签到", [])
        assert "kept" not in r

    def test_returns_parsed_terms(self):
        r = judge("trae checkin_credits 签到", [])
        assert "trae" in r["entities"]
        assert "签到" in r["topics"]

    def test_ok_flag_does_not_drive_decisions(self):
        bad = [{"title": "广告", "url": "https://a.com/1", "snippet": "推广"}]
        r = judge("trae 签到", bad)
        assert r["ok"] is False
        pass
        import app.tools.builtin.web.health as H
        assert not hasattr(H, "disabled_engines")


class TestTerms:

    def test_chinese_and_english(self):
        t = terms("python asyncio 教程")
        assert "asyncio" in t and "教程" in t

    def test_empty_safe(self):
        assert terms("") == []

    def test_single_chinese_char_dropped(self):
        assert "的" not in terms("的")
