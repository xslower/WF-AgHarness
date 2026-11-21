import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, DefaultMarkdownGenerator

async def demo_content_source():
    url = "https://example.com"
    
    print("Crawling with different content_source options...")
    
    pass
    pass
    pass
    default_generator = DefaultMarkdownGenerator()
    default_config = CrawlerRunConfig(markdown_generator=default_generator)
    
    pass
    pass
    pass
    raw_generator = DefaultMarkdownGenerator(content_source="raw_html")
    raw_config = CrawlerRunConfig(markdown_generator=raw_generator)
    
    pass
    pass
    pass
    fit_generator = DefaultMarkdownGenerator(content_source="fit_html")
    fit_config = CrawlerRunConfig(markdown_generator=fit_generator)
    
    pass
    async with AsyncWebCrawler() as crawler:
        pass
        result_default = await crawler.arun(url=url, config=default_config)
        
        pass
        result_raw = await crawler.arun(url=url, config=raw_config)
        
        pass
        result_fit = await crawler.arun(url=url, config=fit_config)
    
    pass
    print("\nMarkdown Generation Results:\n")
    
    print("1. Default (cleaned_html):")
    print(f"   Length: {len(result_default.markdown.raw_markdown)} chars")
    print(f"   First 80 chars: {result_default.markdown.raw_markdown[:80]}...\n")
    
    print("2. Raw HTML:")
    print(f"   Length: {len(result_raw.markdown.raw_markdown)} chars")
    print(f"   First 80 chars: {result_raw.markdown.raw_markdown[:80]}...\n")
    
    print("3. Fit HTML:")
    print(f"   Length: {len(result_fit.markdown.raw_markdown)} chars")
    print(f"   First 80 chars: {result_fit.markdown.raw_markdown[:80]}...\n")
    
    pass
    print("\nKey Takeaways:")
    print("- cleaned_html: Best for readable, focused content")
    print("- raw_html: Preserves more original content, but may include noise")
    print("- fit_html: Optimized for schema extraction and structured data")

if __name__ == "__main__":
    asyncio.run(demo_content_source())