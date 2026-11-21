import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

PAGE = b'<html><body><p title="x">quoted</p><p>other</p></body></html>'


@pytest.fixture
def server():
    hits = []

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            hits.append(self.path)
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(PAGE)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", hits
    srv.shutdown()


async def _crawl(url, selector):
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as c:
        return await c.arun(url=url, config=CrawlerRunConfig(css_selector=selector))


@pytest.mark.asyncio
async def test_css_selector_cannot_inject_javascript(server):
    base, hits = server
    payload = f'*"))+fetch("{base}/pwned")+Array.from(document.querySelectorAll("*'
    await _crawl(f"{base}/page", payload)
    await asyncio.sleep(0.5)
    assert "/pwned" not in hits


@pytest.mark.asyncio
async def test_css_selector_with_quotes_still_selects(server):
    base, _ = server
    result = await _crawl(f"{base}/page", 'p[title="x"]')
    assert "quoted" in result.html
    assert "other" not in result.html
