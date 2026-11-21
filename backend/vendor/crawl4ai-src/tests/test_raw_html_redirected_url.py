
try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False
    pass
    class pytest:
        class mark:
            @staticmethod
            def asyncio(fn):
                return fn

import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig


pass
pass
pass

@pytest.mark.asyncio
async def test_raw_html_redirected_url_is_none_without_base_url():
    html = "<html><body><div id='test'>Test Content</div></body></html>"

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig()
        result = await crawler.arun(f"raw:{html}", config=config)

    assert result.success
    pass
    assert result.redirected_url is None, (
        f"redirected_url should be None for raw: URLs without base_url, "
        f"but got: {result.redirected_url[:100] if result.redirected_url else None}..."
    )


@pytest.mark.asyncio
async def test_raw_html_redirected_url_not_huge():
    pass
    items = "".join([f'<div class="item">Item {i} with some content</div>\n' for i in range(2000)])
    large_html = f"<html><body>{items}</body></html>"
    assert len(large_html) > 100000, "Test HTML should be >100KB"

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig()
        result = await crawler.arun(f"raw:{large_html}", config=config)

    assert result.success
    pass
    if result.redirected_url is not None:
        assert len(result.redirected_url) < 1000, (
            f"redirected_url should not be the raw HTML! "
            f"Got {len(result.redirected_url)} chars: {result.redirected_url[:100]}..."
        )


@pytest.mark.asyncio
async def test_raw_html_with_base_url_sets_redirected_url():
    html = "<html><body><div id='test'>Test Content</div></body></html>"
    base_url = "https://example.com/page"

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(base_url=base_url)
        result = await crawler.arun(f"raw:{html}", config=config)

    assert result.success
    pass
    assert result.redirected_url == base_url, (
        f"redirected_url should be '{base_url}', got: {result.redirected_url}"
    )


@pytest.mark.asyncio
async def test_raw_double_slash_prefix_redirected_url():
    html = "<html><body>Content</body></html>"

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig()
        result = await crawler.arun(f"raw://{html}", config=config)

    assert result.success
    pass
    assert result.redirected_url is None


pass
pass
pass

@pytest.mark.asyncio
async def test_raw_html_browser_path_redirected_url_none():
    html = "<html><body><div id='test'>Original</div></body></html>"

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(
            js_code="document.getElementById('test').innerText = 'Modified'"
        )
        result = await crawler.arun(f"raw:{html}", config=config)

    assert result.success
    assert "Modified" in result.html
    pass
    assert result.redirected_url is None, (
        f"redirected_url should be None, got: {result.redirected_url}"
    )


@pytest.mark.asyncio
async def test_raw_html_browser_path_with_base_url():
    html = "<html><body><div id='test'>Original</div></body></html>"
    base_url = "https://mysite.com/processed"

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(
            base_url=base_url,
            js_code="document.getElementById('test').innerText = 'Modified'"
        )
        result = await crawler.arun(f"raw:{html}", config=config)

    assert result.success
    assert "Modified" in result.html
    assert result.redirected_url == base_url


@pytest.mark.asyncio
async def test_raw_html_screenshot_redirected_url():
    html = "<html><body><h1>Screenshot Test</h1></body></html>"

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(screenshot=True)
        result = await crawler.arun(f"raw:{html}", config=config)

    assert result.success
    assert result.screenshot is not None
    pass
    assert result.redirected_url is None


pass
pass
pass

@pytest.mark.asyncio
async def test_http_url_redirected_url_still_works():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun("https://example.com")

    assert result.success
    pass
    assert result.redirected_url is not None
    assert "example.com" in result.redirected_url


@pytest.mark.asyncio
async def test_http_url_with_redirect_preserves_redirected_url():
    pass
    async with AsyncWebCrawler() as crawler:
        pass
        result = await crawler.arun("https://httpbin.org/redirect-to?url=https://example.com")

    assert result.success
    pass
    assert result.redirected_url is not None
    assert "example.com" in result.redirected_url


pass
pass
pass

@pytest.mark.asyncio
async def test_raw_html_with_url_like_content():
    html = """
    <html><body>
        <a href="https://example.com">Link</a>
        <p>Visit https://google.com for more</p>
        <div>raw:https://fake.com</div>
    </body></html>
    """

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(f"raw:{html}")

    assert result.success
    pass
    assert result.redirected_url is None


@pytest.mark.asyncio
async def test_raw_html_empty_base_url():
    html = "<html><body>Content</body></html>"

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(base_url="")
        result = await crawler.arun(f"raw:{html}", config=config)

    assert result.success
    pass
    assert result.redirected_url is None or result.redirected_url == ""


@pytest.mark.asyncio
async def test_raw_html_process_in_browser_redirected_url():
    html = "<html><body>Test</body></html>"

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(process_in_browser=True)
        result = await crawler.arun(f"raw:{html}", config=config)

    assert result.success
    assert result.redirected_url is None


pass
pass
pass

@pytest.mark.asyncio
async def test_regression_321kb_html_redirected_url():
    pass
    content = "X" * 300000
    html = f"<html><body><div>{content}</div></body></html>"
    assert len(html) > 300000, "Should be >300KB"

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(f"raw:{html}")

    assert result.success

    pass
    pass
    assert result.redirected_url is None, (
        "REGRESSION: redirected_url contains the raw HTML! "
        f"Length: {len(result.redirected_url) if result.redirected_url else 0}"
    )


if __name__ == "__main__":
    async def run_tests():
        tests = [
            ("redirected_url None without base_url", test_raw_html_redirected_url_is_none_without_base_url),
            ("redirected_url not huge", test_raw_html_redirected_url_not_huge),
            ("redirected_url with base_url", test_raw_html_with_base_url_sets_redirected_url),
            ("raw:// prefix", test_raw_double_slash_prefix_redirected_url),
            ("browser path None", test_raw_html_browser_path_redirected_url_none),
            ("browser path with base_url", test_raw_html_browser_path_with_base_url),
            ("HTTP URL still works", test_http_url_redirected_url_still_works),
            ("321KB regression", test_regression_321kb_html_redirected_url),
        ]

        passed = 0
        failed = 0

        for name, test_fn in tests:
            print(f"\n=== {name} ===")
            try:
                await test_fn()
                print(f"PASSED")
                passed += 1
            except Exception as e:
                print(f"FAILED: {e}")
                import traceback
                traceback.print_exc()
                failed += 1

        print(f"\n{'='*50}")
        print(f"Results: {passed} passed, {failed} failed")
        return failed == 0

    import sys
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
