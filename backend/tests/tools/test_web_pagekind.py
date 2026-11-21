from __future__ import annotations

import pytest

from app.tools.builtin.web.pagekind import is_dict, is_nav, is_noise


class TestNavPages:

    @pytest.mark.parametrize("url", [
        "https://github.com/",
        "https://github.com",
        "https://github.com/login",
        "https://github.com/signup",
        "https://trae.cn/",
        "https://trae.cn/ide/",
        "https://work.trae.cn/",
        "https://desktop.github.com/download/",
        "https://example.com/index.html",
    ])
    def test_nav_detected(self, url):
        assert is_nav(url, "某站点") is True

    @pytest.mark.parametrize("url", [
        "https://github.com/jlcodes99/cockpit-tools",
        "https://blog.csdn.net/qq_123/article/details/456",
        "https://zhuanlan.zhihu.com/p/2100883405793772030",
    ])
    def test_real_content_not_nav(self, url):
        assert is_nav(url, "一个足够长的真实文章标题用来绕过短标题判断") is False

    def test_short_title_at_root_is_nav(self):
        assert is_nav("https://example.com/", "GitHub") is True

    def test_bad_url_safe(self):
        assert is_nav("", "") is False
        assert is_nav("not a url", "") is False


class TestDictPages:

    @pytest.mark.parametrize("url", [
        "https://baike.baidu.com/item/refresh_token/68659790",
        "https://zhidao.baidu.com/question/501321647161147132.html",
        "https://dict.youdao.com/result?word=site",
        "https://www.iciba.com/word?w=site",
        "https://zh.wikipedia.org/wiki/Python",
    ])
    def test_dict_host_detected(self, url):
        assert is_dict(url, "某个词条") is True

    @pytest.mark.parametrize("title", [
        "refresh_token - 百度百科",
        "site是什么意思_site怎么读_site翻译",
        "site的翻译、音标、读音、用法",
        "多账号登录- 百度百科",
        ".CN_百度百科",
    ])
    def test_dict_title_detected(self, title):
        assert is_dict("https://example.com/x", title) is True

    def test_real_article_not_dict(self):
        assert is_dict("https://blog.csdn.net/a/article/details/1",
                       "Trae 自动签到脚本实现 - CSDN博客") is False


class TestIsNoise:

    def test_nav_is_noise(self):
        assert is_noise("https://github.com/", "GitHub") is True

    def test_dict_is_noise(self):
        assert is_noise("https://baike.baidu.com/item/x", "x_百度百科") is True

    def test_real_article_not_noise(self):
        assert is_noise("https://blog.csdn.net/a/article/details/1",
                        "Trae 多账号签到完整实现教程 - CSDN博客") is False
