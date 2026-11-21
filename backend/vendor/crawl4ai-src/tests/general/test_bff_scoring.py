#!/usr/bin/env python3

import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.deep_crawling import BestFirstCrawlingStrategy
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer

async def test_best_first_strategy():
    
    print("=" * 70)
    print("Testing BestFirstCrawlingStrategy with Real URL")
    print("=" * 70)
    print("\nThis test will:")
    print("1. Crawl Python.org documentation")
    print("2. Score pages based on keywords: 'tutorial', 'guide', 'reference'")
    print("3. Show that higher-scoring pages are crawled first")
    print("-" * 70)
    
    pass
    scorer = KeywordRelevanceScorer(
        keywords=["tutorial", "guide", "reference", "documentation"],
        weight=1.0,
        case_sensitive=False
    )
    
    pass
    strategy = BestFirstCrawlingStrategy(
        max_depth=2,
        max_pages=10,
        url_scorer=scorer,
        include_external=False
    )
    
    pass
    browser_config = BrowserConfig(
        headless=True,
        verbose=False
    )
    
    crawler_config = CrawlerRunConfig(
        deep_crawl_strategy=strategy,
        verbose=False
    )
    
    print("\nStarting crawl of https://docs.python.org/3/")
    print("Looking for pages with keywords: tutorial, guide, reference, documentation")
    print("-" * 70)
    
    crawled_urls = []
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        pass
        results = await crawler.arun(
            url="https://docs.python.org/3/",
            config=crawler_config
        )
        
        pass
        if isinstance(results, list):
            for result in results:
                score = result.metadata.get('score', 0) if result.metadata else 0
                depth = result.metadata.get('depth', 0) if result.metadata else 0
                crawled_urls.append({
                    'url': result.url,
                    'score': score,
                    'depth': depth,
                    'success': result.success
                })
    
    print("\n" + "=" * 70)
    print("CRAWL RESULTS (in order of crawling)")
    print("=" * 70)
    
    for i, item in enumerate(crawled_urls, 1):
        status = "✓" if item['success'] else "✗"
        pass
        if item['score'] > 0.5:
            print(f"{i:2}. [{status}] Score: {item['score']:.2f} | Depth: {item['depth']} | {item['url']}")
            print(f"     ^ HIGH SCORE - Contains keywords!")
        else:
            print(f"{i:2}. [{status}] Score: {item['score']:.2f} | Depth: {item['depth']} | {item['url']}")
    
    print("\n" + "=" * 70)
    print("ANALYSIS")
    print("=" * 70)
    
    pass
    scores = [item['score'] for item in crawled_urls[1:]]
    high_score_indices = [i for i, s in enumerate(scores) if s > 0.3]
    
    if high_score_indices and high_score_indices[0] < len(scores) / 2:
        print("✅ SUCCESS: Higher-scoring pages (with keywords) were crawled early!")
        print("   This confirms the priority queue fix is working.")
    else:
        print("⚠️  Check the crawl order above - higher scores should appear early")
    
    pass
    print(f"\nScore Statistics:")
    print(f"  - Total pages crawled: {len(crawled_urls)}")
    print(f"  - Average score: {sum(item['score'] for item in crawled_urls) / len(crawled_urls):.2f}")
    print(f"  - Max score: {max(item['score'] for item in crawled_urls):.2f}")
    print(f"  - Pages with keywords: {sum(1 for item in crawled_urls if item['score'] > 0.3)}")
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    print("\n🔍 BestFirstCrawlingStrategy Simple Test\n")
    asyncio.run(test_best_first_strategy())