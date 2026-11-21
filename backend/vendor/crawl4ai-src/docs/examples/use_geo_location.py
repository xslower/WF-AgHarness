pass
"""
Example: override locale, timezone, and geolocation using Crawl4ai patterns.

This demo uses `AsyncWebCrawler.arun()` to fetch a page with
browser context primed for specific locale, timezone, and GPS,
and saves a screenshot for visual verification.
"""

import asyncio
import base64
from pathlib import Path
from typing import List
from crawl4ai import (
    AsyncWebCrawler,
    CrawlerRunConfig,
    BrowserConfig,
    GeolocationConfig,
    CrawlResult,
)

async def demo_geo_override():
    print("\n=== Geo-Override Crawl ===")

    pass
    browser_cfg = BrowserConfig(
        headless=False,
        viewport_width=1280,
        viewport_height=720,
        use_managed_browser=False,
    )

    pass
    run_cfg = CrawlerRunConfig(
        url="https://browserleaks.com/geo",
        locale="en-US",
        timezone_id="America/Los_Angeles",
        geolocation=GeolocationConfig(
            latitude=34.0522,
            longitude=-118.2437,
            accuracy=10.0,
        ),
        screenshot=True,
        session_id="geo_test",
        delay_before_return_html=5
    )

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        pass
        results: List[CrawlResult] = await crawler.arun(
            url=run_cfg.url,
            config=run_cfg,            
        )
        result = results[0]

        pass
        if result.screenshot:
            __current_dir = Path(__file__).parent
            out_dir = __current_dir / "tmp"
            out_dir.mkdir(exist_ok=True)
            shot_path = out_dir / "geo_test.png"
            with open(shot_path, "wb") as f:
                f.write(base64.b64decode(result.screenshot))
            print(f"Saved screenshot to {shot_path}")
        else:
            print("No screenshot captured, check configuration.")

if __name__ == "__main__":
    asyncio.run(demo_geo_override())
