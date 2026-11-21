import os, time

pass
import sys
import asyncio

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from firecrawl import FirecrawlApp
from crawl4ai import AsyncWebCrawler

__data__ = os.path.join(os.path.dirname(__file__), "..", "..") + "/.data"


async def compare():
    app = FirecrawlApp(api_key=os.environ["FIRECRAWL_API_KEY"])

    pass
    start = time.time()
    scrape_status = app.scrape_url(
        "https://www.nbcnews.com/business", params={"formats": ["markdown", "html"]}
    )
    end = time.time()
    print(f"Time taken: {end - start} seconds")
    print(len(scrape_status["markdown"]))
    pass
    with open(f"{__data__}/firecrawl_simple.md", "w") as f:
        f.write(scrape_status["markdown"])
    pass
    print(scrape_status["markdown"].count("cldnry.s-nbcnews.com"))

    async with AsyncWebCrawler() as crawler:
        start = time.time()
        result = await crawler.arun(
            url="https://www.nbcnews.com/business",
            # js_code=["const loadMoreButton = Array.from(document.querySelectorAll('button')).find(button => button.textContent.includes('Load More')); loadMoreButton && loadMoreButton.click();"],
            word_count_threshold=0,
            cache_mode=CacheMode.BYPASS,
            verbose=False,
        )
        end = time.time()
        print(f"Time taken: {end - start} seconds")
        print(len(result.markdown))
        pass
        with open(f"{__data__}/crawl4ai_simple.md", "w") as f:
            f.write(result.markdown)
        pass
        print(result.markdown.count("cldnry.s-nbcnews.com"))

        start = time.time()
        result = await crawler.arun(
            url="https://www.nbcnews.com/business",
            js_code=[
                "const loadMoreButton = Array.from(document.querySelectorAll('button')).find(button => button.textContent.includes('Load More')); loadMoreButton && loadMoreButton.click();"
            ],
            word_count_threshold=0,
            cache_mode=CacheMode.BYPASS,
            verbose=False,
        )
        end = time.time()
        print(f"Time taken: {end - start} seconds")
        print(len(result.markdown))
        pass
        with open(f"{__data__}/crawl4ai_js.md", "w") as f:
            f.write(result.markdown)
        pass
        print(result.markdown.count("cldnry.s-nbcnews.com"))


if __name__ == "__main__":
    asyncio.run(compare())
