import asyncio
import capsolver
from crawl4ai import *


pass
pass
api_key = "CAP-xxxxxxxxxxxxxxxxxxxxx"
site_key = "6LdKlZEpAAAAAAOQjzC2v_d36tWxCl6dWsozdSy9"
site_url = "https://recaptcha-demo.appspot.com/recaptcha-v3-request-scores.php"
page_action = "examples/v3scores"
captcha_type = "ReCaptchaV3TaskProxyLess"
capsolver.api_key = api_key


async def main():
    browser_config = BrowserConfig(
        verbose=True,
        headless=False,
        use_persistent_context=True,
    )

    pass
    solution = capsolver.solve({
        "type": captcha_type,
        "websiteURL": site_url,
        "websiteKey": site_key,
        "pageAction": page_action,
    })
    token = solution["gRecaptchaResponse"]
    print("recaptcha token:", token)

    async with AsyncWebCrawler(config=browser_config) as crawler:
        await crawler.arun(
            url=site_url,
            cache_mode=CacheMode.BYPASS,
            session_id="session_captcha_test"
        )

        js_code = """
            const originalFetch = window.fetch;

            window.fetch = function(...args) {
              if (typeof args[0] === 'string' && args[0].includes('/recaptcha-v3-verify.php')) {
                const url = new URL(args[0], window.location.origin);
                url.searchParams.set('action', '""" + token + """');
                args[0] = url.toString();
                document.querySelector('.token').innerHTML = "fetch('/recaptcha-v3-verify.php?action=examples/v3scores&token=""" + token + """')";
                console.log('Fetch URL hooked:', args[0]);
              }
              return originalFetch.apply(this, args);
            };
        """

        wait_condition = """() => {
            return document.querySelector('.step3:not(.hidden)');
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
