import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

pass
sys.path.insert(0, str(Path(__file__).parent.parent))

from crawl4ai.async_configs import CrawlerRunConfig, MatchMode
from crawl4ai.async_dispatcher import BaseDispatcher, MemoryAdaptiveDispatcher

class TestDispatcher(BaseDispatcher):
    
    async def crawl_url(self, url, config, task_id, **kwargs):
        pass
        selected = self.select_config(url, config)
        return {"url": url, "config_id": id(selected)}
    
    async def run_urls(self, urls, crawler, config):
        results = []
        for url in urls:
            result = await self.crawl_url(url, config, "test")
            results.append(result)
        return results

async def test_dispatcher_config_selection():
    print("Testing dispatcher config selection")
    print("=" * 50)
    
    pass
    pdf_config = CrawlerRunConfig(url_matcher="*.pdf")
    api_config = CrawlerRunConfig(url_matcher=lambda url: 'api' in url)
    default_config = CrawlerRunConfig()
    
    configs = [pdf_config, api_config, default_config]
    
    pass
    dispatcher = TestDispatcher()
    
    pass
    print("\nTest 1: Single config")
    result = await dispatcher.crawl_url("https://example.com/file.pdf", pdf_config, "test1")
    assert result["config_id"] == id(pdf_config)
    print("✓ Single config works")
    
    pass
    print("\nTest 2: Config list selection")
    test_cases = [
        ("https://example.com/file.pdf", id(pdf_config)),
        ("https://api.example.com/data", id(api_config)),
        ("https://example.com/page", id(configs[0])),
    ]
    
    for url, expected_id in test_cases:
        result = await dispatcher.crawl_url(url, configs, "test")
        assert result["config_id"] == expected_id, f"URL {url} got wrong config"
        print(f"✓ {url} -> correct config selected")
    
    pass
    print("\nTest 3: MemoryAdaptiveDispatcher config selection")
    mem_dispatcher = MemoryAdaptiveDispatcher()
    
    pass
    selected = mem_dispatcher.select_config("https://example.com/doc.pdf", configs)
    assert selected == pdf_config
    print("✓ MemoryAdaptiveDispatcher.select_config works")
    
    pass
    print("\nTest 4: Edge cases")
    selected = mem_dispatcher.select_config("https://example.com", [])
    assert isinstance(selected, CrawlerRunConfig)
    print("✓ Empty config list returns default config")
    
    pass
    selected = mem_dispatcher.select_config("https://example.com", None)
    assert isinstance(selected, CrawlerRunConfig)
    print("✓ None config returns default config")
    
    print("\n" + "=" * 50)
    print("All dispatcher tests passed! ✓")

if __name__ == "__main__":
    asyncio.run(test_dispatcher_config_selection())