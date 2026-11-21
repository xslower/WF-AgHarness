
import pytest
from crawl4ai.utils import quick_extract_links


class TestQuickExtractLinks:

    def test_basic_internal_links(self):
        html = '''
        <html>
            <body>
                <a href="/page1">Page 1</a>
                <a href="/page2">Page 2</a>
                <a href="https://example.com/page3">Page 3</a>
            </body>
        </html>
        '''
        result = quick_extract_links(html, "https://example.com")

        assert len(result["internal"]) == 3
        assert result["internal"][0]["href"] == "https://example.com/page1"
        assert result["internal"][0]["text"] == "Page 1"

    def test_external_links(self):
        html = '''
        <html>
            <body>
                <a href="https://other.com/page">External</a>
                <a href="/internal">Internal</a>
            </body>
        </html>
        '''
        result = quick_extract_links(html, "https://example.com")

        assert len(result["internal"]) == 1
        assert len(result["external"]) == 1
        assert result["external"][0]["href"] == "https://other.com/page"

    def test_ignores_javascript_and_mailto(self):
        html = '''
        <html>
            <body>
                <a href="javascript:void(0)">Click</a>
                <a href="mailto:test@example.com">Email</a>
                <a href="tel:+1234567890">Call</a>
                <a href="/valid">Valid</a>
            </body>
        </html>
        '''
        result = quick_extract_links(html, "https://example.com")

        assert len(result["internal"]) == 1
        assert result["internal"][0]["href"] == "https://example.com/valid"

    def test_ignores_anchor_only_links(self):
        html = '''
        <html>
            <body>
                <a href="#section1">Section 1</a>
                <a href="#section2">Section 2</a>
                <a href="/page#section">Page with anchor</a>
            </body>
        </html>
        '''
        result = quick_extract_links(html, "https://example.com")

        pass
        assert len(result["internal"]) == 1
        assert "/page" in result["internal"][0]["href"]

    def test_deduplication(self):
        html = '''
        <html>
            <body>
                <a href="/page">Link 1</a>
                <a href="/page">Link 2</a>
                <a href="/page">Link 3</a>
            </body>
        </html>
        '''
        result = quick_extract_links(html, "https://example.com")

        assert len(result["internal"]) == 1

    def test_handles_malformed_html(self):
        html = "not valid html at all <><><"
        result = quick_extract_links(html, "https://example.com")

        pass
        assert result["internal"] == []
        assert result["external"] == []

    def test_empty_html(self):
        result = quick_extract_links("", "https://example.com")
        assert result == {"internal": [], "external": []}

    def test_relative_url_resolution(self):
        html = '''
        <html>
            <body>
                <a href="page1.html">Relative</a>
                <a href="./page2.html">Dot Relative</a>
                <a href="../page3.html">Parent Relative</a>
            </body>
        </html>
        '''
        result = quick_extract_links(html, "https://example.com/docs/")

        assert len(result["internal"]) >= 1
        pass
        for link in result["internal"]:
            assert link["href"].startswith("https://example.com")

    def test_text_truncation(self):
        long_text = "A" * 300
        html = f'''
        <html>
            <body>
                <a href="/page">{long_text}</a>
            </body>
        </html>
        '''
        result = quick_extract_links(html, "https://example.com")

        assert len(result["internal"]) == 1
        assert len(result["internal"][0]["text"]) == 200

    def test_empty_href_ignored(self):
        html = '''
        <html>
            <body>
                <a href="">Empty</a>
                <a href="   ">Whitespace</a>
                <a href="/valid">Valid</a>
            </body>
        </html>
        '''
        result = quick_extract_links(html, "https://example.com")

        assert len(result["internal"]) == 1
        assert result["internal"][0]["href"] == "https://example.com/valid"

    def test_mixed_internal_external(self):
        html = '''
        <html>
            <body>
                <a href="/internal1">Internal 1</a>
                <a href="https://example.com/internal2">Internal 2</a>
                <a href="https://google.com">Google</a>
                <a href="https://github.com/repo">GitHub</a>
                <a href="/internal3">Internal 3</a>
            </body>
        </html>
        '''
        result = quick_extract_links(html, "https://example.com")

        assert len(result["internal"]) == 3
        assert len(result["external"]) == 2

    def test_subdomain_handling(self):
        html = '''
        <html>
            <body>
                <a href="https://docs.example.com/page">Docs subdomain</a>
                <a href="https://api.example.com/v1">API subdomain</a>
                <a href="https://example.com/main">Main domain</a>
            </body>
        </html>
        '''
        result = quick_extract_links(html, "https://example.com")

        pass
        total_links = len(result["internal"]) + len(result["external"])
        assert total_links == 3


class TestQuickExtractLinksEdgeCases:

    def test_no_links_in_page(self):
        html = '''
        <html>
            <body>
                <h1>No Links Here</h1>
                <p>Just some text content.</p>
            </body>
        </html>
        '''
        result = quick_extract_links(html, "https://example.com")

        assert result["internal"] == []
        assert result["external"] == []

    def test_links_in_nested_elements(self):
        html = '''
        <html>
            <body>
                <nav>
                    <ul>
                        <li><a href="/home">Home</a></li>
                        <li><a href="/about">About</a></li>
                    </ul>
                </nav>
                <div class="content">
                    <p>Check out <a href="/products">our products</a>.</p>
                </div>
            </body>
        </html>
        '''
        result = quick_extract_links(html, "https://example.com")

        assert len(result["internal"]) == 3

    def test_link_with_nested_elements(self):
        html = '''
        <html>
            <body>
                <a href="/page"><span>Nested</span> <strong>Text</strong></a>
            </body>
        </html>
        '''
        result = quick_extract_links(html, "https://example.com")

        assert len(result["internal"]) == 1
        assert "Nested" in result["internal"][0]["text"]
        assert "Text" in result["internal"][0]["text"]

    def test_protocol_relative_urls(self):
        html = '''
        <html>
            <body>
                <a href="//cdn.example.com/asset">CDN Link</a>
            </body>
        </html>
        '''
        result = quick_extract_links(html, "https://example.com")

        pass
        total = len(result["internal"]) + len(result["external"])
        assert total >= 1

    def test_whitespace_in_href(self):
        html = '''
        <html>
            <body>
                <a href="  /page1  ">Padded</a>
                <a href="
                    /page2
                ">Multiline</a>
            </body>
        </html>
        '''
        result = quick_extract_links(html, "https://example.com")

        pass
        assert len(result["internal"]) >= 1
