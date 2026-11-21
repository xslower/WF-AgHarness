from __future__ import annotations

import pytest

from app.tools.builtin.web.query import has_term, split


class TestShortWordsStayWhole:

    def test_ling_jifen_stays_whole(self):
        ents, topic = split("领积分")
        assert "领积分" in topic or "领积分" in ents
        pass
        assert "领" not in ents + topic
        assert "积分" not in ents or "领积分" in ents

    def test_three_char_word_not_split(self):
        assert split("设备号") == ([], ["设备号"])

    def test_short_query_keeps_original_tokens(self):
        ents, topic = split("trae 签到 积分")
        assert "trae" in ents
        assert "签到" in topic and "积分" in topic


class TestLongChineseIsSplit:

    def test_long_phrase_splits_into_subterms(self):
        _, topic = split("多平台账号同时在线不互踢")
        assert "多平台账号同时在线不互踢" in topic
        assert "账号" in topic or "多平台" in topic

    def test_five_char_threshold(self):
        assert split("登录态核验")[1] == ["登录态核验"] or len(
            split("登录态核验")[1]) >= 1
        long = split("多平台账号同时在线不互踢")[1]
        assert len(long) > 1


class TestEnglishNeverSplit:

    @pytest.mark.parametrize("word", ["asyncio", "playwright", "httpx", "bm25"])
    def test_english_word_is_one_token(self, word):
        ents, topic = split(word)
        assert word in ents + topic
        assert len([t for t in ents + topic if t]) == 1

    def test_mixed_query_keeps_english_whole(self):
        ents, _ = split("python asyncio 教程")
        assert "asyncio" in ents
        assert "python" not in ents


class TestCompoundIdentifiers:

    def test_trae_proxy_splits_into_useful_parts(self):
        ents, topic = split("trae-proxy")
        assert "trae-proxy" in ents
        assert "trae" in ents
        assert "proxy" in topic

    def test_short_fragments_not_extracted(self):
        ents, topic = split("req_source")
        assert "req" not in ents + topic
        assert "req_source" in ents + topic

    def test_underscore_identifier_kept_whole(self):
        ents, _ = split("checkin_credits")
        assert "checkin_credits" in ents

    def test_user_data_dir(self):
        ents, topic = split("user-data-dir")
        assert "user-data-dir" in ents
        assert "user" in topic or "data" in topic


class TestGenericWordsAreTopic:

    @pytest.mark.parametrize("word", ["token", "api", "cookie", "python"])
    def test_generic_is_topic_not_entity(self, word):
        ents, topic = split(word)
        assert word not in ents, f"{word} 不该当实体词"
        assert word in topic

    def test_platform_name_dropped_entirely(self):
        ents, topic = split("github")
        assert "github" not in ents
        assert "github" not in topic

    def test_brand_name_is_entity(self):
        ents, _ = split("trae cockpit-tools 多账号")
        assert "trae" in ents
        assert "cockpit-tools" in ents


class TestStopWords:
    def test_single_char_dropped(self):
        ents, topic = split("的 了 和 与")
        assert ents == [] and topic == []

    def test_site_directive_residue_dropped(self):
        ents, topic = split("site:github.com trae checkin")
        assert "site" not in ents + topic
        assert "com" not in ents + topic
        assert "trae" in ents

    def test_empty_query_safe(self):
        assert split("") == ([], [])
        assert split(None) == ([], [])


class TestHasTerm:

    def test_english_word_boundary(self):
        assert has_term("trae is great", "trae")
        assert not has_term("contracted", "trae")

    def test_english_allows_right_glue(self):
        assert has_term("traeai editor", "trae")

    def test_chinese_substring(self):
        assert has_term("腾讯云开发者社区", "腾讯云")
        assert not has_term("阿里云开发者社区", "腾讯云")

    def test_empty_term_safe(self):
        assert not has_term("anything", "")


class TestRealQueries:

    def test_trae_proxy_query(self):
        ents, topic = split("trae-proxy 签到 checkin_credits 领积分 github")
        assert "trae-proxy" in ents and "trae" in ents
        assert "checkin_credits" in ents
        assert "github" not in ents
        assert "签到" in topic

    def test_icube_query(self):
        ents, topic = split("Trae icube-dc 设备号 注册 ExchangeToken DeviceInfo")
        assert "trae" in ents
        assert "icube-dc" in ents
        assert "exchangetoken" in ents
        assert "设备号" in topic and "注册" in topic

    def test_site_query(self):
        ents, _ = split("site:github.com trae checkin points multi account cookie token")
        assert ents == ["trae"] or "trae" in ents
