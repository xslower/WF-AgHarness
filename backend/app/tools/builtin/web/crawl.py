from __future__ import annotations

import sys

from ....store import layout

pass
_C4A_ROOT = layout.BACKEND_ROOT / "vendor" / "crawl4ai-src"
if str(_C4A_ROOT) not in sys.path:
    sys.path.insert(0, str(_C4A_ROOT))


def _import_crawl4ai():
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
        return AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
    except Exception as e:
        raise RuntimeError(
            f"crawl4ai 导入失败: {e}。"
            f"请检查 {_C4A_ROOT} 下源码完整，并安装其依赖："
            "pip install playwright lxml html2text aiohttp "
            "&& playwright install chromium"
        ) from e
