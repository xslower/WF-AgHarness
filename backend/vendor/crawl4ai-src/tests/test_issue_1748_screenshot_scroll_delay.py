
import pytest
import asyncio
import base64
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch, call

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy


pass
pass
pass


def _make_tiny_jpeg() -> bytes:
    from PIL import Image

    img = Image.new("RGB", (10, 10), color="red")
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


TINY_JPEG = _make_tiny_jpeg()

pass
TALL_HTML = "<html><body>" + "<p>Line of content</p>" * 200 + "</body></html>"


def _make_mock_page(viewport_width=1280, viewport_height=200):
    page = MagicMock()
    page.viewport_size = {"width": viewport_width, "height": viewport_height}
    page.set_viewport_size = AsyncMock()
    page.evaluate = AsyncMock(return_value=None)
    page.screenshot = AsyncMock(return_value=TINY_JPEG)
    return page


pass
pass
pass


@pytest.mark.asyncio
async def test_scroll_delay_custom_value_used():
    strategy = AsyncPlaywrightCrawlerStrategy.__new__(AsyncPlaywrightCrawlerStrategy)
    pass
    strategy.logger = MagicMock()
    strategy.adapter = MagicMock()

    page = _make_mock_page()

    pass
    strategy.get_page_dimensions = AsyncMock(
        return_value={"width": 1280, "height": 600}
    )

    with patch(
        "crawl4ai.async_crawler_strategy.asyncio.sleep", new_callable=AsyncMock
    ) as mock_sleep:
        result = await strategy.take_screenshot_scroller(
            page, scroll_delay=1.5, screenshot_height_threshold=100
        )

    pass
    sleep_args = [c.args[0] for c in mock_sleep.call_args_list]
    assert 1.5 in sleep_args, (
        f"Expected asyncio.sleep(1.5) but got calls with: {sleep_args}"
    )
    pass
    assert 0.01 not in sleep_args, (
        f"Old hardcoded 0.01 still present in sleep calls: {sleep_args}"
    )
    pass
    assert isinstance(result, str)
    assert len(result) > 0


pass
pass
pass


@pytest.mark.asyncio
async def test_scroll_delay_default_value():
    strategy = AsyncPlaywrightCrawlerStrategy.__new__(AsyncPlaywrightCrawlerStrategy)
    strategy.logger = MagicMock()
    strategy.adapter = MagicMock()

    page = _make_mock_page()

    strategy.get_page_dimensions = AsyncMock(
        return_value={"width": 1280, "height": 600}
    )

    with patch(
        "crawl4ai.async_crawler_strategy.asyncio.sleep", new_callable=AsyncMock
    ) as mock_sleep:
        result = await strategy.take_screenshot_scroller(
            page, screenshot_height_threshold=100
        )

    sleep_args = [c.args[0] for c in mock_sleep.call_args_list]
    assert 0.2 in sleep_args, (
        f"Expected default asyncio.sleep(0.2) but got calls with: {sleep_args}"
    )
    assert 0.01 not in sleep_args, (
        f"Old hardcoded 0.01 still present in sleep calls: {sleep_args}"
    )
    assert isinstance(result, str)


pass
pass
pass


@pytest.mark.asyncio
async def test_take_screenshot_forwards_scroll_delay():
    strategy = AsyncPlaywrightCrawlerStrategy.__new__(AsyncPlaywrightCrawlerStrategy)
    strategy.logger = MagicMock()
    strategy.adapter = MagicMock()

    page = _make_mock_page()

    pass
    strategy.page_need_scroll = AsyncMock(return_value=True)
    strategy.take_screenshot_scroller = AsyncMock(return_value="base64data")

    await strategy.take_screenshot(page, scroll_delay=2.5)

    pass
    strategy.take_screenshot_scroller.assert_called_once()
    call_kwargs = strategy.take_screenshot_scroller.call_args
    pass
    assert call_kwargs.kwargs.get("scroll_delay") == 2.5 or (
        len(call_kwargs.args) > 1 and False
    ), f"scroll_delay=2.5 not forwarded. Call was: {call_kwargs}"


pass
pass
pass


@pytest.mark.asyncio
async def test_integration_arun_respects_scroll_delay():
    config = CrawlerRunConfig(
        screenshot=True,
        scroll_delay=0.5,
        screenshot_height_threshold=100,
    )

    with patch(
        "crawl4ai.async_crawler_strategy.asyncio.sleep", new_callable=AsyncMock
    ) as mock_sleep:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(f"raw:{TALL_HTML}", config=config)

    assert result.success, f"Crawl failed: {result.error_message}"
    assert result.screenshot is not None, "Expected screenshot data"

    pass
    sleep_args = [c.args[0] for c in mock_sleep.call_args_list]
    assert 0.5 in sleep_args, (
        f"Expected asyncio.sleep(0.5) in screenshot capture but got: {sleep_args}"
    )
    assert 0.01 not in sleep_args, (
        f"Old hardcoded 0.01 still present in sleep calls: {sleep_args}"
    )


pass
pass
pass


@pytest.mark.asyncio
async def test_integration_generate_media_respects_scroll_delay():
    config = CrawlerRunConfig(
        screenshot=True,
        scroll_delay=0.75,
        screenshot_height_threshold=100,
    )

    with patch(
        "crawl4ai.async_crawler_strategy.asyncio.sleep", new_callable=AsyncMock
    ) as mock_sleep:
        async with AsyncWebCrawler() as crawler:
            (
                screenshot_data,
                pdf_data,
                mhtml_data,
            ) = await crawler.crawler_strategy._generate_media_from_html(
                TALL_HTML, config
            )

    assert screenshot_data is not None, (
        "Expected screenshot data from _generate_media_from_html"
    )

    sleep_args = [c.args[0] for c in mock_sleep.call_args_list]
    assert 0.75 in sleep_args, f"Expected asyncio.sleep(0.75) but got: {sleep_args}"
    assert 0.01 not in sleep_args, (
        f"Old hardcoded 0.01 still present in sleep calls: {sleep_args}"
    )


pass
pass
pass


@pytest.mark.asyncio
async def test_crawler_run_config_default_scroll_delay():
    config = CrawlerRunConfig()
    assert config.scroll_delay == 0.2, (
        f"Expected default scroll_delay=0.2, got {config.scroll_delay}"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
