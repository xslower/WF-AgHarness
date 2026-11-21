
import pytest
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy


SAMPLE_HTML = """
<html>
<body>
    <div class="header">Header content</div>
    <div class="main-content">
        <p>Main paragraph one with enough words to pass threshold easily here.</p>
        <p>Main paragraph two with enough words to pass threshold easily here.</p>
    </div>
    <div class="sidebar">
        <p>Sidebar content with enough words to pass the word count threshold easily.</p>
    </div>
    <div class="footer">Footer content here</div>
</body>
</html>
"""

NESTED_HTML = """
<html>
<body>
    <div class="wrapper">
        <div class="el-drawer">
            <div class="drawer-body">
                <p>Drawer content with enough words to pass threshold filter check.</p>
            </div>
        </div>
        <div class="other">
            <p>Other content with enough words to pass threshold filter easily here.</p>
        </div>
    </div>
</body>
</html>
"""


@pytest.fixture
def scraper():
    return LXMLWebScrapingStrategy()


class TestCssSelectorBasic:
    def test_css_selector_filters_content(self, scraper):
        result = scraper._scrap(
            url="raw://test",
            html=SAMPLE_HTML,
            css_selector=".main-content",
        )
        assert result is not None
        text = result.get("markdown", "") or result.get("cleaned_html", "")
        assert "Main paragraph" in text
        assert "Sidebar content" not in text

    def test_css_selector_none_returns_full_content(self, scraper):
        result = scraper._scrap(
            url="raw://test",
            html=SAMPLE_HTML,
            css_selector=None,
        )
        assert result is not None
        html = result.get("cleaned_html", "")
        assert "Main paragraph" in html
        assert "Sidebar content" in html

    def test_css_selector_no_match_returns_full_content(self, scraper):
        result = scraper._scrap(
            url="raw://test",
            html=SAMPLE_HTML,
            css_selector=".nonexistent-class",
        )
        assert result is not None
        html = result.get("cleaned_html", "")
        assert "Main paragraph" in html

    def test_css_selector_invalid_falls_back(self, scraper):
        result = scraper._scrap(
            url="raw://test",
            html=SAMPLE_HTML,
            css_selector="[[[invalid",
        )
        assert result is not None

    def test_css_selector_nested_selector(self, scraper):
        result = scraper._scrap(
            url="raw://test",
            html=NESTED_HTML,
            css_selector=".el-drawer .drawer-body",
        )
        assert result is not None
        html = result.get("cleaned_html", "")
        assert "Drawer content" in html
        assert "Other content" not in html


class TestCssSelectorWithTargetElements:
    def test_css_selector_combined_with_target_elements(self, scraper):
        result = scraper._scrap(
            url="raw://test",
            html=SAMPLE_HTML,
            css_selector=".main-content",
            target_elements=["p"],
        )
        assert result is not None
        html = result.get("cleaned_html", "")
        assert "Main paragraph" in html
        assert "Sidebar content" not in html

    def test_target_elements_alone_still_works(self, scraper):
        result = scraper._scrap(
            url="raw://test",
            html=SAMPLE_HTML,
            target_elements=[".main-content"],
        )
        assert result is not None
        html = result.get("cleaned_html", "")
        assert "Main paragraph" in html

    def test_css_selector_multiple_matches(self, scraper):
        result = scraper._scrap(
            url="raw://test",
            html=SAMPLE_HTML,
            css_selector="div p",
        )
        assert result is not None
        html = result.get("cleaned_html", "")
        assert "Main paragraph one" in html
        assert "Main paragraph two" in html

    def test_css_selector_id_selector(self, scraper):
        html = '<html><body><div id="target"><p>Target content here with enough words.</p></div><div><p>Other stuff</p></div></body></html>'
        result = scraper._scrap(
            url="raw://test",
            html=html,
            css_selector="#target",
        )
        assert result is not None
        cleaned = result.get("cleaned_html", "")
        assert "Target content" in cleaned

    def test_css_selector_excludes_non_matching(self, scraper):
        result = scraper._scrap(
            url="raw://test",
            html=SAMPLE_HTML,
            css_selector=".sidebar",
        )
        assert result is not None
        html = result.get("cleaned_html", "")
        assert "Sidebar content" in html
        assert "Main paragraph" not in html
