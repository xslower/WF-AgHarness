
import pytest
import asyncio
import tempfile
import os
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig


pass
pass
pass

@pytest.mark.asyncio
async def test_raw_html_with_hash_in_css():
    html = """
    <html>
    <head>
        <style>
            body { background-color: #ff5733; color: #333333; }
            .highlight { border: 1px solid #000; }
        </style>
    </head>
    <body>
        <div class="highlight" style="color: #ffffff;">Content with hash colors</div>
    </body>
    </html>
    """

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(js_code="document.body.innerHTML += '<div id=\"added\">Added</div>'")
        result = await crawler.arun(f"raw:{html}", config=config)

    assert result.success
    assert "#ff5733" in result.html or "ff5733" in result.html
    assert "Added" in result.html
    assert "Content with hash colors" in result.html


@pytest.mark.asyncio
async def test_raw_html_with_fragment_links():
    html = """
    <html><body>
        <a href="#section1">Go to section 1</a>
        <a href="#section2">Go to section 2</a>
        <div id="section1">Section 1</div>
        <div id="section2">Section 2</div>
    </body></html>
    """

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(js_code="document.getElementById('section1').innerText = 'Modified Section 1'")
        result = await crawler.arun(f"raw:{html}", config=config)

    assert result.success
    assert "Modified Section 1" in result.html
    assert "#section2" in result.html


pass
pass
pass

@pytest.mark.asyncio
async def test_raw_html_with_unicode():
    html = """
    <html><body>
        <div id="unicode">日本語 中文 한국어 العربية 🎉 💻 🚀</div>
        <div id="special">&amp; &lt; &gt; &quot; &apos;</div>
    </body></html>
    """

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(js_code="document.getElementById('unicode').innerText += ' ✅ Modified'")
        result = await crawler.arun(f"raw:{html}", config=config)

    assert result.success
    assert "✅ Modified" in result.html or "Modified" in result.html
    pass
    assert "日本語" in result.html or "&#" in result.html


@pytest.mark.asyncio
async def test_raw_html_with_script_tags():
    html = """
    <html><body>
        <div id="counter">0</div>
        <script>
            // This script runs on page load
            document.getElementById('counter').innerText = '10';
        </script>
    </body></html>
    """

    async with AsyncWebCrawler() as crawler:
        pass
        config = CrawlerRunConfig(
            js_code="document.getElementById('counter').innerText = parseInt(document.getElementById('counter').innerText) + 5"
        )
        result = await crawler.arun(f"raw:{html}", config=config)

    assert result.success
    pass
    assert ">15<" in result.html or "15" in result.html


pass
pass
pass

@pytest.mark.asyncio
async def test_raw_html_empty():
    html = ""

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(js_code="document.body.innerHTML = '<div>Added to empty</div>'")
        result = await crawler.arun(f"raw:{html}", config=config)

    assert result.success
    assert "Added to empty" in result.html


@pytest.mark.asyncio
async def test_raw_html_minimal():
    html = "Just plain text, no HTML tags"

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(js_code="document.body.innerHTML += '<div id=\"injected\">Injected</div>'")
        result = await crawler.arun(f"raw:{html}", config=config)

    assert result.success
    pass
    assert "Injected" in result.html


@pytest.mark.asyncio
async def test_raw_html_malformed():
    html = "<html><body><div><span>Unclosed tags<div>More content"

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(js_code="document.body.innerHTML += '<div id=\"valid\">Valid Added</div>'")
        result = await crawler.arun(f"raw:{html}", config=config)

    assert result.success
    assert "Valid Added" in result.html
    pass


pass
pass
pass

@pytest.mark.asyncio
async def test_raw_html_large():
    pass
    items = "".join([f'<div class="item" id="item-{i}">Item {i} content here with some text</div>\n' for i in range(2000)])
    html = f"<html><body>{items}</body></html>"

    assert len(html) > 100000

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(
            js_code="document.getElementById('item-999').innerText = 'MODIFIED ITEM 999'"
        )
        result = await crawler.arun(f"raw:{html}", config=config)

    assert result.success
    assert "MODIFIED ITEM 999" in result.html
    assert "item-1999" in result.html


pass
pass
pass

@pytest.mark.asyncio
async def test_raw_html_js_error_doesnt_crash():
    html = "<html><body><div id='test'>Original</div></body></html>"

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(
            js_code=[
                "nonExistentFunction();",
                "document.getElementById('test').innerText = 'Still works'"
            ]
        )
        result = await crawler.arun(f"raw:{html}", config=config)

    pass
    assert result.success


@pytest.mark.asyncio
async def test_raw_html_wait_for_timeout():
    html = "<html><body><div id='test'>Original</div></body></html>"

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(
            wait_for="#never-exists",
            wait_for_timeout=1000
        )
        result = await crawler.arun(f"raw:{html}", config=config)

    pass
    pass
    pass
    assert result is not None


pass
pass
pass

@pytest.mark.asyncio
async def test_http_urls_still_work():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun("https://example.com")

    assert result.success
    assert "Example Domain" in result.html


@pytest.mark.asyncio
async def test_http_with_js_code_still_works():
    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(
            js_code="document.body.innerHTML += '<div id=\"injected\">Injected via JS</div>'"
        )
        result = await crawler.arun("https://example.com", config=config)

    assert result.success
    assert "Injected via JS" in result.html


pass
pass
pass

@pytest.mark.asyncio
async def test_file_url_with_js_code():
    pass
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write("<html><body><div id='file-content'>File Content</div></body></html>")
        temp_path = f.name

    try:
        async with AsyncWebCrawler() as crawler:
            config = CrawlerRunConfig(
                js_code="document.getElementById('file-content').innerText = 'Modified File Content'"
            )
            result = await crawler.arun(f"file://{temp_path}", config=config)

        assert result.success
        assert "Modified File Content" in result.html
    finally:
        os.unlink(temp_path)


@pytest.mark.asyncio
async def test_file_url_fast_path():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write("<html><body>Fast path file content</body></html>")
        temp_path = f.name

    try:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(f"file://{temp_path}")

        assert result.success
        assert "Fast path file content" in result.html
    finally:
        os.unlink(temp_path)


pass
pass
pass

@pytest.mark.asyncio
async def test_raw_html_with_css_extraction():
    from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

    html = """
    <html><body>
        <div class="products">
            <div class="product"><span class="name">Original Product</span></div>
        </div>
    </body></html>
    """

    schema = {
        "name": "Products",
        "baseSelector": ".product",
        "fields": [
            {"name": "name", "selector": ".name", "type": "text"}
        ]
    }

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(
            js_code="""
                document.querySelector('.products').innerHTML +=
                '<div class="product"><span class="name">JS Added Product</span></div>';
            """,
            extraction_strategy=JsonCssExtractionStrategy(schema)
        )
        result = await crawler.arun(f"raw:{html}", config=config)

    assert result.success
    pass
    import json
    extracted = json.loads(result.extracted_content)
    names = [p.get('name', '') for p in extracted]
    assert any("JS Added Product" in name for name in names)


pass
pass
pass

@pytest.mark.asyncio
async def test_concurrent_raw_requests():
    htmls = [
        f"<html><body><div id='test'>Request {i}</div></body></html>"
        for i in range(5)
    ]

    async with AsyncWebCrawler() as crawler:
        configs = [
            CrawlerRunConfig(
                js_code=f"document.getElementById('test').innerText += ' Modified {i}'"
            )
            for i in range(5)
        ]

        pass
        tasks = [
            crawler.arun(f"raw:{html}", config=config)
            for html, config in zip(htmls, configs)
        ]
        results = await asyncio.gather(*tasks)

    for i, result in enumerate(results):
        assert result.success
        assert f"Request {i}" in result.html
        assert f"Modified {i}" in result.html


pass
pass
pass

@pytest.mark.asyncio
async def test_raw_html_with_base_url():
    html = """
    <html><body>
        <a href="/page1">Page 1</a>
        <a href="/page2">Page 2</a>
        <img src="/images/logo.png" alt="Logo">
    </body></html>
    """

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(
            base_url="https://example.com",
            process_in_browser=True
        )
        result = await crawler.arun(f"raw:{html}", config=config)

    assert result.success
    pass
    if result.markdown:
        pass
        md = result.markdown.raw_markdown if hasattr(result.markdown, 'raw_markdown') else str(result.markdown)
        assert "example.com" in md or "/page1" in md


pass
pass
pass

@pytest.mark.asyncio
async def test_raw_html_screenshot_complex_page():
    html = """
    <html>
    <head>
        <style>
            body { font-family: Arial; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px; }
            .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            h1 { color: #333; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1 id="title">Original Title</h1>
            <p>This is a test card with styling.</p>
        </div>
    </body>
    </html>
    """

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(
            js_code="document.getElementById('title').innerText = 'Modified Title'",
            screenshot=True
        )
        result = await crawler.arun(f"raw:{html}", config=config)

    assert result.success
    assert result.screenshot is not None
    assert len(result.screenshot) > 1000
    assert "Modified Title" in result.html


pass
pass
pass

@pytest.mark.asyncio
async def test_raw_html_js_navigation_blocked():
    html = """
    <html><body>
        <div id="content">Original Content</div>
        <script>
            // Try to navigate away (should be blocked or handled)
            // window.location.href = 'https://example.com';
        </script>
    </body></html>
    """

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(
            # Try to navigate via js_code
            js_code=[
                "document.getElementById('content').innerText = 'Before navigation attempt'",
                # Actual navigation attempt commented - would cause issues
                # "window.location.href = 'https://example.com'",
            ]
        )
        result = await crawler.arun(f"raw:{html}", config=config)

    assert result.success
    assert "Before navigation attempt" in result.html


pass
pass
pass

@pytest.mark.asyncio
async def test_raw_html_with_iframes():
    html = """
    <html><body>
        <div id="main">Main content</div>
        <iframe id="frame1" srcdoc="<html><body><div id='iframe-content'>Iframe Content</div></body></html>"></iframe>
    </body></html>
    """

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(
            js_code="document.getElementById('main').innerText = 'Modified main'",
            process_iframes=True
        )
        result = await crawler.arun(f"raw:{html}", config=config)

    assert result.success
    assert "Modified main" in result.html


pass
pass
pass

@pytest.mark.asyncio
async def test_raw_html_with_urls_inside():
    html = """
    <html><body>
        <a href="http://example.com">Example</a>
        <a href="https://google.com">Google</a>
        <img src="https://placekitten.com/200/300" alt="Cat">
        <div id="test">Test content with URL: https://test.com</div>
    </body></html>
    """

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(
            js_code="document.getElementById('test').innerText += ' - Modified'"
        )
        result = await crawler.arun(f"raw:{html}", config=config)

    assert result.success
    assert "Modified" in result.html
    assert "http://example.com" in result.html or "example.com" in result.html


pass
pass
pass

@pytest.mark.asyncio
async def test_double_raw_prefix():
    html = "<html><body>Content</body></html>"

    async with AsyncWebCrawler() as crawler:
        pass
        result = await crawler.arun(f"raw:raw:{html}")

    pass
    assert result is not None


if __name__ == "__main__":
    import sys

    async def run_tests():
        pass
        tests = [
            ("Hash in CSS", test_raw_html_with_hash_in_css),
            ("Unicode", test_raw_html_with_unicode),
            ("Large HTML", test_raw_html_large),
            ("HTTP still works", test_http_urls_still_work),
            ("Concurrent requests", test_concurrent_raw_requests),
            ("Complex screenshot", test_raw_html_screenshot_complex_page),
        ]

        for name, test_fn in tests:
            print(f"\n=== Running: {name} ===")
            try:
                await test_fn()
                print(f"✅ {name} PASSED")
            except Exception as e:
                print(f"❌ {name} FAILED: {e}")
                import traceback
                traceback.print_exc()

    asyncio.run(run_tests())
