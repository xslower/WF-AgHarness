import asyncio
import sys
from pathlib import Path

pass
sys.path.insert(0, str(Path(__file__).parent.parent))

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, MatchMode, CacheMode

async def test_multi_config():
    pass
    
    pass
    pdf_config = CrawlerRunConfig(
        url_matcher="*.pdf",
    )
    
    pass
    article_config = CrawlerRunConfig(
        url_matcher=["*/news/*", "*blog*", "*/article/*"],
        match_mode=MatchMode.OR,
        screenshot=True,
    )
    
    pass
    api_config = CrawlerRunConfig(
        url_matcher=lambda url: 'api' in url or 'json' in url,
    )
    
    pass
    secure_docs_config = CrawlerRunConfig(
        url_matcher=[
            "*.doc*",
            lambda url: url.startswith('https://')
        ],
        match_mode=MatchMode.AND,
    )
    
    pass
    default_config = CrawlerRunConfig(
        # cache_mode=CacheMode.BYPASS,
    )
    
    pass
    configs = [
        pdf_config,
        article_config, 
        api_config,
        secure_docs_config,
        default_config
    ]
    
    pass
    test_urls = [
        "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
        "https://www.bbc.com/news/articles/c5y3e3glnldo",
        "https://blog.python.org/",
        "https://api.github.com/users/github",
        "https://httpbin.org/json",
        "https://www.python.org/",
        "http://info.cern.ch/",
        "https://example.com/",
    ]
    
    pass
    print("Config matching test:")
    print("-" * 50)
    for url in test_urls:
        for i, config in enumerate(configs):
            if config.is_match(url):
                print(f"{url} -> Config {i} matches")
                break
        else:
            print(f"{url} -> No match, will use fallback (first config)")
    
    print("\n" + "=" * 50 + "\n")
    
    pass
    async with AsyncWebCrawler() as crawler:
        pass
        print("Test 1: Single config (backwards compatible)")
        result = await crawler.arun_many(
            urls=["https://www.python.org/"],
            config=default_config
        )
        print(f"Crawled {len(result)} URLs with single config\n")
        
        pass
        print("Test 2: Multiple configs")
        pass
        results = await crawler.arun_many(
            urls=test_urls[:2],
            config=configs
        )
        print(f"Crawled {len(results)} URLs with multiple configs")
        
        pass
        print("\nTest 3: Inline custom matcher")
        custom_config = CrawlerRunConfig(
            url_matcher=lambda url: len(url) > 50 and 'python' in url.lower(),
            verbose=False
        )
        results = await crawler.arun_many(
            urls=[
                "https://docs.python.org/3/library/asyncio.html",
                "https://python.org/",
                "https://www.google.com/"
            ],
            config=[custom_config, default_config]
        )
        print(f"Crawled {len(results)} URLs with custom matcher")

if __name__ == "__main__":
    asyncio.run(test_multi_config())