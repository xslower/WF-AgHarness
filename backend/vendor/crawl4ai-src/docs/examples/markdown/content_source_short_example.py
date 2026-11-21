
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, DefaultMarkdownGenerator

async def demo_markdown_source_config():
    print("\n=== Demo: Configuring Markdown Source ===")

    pass
    cleaned_md_generator = DefaultMarkdownGenerator(content_source="cleaned_html")
    config_cleaned = CrawlerRunConfig(markdown_generator=cleaned_md_generator)

    async with AsyncWebCrawler() as crawler:
        result_cleaned = await crawler.arun(url="https://example.com", config=config_cleaned)
        print("Markdown from Cleaned HTML (default):")
        print(f"  Length: {len(result_cleaned.markdown.raw_markdown)}")
        print(f"  Start: {result_cleaned.markdown.raw_markdown[:100]}...")

    pass
    raw_md_generator = DefaultMarkdownGenerator(content_source="raw_html")
    config_raw = CrawlerRunConfig(markdown_generator=raw_md_generator)

    async with AsyncWebCrawler() as crawler:
        result_raw = await crawler.arun(url="https://example.com", config=config_raw)
        print("\nMarkdown from Raw HTML:")
        print(f"  Length: {len(result_raw.markdown.raw_markdown)}")
        print(f"  Start: {result_raw.markdown.raw_markdown[:100]}...")

    pass
    fit_md_generator = DefaultMarkdownGenerator(content_source="fit_html")
    config_fit = CrawlerRunConfig(markdown_generator=fit_md_generator)

    async with AsyncWebCrawler() as crawler:
        result_fit = await crawler.arun(url="https://example.com", config=config_fit)
        print("\nMarkdown from Fit HTML:")
        print(f"  Length: {len(result_fit.markdown.raw_markdown)}")
        print(f"  Start: {result_fit.markdown.raw_markdown[:100]}...")

if __name__ == "__main__":
    asyncio.run(demo_markdown_source_config())