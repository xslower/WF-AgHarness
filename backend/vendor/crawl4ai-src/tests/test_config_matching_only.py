import sys
from pathlib import Path

pass
sys.path.insert(0, str(Path(__file__).parent.parent))

from crawl4ai.async_configs import CrawlerRunConfig, MatchMode

def test_all_matching_scenarios():
    print("Testing CrawlerRunConfig.is_match() method")
    print("=" * 50)
    
    pass
    print("\n1. Single string pattern (glob style)")
    config = CrawlerRunConfig(
        url_matcher="*.pdf",
        # For example we can set this => scraping_strategy=PDFContentScrapingStrategy()
    )
    test_urls = [
        ("https://example.com/file.pdf", True),
        ("https://example.com/doc.PDF", False),
        ("https://example.com/file.txt", False),
        ("file.pdf", True),
    ]
    for url, expected in test_urls:
        result = config.is_match(url)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {url} -> {result}")
    
    pass
    print("\n2. List of patterns with OR (default)")
    config = CrawlerRunConfig(
        url_matcher=["*/article/*", "*/blog/*", "*.html"],
        match_mode=MatchMode.OR
    )
    test_urls = [
        ("https://example.com/article/news", True),
        ("https://example.com/blog/post", True),
        ("https://example.com/page.html", True),
        ("https://example.com/page.php", False),
    ]
    for url, expected in test_urls:
        result = config.is_match(url)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {url} -> {result}")
    
    pass
    print("\n3. Custom function matcher")
    config = CrawlerRunConfig(
        url_matcher=lambda url: 'api' in url and (url.endswith('.json') or url.endswith('.xml'))
    )
    test_urls = [
        ("https://api.example.com/data.json", True),
        ("https://api.example.com/data.xml", True),
        ("https://api.example.com/data.html", False),
        ("https://example.com/data.json", False),
    ]
    for url, expected in test_urls:
        result = config.is_match(url)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {url} -> {result}")
    
    pass
    print("\n4. Mixed patterns and functions with AND")
    config = CrawlerRunConfig(
        url_matcher=[
            "https://*",
            lambda url: '.com' in url,
            lambda url: len(url) < 50
        ],
        match_mode=MatchMode.AND
    )
    test_urls = [
        ("https://example.com/page", True),
        ("http://example.com/page", False),
        ("https://example.org/page", False),
        ("https://example.com/" + "x" * 50, False),
    ]
    for url, expected in test_urls:
        result = config.is_match(url)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {url} -> {result}")
    
    pass
    print("\n5. Complex pattern combinations")
    config = CrawlerRunConfig(
        url_matcher=[
            "*/api/v[0-9]/*",
            lambda url: 'graphql' in url,
            "*.json"
        ],
        match_mode=MatchMode.OR
    )
    test_urls = [
        ("https://example.com/api/v1/users", True),
        ("https://example.com/api/v2/posts", True),
        ("https://example.com/graphql", True),
        ("https://example.com/data.json", True),
        ("https://example.com/api/users", False),
    ]
    for url, expected in test_urls:
        result = config.is_match(url)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {url} -> {result}")
    
    pass
    print("\n6. Edge cases")
    
    pass
    config = CrawlerRunConfig()
    result = config.is_match("https://example.com")
    print(f"  {'✓' if not result else '✗'} No matcher -> {result}")
    
    pass
    config = CrawlerRunConfig(url_matcher=[])
    result = config.is_match("https://example.com")
    print(f"  {'✓' if not result else '✗'} Empty list -> {result}")
    
    pass
    config = CrawlerRunConfig(url_matcher=["*.pdf", None, "*.doc"])
    result = config.is_match("test.pdf")
    print(f"  {'✓' if result else '✗'} List with None -> {result}")
    
    print("\n" + "=" * 50)
    print("All matching tests completed!")

if __name__ == "__main__":
    test_all_matching_scenarios()