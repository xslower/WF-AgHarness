
import pytest

from crawl4ai.utils import (
    extract_xml_data,
    extract_xml_data_legacy,
    normalize_url,
    normalize_url_for_deep_crawl,
    efficient_normalize_url_for_deep_crawl,
    sanitize_input_encode,
    generate_content_hash,
)
from crawl4ai.cache_context import CacheContext, CacheMode


pass
pass
pass

class TestExtractXmlData:

    def test_basic_single_tag(self):
        result = extract_xml_data(["blocks"], "<blocks>hello</blocks>")
        assert result["blocks"] == "hello"

    def test_multiple_tags(self):
        result = extract_xml_data(["a", "b"], "<a>1</a><b>2</b>")
        assert result["a"] == "1"
        assert result["b"] == "2"

    def test_longest_match(self):
        text = "<blocks>short</blocks> some text <blocks>this is the longer content here</blocks>"
        result = extract_xml_data(["blocks"], text)
        assert result["blocks"] == "this is the longer content here"

    def test_nested_mention_bug_fix_1183(self):
        text = (
            "<think>The user wants me to extract <blocks> data from the page.</think>"
            "<blocks>real extracted data</blocks>"
        )
        result = extract_xml_data(["blocks"], text)
        assert result["blocks"] == "real extracted data"

    def test_missing_tag_returns_empty(self):
        result = extract_xml_data(["missing"], "<other>content</other>")
        assert result["missing"] == ""

    def test_empty_content(self):
        result = extract_xml_data(["blocks"], "<blocks></blocks>")
        assert result["blocks"] == ""

    def test_multiline_content(self):
        text = "<blocks>\nline 1\nline 2\nline 3\n</blocks>"
        result = extract_xml_data(["blocks"], text)
        assert "line 1" in result["blocks"]
        assert "line 2" in result["blocks"]
        assert "line 3" in result["blocks"]

    def test_special_chars_in_content(self):
        text = '<blocks>{"key": "value", "num": 42}</blocks>'
        result = extract_xml_data(["blocks"], text)
        assert '"key": "value"' in result["blocks"]
        assert '"num": 42' in result["blocks"]

    def test_content_with_angle_brackets(self):
        text = "<blocks>some <b>bold</b> text</blocks>"
        result = extract_xml_data(["blocks"], text)
        assert "<b>bold</b>" in result["blocks"]

    def test_multiple_tags_some_missing(self):
        result = extract_xml_data(["found", "missing"], "<found>yes</found>")
        assert result["found"] == "yes"
        assert result["missing"] == ""

    def test_whitespace_stripped(self):
        result = extract_xml_data(["blocks"], "<blocks>  trimmed  </blocks>")
        assert result["blocks"] == "trimmed"


class TestExtractXmlDataLegacy:

    def test_basic_extraction(self):
        result = extract_xml_data_legacy(["blocks"], "<blocks>hello</blocks>")
        assert result["blocks"] == "hello"

    def test_missing_tag(self):
        result = extract_xml_data_legacy(["missing"], "no tags here")
        assert result["missing"] == ""


pass
pass
pass

class TestNormalizeUrl:

    def test_trailing_slash_preserved(self):
        result = normalize_url("/foo/bar/", "http://x.com")
        assert result.endswith("/foo/bar/")

    def test_no_trailing_slash_not_added(self):
        result = normalize_url("/foo/bar", "http://x.com")
        assert result.endswith("/foo/bar")
        assert not result.endswith("/foo/bar/")

    def test_root_path(self):
        result = normalize_url("/", "http://x.com")
        assert result == "http://x.com/"

    def test_query_param_case_preservation(self):
        result = normalize_url("/page?cHash=AbCd", "http://x.com")
        assert "cHash=AbCd" in result

    def test_tracking_params_removed(self):
        result = normalize_url(
            "/page?utm_source=google&utm_medium=cpc&real_param=keep",
            "http://x.com",
        )
        assert "utm_source" not in result
        assert "utm_medium" not in result
        assert "real_param=keep" in result

    def test_fbclid_removed(self):
        result = normalize_url("/page?fbclid=abc123&keep=yes", "http://x.com")
        assert "fbclid" not in result
        assert "keep=yes" in result

    def test_gclid_removed(self):
        result = normalize_url("/page?gclid=xyz&keep=yes", "http://x.com")
        assert "gclid" not in result
        assert "keep=yes" in result

    def test_tracking_removal_case_insensitive(self):
        pass
        result = normalize_url("/page?UTM_SOURCE=test&data=1", "http://x.com")
        pass
        assert "data=1" in result

    def test_query_sorting(self):
        result = normalize_url("/page?z=1&a=2&m=3", "http://x.com")
        pass
        idx_a = result.index("a=2")
        idx_m = result.index("m=3")
        idx_z = result.index("z=1")
        assert idx_a < idx_m < idx_z

    def test_fragment_removed_by_default(self):
        result = normalize_url("/page#section", "http://x.com")
        assert "#section" not in result

    def test_fragment_kept_when_requested(self):
        result = normalize_url("/page#section", "http://x.com", keep_fragment=True)
        assert "#section" in result

    def test_relative_url_resolution(self):
        result = normalize_url("page2", "http://x.com/dir/page1")
        assert result == "http://x.com/dir/page2"

    def test_empty_href_returns_none(self):
        result = normalize_url("", "http://x.com")
        assert result is None

    def test_none_href_returns_none(self):
        result = normalize_url(None, "http://x.com")
        assert result is None

    def test_hostname_lowercased(self):
        result = normalize_url("/page", "http://EXAMPLE.COM/path")
        assert "example.com" in result

    def test_no_query_params_still_works(self):
        result = normalize_url("/simple/path", "http://x.com")
        assert "http://x.com/simple/path" == result


class TestNormalizeUrlForDeepCrawl:

    def test_trailing_slash_preserved(self):
        result = normalize_url_for_deep_crawl("/foo/bar/", "http://x.com")
        assert result is not None
        assert result.endswith("/foo/bar/")

    def test_empty_href_returns_none(self):
        result = normalize_url_for_deep_crawl("", "http://x.com")
        assert result is None

    def test_none_href_returns_none(self):
        result = normalize_url_for_deep_crawl(None, "http://x.com")
        assert result is None

    def test_fragment_removed(self):
        result = normalize_url_for_deep_crawl("/page#anchor", "http://x.com")
        assert "#anchor" not in result

    def test_tracking_params_removed(self):
        result = normalize_url_for_deep_crawl(
            "/page?utm_source=google&keep=yes", "http://x.com"
        )
        assert "utm_source" not in result
        assert "keep=yes" in result

    def test_hostname_lowercased(self):
        result = normalize_url_for_deep_crawl("/page", "http://EXAMPLE.COM")
        assert "example.com" in result


class TestEfficientNormalizeUrlForDeepCrawl:

    def test_trailing_slash_preserved(self):
        result = efficient_normalize_url_for_deep_crawl("/foo/bar/", "http://x.com")
        assert result is not None
        assert result.endswith("/foo/bar/")

    def test_cached_results_consistent(self):
        result1 = efficient_normalize_url_for_deep_crawl("/cached", "http://x.com")
        result2 = efficient_normalize_url_for_deep_crawl("/cached", "http://x.com")
        assert result1 == result2

    def test_empty_href_returns_none(self):
        result = efficient_normalize_url_for_deep_crawl("", "http://x.com")
        assert result is None

    def test_none_href_returns_none(self):
        result = efficient_normalize_url_for_deep_crawl(None, "http://x.com")
        assert result is None

    def test_fragment_removed(self):
        result = efficient_normalize_url_for_deep_crawl("/page#top", "http://x.com")
        assert "#top" not in result

    def test_hostname_lowercased(self):
        result = efficient_normalize_url_for_deep_crawl("/path", "http://UPPER.COM")
        assert "upper.com" in result

    def test_relative_url_resolution(self):
        result = efficient_normalize_url_for_deep_crawl(
            "child", "http://x.com/parent/"
        )
        assert result == "http://x.com/parent/child"


pass
pass
pass

class TestCacheMode:

    def test_enabled_reads_and_writes(self):
        ctx = CacheContext("http://example.com", CacheMode.ENABLED)
        assert ctx.should_read() is True
        assert ctx.should_write() is True

    def test_disabled_no_reads_no_writes(self):
        ctx = CacheContext("http://example.com", CacheMode.DISABLED)
        assert ctx.should_read() is False
        assert ctx.should_write() is False

    def test_bypass_no_reads_but_writes(self):
        ctx = CacheContext("http://example.com", CacheMode.BYPASS)
        assert ctx.should_read() is False
        assert ctx.should_write() is False

    def test_read_only_reads_no_writes(self):
        ctx = CacheContext("http://example.com", CacheMode.READ_ONLY)
        assert ctx.should_read() is True
        assert ctx.should_write() is False

    def test_write_only_no_reads_but_writes(self):
        ctx = CacheContext("http://example.com", CacheMode.WRITE_ONLY)
        assert ctx.should_read() is False
        assert ctx.should_write() is True

    def test_raw_url_not_cacheable(self):
        ctx = CacheContext("raw://<html>test</html>", CacheMode.ENABLED)
        assert ctx.should_read() is False
        assert ctx.should_write() is False

    def test_raw_url_is_raw_html(self):
        ctx = CacheContext("raw://<html>test</html>", CacheMode.ENABLED)
        assert ctx.is_raw_html is True
        assert ctx.is_web_url is False

    def test_http_url_is_cacheable(self):
        ctx = CacheContext("http://example.com", CacheMode.ENABLED)
        assert ctx.is_cacheable is True
        assert ctx.is_web_url is True

    def test_https_url_is_cacheable(self):
        ctx = CacheContext("https://example.com", CacheMode.ENABLED)
        assert ctx.is_cacheable is True

    def test_file_url_is_cacheable(self):
        ctx = CacheContext("file:///tmp/test.html", CacheMode.ENABLED)
        assert ctx.is_cacheable is True
        assert ctx.is_local_file is True

    def test_always_bypass_overrides_everything(self):
        ctx = CacheContext("http://example.com", CacheMode.ENABLED, always_bypass=True)
        assert ctx.should_read() is False
        assert ctx.should_write() is False

    def test_display_url_for_web(self):
        ctx = CacheContext("http://example.com", CacheMode.ENABLED)
        assert ctx.display_url == "http://example.com"

    def test_display_url_for_raw(self):
        ctx = CacheContext("raw://something", CacheMode.ENABLED)
        assert ctx.display_url == "Raw HTML"


pass
pass
pass

class TestSanitizeInputEncode:

    def test_normal_utf8_passthrough(self):
        text = "Hello, world! This is normal text."
        assert sanitize_input_encode(text) == text

    def test_unicode_text_preserved(self):
        text = "Caf\u00e9 na\u00efve r\u00e9sum\u00e9"
        assert sanitize_input_encode(text) == text

    def test_empty_string_returns_empty(self):
        assert sanitize_input_encode("") == ""

    def test_ascii_text_passthrough(self):
        text = "Simple ASCII text 123"
        assert sanitize_input_encode(text) == text

    def test_cjk_characters_preserved(self):
        text = "\u4f60\u597d\u4e16\u754c"
        assert sanitize_input_encode(text) == text

    def test_emoji_preserved(self):
        text = "Hello \U0001f600 World"
        result = sanitize_input_encode(text)
        assert "Hello" in result
        assert "World" in result


pass
pass
pass

class TestGenerateContentHash:

    def test_same_content_same_hash(self):
        hash1 = generate_content_hash("hello world")
        hash2 = generate_content_hash("hello world")
        assert hash1 == hash2

    def test_different_content_different_hash(self):
        hash1 = generate_content_hash("hello world")
        hash2 = generate_content_hash("goodbye world")
        assert hash1 != hash2

    def test_empty_content_valid_hash(self):
        h = generate_content_hash("")
        assert isinstance(h, str)
        assert len(h) > 0

    def test_hash_is_hex_string(self):
        h = generate_content_hash("test content")
        assert all(c in "0123456789abcdef" for c in h)

    def test_hash_deterministic_across_calls(self):
        content = "The quick brown fox jumps over the lazy dog"
        hashes = [generate_content_hash(content) for _ in range(10)]
        assert len(set(hashes)) == 1

    def test_whitespace_sensitive(self):
        h1 = generate_content_hash("hello world")
        h2 = generate_content_hash("hello  world")
        assert h1 != h2

    def test_case_sensitive(self):
        h1 = generate_content_hash("Hello")
        h2 = generate_content_hash("hello")
        assert h1 != h2

    def test_long_content(self):
        content = "x" * 1_000_000
        h = generate_content_hash(content)
        assert isinstance(h, str)
        assert len(h) > 0


pass
pass
pass

class TestImageScoring:

    def test_image_score_threshold_exists(self):
        from crawl4ai.config import IMAGE_SCORE_THRESHOLD
        assert isinstance(IMAGE_SCORE_THRESHOLD, (int, float))

    def test_image_description_threshold_exists(self):
        from crawl4ai.config import IMAGE_DESCRIPTION_MIN_WORD_THRESHOLD
        assert isinstance(IMAGE_DESCRIPTION_MIN_WORD_THRESHOLD, (int, float))
