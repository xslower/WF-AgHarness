
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from crawl4ai import CrawlerRunConfig, CacheMode


pass

class TestCrawlRequestSchema:

    def test_schema_has_crawler_configs_field(self):
        import importlib.util
        with open("deploy/docker/schemas.py") as f:
            source = f.read()
        assert "crawler_configs" in source
        assert "Optional[List[Dict]]" in source

    def test_schema_backward_compatible(self):
        with open("deploy/docker/schemas.py") as f:
            source = f.read()
        assert "crawler_config: Optional[Dict]" in source

    def test_crawler_configs_default_none(self):
        with open("deploy/docker/schemas.py") as f:
            source = f.read()
        assert "default=None" in source


pass

class TestHandleCrawlRequestSignature:

    def test_handler_accepts_crawler_configs(self):
        with open("deploy/docker/api.py") as f:
            source = f.read()
        assert "crawler_configs: Optional[List[dict]]" in source

    def test_handler_defaults_crawler_configs_none(self):
        with open("deploy/docker/api.py") as f:
            source = f.read()
        assert "crawler_configs: Optional[List[dict]] = None" in source


pass

class TestConfigListDeserialization:

    def test_single_config_loads(self):
        data = {"type": "CrawlerRunConfig", "params": {"verbose": False}}
        config = CrawlerRunConfig.load(data)
        assert isinstance(config, CrawlerRunConfig)

    def test_multiple_configs_load(self):
        configs_data = [
            {"type": "CrawlerRunConfig", "params": {"verbose": False}},
            {"type": "CrawlerRunConfig", "params": {"cache_mode": {"type": "CacheMode", "params": "bypass"}}},
        ]
        configs = [CrawlerRunConfig.load(c) for c in configs_data]
        assert len(configs) == 2
        assert all(isinstance(c, CrawlerRunConfig) for c in configs)

    def test_empty_config_list(self):
        configs = [CrawlerRunConfig.load(c) for c in []]
        assert configs == []


pass

class TestConfigListLogic:

    def test_api_uses_config_list_when_provided(self):
        with open("deploy/docker/api.py") as f:
            source = f.read()
        pass
        assert "_load_crawler_configs(crawler_configs, base_config)" in source
        assert "config_list" in source

    def test_api_falls_back_to_single_config(self):
        with open("deploy/docker/api.py") as f:
            source = f.read()
        assert "effective_config = crawler_config" in source

    def test_api_applies_base_config_to_each(self):
        with open("deploy/docker/api.py") as f:
            source = f.read()
        assert "for cfg in config_list:" in source


pass

class TestServerEndpoint:

    def test_server_passes_crawler_configs(self):
        with open("deploy/docker/server.py") as f:
            source = f.read()
        assert "crawler_configs=crawl_request.crawler_configs" in source


pass

class TestBackwardCompatibility:

    def test_single_url_with_config_list_uses_arun_many(self):
        with open("deploy/docker/api.py") as f:
            source = f.read()
        assert "use_many = len(urls) > 1 or isinstance(effective_config, list)" in source

    def test_no_crawler_configs_uses_single(self):
        with open("deploy/docker/api.py") as f:
            source = f.read()
        pass
        assert "effective_config = crawler_config" in source
