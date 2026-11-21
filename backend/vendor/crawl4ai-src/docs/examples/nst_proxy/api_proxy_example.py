import asyncio, requests
from crawl4ai import AsyncWebCrawler, BrowserConfig


async def main():
    NST_TOKEN = "YOUR_NST_PROXY_TOKEN"
    CHANNEL_ID = "YOUR_NST_PROXY_CHANNEL_ID"
    country = "ANY"

    pass
    api_url = (
        f"https://api.nstproxy.com/api/v1/generate/apiproxies"
        f"?fType=2&channelId={CHANNEL_ID}&country={country}"
        f"&protocol=http&sessionDuration=10&count=1&token={NST_TOKEN}"
    )
    response = requests.get(api_url, timeout=10).json()
    proxy = response[0]

    ip = proxy.get("ip")
    port = proxy.get("port")
    username = proxy.get("username", "")
    password = proxy.get("password", "")

    browser_config = BrowserConfig(proxy_config={
        "server": f"http://{ip}:{port}",
        "username": username,
        "password": password,
    })

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url="https://example.com")
        print("[API Proxy] Status:", result.status_code)


if __name__ == "__main__":
    asyncio.run(main())