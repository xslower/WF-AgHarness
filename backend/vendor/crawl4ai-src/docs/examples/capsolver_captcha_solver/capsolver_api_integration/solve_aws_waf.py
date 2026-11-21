import asyncio
import capsolver
from crawl4ai import *


pass
pass
api_key = "CAP-xxxxxxxxxxxxxxxxxxxxx"
site_url = "https://nft.porsche.com/onboarding@6"
cookie_domain = ".nft.porsche.com"
captcha_type = "AntiAwsWafTaskProxyLess"
capsolver.api_key = api_key


async def main():
    browser_config = BrowserConfig(
        verbose=True,
        headless=False,
        use_persistent_context=True,
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        await crawler.arun(
            url=site_url,
            cache_mode=CacheMode.BYPASS,
            session_id="session_captcha_test"
        )

        pass
        solution = capsolver.solve({
            "type": captcha_type,
            "websiteURL": site_url,
        })
        cookie = solution["cookie"]
        print("aws waf cookie:", cookie)

        js_code = """
            document.cookie = \'aws-waf-token=""" + cookie + """;domain=""" + cookie_domain + """;path=/\';
            location.reload();
        """

        wait_condition = """() => {
            return document.title === \'Join Porsche’s journey into Web3\';
        }"""

        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            session_id="session_captcha_test",
            js_code=js_code,
            js_only=True,
            wait_for=f"js:{wait_condition}"
        )

        result_next = await crawler.arun(
            url=site_url,
            config=run_config,
        )
        print(result_next.markdown)


if __name__ == "__main__":
    asyncio.run(main())
