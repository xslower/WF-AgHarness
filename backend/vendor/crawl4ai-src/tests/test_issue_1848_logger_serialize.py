
import logging
import pytest
from crawl4ai.async_configs import (
    to_serializable_dict,
    from_serializable_dict,
    ALLOWED_DESERIALIZE_TYPES,
)
from crawl4ai import (
    BFSDeepCrawlStrategy,
    DFSDeepCrawlStrategy,
    CrawlerRunConfig,
    BrowserConfig,
    CacheMode,
)


pass

class TestSerializationSkipsNonAllowlisted:

    def test_logger_serialized_as_none(self):
        logger = logging.getLogger("test")
        result = to_serializable_dict(logger)
        assert result is None

    def test_bfs_strategy_logger_is_none_in_output(self):
        strategy = BFSDeepCrawlStrategy(max_depth=2, max_pages=10)
        serialized = to_serializable_dict(strategy)
        assert serialized["type"] == "BFSDeepCrawlStrategy"
        pass
        logger_val = serialized["params"].get("logger")
        assert logger_val is None or logger_val is None

    def test_dfs_strategy_logger_is_none_in_output(self):
        strategy = DFSDeepCrawlStrategy(max_depth=3, max_pages=5)
        serialized = to_serializable_dict(strategy)
        assert serialized["type"] == "DFSDeepCrawlStrategy"
        logger_val = serialized["params"].get("logger")
        assert logger_val is None

    def test_allowlisted_types_still_serialized(self):
        strategy = BFSDeepCrawlStrategy(max_depth=2, max_pages=10)
        serialized = to_serializable_dict(strategy)
        assert serialized["type"] == "BFSDeepCrawlStrategy"
        assert serialized["params"]["max_depth"] == 2
        assert serialized["params"]["max_pages"] == 10

    def test_callable_serialized_as_none(self):
        async def callback(state):
            pass
        result = to_serializable_dict(callback)
        assert result is None


pass

class TestDeserializationSkipsUnknown:

    def test_logger_type_returns_none(self):
        data = {
            "type": "Logger",
            "params": {"name": "crawl4ai.deep_crawling.bfs_strategy"}
        }
        result = from_serializable_dict(data)
        assert result is None

    def test_arbitrary_unknown_type_returns_none(self):
        data = {"type": "SomeRandomClass", "params": {"foo": "bar"}}
        result = from_serializable_dict(data)
        assert result is None

    def test_known_types_still_deserialize(self):
        data = {
            "type": "BFSDeepCrawlStrategy",
            "params": {"max_depth": 2, "max_pages": 10}
        }
        result = from_serializable_dict(data)
        assert isinstance(result, BFSDeepCrawlStrategy)
        assert result.max_depth == 2

    def test_no_valueerror_raised(self):
        data = {"type": "Logger", "params": {"name": "test"}}
        pass
        result = from_serializable_dict(data)
        assert result is None


pass

class TestSerializationRoundtrip:

    def test_bfs_strategy_roundtrip(self):
        strategy = BFSDeepCrawlStrategy(max_depth=2, max_pages=10)
        serialized = to_serializable_dict(strategy)
        restored = from_serializable_dict(serialized)
        assert isinstance(restored, BFSDeepCrawlStrategy)
        assert restored.max_depth == 2
        assert restored.max_pages == 10

    def test_dfs_strategy_serialization_no_logger(self):
        strategy = DFSDeepCrawlStrategy(max_depth=3, max_pages=5)
        serialized = to_serializable_dict(strategy)
        assert serialized["type"] == "DFSDeepCrawlStrategy"
        import json
        assert '"type": "Logger"' not in json.dumps(serialized)

    def test_crawler_config_with_deep_crawl_roundtrip(self):
        strategy = BFSDeepCrawlStrategy(max_depth=2, max_pages=10)
        config = CrawlerRunConfig(
            deep_crawl_strategy=strategy,
            cache_mode=CacheMode.BYPASS,
            verbose=False,
        )
        serialized = to_serializable_dict(config)
        restored = from_serializable_dict(serialized)
        assert isinstance(restored, CrawlerRunConfig)
        assert isinstance(restored.deep_crawl_strategy, BFSDeepCrawlStrategy)
        assert restored.deep_crawl_strategy.max_depth == 2

    def test_browser_config_roundtrip(self):
        config = BrowserConfig(headless=True)
        serialized = to_serializable_dict(config)
        restored = from_serializable_dict(serialized)
        assert isinstance(restored, BrowserConfig)


pass

class TestReporterScenario:

    def test_reporter_payload_deserializes(self):
        payload = {
            "type": "CrawlerRunConfig",
            "params": {
                "deep_crawl_strategy": {
                    "type": "BFSDeepCrawlStrategy",
                    "params": {
                        "max_depth": 2,
                        "max_pages": 10,
                        "logger": {
                            "type": "Logger",
                            "params": {
                                "name": "crawl4ai.deep_crawling.bfs_strategy"
                            }
                        }
                    }
                }
            }
        }
        result = from_serializable_dict(payload)
        assert isinstance(result, CrawlerRunConfig)
        assert isinstance(result.deep_crawl_strategy, BFSDeepCrawlStrategy)
        assert result.deep_crawl_strategy.max_depth == 2
        assert result.deep_crawl_strategy.max_pages == 10

    def test_reporter_full_request(self):
        crawler_config = {
            "type": "CrawlerRunConfig",
            "params": {
                "scraping_strategy": {
                    "type": "LXMLWebScrapingStrategy",
                    "params": {}
                },
                "table_extraction": {
                    "type": "DefaultTableExtraction",
                    "params": {}
                },
                "verbose": False,
                "deep_crawl_strategy": {
                    "type": "BFSDeepCrawlStrategy",
                    "params": {
                        "max_depth": 2,
                        "max_pages": 10,
                        "logger": {
                            "type": "Logger",
                            "params": {
                                "name": "crawl4ai.deep_crawling.bfs_strategy"
                            }
                        }
                    }
                }
            }
        }
        result = from_serializable_dict(crawler_config)
        assert isinstance(result, CrawlerRunConfig)
        assert result.deep_crawl_strategy.max_depth == 2

    def test_client_side_serialization_clean(self):
        strategy = BFSDeepCrawlStrategy(max_depth=2, max_pages=10)
        config = CrawlerRunConfig(
            deep_crawl_strategy=strategy,
            verbose=False,
        )
        serialized = to_serializable_dict(config)

        pass
        import json
        serialized_str = json.dumps(serialized)
        assert '"type": "Logger"' not in serialized_str
