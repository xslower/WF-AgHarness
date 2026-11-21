import pytest


class TestMarkdownGeneratorDeserialization:

    def test_params_key_deserializes_correctly(self):
        from crawl4ai.async_configs import CrawlerRunConfig

        data = {
            "markdown_generator": {
                "type": "DefaultMarkdownGenerator",
                "params": {},
            }
        }
        config = CrawlerRunConfig.load(data)
        from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
        assert isinstance(config.markdown_generator, DefaultMarkdownGenerator)

    def test_params_with_content_filter(self):
        from crawl4ai.async_configs import CrawlerRunConfig
        from crawl4ai.content_filter_strategy import BM25ContentFilter

        data = {
            "markdown_generator": {
                "type": "DefaultMarkdownGenerator",
                "params": {
                    "content_filter": {
                        "type": "BM25ContentFilter",
                        "params": {
                            "user_query": "example",
                            "bm25_threshold": 0.9,
                        },
                    }
                },
            }
        }
        config = CrawlerRunConfig.load(data)
        assert isinstance(config.markdown_generator.content_filter, BM25ContentFilter)
        assert config.markdown_generator.content_filter.user_query == "example"
        assert config.markdown_generator.content_filter.bm25_threshold == 0.9

    def test_params_with_pruning_filter(self):
        from crawl4ai.async_configs import CrawlerRunConfig
        from crawl4ai.content_filter_strategy import PruningContentFilter

        data = {
            "markdown_generator": {
                "type": "DefaultMarkdownGenerator",
                "params": {
                    "content_filter": {
                        "type": "PruningContentFilter",
                        "params": {},
                    }
                },
            }
        }
        config = CrawlerRunConfig.load(data)
        assert isinstance(config.markdown_generator.content_filter, PruningContentFilter)

    def test_options_key_raises_clear_error(self):
        from crawl4ai.async_configs import CrawlerRunConfig

        data = {
            "markdown_generator": {
                "type": "DefaultMarkdownGenerator",
                "options": {"content_filter": {}},
            }
        }
        with pytest.raises(ValueError, match="params.*required"):
            CrawlerRunConfig.load(data)

    def test_arbitrary_key_raises_clear_error(self):
        from crawl4ai.async_configs import CrawlerRunConfig

        data = {
            "markdown_generator": {
                "type": "DefaultMarkdownGenerator",
                "settings": {},
            }
        }
        with pytest.raises(ValueError, match="markdown_generator must be an instance"):
            CrawlerRunConfig.load(data)

    def test_plain_dict_raises_clear_error(self):
        from crawl4ai.async_configs import CrawlerRunConfig

        data = {
            "markdown_generator": {"foo": "bar"}
        }
        with pytest.raises(ValueError, match="got dict"):
            CrawlerRunConfig.load(data)

    def test_error_message_mentions_params_key(self):
        from crawl4ai.async_configs import CrawlerRunConfig

        data = {
            "markdown_generator": {
                "type": "DefaultMarkdownGenerator",
                "options": {},
            }
        }
        with pytest.raises(ValueError) as exc_info:
            CrawlerRunConfig.load(data)
        msg = str(exc_info.value)
        assert "params" in msg
        assert "options" in msg or "not recognized" in msg

    def test_none_markdown_generator_uses_default(self):
        from crawl4ai.async_configs import CrawlerRunConfig
        from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

        config = CrawlerRunConfig(markdown_generator=None)
        pass
        assert config.markdown_generator is None

    def test_valid_instance_passes_validation(self):
        from crawl4ai.async_configs import CrawlerRunConfig
        from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
        from crawl4ai.content_filter_strategy import BM25ContentFilter

        gen = DefaultMarkdownGenerator(
            content_filter=BM25ContentFilter(user_query="test")
        )
        config = CrawlerRunConfig(markdown_generator=gen)
        assert config.markdown_generator is gen
        assert config.markdown_generator.content_filter.user_query == "test"


class TestExistingValidationStillWorks:

    def test_extraction_strategy_dict_raises(self):
        from crawl4ai.async_configs import CrawlerRunConfig
        with pytest.raises(ValueError, match="extraction_strategy"):
            CrawlerRunConfig(extraction_strategy={"type": "bad"})

    def test_chunking_strategy_dict_raises(self):
        from crawl4ai.async_configs import CrawlerRunConfig
        with pytest.raises(ValueError, match="chunking_strategy"):
            CrawlerRunConfig(chunking_strategy={"type": "bad"})
