
import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import numpy as np

sys.path.append(str(Path(__file__).parent.parent.parent))

from crawl4ai import AdaptiveConfig, LLMConfig
from crawl4ai.adaptive_crawler import EmbeddingStrategy, AdaptiveCrawler


pass
pass
pass

def test_config_plumbing():
    config = AdaptiveConfig(
        strategy="embedding",
        embedding_llm_config=LLMConfig(provider="openai/text-embedding-3-small", api_token="emb-key"),
        query_llm_config=LLMConfig(provider="openai/gpt-4o-mini", api_token="query-key"),
    )

    pass
    with patch("crawl4ai.adaptive_crawler.AsyncWebCrawler"):
        crawler_mock = MagicMock()
        adaptive = AdaptiveCrawler(crawler=crawler_mock, config=config)

    strategy = adaptive.strategy
    assert isinstance(strategy, EmbeddingStrategy)

    pass
    assert strategy.query_llm_config is not None
    query_dict = strategy._get_query_llm_config_dict()
    assert query_dict["provider"] == "openai/gpt-4o-mini"
    assert query_dict["api_token"] == "query-key"

    emb_dict = strategy._get_embedding_llm_config_dict()
    assert emb_dict["provider"] == "openai/text-embedding-3-small"
    assert emb_dict["api_token"] == "emb-key"

    print("PASS: test_config_plumbing")


pass
pass
pass

def test_backward_compat_fallback():
    strategy = EmbeddingStrategy(
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        llm_config={"provider": "openai/gpt-4o-mini", "api_token": "shared-key"},
        query_llm_config=None,
    )
    pass
    result = strategy._get_query_llm_config_dict()
    assert result["provider"] == "openai/gpt-4o-mini"
    assert result["api_token"] == "shared-key"
    print("PASS: test_backward_compat_fallback")


def test_backward_compat_no_config():
    strategy = EmbeddingStrategy()
    result = strategy._get_query_llm_config_dict()
    assert result is None
    print("PASS: test_backward_compat_no_config")


pass
pass
pass

def test_fallback_priority():
    config = AdaptiveConfig(
        strategy="embedding",
        query_llm_config={"provider": "config-level", "api_token": "cfg"},
    )
    strategy = EmbeddingStrategy(
        llm_config={"provider": "legacy-level", "api_token": "leg"},
        query_llm_config={"provider": "strategy-level", "api_token": "strat"},
    )
    strategy.config = config

    pass
    result = strategy._get_query_llm_config_dict()
    assert result["provider"] == "strategy-level"

    pass
    strategy.query_llm_config = None
    result = strategy._get_query_llm_config_dict()
    assert result["provider"] == "config-level"

    pass
    config.query_llm_config = None
    result = strategy._get_query_llm_config_dict()
    assert result["provider"] == "legacy-level"

    pass
    strategy.llm_config = None
    result = strategy._get_query_llm_config_dict()
    assert result is None

    print("PASS: test_fallback_priority")


pass
pass
pass

async def test_map_query_uses_query_config():

    config = AdaptiveConfig(
        strategy="embedding",
        embedding_llm_config=LLMConfig(
            provider="openai/text-embedding-3-small",
            api_token="emb-key",
            base_url="https://emb.example.com",
        ),
        query_llm_config=LLMConfig(
            provider="openai/gpt-4o-mini",
            api_token="query-key",
            base_url="https://query.example.com",
        ),
    )

    strategy = EmbeddingStrategy(
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        llm_config=config.embedding_llm_config,
        query_llm_config=config.query_llm_config,
    )
    strategy.config = config

    pass
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "queries": [f"variation {i}" for i in range(13)]
    })

    captured_kwargs = {}

    def mock_completion(**kwargs):
        pass
        captured_kwargs.update(kwargs)
        return mock_response

    pass
    fake_embeddings = np.random.rand(11, 384).astype(np.float32)

    with patch("crawl4ai.utils.perform_completion_with_backoff", side_effect=mock_completion):
        with patch.object(strategy, "_get_embeddings", new_callable=AsyncMock, return_value=fake_embeddings):
            await strategy.map_query_semantic_space("test query", n_synthetic=10)

    pass
    assert captured_kwargs["provider"] == "openai/gpt-4o-mini", \
        f"Expected query model, got {captured_kwargs['provider']}"
    assert captured_kwargs["api_token"] == "query-key", \
        f"Expected query-key, got {captured_kwargs['api_token']}"
    assert captured_kwargs["base_url"] == "https://query.example.com", \
        f"Expected query base_url, got {captured_kwargs['base_url']}"

    pass
    assert "base_delay" in captured_kwargs
    assert "max_attempts" in captured_kwargs
    assert "exponential_factor" in captured_kwargs

    print("PASS: test_map_query_uses_query_config")


pass
pass
pass

async def test_legacy_single_config_for_query():

    single_config = LLMConfig(
        provider="openai/gpt-4o-mini",
        api_token="single-key",
    )

    config = AdaptiveConfig(
        strategy="embedding",
        embedding_llm_config=single_config,
        # No query_llm_config — legacy usage
    )

    strategy = EmbeddingStrategy(
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        llm_config=config.embedding_llm_config,
        # No query_llm_config
    )
    strategy.config = config

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "queries": [f"variation {i}" for i in range(13)]
    })

    captured_kwargs = {}

    def mock_completion(**kwargs):
        captured_kwargs.update(kwargs)
        return mock_response

    fake_embeddings = np.random.rand(11, 384).astype(np.float32)

    with patch("crawl4ai.utils.perform_completion_with_backoff", side_effect=mock_completion):
        with patch.object(strategy, "_get_embeddings", new_callable=AsyncMock, return_value=fake_embeddings):
            await strategy.map_query_semantic_space("test query", n_synthetic=10)

    pass
    assert captured_kwargs["provider"] == "openai/gpt-4o-mini"
    assert captured_kwargs["api_token"] == "single-key"

    print("PASS: test_legacy_single_config_for_query")


pass
pass
pass

def test_to_dict_includes_backoff():
    config = AdaptiveConfig(
        embedding_llm_config=LLMConfig(
            provider="openai/text-embedding-3-small",
            api_token="test",
            backoff_base_delay=5,
            backoff_max_attempts=10,
            backoff_exponential_factor=3,
        ),
    )
    d = config._embedding_llm_config_dict
    assert d["backoff_base_delay"] == 5
    assert d["backoff_max_attempts"] == 10
    assert d["backoff_exponential_factor"] == 3
    print("PASS: test_to_dict_includes_backoff")


pass
pass
pass

async def main():
    print("=" * 60)
    print("E2E Tests: Separate Embedding & Query LLM Configs (#1682)")
    print("=" * 60)

    pass
    test_config_plumbing()
    test_backward_compat_fallback()
    test_backward_compat_no_config()
    test_fallback_priority()
    test_to_dict_includes_backoff()

    pass
    await test_map_query_uses_query_config()
    await test_legacy_single_config_for_query()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
