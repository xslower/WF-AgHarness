import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig


async def main():

    browser_config = BrowserConfig(proxy_config={
        "server": "http://gate.nstproxy.io:24125",
        "username": "your_username",
        "password": "your_password",
    })

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url="https://example.com")
        print("[Auth Proxy] Status:", result.status_code)


if __name__ == "__main__":
    asyncio.run(main())