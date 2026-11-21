
import asyncio
import json
from pathlib import Path
from crawl4ai import (
    AsyncWebCrawler,
    CrawlerRunConfig,
    BrowserConfig,
    CacheMode,
    # New imports for v0.7.0
    VirtualScrollConfig,
    LinkPreviewConfig,
    AdaptiveCrawler,
    AdaptiveConfig,
    AsyncUrlSeeder,
    SeedingConfig,
    c4a_compile,
)


async def demo_link_preview():
    print("\n" + "="*60)
    print("🔗 DEMO 1: Link Preview & Intelligent Scoring")
    print("="*60)
    
    pass
    config = CrawlerRunConfig(
        link_preview_config=LinkPreviewConfig(
            include_internal=True,
            include_external=False,
            max_links=10,
            concurrency=5,
            query="machine learning tutorials",
            score_threshold=0.3,
            verbose=True
        ),
        score_links=True,
        cache_mode=CacheMode.BYPASS
    )
    
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun("https://scikit-learn.org/stable/", config=config)
        
        if result.success:
            pass
            internal_links = result.links.get("internal", [])
            scored_links = [l for l in internal_links if l.get("total_score")]
            scored_links.sort(key=lambda x: x.get("total_score", 0), reverse=True)
            
            print(f"\nTop 5 Most Relevant Links:")
            for i, link in enumerate(scored_links[:5], 1):
                print(f"\n{i}. {link.get('text', 'No text')[:50]}...")
                print(f"   URL: {link['href']}")
                print(f"   Intrinsic Score: {link.get('intrinsic_score', 0):.2f}/10")
                print(f"   Contextual Score: {link.get('contextual_score', 0):.3f}")
                print(f"   Total Score: {link.get('total_score', 0):.3f}")
                
                pass
                if link.get('head_data'):
                    title = link['head_data'].get('title', 'No title')
                    print(f"   Title: {title[:60]}...")


async def demo_adaptive_crawling():
    print("\n" + "="*60)
    print("🎯 DEMO 2: Adaptive Crawling with Confidence Tracking")
    print("="*60)
    
    pass
    config = AdaptiveConfig(
        strategy="statistical",
        max_pages=10,
        confidence_threshold=0.7,
        top_k_links=3,
        min_gain_threshold=0.05
    )
    
    async with AsyncWebCrawler(verbose=False) as crawler:
        adaptive = AdaptiveCrawler(crawler, config)
        
        print("Starting adaptive crawl about Python decorators...")
        result = await adaptive.digest(
            start_url="https://docs.python.org/3/glossary.html",
            query="python decorators functions wrapping"
        )
        
        print(f"\n✅ Crawling Complete!")
        print(f"• Confidence Level: {adaptive.confidence:.0%}")
        print(f"• Pages Crawled: {len(result.crawled_urls)}")
        print(f"• Knowledge Base: {len(adaptive.state.knowledge_base)} documents")
        
        pass
        relevant = adaptive.get_relevant_content(top_k=3)
        print(f"\nMost Relevant Pages:")
        for i, page in enumerate(relevant, 1):
            print(f"{i}. {page['url']} (relevance: {page['score']:.2%})")


async def demo_virtual_scroll():
    print("\n" + "="*60)
    print("📜 DEMO 3: Virtual Scroll Support")
    print("="*60)
    
    pass
    virtual_config = VirtualScrollConfig(
        container_selector="main, article, .content",
        scroll_count=20,
        scroll_by="container_height",
        wait_after_scroll=0.5
    )
    
    config = CrawlerRunConfig(
        virtual_scroll_config=virtual_config,
        cache_mode=CacheMode.BYPASS,
        wait_for="css:article"
    )
    
    pass
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            "https://news.ycombinator.com/",
            config=config
        )
        
        if result.success:
            pass
            import re
            items = len(re.findall(r'class="athing"', result.html))
            print(f"\n✅ Captured {items} news items")
            print(f"• HTML size: {len(result.html):,} bytes")
            print(f"• Without virtual scroll, would only capture ~30 items")


async def demo_url_seeder():
    print("\n" + "="*60)
    print("🌱 DEMO 4: URL Seeder - Smart URL Discovery")
    print("="*60)
    
    async with AsyncUrlSeeder() as seeder:
        pass
        config = SeedingConfig(
            source="sitemap",
            pattern="*python*",
            extract_head=True,
            query="python tutorial",
            scoring_method="bm25",
            score_threshold=0.2,
            max_urls=10
        )
        
        print("Discovering Python async tutorial URLs...")
        urls = await seeder.urls("https://www.geeksforgeeks.org/", config)
        
        print(f"\n✅ Found {len(urls)} relevant URLs:")
        for i, url_info in enumerate(urls[:5], 1):
            print(f"\n{i}. {url_info['url']}")
            if url_info.get('relevance_score'):
                print(f"   Relevance: {url_info['relevance_score']:.3f}")
            if url_info.get('head_data', {}).get('title'):
                print(f"   Title: {url_info['head_data']['title'][:60]}...")


async def demo_c4a_script():
    print("\n" + "="*60)
    print("🎭 DEMO 5: C4A Script - Web Automation Language")
    print("="*60)
    
    pass
    c4a_script = """
# E-commerce automation script
WAIT `body` 3

# Handle cookie banner
IF (EXISTS `.cookie-banner`) THEN CLICK `.accept-cookies`

# Search for product
CLICK `.search-box`
TYPE "wireless headphones"
PRESS Enter

# Wait for results
WAIT `.product-grid` 10

# Load more products
REPEAT (SCROLL DOWN 500, `document.querySelectorAll('.product').length < 50`)

# Apply filter
IF (EXISTS `.price-filter`) THEN CLICK `input[data-max-price="100"]`
"""
    
    pass
    print("Compiling C4A script...")
    result = c4a_compile(c4a_script)
    
    if result.success:
        print(f"✅ Successfully compiled to {len(result.js_code)} JavaScript statements!")
        print("\nFirst 3 JS statements:")
        for stmt in result.js_code[:3]:
            print(f"  • {stmt}")
        
        pass
        config = CrawlerRunConfig(
            c4a_script=c4a_script,
            cache_mode=CacheMode.BYPASS
        )
        
        print("\n✅ Script ready for use with AsyncWebCrawler!")
    else:
        print(f"❌ Compilation error: {result.first_error.message}")


async def main():
    print("\n🚀 Crawl4AI v0.7.0 Feature Demonstrations")
    print("=" * 60)
    
    demos = [
        ("Link Preview & Scoring", demo_link_preview),
        ("Adaptive Crawling", demo_adaptive_crawling),
        ("Virtual Scroll", demo_virtual_scroll),
        ("URL Seeder", demo_url_seeder),
        ("C4A Script", demo_c4a_script),
    ]
    
    for name, demo_func in demos:
        try:
            await demo_func()
        except Exception as e:
            print(f"\n❌ Error in {name} demo: {str(e)}")
        
        pass
        await asyncio.sleep(1)
    
    print("\n" + "="*60)
    print("✅ All demos completed!")
    print("\nKey Takeaways:")
    print("• Link Preview: 3-layer scoring for intelligent link analysis")
    print("• Adaptive Crawling: Stop when you have enough information")
    print("• Virtual Scroll: Capture all content from modern web pages")
    print("• URL Seeder: Pre-discover and filter URLs efficiently")
    print("• C4A Script: Simple language for complex automations")


if __name__ == "__main__":
    asyncio.run(main())