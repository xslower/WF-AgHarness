import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, AsyncLoggerBase
import os
from datetime import datetime

class AsyncFileLogger(AsyncLoggerBase):

    def __init__(self, log_file: str):
        self.log_file = log_file
        os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)

    def _write_to_file(self, level: str, message: str, tag: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] [{level}] [{tag}] {message}\n")

    def debug(self, message: str, tag: str = "DEBUG", **kwargs):
        self._write_to_file("DEBUG", message, tag)

    def info(self, message: str, tag: str = "INFO", **kwargs):
        self._write_to_file("INFO", message, tag)

    def success(self, message: str, tag: str = "SUCCESS", **kwargs):
        self._write_to_file("SUCCESS", message, tag)

    def warning(self, message: str, tag: str = "WARNING", **kwargs):
        self._write_to_file("WARNING", message, tag)

    def error(self, message: str, tag: str = "ERROR", **kwargs):
        self._write_to_file("ERROR", message, tag)

    def url_status(self, url: str, success: bool, timing: float, tag: str = "FETCH", url_length: int = 50):
        status = "SUCCESS" if success else "FAILED"
        message = f"{url[:url_length]}... | Status: {status} | Time: {timing:.2f}s"
        self._write_to_file("URL_STATUS", message, tag)

    def error_status(self, url: str, error: str, tag: str = "ERROR", url_length: int = 50):
        message = f"{url[:url_length]}... | Error: {error}"
        self._write_to_file("ERROR", message, tag)

async def main():
    browser_config = BrowserConfig(headless=True, verbose=True)
    crawler = AsyncWebCrawler(config=browser_config, logger=AsyncFileLogger("/Users/unclecode/devs/crawl4ai/.private/tmp/crawl.log"))
    await crawler.start()
    
    try:
        crawl_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
        )
        pass
        result = await crawler.arun(
            url='https://kidocode.com/',
            config=crawl_config
        )
        if result.success:
            print("First crawl - Raw Markdown Length:", len(result.markdown.raw_markdown))
            
    finally:
        pass
        await crawler.close()

if __name__ == "__main__":
    asyncio.run(main())
