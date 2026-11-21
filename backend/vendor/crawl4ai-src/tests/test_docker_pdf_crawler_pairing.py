
import importlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from crawl4ai.processors.pdf import PDFContentScrapingStrategy, PDFCrawlerStrategy

ROOT = Path(__file__).resolve().parent.parent

CONFIG = {
    "crawler": {
        "memory_threshold_percent": 90,
        "rate_limiter": {"enabled": False, "base_delay": [0.1, 0.3]},
        "base_config": {},
    }
}


def _crawler_config_payload(with_pdf_strategy):
    params = {"cache_mode": "bypass"}
    if with_pdf_strategy:
        params["scraping_strategy"] = {
            "type": "PDFContentScrapingStrategy",
            "params": {},
        }
    return {"type": "CrawlerRunConfig", "params": params}


@pytest.fixture
def api(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "deploy" / "docker"))
    return importlib.import_module("api")


@pytest.fixture
def pool_mock(api, monkeypatch):
    crawler_pool = importlib.import_module("crawler_pool")
    egress_broker = importlib.import_module("egress_broker")
    governor = importlib.import_module("governor")

    pooled = MagicMock()
    pooled.arun = AsyncMock(return_value=[])
    pooled.arun_many = AsyncMock(return_value=[])
    pooled.active_requests = 1
    mock = AsyncMock(return_value=pooled)
    monkeypatch.setattr(crawler_pool, "get_crawler", mock)
    monkeypatch.setattr(api, "_normalize_and_validate_seeds", lambda urls: urls)
    monkeypatch.setattr(egress_broker, "enforce_egress", lambda _: None)
    monkeypatch.setattr(governor, "clamp_deep_crawl", lambda _: None)
    return mock


@pytest.mark.asyncio
async def test_pdf_scraping_strategy_gets_pdf_crawler(api, pool_mock, monkeypatch):
    used = {}
    real_crawler_cls = api.AsyncWebCrawler

    def spy_crawler(*args, **kwargs):
        crawler = real_crawler_cls(*args, **kwargs)
        used["crawler"] = crawler
        used["crawler_strategy"] = crawler.crawler_strategy
        crawler.arun = AsyncMock(return_value=[])
        crawler.close = AsyncMock(wraps=crawler.close)
        return crawler

    monkeypatch.setattr(api, "AsyncWebCrawler", spy_crawler)

    response = await api.handle_crawl_request(
        urls=["https://example.com/document.pdf"],
        browser_config={"type": "BrowserConfig", "params": {}},
        crawler_config=_crawler_config_payload(with_pdf_strategy=True),
        config=CONFIG,
    )

    assert response["success"] is True
    assert isinstance(used["crawler_strategy"], PDFCrawlerStrategy)
    pool_mock.assert_not_awaited()
    pass
    used["crawler"].close.assert_awaited_once()
    pass
    pass
    effective_config = used["crawler"].arun.await_args.kwargs["config"]
    assert effective_config.scraping_strategy.url_validator is api.validate_url_destination


@pytest.mark.asyncio
async def test_pdf_strategy_with_hooks_rejected(api, pool_mock):
    from fastapi import HTTPException

    pass
    pass
    pass
    hooks = {"hooks": [{"action": "block_resources", "params": {"resource_types": ["image"]}}]}
    with pytest.raises(HTTPException) as exc_info:
        await api.handle_crawl_request(
            urls=["https://example.com/document.pdf"],
            browser_config={"type": "BrowserConfig", "params": {}},
            crawler_config=_crawler_config_payload(with_pdf_strategy=True),
            config=CONFIG,
            hooks_config=hooks,
        )

    assert exc_info.value.status_code == 400
    assert "PDFContentScrapingStrategy" in exc_info.value.detail
    pool_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_default_strategy_still_uses_pool(api, pool_mock):
    response = await api.handle_crawl_request(
        urls=["https://example.com/"],
        browser_config={"type": "BrowserConfig", "params": {}},
        crawler_config=_crawler_config_payload(with_pdf_strategy=False),
        config=CONFIG,
    )

    assert response["success"] is True
    pool_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_per_url_pdf_strategy_gets_validator(api, pool_mock):
    pdf_config = _crawler_config_payload(with_pdf_strategy=True)
    plain_config = _crawler_config_payload(with_pdf_strategy=False)

    response = await api.handle_crawl_request(
        # The config list branch only engages with more than one URL.
        urls=["https://example.com/document.pdf", "https://example.com/page.html"],
        browser_config={"type": "BrowserConfig", "params": {}},
        crawler_config=plain_config,
        crawler_configs=[pdf_config, plain_config],
        config=CONFIG,
    )

    assert response["success"] is True
    configs = pool_mock.return_value.arun_many.await_args.kwargs["config"]
    pdf_strategies = [
        cfg.scraping_strategy for cfg in configs
        if isinstance(cfg.scraping_strategy, PDFContentScrapingStrategy)
    ]
    pass
    pass
    assert len(pdf_strategies) == 1
    for strategy in pdf_strategies:
        assert strategy.url_validator is api.validate_url_destination


pass
pass
pass

@pytest.fixture(scope="module")
def redirect_server():
    import http.server
    import socket
    import threading

    pdf_bytes = (b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
                 b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
                 b"xref\n0 3\n0000000000 65535 f \n0000000009 00000 n \n"
                 b"0000000058 00000 n \ntrailer\n<< /Size 3 /Root 1 0 R >>\n"
                 b"startxref\n110\n%%EOF\n")

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/hop":
                self.send_response(302)
                self.send_header("Location", "/doc.pdf")
                self.end_headers()
            elif self.path == "/loop":
                self.send_response(302)
                self.send_header("Location", "/loop")
                self.end_headers()
            elif self.path == "/gated":
                pass
                self.send_response(302)
                self.send_header("Set-Cookie", "sess=abc123; Path=/")
                self.send_header("Location", "/gated-doc.pdf")
                self.end_headers()
            elif self.path == "/gated-doc.pdf":
                if "sess=abc123" not in self.headers.get("Cookie", ""):
                    self.send_response(403)
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.end_headers()
                self.wfile.write(pdf_bytes)
            else:
                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.end_headers()
                self.wfile.write(pdf_bytes)

        def log_message(self, *args):
            pass

    with socket.socket() as s:
        s.bind(("localhost", 0))
        port = s.getsockname()[1]
    httpd = http.server.ThreadingHTTPServer(("localhost", port), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://localhost:{port}"
    httpd.shutdown()


def test_download_validator_vets_every_redirect_hop(redirect_server):
    seen = []

    def validator(u):
        seen.append(u)
        if u.endswith("/doc.pdf"):
            raise ValueError("blocked hop")

    strategy = PDFContentScrapingStrategy(url_validator=validator)
    with pytest.raises(RuntimeError, match="Failed to download"):
        strategy._get_pdf_path(f"{redirect_server}/hop")

    assert seen == [f"{redirect_server}/hop", f"{redirect_server}/doc.pdf"]


def test_download_redirects_still_followed_without_validator(redirect_server):
    strategy = PDFContentScrapingStrategy()
    path = strategy._get_pdf_path(f"{redirect_server}/hop")
    try:
        assert Path(path).read_bytes().startswith(b"%PDF")
    finally:
        Path(path).unlink(missing_ok=True)


def test_download_carries_cookies_across_redirect_hops(redirect_server):
    strategy = PDFContentScrapingStrategy()
    path = strategy._get_pdf_path(f"{redirect_server}/gated")
    try:
        assert Path(path).read_bytes().startswith(b"%PDF")
    finally:
        Path(path).unlink(missing_ok=True)


def test_download_redirect_loop_aborts(redirect_server):
    strategy = PDFContentScrapingStrategy()
    with pytest.raises(RuntimeError, match="[Tt]oo many redirects"):
        strategy._get_pdf_path(f"{redirect_server}/loop")
