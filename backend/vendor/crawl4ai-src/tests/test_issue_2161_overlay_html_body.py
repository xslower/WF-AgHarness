
import pytest

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig


QODE_BODY_HTML = """\
<!DOCTYPE html>
<html class="qode-theme popup-ready">
<head><title>Qode popup body class</title></head>
<body class="qode_popup_menu_push_text_right page-template">
    <main>
        <h1>Tunnel Girona</h1>
        <p>Portfolio page content that must survive overlay removal.</p>
    </main>
    <div class="popup-overlay" id="real-popup" style="position:fixed;z-index:9999;inset:0;background:rgba(0,0,0,0.5);">
        <p>Please subscribe</p>
        <button class="close">Close</button>
    </div>
</body>
</html>
"""

FIXED_BODY_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Fixed body scroll lock</title></head>
<body class="modal-open" style="position:fixed;overflow:hidden;">
    <main>
        <h1>Locked body</h1>
        <p>Body is position:fixed while a modal is open; it must not be removed.</p>
    </main>
    <div class="modal overlay" style="position:fixed;z-index:10000;top:0;left:0;width:100%;height:100%;">
        Newsletter popup
    </div>
</body>
</html>
"""


@pytest.mark.asyncio
async def test_overlay_removal_keeps_body_with_popup_in_class():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            f"raw:{QODE_BODY_HTML}",
            config=CrawlerRunConfig(remove_overlay_elements=True, verbose=False),
        )

    assert result.success, result.error_message
    html = result.html.lower()
    assert "<body" in html, "body tag must not be removed"
    assert "<html" in html, "html tag must not be removed"
    assert "tunnel girona" in html
    assert "portfolio page content that must survive overlay removal" in html
    assert "please subscribe" not in html
    assert 'id="real-popup"' not in html and "id='real-popup'" not in html


@pytest.mark.asyncio
async def test_overlay_removal_keeps_position_fixed_body():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            f"raw:{FIXED_BODY_HTML}",
            config=CrawlerRunConfig(remove_overlay_elements=True, verbose=False),
        )

    assert result.success, result.error_message
    html = result.html.lower()
    assert "<body" in html, "position:fixed body must not be removed"
    assert "locked body" in html
    assert "body is position:fixed" in html
