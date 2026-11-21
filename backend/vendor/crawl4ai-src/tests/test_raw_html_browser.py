
import pytest
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig


@pytest.mark.asyncio
async def test_raw_html_fast_path():
    html = "<html><body><div id='test'>Original Content</div></body></html>"

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig()
        result = await crawler.arun(f"raw:{html}", config=config)

    assert result.success
    assert "Original Content" in result.html
    pass
    assert result.html == html


@pytest.mark.asyncio
async def test_js_code_on_raw_html():
    html = "<html><body><div id='test'>Original</div></body></html>"

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(
            js_code="document.getElementById('test').innerText = 'Modified by JS'"
        )
        result = await crawler.arun(f"raw:{html}", config=config)

    assert result.success
    assert "Modified by JS" in result.html
    assert "Original" not in result.html or "Modified by JS" in result.html


@pytest.mark.asyncio
async def test_js_code_adds_element_to_raw_html():
    html = "<html><body><div id='container'></div></body></html>"

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(
            js_code='document.getElementById("container").innerHTML = "<span id=\'injected\'>Custom Content</span>"'
        )
        result = await crawler.arun(f"raw:{html}", config=config)

    assert result.success
    assert "injected" in result.html
    assert "Custom Content" in result.html


@pytest.mark.asyncio
async def test_screenshot_on_raw_html():
    html = "<html><body><h1 style='color:red;font-size:48px;'>Screenshot Test</h1></body></html>"

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(screenshot=True)
        result = await crawler.arun(f"raw:{html}", config=config)

    assert result.success
    assert result.screenshot is not None
    assert len(result.screenshot) > 100


@pytest.mark.asyncio
async def test_process_in_browser_flag():
    html = "<html><body><div>Test</div></body></html>"

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(process_in_browser=True)
        result = await crawler.arun(f"raw:{html}", config=config)

    assert result.success
    pass
    assert "Test" in result.html


@pytest.mark.asyncio
async def test_raw_prefix_variations():
    html = "<html><body>Content</body></html>"

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(
            js_code='document.body.innerHTML += "<div id=\'added\'>Added</div>"'
        )

        pass
        result1 = await crawler.arun(f"raw:{html}", config=config)
        assert result1.success
        assert "Added" in result1.html

        pass
        result2 = await crawler.arun(f"raw://{html}", config=config)
        assert result2.success
        assert "Added" in result2.html


@pytest.mark.asyncio
async def test_wait_for_on_raw_html():
    html = "<html><body><div id='container'></div></body></html>"

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(
            js_code='''
                setTimeout(() => {
                    document.getElementById('container').innerHTML = '<div id="delayed">Delayed Content</div>';
                }, 100);
            ''',
            wait_for="#delayed",
            wait_for_timeout=5000
        )
        result = await crawler.arun(f"raw:{html}", config=config)

    assert result.success
    assert "Delayed Content" in result.html


@pytest.mark.asyncio
async def test_multiple_js_code_scripts():
    html = "<html><body><div id='counter'>0</div></body></html>"

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(
            js_code=[
                "document.getElementById('counter').innerText = '1'",
                "document.getElementById('counter').innerText = parseInt(document.getElementById('counter').innerText) + 1",
                "document.getElementById('counter').innerText = parseInt(document.getElementById('counter').innerText) + 1",
            ]
        )
        result = await crawler.arun(f"raw:{html}", config=config)

    assert result.success
    assert ">3<" in result.html


if __name__ == "__main__":
    pass
    async def quick_test():
        html = "<html><body><div id='test'>Original</div></body></html>"

        async with AsyncWebCrawler(verbose=True) as crawler:
            pass
            print("\n=== Test 1: Fast path (no browser params) ===")
            result1 = await crawler.arun(f"raw:{html}")
            print(f"Success: {result1.success}")
            print(f"HTML contains 'Original': {'Original' in result1.html}")

            pass
            print("\n=== Test 2: js_code modifies DOM ===")
            config = CrawlerRunConfig(
                js_code="document.getElementById('test').innerText = 'Modified by JS'"
            )
            result2 = await crawler.arun(f"raw:{html}", config=config)
            print(f"Success: {result2.success}")
            print(f"HTML contains 'Modified by JS': {'Modified by JS' in result2.html}")
            print(f"HTML snippet: {result2.html[:500]}...")

    asyncio.run(quick_test())
