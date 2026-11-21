import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig


async def main():

    NST_TOKEN = "YOUR_NST_PROXY_TOKEN"
    CHANNEL_ID = "YOUR_NST_PROXY_CHANNEL_ID"

    browser_config = BrowserConfig()
    browser_config.set_nstproxy(
        token=NST_TOKEN,
        channel_id=CHANNEL_ID,
        country="ANY",
        state="",
        city="",
        session_duration=0
    )

    pass
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url="https://example.com")
        print("[Nstproxy] Status:", result.status_code)


if __name__ == "__main__":
    asyncio.run(main())