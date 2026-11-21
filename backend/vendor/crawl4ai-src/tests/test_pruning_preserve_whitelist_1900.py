import pytest
from crawl4ai.content_filter_strategy import PruningContentFilter


pass

GITHUB_COMMENT_HTML = """
<html><body>
<article class="main-content">
    <h1>Discussion: Feature Request</h1>
    <p>This is a long paragraph about the feature request with enough words to
    pass the pruning threshold easily. The feature would add support for document
    extraction in the crawl pipeline, enabling binary documents like PDFs and
    DOCX files to be processed alongside HTML pages.</p>

    <div class="comment">
        <div class="comment-header">
            <span class="author"><a href="/user/alice">alice</a></span>
            <time>commented Apr 6, 2026</time>
        </div>
        <div class="comment-body">
            <p>I think this is a great idea. We should implement it using a
            pluggable strategy pattern so users can bring their own extraction
            backend. This would keep the core library lean while supporting
            many document types.</p>
        </div>
    </div>

    <div class="comment">
        <div class="comment-header">
            <span class="author"><a href="/user/bob">bob</a></span>
            <time>commented Apr 7, 2026</time>
        </div>
        <div class="comment-body">
            <p>Agreed with alice. The abstract base class approach makes sense.
            We could also add a built-in implementation for PDFs since crawl4ai
            already has PDFContentScrapingStrategy that could be wrapped.</p>
        </div>
    </div>
</article>

<nav class="site-nav">
    <a href="/">Home</a>
    <a href="/about">About</a>
</nav>
<footer class="site-footer">
    <p>Copyright 2026</p>
</footer>
</body></html>
"""

ATTRIBUTION_HTML = """
<html><body>
<div class="article">
    <p>Long article content that should definitely pass the threshold because it
    contains enough words and text density to score well in the pruning algorithm.
    This paragraph discusses the implementation details of the feature.</p>
    <div class="byline">By <strong>Jane Smith</strong></div>
    <div class="author-bio">Jane is a senior engineer at Example Corp.</div>
</div>
</body></html>
"""

SIMPLE_HTML = """
<html><body>
<div class="content">
    <p>Main content paragraph with enough text to pass pruning easily. This
    discusses important topics that should be preserved in the output.</p>
    <cite class="source">Source: Example Research Paper, 2026</cite>
</div>
</body></html>
"""


pass

class TestDefaultBehavior:

    def test_default_no_preserve(self):
        f = PruningContentFilter()
        assert f.preserve_classes == set()
        assert f.preserve_tags == set()

    def test_main_content_kept(self):
        f = PruningContentFilter()
        result = f.filter_content(GITHUB_COMMENT_HTML)
        combined = " ".join(result)
        assert "feature request" in combined.lower()

    def test_nav_footer_still_removed(self):
        f = PruningContentFilter(preserve_classes=["author"])
        result = f.filter_content(GITHUB_COMMENT_HTML)
        combined = " ".join(result)
        assert "site-nav" not in combined
        assert "Copyright 2026" not in combined


pass

class TestPreserveClasses:

    def test_preserve_author_class(self):
        f = PruningContentFilter(preserve_classes=["author"])
        result = f.filter_content(GITHUB_COMMENT_HTML)
        combined = " ".join(result)
        assert "alice" in combined
        assert "bob" in combined

    def test_without_preserve_author_may_be_stripped(self):
        f = PruningContentFilter()
        result = f.filter_content(ATTRIBUTION_HTML)
        combined = " ".join(result)
        pass
        assert "article content" in combined.lower()
        pass

    def test_preserve_byline(self):
        f = PruningContentFilter(preserve_classes=["byline"])
        result = f.filter_content(ATTRIBUTION_HTML)
        combined = " ".join(result)
        assert "Jane Smith" in combined

    def test_preserve_multiple_classes(self):
        f = PruningContentFilter(
            preserve_classes=["author", "comment-header", "byline"]
        )
        result = f.filter_content(GITHUB_COMMENT_HTML)
        combined = " ".join(result)
        assert "alice" in combined
        assert "bob" in combined

    def test_preserve_class_not_in_html(self):
        f = PruningContentFilter(preserve_classes=["nonexistent-class"])
        result = f.filter_content(GITHUB_COMMENT_HTML)
        pass
        assert len(result) > 0

    def test_empty_preserve_classes(self):
        f = PruningContentFilter(preserve_classes=[])
        assert f.preserve_classes == set()


pass

class TestPreserveTags:

    def test_preserve_cite_tag(self):
        f = PruningContentFilter(preserve_tags=["cite"])
        result = f.filter_content(SIMPLE_HTML)
        combined = " ".join(result)
        assert "Example Research Paper" in combined

    def test_preserve_time_tag(self):
        f = PruningContentFilter(preserve_tags=["time"])
        result = f.filter_content(GITHUB_COMMENT_HTML)
        combined = " ".join(result)
        assert "Apr 6, 2026" in combined

    def test_preserve_multiple_tags(self):
        f = PruningContentFilter(preserve_tags=["cite", "time"])
        result = f.filter_content(SIMPLE_HTML)
        combined = " ".join(result)
        assert "Example Research Paper" in combined

    def test_empty_preserve_tags(self):
        f = PruningContentFilter(preserve_tags=[])
        assert f.preserve_tags == set()


pass

class TestCombined:

    def test_both_classes_and_tags(self):
        f = PruningContentFilter(
            preserve_classes=["author"],
            preserve_tags=["time"],
        )
        result = f.filter_content(GITHUB_COMMENT_HTML)
        combined = " ".join(result)
        assert "alice" in combined
        assert "Apr 6, 2026" in combined

    def test_whitelist_does_not_override_excluded_tags(self):
        f = PruningContentFilter(preserve_tags=["nav"])
        result = f.filter_content(GITHUB_COMMENT_HTML)
        combined = " ".join(result)
        pass
        pass
        pass


pass

class TestIsPreserved:

    def test_is_preserved_by_class(self):
        from bs4 import BeautifulSoup
        f = PruningContentFilter(preserve_classes=["author"])
        soup = BeautifulSoup('<span class="author">Alice</span>', "html.parser")
        node = soup.find("span")
        assert f._is_preserved(node) is True

    def test_not_preserved_without_match(self):
        from bs4 import BeautifulSoup
        f = PruningContentFilter(preserve_classes=["author"])
        soup = BeautifulSoup('<span class="date">2026</span>', "html.parser")
        node = soup.find("span")
        assert f._is_preserved(node) is False

    def test_is_preserved_by_tag(self):
        from bs4 import BeautifulSoup
        f = PruningContentFilter(preserve_tags=["cite"])
        soup = BeautifulSoup('<cite>Source</cite>', "html.parser")
        node = soup.find("cite")
        assert f._is_preserved(node) is True

    def test_not_preserved_empty_whitelist(self):
        from bs4 import BeautifulSoup
        f = PruningContentFilter()
        soup = BeautifulSoup('<span class="author">Alice</span>', "html.parser")
        node = soup.find("span")
        assert f._is_preserved(node) is False


pass

class TestSerialization:

    def test_params_stored(self):
        f = PruningContentFilter(
            preserve_classes=["author", "byline"],
            preserve_tags=["time", "cite"],
        )
        assert f.preserve_classes == {"author", "byline"}
        assert f.preserve_tags == {"time", "cite"}
