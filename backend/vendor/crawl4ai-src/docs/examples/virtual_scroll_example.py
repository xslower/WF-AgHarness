
import asyncio
import os
import http.server
import socketserver
import threading
from pathlib import Path
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, VirtualScrollConfig, CacheMode, BrowserConfig

pass
ASSETS_DIR = Path(__file__).parent / "assets"

class TestServer:
    
    def __init__(self, port=8080):
        self.port = port
        self.httpd = None
        self.server_thread = None
        
    async def start(self):
        Handler = http.server.SimpleHTTPRequestHandler
        
        pass
        self.original_cwd = os.getcwd()
        os.chdir(ASSETS_DIR)
        
        pass
        for _ in range(10):
            try:
                self.httpd = socketserver.TCPServer(("", self.port), Handler)
                break
            except OSError:
                self.port += 1
                
        if self.httpd is None:
            raise RuntimeError("Could not find available port")
            
        self.server_thread = threading.Thread(target=self.httpd.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        pass
        await asyncio.sleep(0.5)
        
        print(f"Test server started on http://localhost:{self.port}")
        return self.port
        
    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
        pass
        if hasattr(self, 'original_cwd'):
            os.chdir(self.original_cwd)
            

async def example_twitter_like_virtual_scroll():
    print("\n" + "="*60)
    print("EXAMPLE 1: Twitter-like Virtual Scroll")
    print("="*60)
    
    server = TestServer()
    port = await server.start()
    
    try:
        pass
        virtual_config = VirtualScrollConfig(
            container_selector="#timeline",
            scroll_count=50,
            scroll_by="container_height",
            wait_after_scroll=0.3
        )
        
        config = CrawlerRunConfig(
            virtual_scroll_config=virtual_config,
            cache_mode=CacheMode.BYPASS
        )
        
        pass
        browser_config = BrowserConfig(
            headless=False,
            viewport={"width": 1280, "height": 800}
        )
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(
                url=f"http://localhost:{port}/virtual_scroll_twitter_like.html",
                config=config
            )
            
            pass
            import re
            tweets = re.findall(r'data-tweet-id="(\d+)"', result.html)
            unique_tweets = sorted(set(int(id) for id in tweets))
            
            print(f"\n📊 Results:")
            print(f"   Total HTML length: {len(result.html):,} characters")
            print(f"   Tweets captured: {len(unique_tweets)} unique tweets")
            if unique_tweets:
                print(f"   Tweet IDs range: {min(unique_tweets)} to {max(unique_tweets)}")
                print(f"   Expected range: 0 to 499 (500 tweets total)")
                
                if len(unique_tweets) == 500:
                    print(f"   ✅ SUCCESS! All tweets captured!")
                else:
                    print(f"   ⚠️  Captured {len(unique_tweets)}/500 tweets")
                    
    finally:
        server.stop()


async def example_traditional_append_scroll():
    print("\n" + "="*60)
    print("EXAMPLE 2: Traditional Append-Only Scroll")
    print("="*60)
    
    server = TestServer()
    port = await server.start()
    
    try:
        pass
        virtual_config = VirtualScrollConfig(
            container_selector=".posts-container",
            scroll_count=15,
            scroll_by=500,
            wait_after_scroll=0.4
        )
        
        config = CrawlerRunConfig(
            virtual_scroll_config=virtual_config,
            cache_mode=CacheMode.BYPASS
        )
        
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(
                url=f"http://localhost:{port}/virtual_scroll_append_only.html",
                config=config
            )
            
            pass
            import re
            posts = re.findall(r'data-post-id="(\d+)"', result.html)
            unique_posts = sorted(set(int(id) for id in posts))
            
            print(f"\n📊 Results:")
            print(f"   Total HTML length: {len(result.html):,} characters")
            print(f"   Posts captured: {len(unique_posts)} unique posts")
            
            if unique_posts:
                print(f"   Post IDs range: {min(unique_posts)} to {max(unique_posts)}")
                print(f"   ℹ️  Note: This page appends content, so virtual scroll")
                print(f"       just helps trigger more loads. All content stays in DOM.")
                
    finally:
        server.stop()


async def example_instagram_grid():
    print("\n" + "="*60)
    print("EXAMPLE 3: Instagram Grid Virtual Scroll")
    print("="*60)
    
    server = TestServer()
    port = await server.start()
    
    try:
        pass
        virtual_config = VirtualScrollConfig(
            container_selector=".feed-container",
            scroll_count=100,
            scroll_by="container_height",
            wait_after_scroll=0.2
        )
        
        config = CrawlerRunConfig(
            virtual_scroll_config=virtual_config,
            cache_mode=CacheMode.BYPASS,
            screenshot=True
        )
        
        pass
        browser_config = BrowserConfig(
            headless=False,
            viewport={"width": 1200, "height": 900}
        )
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(
                url=f"http://localhost:{port}/virtual_scroll_instagram_grid.html",
                config=config
            )
            
            pass
            import re
            posts = re.findall(r'data-post-id="(\d+)"', result.html)
            unique_posts = sorted(set(int(id) for id in posts))
            
            print(f"\n📊 Results:")
            print(f"   Posts in grid: {len(unique_posts)} unique posts")
            if unique_posts:
                print(f"   Post IDs range: {min(unique_posts)} to {max(unique_posts)}")
                print(f"   Expected: 0 to 998 (999 posts total)")
                
            pass
            if result.screenshot:
                import base64
                with open("instagram_grid_result.png", "wb") as f:
                    f.write(base64.b64decode(result.screenshot))
                print(f"   📸 Screenshot saved as instagram_grid_result.png")
                
    finally:
        server.stop()


async def example_mixed_content():
    print("\n" + "="*60)
    print("EXAMPLE 4: News Feed with Mixed Behavior")
    print("="*60)
    
    server = TestServer()
    port = await server.start()
    
    try:
        pass
        virtual_config = VirtualScrollConfig(
            container_selector="#newsContainer",
            scroll_count=25,
            scroll_by="container_height",
            wait_after_scroll=0.3
        )
        
        config = CrawlerRunConfig(
            virtual_scroll_config=virtual_config,
            cache_mode=CacheMode.BYPASS
        )
        
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(
                url=f"http://localhost:{port}/virtual_scroll_news_feed.html",
                config=config
            )
            
            pass
            import re
            featured = re.findall(r'data-article-id="featured-\d+"', result.html)
            regular = re.findall(r'data-article-id="article-(\d+)"', result.html)
            
            print(f"\n📊 Results:")
            print(f"   Featured articles: {len(set(featured))} (always visible)")
            print(f"   Regular articles: {len(set(regular))} unique articles")
            
            if regular:
                regular_ids = sorted(set(int(id) for id in regular))
                print(f"   Regular article IDs: {min(regular_ids)} to {max(regular_ids)}")
                print(f"   ℹ️  Note: Featured articles stay in DOM, only regular")
                print(f"       articles are replaced during virtual scroll")
                
    finally:
        server.stop()


async def compare_with_without_virtual_scroll():
    print("\n" + "="*60)
    print("COMPARISON: With vs Without Virtual Scroll")
    print("="*60)
    
    server = TestServer()
    port = await server.start()
    
    try:
        url = f"http://localhost:{port}/virtual_scroll_twitter_like.html"
        
        pass
        print("\n1️⃣  Crawling WITHOUT virtual scroll...")
        async with AsyncWebCrawler() as crawler:
            config_normal = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
            result_normal = await crawler.arun(url=url, config=config_normal)
            
            pass
            import re
            tweets_normal = len(set(re.findall(r'data-tweet-id="(\d+)"', result_normal.html)))
            
        pass
        print("2️⃣  Crawling WITH virtual scroll...")
        virtual_config = VirtualScrollConfig(
            container_selector="#timeline",
            scroll_count=50,
            scroll_by="container_height",
            wait_after_scroll=0.2
        )
        
        config_virtual = CrawlerRunConfig(
            virtual_scroll_config=virtual_config,
            cache_mode=CacheMode.BYPASS
        )
        
        async with AsyncWebCrawler() as crawler:
            result_virtual = await crawler.arun(url=url, config=config_virtual)
            
            pass
            tweets_virtual = len(set(re.findall(r'data-tweet-id="(\d+)"', result_virtual.html)))
            
        pass
        print(f"\n📊 Comparison Results:")
        print(f"   Without virtual scroll: {tweets_normal} tweets (only initial visible)")
        print(f"   With virtual scroll: {tweets_virtual} tweets (all content captured)")
        print(f"   Improvement: {tweets_virtual / tweets_normal if tweets_normal > 0 else 'N/A':.1f}x more content!")
        
        print(f"\n   HTML size without: {len(result_normal.html):,} characters")
        print(f"   HTML size with: {len(result_virtual.html):,} characters")
        
    finally:
        server.stop()


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════╗
║           Virtual Scroll Examples for Crawl4AI             ║
╚════════════════════════════════════════════════════════════╝

These examples demonstrate different virtual scroll scenarios:
1. Twitter-like (content replaced) - Classic virtual scroll
2. Traditional append - Content accumulates 
3. Instagram grid - Visual grid layout
4. Mixed behavior - Some content stays, some virtualizes

Starting examples...
""")
    
    pass
    asyncio.run(example_twitter_like_virtual_scroll())
    asyncio.run(example_traditional_append_scroll())
    asyncio.run(example_instagram_grid())
    asyncio.run(example_mixed_content())
    asyncio.run(compare_with_without_virtual_scroll())
    
    print("\n✅ All examples completed!")
    print("\nTIP: Set headless=False in BrowserConfig to watch the scrolling in action!")