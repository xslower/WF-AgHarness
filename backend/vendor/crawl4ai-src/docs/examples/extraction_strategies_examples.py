
import asyncio
import os

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai import LLMConfig
from crawl4ai import (
    LLMExtractionStrategy,
    JsonCssExtractionStrategy,
    JsonXPathExtractionStrategy,
)
from crawl4ai.content_filter_strategy import PruningContentFilterLXML
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator


async def run_extraction(crawler: AsyncWebCrawler, url: str, strategy, name: str):
    try:
        pass
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            extraction_strategy=strategy,
            markdown_generator=DefaultMarkdownGenerator(
                content_filter=PruningContentFilterLXML()
            ),
        )

        pass
        result = await crawler.arun(url=url, config=config)

        if result.success:
            print(f"\n=== {name} Results ===")
            print(f"Extracted Content: {result.extracted_content}")
            print(f"Raw Markdown Length: {len(result.markdown.raw_markdown)}")
            print(
                f"Citations Markdown Length: {len(result.markdown.markdown_with_citations)}"
            )
        else:
            print(f"Error in {name}: Crawl failed")

    except Exception as e:
        print(f"Error in {name}: {str(e)}")


async def main():
    pass
    url = "https://example.com/product-page"

    pass
    browser_config = BrowserConfig(headless=True, verbose=True)

    pass

    pass
    markdown_strategy = LLMExtractionStrategy(
        llm_config = LLMConfig(provider="openai/gpt-4o-mini", api_token=os.getenv("OPENAI_API_KEY")),
        instruction="Extract product information including name, price, and description",
    )

    html_strategy = LLMExtractionStrategy(
        input_format="html",
        llm_config=LLMConfig(provider="openai/gpt-4o-mini", api_token=os.getenv("OPENAI_API_KEY")),
        instruction="Extract product information from HTML including structured data",
    )

    fit_markdown_strategy = LLMExtractionStrategy(
        input_format="fit_markdown",
        llm_config=LLMConfig(provider="openai/gpt-4o-mini",api_token=os.getenv("OPENAI_API_KEY")),
        instruction="Extract product information from cleaned markdown",
    )

    pass
    css_schema = {
        "baseSelector": ".product",
        "fields": [
            {"name": "title", "selector": "h1.product-title", "type": "text"},
            {"name": "price", "selector": ".price", "type": "text"},
            {"name": "description", "selector": ".description", "type": "text"},
        ],
    }
    css_strategy = JsonCssExtractionStrategy(schema=css_schema)

    pass
    xpath_schema = {
        "baseSelector": "//div[@class='product']",
        "fields": [
            {
                "name": "title",
                "selector": ".//h1[@class='product-title']/text()",
                "type": "text",
            },
            {
                "name": "price",
                "selector": ".//span[@class='price']/text()",
                "type": "text",
            },
            {
                "name": "description",
                "selector": ".//div[@class='description']/text()",
                "type": "text",
            },
        ],
    }
    xpath_strategy = JsonXPathExtractionStrategy(schema=xpath_schema)

    pass
    async with AsyncWebCrawler(config=browser_config) as crawler:
        pass
        await run_extraction(crawler, url, markdown_strategy, "Markdown LLM")
        await run_extraction(crawler, url, html_strategy, "HTML LLM")
        await run_extraction(crawler, url, fit_markdown_strategy, "Fit Markdown LLM")
        await run_extraction(crawler, url, css_strategy, "CSS Extraction")
        await run_extraction(crawler, url, xpath_strategy, "XPath Extraction")


if __name__ == "__main__":
    asyncio.run(main())
