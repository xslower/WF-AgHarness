
import asyncio

import pytest

from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig
from crawl4ai.antibot_detector import is_blocked
from crawl4ai.models import AsyncCrawlResponse

PDF_TEXT = "Hello crawl4ai PDF fixture"


def _build_minimal_pdf(text: str = PDF_TEXT) -> bytes:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
        b" /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        None,
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    stream = f"BT /F1 18 Tf 72 720 Td ({text}) Tj ET".encode()
    objects[3] = (
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n"
        + stream + b"\nendstream"
    )
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_pos = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += b"trailer\n<< /Size " + str(len(objects) + 1).encode() + b" /Root 1 0 R >>\n"
    out += b"startxref\n" + str(xref_pos).encode() + b"\n%%EOF\n"
    return bytes(out)


@pytest.fixture
def pdf_file(tmp_path):
    pytest.importorskip("pypdf", reason="requires the crawl4ai[pdf] extra")
    path = tmp_path / "fixture.pdf"
    path.write_bytes(_build_minimal_pdf())
    return path


def _run_pdf_crawl(pdf_file, **config_kwargs):
    from crawl4ai.processors.pdf import (
        PDFContentScrapingStrategy,
        PDFCrawlerStrategy,
    )

    async def run():
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            scraping_strategy=PDFContentScrapingStrategy(extract_images=False),
            **config_kwargs,
        )
        async with AsyncWebCrawler(crawler_strategy=PDFCrawlerStrategy()) as crawler:
            return await crawler.arun(f"file://{pdf_file}", config=config)

    return asyncio.run(run())


def test_placeholder_html_defaults_false():
    response = AsyncCrawlResponse(
        html="<html></html>", response_headers={}, status_code=200
    )
    assert response.placeholder_html is False


def test_is_blocked_still_flags_near_empty_html():
    blocked, reason = is_blocked(200, "Scraper will handle the real work")
    assert blocked
    assert "Near-empty content" in reason


def test_pdf_pairing_is_not_vetoed_by_antibot(pdf_file):
    result = _run_pdf_crawl(pdf_file)

    assert result.success, f"crawl failed: {result.error_message}"
    assert "anti-bot" not in (result.error_message or "")
    markdown = (
        result.markdown.raw_markdown
        if hasattr(result.markdown, "raw_markdown")
        else result.markdown
    )
    assert PDF_TEXT in (markdown or "")


def test_pdf_crawl_does_not_burn_retries_or_fallback(pdf_file):
    fallback_calls = []

    async def fake_fallback(url):
        fallback_calls.append(url)
        return "<html><body>should not be used</body></html>"

    result = _run_pdf_crawl(
        pdf_file, max_retries=2, fallback_fetch_function=fake_fallback
    )

    stats = result.crawl_stats or {}
    assert stats.get("resolved_by") == "direct"
    assert stats.get("attempts") == 1
    assert all(not p.get("blocked") for p in stats.get("proxies_used", []))
    assert not fallback_calls
    assert stats.get("fallback_fetch_used") is False
