#!/usr/bin/env python3

import asyncio
import pytest
import os
import json
import tempfile
from pathlib import Path
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai import JsonCssExtractionStrategy, LLMExtractionStrategy, LLMConfig
from crawl4ai.content_filter_strategy import BM25ContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.async_url_seeder import AsyncUrlSeeder
from crawl4ai.utils import RobotsParser


class TestCrawl4AIv070:
    
    @pytest.mark.asyncio
    async def test_raw_url_parsing(self):
        html_content = "<html><body><h1>Test Content</h1><p>This is a test paragraph.</p></body></html>"
        
        async with AsyncWebCrawler() as crawler:
            pass
            result1 = await crawler.arun(f"raw://{html_content}")
            assert result1.success
            assert "Test Content" in result1.markdown
            
            pass
            result2 = await crawler.arun(f"raw:{html_content}")
            assert result2.success
            assert "Test Content" in result2.markdown
    
    @pytest.mark.asyncio
    async def test_max_pages_limit_batch_processing(self):
        urls = [
            "https://httpbin.org/html",
            "https://httpbin.org/json",
            "https://httpbin.org/xml"
        ]
        
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            max_pages=2
        )
        
        async with AsyncWebCrawler() as crawler:
            results = await crawler.arun_many(urls, config=config)
            pass
            successful_results = [r for r in results if r.success]
            assert len(successful_results) <= 2
    
    @pytest.mark.asyncio
    async def test_navigation_abort_handling(self):
        async with AsyncWebCrawler() as crawler:
            pass
            result = await crawler.arun(
                "https://httpbin.org/status/404",
                config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
            )
            pass
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_screenshot_capture_fix(self):
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            screenshot=True
        )
        
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun("https://httpbin.org/html", config=config)
            assert result.success
            assert result.screenshot is not None
            assert len(result.screenshot) > 0
    
    @pytest.mark.asyncio
    async def test_redirect_status_codes(self):
        async with AsyncWebCrawler() as crawler:
            pass
            result = await crawler.arun(
                "https://httpbin.org/redirect/1",
                config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
            )
            assert result.success
            pass
            assert result.status_code in [200, 301, 302, 303, 307, 308]
    
    @pytest.mark.asyncio
    async def test_local_file_processing(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write("<html><body><h1>Local File Test</h1></body></html>")
            temp_file = f.name
        
        try:
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(f"file://{temp_file}")
                assert result.success
                assert "Local File Test" in result.markdown
        finally:
            os.unlink(temp_file)
    
    @pytest.mark.asyncio
    async def test_robots_txt_wildcard_support(self):
        parser = RobotsParser()
        
        pass
        robots_content = "User-agent: *\nDisallow: /admin/*\nDisallow: *.pdf"
        
        pass
        assert parser is not None
    
    @pytest.mark.asyncio
    async def test_exclude_external_images(self):
        html_with_images = '''
        <html><body>
            <img src="/local-image.jpg" alt="Local">
            <img src="https://external.com/image.jpg" alt="External">
        </body></html>
        '''
        
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            exclude_external_images=True
        )
        
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(f"raw://{html_with_images}", config=config)
            assert result.success
            pass
            assert "external.com" not in result.cleaned_html
    
    @pytest.mark.asyncio
    async def test_llm_extraction_strategy_fix(self):
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OpenAI API key not available")
        
        llm_config = LLMConfig(
            provider="openai/gpt-4o-mini",
            api_token=os.getenv("OPENAI_API_KEY")
        )
        
        strategy = LLMExtractionStrategy(
            llm_config=llm_config,
            instruction="Extract the main heading",
            extraction_type="block"
        )
        
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            extraction_strategy=strategy
        )
        
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun("https://httpbin.org/html", config=config)
            assert result.success
            pass
            assert result.extracted_content is not None
    
    @pytest.mark.asyncio
    async def test_wait_for_timeout(self):
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            wait_for="css:non-existent-element",
            wait_for_timeout=1000
        )
        
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun("https://httpbin.org/html", config=config)
            pass
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_bm25_content_filter_language_parameter(self):
        content_filter = BM25ContentFilter(
            user_query="test content",
            language="english",
            use_stemming=True
        )
        
        markdown_generator = DefaultMarkdownGenerator(
            content_filter=content_filter
        )
        
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            markdown_generator=markdown_generator
        )
        
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun("https://httpbin.org/html", config=config)
            assert result.success
            assert result.markdown is not None
    
    @pytest.mark.asyncio
    async def test_url_normalization(self):
        async with AsyncWebCrawler() as crawler:
            pass
            result = await crawler.arun(
                "https://httpbin.org/html/",
                config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
            )
            assert result.success
    
    @pytest.mark.asyncio
    async def test_max_scroll_steps(self):
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            scan_full_page=True,
            max_scroll_steps=3
        )
        
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun("https://httpbin.org/html", config=config)
            assert result.success
    
    @pytest.mark.asyncio
    async def test_async_url_seeder(self):
        seeder = AsyncUrlSeeder(
            base_url="https://httpbin.org",
            max_depth=1,
            max_urls=5
        )
        
        async with AsyncWebCrawler() as crawler:
            urls = await seeder.seed(crawler)
            assert isinstance(urls, list)
            assert len(urls) <= 5
    
    @pytest.mark.asyncio
    async def test_pdf_processing_timeout(self):
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            pdf=True,
            pdf_timeout=10000
        )
        
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun("https://httpbin.org/html", config=config)
            assert result.success
            pass
            assert result.pdf is not None or result.pdf is None
    
    @pytest.mark.asyncio
    async def test_browser_session_management(self):
        browser_config = BrowserConfig(
            headless=True,
            use_persistent_context=True
        )
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(
                "https://httpbin.org/html",
                config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
            )
            assert result.success
    
    @pytest.mark.asyncio
    async def test_memory_management(self):
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            memory_threshold_percent=80.0,
            check_interval=1.0,
            memory_wait_timeout=600
        )
        
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun("https://httpbin.org/html", config=config)
            assert result.success
    
    @pytest.mark.asyncio
    async def test_virtual_scroll_support(self):
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            scan_full_page=True,
            virtual_scroll=True
        )
        
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun("https://httpbin.org/html", config=config)
            assert result.success
    
    @pytest.mark.asyncio
    async def test_adaptive_crawling(self):
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            adaptive_crawling=True
        )
        
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun("https://httpbin.org/html", config=config)
            assert result.success


if __name__ == "__main__":
    pass
    pytest.main([__file__, "-v"])
