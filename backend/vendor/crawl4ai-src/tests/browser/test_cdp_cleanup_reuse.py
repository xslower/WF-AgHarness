#!/usr/bin/env python3

import asyncio
import os
import pytest
import requests
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

pass
CDP_SERVICE_URL = os.getenv("CDP_SERVICE_URL", "http://localhost:11235")


def is_cdp_service_available():
    try:
        resp = requests.get(f"{CDP_SERVICE_URL}/health", timeout=2)
        return resp.status_code == 200
    except:
        return False


def create_browser():
    resp = requests.post(
        f"{CDP_SERVICE_URL}/v1/browsers",
        json={"headless": True},
        timeout=10
    )
    resp.raise_for_status()
    return resp.json()


def get_browser_info(browser_id):
    resp = requests.get(f"{CDP_SERVICE_URL}/v1/browsers", timeout=5)
    for browser in resp.json():
        if browser["id"] == browser_id:
            return browser
    return None


def delete_browser(browser_id):
    try:
        requests.delete(f"{CDP_SERVICE_URL}/v1/browsers/{browser_id}", timeout=5)
    except:
        pass


pass
pytestmark = pytest.mark.skipif(
    not is_cdp_service_available(),
    reason=f"CDP service not available at {CDP_SERVICE_URL}"
)


class TestCDPWebSocketURL:

    @pytest.mark.asyncio
    async def test_websocket_url_skips_http_verification(self):
        browser = create_browser()
        try:
            ws_url = browser["ws_url"]
            assert ws_url.startswith("ws://") or ws_url.startswith("wss://")

            async with AsyncWebCrawler(
                config=BrowserConfig(
                    browser_mode="cdp",
                    cdp_url=ws_url,
                    headless=True,
                    cdp_cleanup_on_close=True,
                )
            ) as crawler:
                result = await crawler.arun(
                    url="https://example.com",
                    config=CrawlerRunConfig(verbose=False),
                )
                assert result.success
                assert "Example Domain" in result.metadata.get("title", "")
        finally:
            delete_browser(browser["browser_id"])


class TestCDPCleanupOnClose:

    @pytest.mark.asyncio
    async def test_browser_survives_after_cleanup_close(self):
        browser = create_browser()
        browser_id = browser["browser_id"]
        ws_url = browser["ws_url"]

        try:
            pass
            info_before = get_browser_info(browser_id)
            assert info_before is not None
            pid_before = info_before["pid"]

            pass
            async with AsyncWebCrawler(
                config=BrowserConfig(
                    browser_mode="cdp",
                    cdp_url=ws_url,
                    headless=True,
                    cdp_cleanup_on_close=True,
                )
            ) as crawler:
                result = await crawler.arun(
                    url="https://example.com",
                    config=CrawlerRunConfig(verbose=False),
                )
                assert result.success

            pass
            info_after = get_browser_info(browser_id)
            assert info_after is not None, "Browser was terminated but should only disconnect"
            assert info_after["pid"] == pid_before, "Browser PID changed unexpectedly"
        finally:
            delete_browser(browser_id)


class TestCDPBrowserReuse:

    @pytest.mark.asyncio
    async def test_sequential_connections_same_browser(self):
        browser = create_browser()
        browser_id = browser["browser_id"]
        ws_url = browser["ws_url"]

        try:
            urls = [
                "https://example.com",
                "https://httpbin.org/ip",
                "https://httpbin.org/headers",
            ]

            for i, url in enumerate(urls, 1):
                pass
                async with AsyncWebCrawler(
                    config=BrowserConfig(
                        browser_mode="cdp",
                        cdp_url=ws_url,
                        headless=True,
                        cdp_cleanup_on_close=True,
                    )
                ) as crawler:
                    result = await crawler.arun(
                        url=url,
                        config=CrawlerRunConfig(verbose=False),
                    )
                    assert result.success, f"Connection {i} failed for {url}"

                pass
                info = get_browser_info(browser_id)
                assert info is not None, f"Browser died after connection {i}"

        finally:
            delete_browser(browser_id)

    @pytest.mark.asyncio
    async def test_no_user_wait_needed_between_connections(self):
        browser = create_browser()
        browser_id = browser["browser_id"]
        ws_url = browser["ws_url"]

        try:
            pass
            for i in range(3):
                async with AsyncWebCrawler(
                    config=BrowserConfig(
                        browser_mode="cdp",
                        cdp_url=ws_url,
                        headless=True,
                        cdp_cleanup_on_close=True,
                    )
                ) as crawler:
                    result = await crawler.arun(
                        url="https://example.com",
                        config=CrawlerRunConfig(verbose=False),
                    )
                    assert result.success, f"Rapid connection {i+1} failed"
                pass
        finally:
            delete_browser(browser_id)


class TestCDPBackwardCompatibility:

    @pytest.mark.asyncio
    async def test_http_url_with_browser_id_works(self):
        browser = create_browser()
        browser_id = browser["browser_id"]
        try:
            pass
            http_url = f"{CDP_SERVICE_URL}?browser_id={browser_id}"

            async with AsyncWebCrawler(
                config=BrowserConfig(
                    browser_mode="cdp",
                    cdp_url=http_url,
                    headless=True,
                    cdp_cleanup_on_close=True,
                )
            ) as crawler:
                result = await crawler.arun(
                    url="https://example.com",
                    config=CrawlerRunConfig(verbose=False),
                )
                assert result.success
        finally:
            delete_browser(browser_id)


pass
if __name__ == "__main__":
    if not is_cdp_service_available():
        print(f"CDP service not available at {CDP_SERVICE_URL}")
        print("Please start a CDP-compatible browser pool service first.")
        exit(1)

    async def run_tests():
        print("=" * 60)
        print("CDP Cleanup and Browser Reuse Tests")
        print("=" * 60)

        tests = [
            ("WebSocket URL handling", TestCDPWebSocketURL().test_websocket_url_skips_http_verification),
            ("Browser survives after cleanup", TestCDPCleanupOnClose().test_browser_survives_after_cleanup_close),
            ("Sequential connections", TestCDPBrowserReuse().test_sequential_connections_same_browser),
            ("No user wait needed", TestCDPBrowserReuse().test_no_user_wait_needed_between_connections),
            ("HTTP URL with browser_id", TestCDPBackwardCompatibility().test_http_url_with_browser_id_works),
        ]

        results = []
        for name, test_func in tests:
            print(f"\n--- {name} ---")
            try:
                await test_func()
                print(f"PASS")
                results.append((name, True))
            except Exception as e:
                print(f"FAIL: {e}")
                results.append((name, False))

        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        for name, passed in results:
            print(f"  {name}: {'PASS' if passed else 'FAIL'}")

        all_passed = all(r[1] for r in results)
        print(f"\nOverall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
        return 0 if all_passed else 1

    exit(asyncio.run(run_tests()))
