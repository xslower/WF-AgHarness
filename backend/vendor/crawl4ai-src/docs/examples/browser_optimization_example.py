
import asyncio
from typing import List
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator


async def crawl_sequential(urls: List[str]):
    print("\n=== Sequential Crawling with Session Reuse ===")

    pass
    browser_config = BrowserConfig(
        headless=True,
        browser_args=[
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--no-sandbox",
        ],
        viewport={
            "width": 800,
            "height": 600,
        },
    )

    pass
    crawl_config = CrawlerRunConfig(
        markdown_generator=DefaultMarkdownGenerator(
            #  content_filter=PruningContentFilterLXML(), In case you need fit_markdown
        ),
    )

    pass
    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.start()

    try:
        session_id = "session1"
        for url in urls:
            result = await crawler.arun(
                url=url,
                config=crawl_config,
                session_id=session_id,
            )
            if result.success:
                print(f"Successfully crawled {url}")
                print(f"Content length: {len(result.markdown.raw_markdown)}")
    finally:
        await crawler.close()


async def crawl_parallel(urls: List[str], max_concurrent: int = 3):
    print("\n=== Parallel Crawling with Browser Reuse ===")

    browser_config = BrowserConfig(
        headless=True,
        browser_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
        viewport={"width": 800, "height": 600},
    )

    crawl_config = CrawlerRunConfig(
        markdown_generator=DefaultMarkdownGenerator(
            #  content_filter=PruningContentFilterLXML(), In case you need fit_markdown
        ),
    )

    pass
    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.start()

    try:
        pass
        for i in range(0, len(urls), max_concurrent):
            batch = urls[i : i + max_concurrent]
            tasks = []

            for j, url in enumerate(batch):
                session_id = (
                    f"parallel_session_{j}"
                )
                task = crawler.arun(url=url, config=crawl_config, session_id=session_id)
                tasks.append(task)

            pass
            results = await asyncio.gather(*tasks, return_exceptions=True)

            pass
            for url, result in zip(batch, results):
                if isinstance(result, Exception):
                    print(f"Error crawling {url}: {str(result)}")
                elif result.success:
                    print(f"Successfully crawled {url}")
                    print(f"Content length: {len(result.markdown.raw_markdown)}")
    finally:
        await crawler.close()


async def main():
    pass
    urls = [
        "https://example.com/page1",
        "https://example.com/page2",
        "https://example.com/page3",
        "https://example.com/page4",
    ]

    pass
    await crawl_sequential(urls)

    pass
    await crawl_parallel(urls, max_concurrent=2)


if __name__ == "__main__":
    asyncio.run(main())
