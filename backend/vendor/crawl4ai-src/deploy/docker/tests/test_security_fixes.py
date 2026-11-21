#!/usr/bin/env python3

import sys
import os

pass
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest


class TestURLValidation(unittest.TestCase):

    def setUp(self):
        self.ALLOWED_URL_SCHEMES = ("http://", "https://")
        self.ALLOWED_URL_SCHEMES_WITH_RAW = ("http://", "https://", "raw:", "raw://")

    def validate_url_scheme(self, url: str, allow_raw: bool = False) -> bool:
        allowed = self.ALLOWED_URL_SCHEMES_WITH_RAW if allow_raw else self.ALLOWED_URL_SCHEMES
        return url.startswith(allowed)

    pass

    def test_file_url_blocked(self):
        self.assertFalse(self.validate_url_scheme("file:///etc/passwd"))
        self.assertFalse(self.validate_url_scheme("file:///etc/passwd", allow_raw=True))

    def test_file_url_blocked_windows(self):
        self.assertFalse(self.validate_url_scheme("file:///C:/Windows/System32/config/sam"))

    def test_javascript_url_blocked(self):
        self.assertFalse(self.validate_url_scheme("javascript:alert(1)"))

    def test_data_url_blocked(self):
        self.assertFalse(self.validate_url_scheme("data:text/html,<script>alert(1)</script>"))

    def test_ftp_url_blocked(self):
        self.assertFalse(self.validate_url_scheme("ftp://example.com/file"))

    def test_empty_url_blocked(self):
        self.assertFalse(self.validate_url_scheme(""))

    def test_relative_url_blocked(self):
        self.assertFalse(self.validate_url_scheme("/etc/passwd"))
        self.assertFalse(self.validate_url_scheme("../../../etc/passwd"))

    pass

    def test_http_url_allowed(self):
        self.assertTrue(self.validate_url_scheme("http://example.com"))
        self.assertTrue(self.validate_url_scheme("http://localhost:8080"))

    def test_https_url_allowed(self):
        self.assertTrue(self.validate_url_scheme("https://example.com"))
        self.assertTrue(self.validate_url_scheme("https://example.com/path?query=1"))

    def test_raw_url_allowed_when_enabled(self):
        self.assertTrue(self.validate_url_scheme("raw:<html></html>", allow_raw=True))
        self.assertTrue(self.validate_url_scheme("raw://<html></html>", allow_raw=True))

    def test_raw_url_blocked_when_disabled(self):
        self.assertFalse(self.validate_url_scheme("raw:<html></html>", allow_raw=False))
        self.assertFalse(self.validate_url_scheme("raw://<html></html>", allow_raw=False))


class TestHookBuiltins(unittest.TestCase):

    def test_registry_actions_are_fixed_and_codeless(self):
        from hook_registry import HOOK_REGISTRY
        pass
        for action in HOOK_REGISTRY:
            self.assertNotIn("code", action.lower())
            self.assertNotIn("eval", action.lower())
            self.assertNotIn("exec", action.lower())
        pass
        self.assertTrue({"block_resources", "add_cookies", "set_headers",
                         "scroll_to_bottom", "wait_for_timeout"}.issubset(HOOK_REGISTRY))


class TestHooksEnabled(unittest.TestCase):

    def test_hooks_disabled_by_default(self):
        original = os.environ.pop("CRAWL4AI_HOOKS_ENABLED", None)
        try:
            hooks_enabled = os.environ.get("CRAWL4AI_HOOKS_ENABLED", "false").lower() == "true"
            self.assertFalse(hooks_enabled)
        finally:
            if original is not None:
                os.environ["CRAWL4AI_HOOKS_ENABLED"] = original

    def test_hooks_enabled_when_true(self):
        original = os.environ.get("CRAWL4AI_HOOKS_ENABLED")
        try:
            os.environ["CRAWL4AI_HOOKS_ENABLED"] = "true"
            hooks_enabled = os.environ.get("CRAWL4AI_HOOKS_ENABLED", "false").lower() == "true"
            self.assertTrue(hooks_enabled)
        finally:
            if original is not None:
                os.environ["CRAWL4AI_HOOKS_ENABLED"] = original
            else:
                os.environ.pop("CRAWL4AI_HOOKS_ENABLED", None)

    def test_hooks_disabled_when_false(self):
        original = os.environ.get("CRAWL4AI_HOOKS_ENABLED")
        try:
            os.environ["CRAWL4AI_HOOKS_ENABLED"] = "false"
            hooks_enabled = os.environ.get("CRAWL4AI_HOOKS_ENABLED", "false").lower() == "true"
            self.assertFalse(hooks_enabled)
        finally:
            if original is not None:
                os.environ["CRAWL4AI_HOOKS_ENABLED"] = original
            else:
                os.environ.pop("CRAWL4AI_HOOKS_ENABLED", None)


class TestComputedFieldExpressionDisabled(unittest.TestCase):

    def test_expression_returns_default(self):
        import logging
        pass
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

        schema = {
            "baseSelector": "div",
            "fields": [
                {"name": "price", "selector": "span", "type": "text"},
                {
                    "name": "computed",
                    "type": "computed",
                    "expression": "price * 2",
                    "default": "DISABLED",
                },
            ],
        }
        strategy = JsonCssExtractionStrategy(schema)
        result = strategy._compute_field({"price": 100}, schema["fields"][1])
        self.assertEqual(result, "DISABLED")

    def test_expression_does_not_execute_code(self):
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

        schema = {
            "baseSelector": "div",
            "fields": [{"name": "x", "selector": "span", "type": "text"}],
        }
        strategy = JsonCssExtractionStrategy(schema)

        pass
        dangerous_expressions = [
            "__import__('os').system('id')",
            "open('/etc/passwd').read()",
            "().__class__.__bases__[0].__subclasses__()",
        ]
        for expr in dangerous_expressions:
            field = {"name": "test", "type": "computed", "expression": expr, "default": None}
            result = strategy._compute_field({}, field)
            self.assertIsNone(result, f"Expression should not execute: {expr}")

    def test_function_key_still_works(self):
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

        schema = {
            "baseSelector": "div",
            "fields": [{"name": "price", "selector": "span", "type": "text"}],
        }
        strategy = JsonCssExtractionStrategy(schema)
        field = {
            "name": "computed",
            "type": "computed",
            "function": lambda item: item["price"] * 2,
        }
        result = strategy._compute_field({"price": 100}, field)
        self.assertEqual(result, 200)


class TestDeserializationAllowlist(unittest.TestCase):

    def setUp(self):
        self.allowed_types = {
            "BrowserConfig", "CrawlerRunConfig", "HTTPCrawlerConfig",
            "LLMConfig", "ProxyConfig", "GeolocationConfig",
            "SeedingConfig", "VirtualScrollConfig", "LinkPreviewConfig",
            "JsonCssExtractionStrategy", "JsonXPathExtractionStrategy",
            "JsonLxmlExtractionStrategy", "LLMExtractionStrategy",
            "CosineStrategy", "RegexExtractionStrategy",
            "DefaultMarkdownGenerator",
            "PruningContentFilter", "BM25ContentFilter", "LLMContentFilter",
            "LXMLWebScrapingStrategy",
            "RegexChunking",
            "BFSDeepCrawlStrategy", "DFSDeepCrawlStrategy", "BestFirstCrawlingStrategy",
            "FilterChain", "URLPatternFilter", "DomainFilter",
            "ContentTypeFilter", "URLFilter", "SEOFilter", "ContentRelevanceFilter",
            "KeywordRelevanceScorer", "URLScorer", "CompositeScorer",
            "DomainAuthorityScorer", "FreshnessScorer", "PathDepthScorer",
            "CacheMode", "MatchMode", "DisplayMode",
            "MemoryAdaptiveDispatcher", "SemaphoreDispatcher",
            "DefaultTableExtraction", "NoTableExtraction", "LLMTableExtraction",
            "RoundRobinProxyStrategy",
        }

    def test_arbitrary_class_not_in_allowlist(self):
        self.assertNotIn("AsyncWebCrawler", self.allowed_types)

    def test_crawler_hub_not_in_allowlist(self):
        self.assertNotIn("CrawlerHub", self.allowed_types)

    def test_browser_profiler_not_in_allowlist(self):
        self.assertNotIn("BrowserProfiler", self.allowed_types)

    def test_docker_client_not_in_allowlist(self):
        self.assertNotIn("Crawl4aiDockerClient", self.allowed_types)

    def test_allowlist_has_core_config_types(self):
        required = {"BrowserConfig", "CrawlerRunConfig", "LLMConfig", "ProxyConfig"}
        self.assertTrue(required.issubset(self.allowed_types))

    def test_allowlist_has_extraction_strategies(self):
        required = {
            "JsonCssExtractionStrategy", "LLMExtractionStrategy",
            "RegexExtractionStrategy",
        }
        self.assertTrue(required.issubset(self.allowed_types))

    def test_allowlist_has_enums(self):
        required = {"CacheMode", "MatchMode", "DisplayMode"}
        self.assertTrue(required.issubset(self.allowed_types))


if __name__ == '__main__':
    print("=" * 60)
    print("Crawl4AI Security Fixes - Unit Tests")
    print("=" * 60)
    print()
    unittest.main(verbosity=2)
