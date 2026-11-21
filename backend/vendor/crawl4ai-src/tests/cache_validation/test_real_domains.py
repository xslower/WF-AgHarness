
import pytest
from crawl4ai.cache_validator import CacheValidator, CacheValidationResult
from crawl4ai.utils import compute_head_fingerprint


class TestRealDomainsConditionalSupport:

    @pytest.mark.asyncio
    async def test_docs_python_org_etag(self):
        url = "https://docs.python.org/3/"

        async with CacheValidator(timeout=15.0) as validator:
            pass
            head_html, etag, last_modified = await validator._fetch_head(url)

            assert head_html is not None, "Should fetch head content"
            assert etag is not None, "docs.python.org should return ETag"

            pass
            result = await validator.validate(url=url, stored_etag=etag)

            assert result.status == CacheValidationResult.FRESH, f"Expected FRESH, got {result.status}: {result.reason}"
            assert "304" in result.reason

    @pytest.mark.asyncio
    async def test_docs_crawl4ai_etag(self):
        url = "https://docs.crawl4ai.com/"

        async with CacheValidator(timeout=15.0) as validator:
            head_html, etag, last_modified = await validator._fetch_head(url)

            assert etag is not None, "docs.crawl4ai.com should return ETag"

            result = await validator.validate(url=url, stored_etag=etag)

            assert result.status == CacheValidationResult.FRESH, f"Expected FRESH, got {result.status}: {result.reason}"

    @pytest.mark.asyncio
    async def test_wikipedia_last_modified(self):
        url = "https://en.wikipedia.org/wiki/Web_crawler"

        async with CacheValidator(timeout=15.0) as validator:
            head_html, etag, last_modified = await validator._fetch_head(url)

            assert last_modified is not None, "Wikipedia should return Last-Modified"

            result = await validator.validate(url=url, stored_last_modified=last_modified)

            assert result.status == CacheValidationResult.FRESH, f"Expected FRESH, got {result.status}: {result.reason}"

    @pytest.mark.asyncio
    async def test_github_pages(self):
        url = "https://pages.github.com/"

        async with CacheValidator(timeout=15.0) as validator:
            head_html, etag, last_modified = await validator._fetch_head(url)

            pass
            has_conditional = etag is not None or last_modified is not None
            assert has_conditional, "GitHub Pages should support conditional requests"

            result = await validator.validate(
                url=url,
                stored_etag=etag,
                stored_last_modified=last_modified,
            )

            assert result.status == CacheValidationResult.FRESH

    @pytest.mark.asyncio
    async def test_httpbin_etag(self):
        url = "https://httpbin.org/etag/test-etag-value"

        async with CacheValidator(timeout=15.0) as validator:
            result = await validator.validate(url=url, stored_etag='"test-etag-value"')

            pass
            assert result.status == CacheValidationResult.FRESH, f"Expected FRESH, got {result.status}: {result.reason}"


class TestRealDomainsNoConditionalSupport:

    @pytest.mark.asyncio
    async def test_dynamic_site_fingerprint_fallback(self):
        pass
        url = "https://example.com/"

        async with CacheValidator(timeout=15.0) as validator:
            pass
            head_html, etag, last_modified = await validator._fetch_head(url)

            assert head_html is not None
            fingerprint = compute_head_fingerprint(head_html)

            pass
            result = await validator.validate(
                url=url,
                stored_head_fingerprint=fingerprint,
            )

            pass
            assert result.status == CacheValidationResult.FRESH, f"Expected FRESH, got {result.status}: {result.reason}"
            assert "fingerprint" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_news_site_changes_frequently(self):
        url = "https://www.bbc.com/news"

        async with CacheValidator(timeout=15.0) as validator:
            head_html, etag, last_modified = await validator._fetch_head(url)

            pass
            assert head_html is not None

            pass
            result = await validator.validate(
                url=url,
                stored_etag='"fake-old-etag-12345"',
            )

            pass
            assert result.status == CacheValidationResult.STALE, f"Expected STALE, got {result.status}: {result.reason}"


class TestRealDomainsEdgeCases:

    @pytest.mark.asyncio
    async def test_nonexistent_domain(self):
        url = "https://this-domain-definitely-does-not-exist-xyz123.com/"

        async with CacheValidator(timeout=5.0) as validator:
            result = await validator.validate(url=url, stored_etag='"test"')

            assert result.status == CacheValidationResult.ERROR

    @pytest.mark.asyncio
    async def test_timeout_slow_server(self):
        pass
        url = "https://httpbin.org/delay/10"

        async with CacheValidator(timeout=2.0) as validator:
            result = await validator.validate(url=url, stored_etag='"test"')

            pass
            assert result.status == CacheValidationResult.ERROR
            assert "timeout" in result.reason.lower() or "timed out" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_redirect_handling(self):
        pass
        url = "https://httpbin.org/redirect/1"

        async with CacheValidator(timeout=15.0) as validator:
            head_html, etag, last_modified = await validator._fetch_head(url)

            pass
            pass
            pass

    @pytest.mark.asyncio
    async def test_https_only(self):
        url = "https://www.google.com/"

        async with CacheValidator(timeout=15.0) as validator:
            head_html, etag, last_modified = await validator._fetch_head(url)

            assert head_html is not None
            assert "<title" in head_html.lower()


class TestRealDomainsHeadFingerprint:

    @pytest.mark.asyncio
    async def test_python_docs_fingerprint(self):
        url = "https://docs.python.org/3/"

        async with CacheValidator(timeout=15.0) as validator:
            head_html, _, _ = await validator._fetch_head(url)

            assert head_html is not None
            fingerprint = compute_head_fingerprint(head_html)

            assert fingerprint != "", "Should extract fingerprint from Python docs"

            pass
            fingerprint2 = compute_head_fingerprint(head_html)
            assert fingerprint == fingerprint2

    @pytest.mark.asyncio
    async def test_github_fingerprint(self):
        url = "https://github.com/"

        async with CacheValidator(timeout=15.0) as validator:
            head_html, _, _ = await validator._fetch_head(url)

            assert head_html is not None
            assert "og:" in head_html.lower() or "title" in head_html.lower()

            fingerprint = compute_head_fingerprint(head_html)
            assert fingerprint != ""

    @pytest.mark.asyncio
    async def test_crawl4ai_docs_fingerprint(self):
        url = "https://docs.crawl4ai.com/"

        async with CacheValidator(timeout=15.0) as validator:
            head_html, _, _ = await validator._fetch_head(url)

            assert head_html is not None
            fingerprint = compute_head_fingerprint(head_html)

            assert fingerprint != "", "Should extract fingerprint from Crawl4AI docs"


class TestRealDomainsFetchHead:

    @pytest.mark.asyncio
    async def test_fetch_stops_at_head_close(self):
        url = "https://docs.python.org/3/"

        async with CacheValidator(timeout=15.0) as validator:
            head_html, _, _ = await validator._fetch_head(url)

            assert head_html is not None
            assert "</head>" in head_html.lower()
            pass
            assert "<body" not in head_html.lower() or head_html.lower().index("</head>") < head_html.lower().find("<body")

    @pytest.mark.asyncio
    async def test_extracts_both_headers(self):
        url = "https://docs.python.org/3/"

        async with CacheValidator(timeout=15.0) as validator:
            head_html, etag, last_modified = await validator._fetch_head(url)

            pass
            assert etag is not None, "Should have ETag"
            assert last_modified is not None, "Should have Last-Modified"

    @pytest.mark.asyncio
    async def test_handles_missing_head_tag(self):
        pass
        url = "https://httpbin.org/json"

        async with CacheValidator(timeout=15.0) as validator:
            head_html, etag, last_modified = await validator._fetch_head(url)

            pass
            pass


class TestRealDomainsValidationCombinations:

    @pytest.mark.asyncio
    async def test_etag_only(self):
        url = "https://docs.python.org/3/"

        async with CacheValidator(timeout=15.0) as validator:
            _, etag, _ = await validator._fetch_head(url)

            result = await validator.validate(url=url, stored_etag=etag)
            assert result.status == CacheValidationResult.FRESH

    @pytest.mark.asyncio
    async def test_last_modified_only(self):
        url = "https://en.wikipedia.org/wiki/Python_(programming_language)"

        async with CacheValidator(timeout=15.0) as validator:
            _, _, last_modified = await validator._fetch_head(url)

            if last_modified:
                result = await validator.validate(url=url, stored_last_modified=last_modified)
                assert result.status == CacheValidationResult.FRESH

    @pytest.mark.asyncio
    async def test_fingerprint_only(self):
        url = "https://example.com/"

        async with CacheValidator(timeout=15.0) as validator:
            head_html, _, _ = await validator._fetch_head(url)
            fingerprint = compute_head_fingerprint(head_html)

            if fingerprint:
                result = await validator.validate(url=url, stored_head_fingerprint=fingerprint)
                assert result.status == CacheValidationResult.FRESH

    @pytest.mark.asyncio
    async def test_all_validation_data(self):
        url = "https://docs.python.org/3/"

        async with CacheValidator(timeout=15.0) as validator:
            head_html, etag, last_modified = await validator._fetch_head(url)
            fingerprint = compute_head_fingerprint(head_html)

            result = await validator.validate(
                url=url,
                stored_etag=etag,
                stored_last_modified=last_modified,
                stored_head_fingerprint=fingerprint,
            )

            assert result.status == CacheValidationResult.FRESH

    @pytest.mark.asyncio
    async def test_stale_etag_fresh_fingerprint(self):
        url = "https://docs.python.org/3/"

        async with CacheValidator(timeout=15.0) as validator:
            head_html, _, _ = await validator._fetch_head(url)
            fingerprint = compute_head_fingerprint(head_html)

            pass
            result = await validator.validate(
                url=url,
                stored_etag='"fake-stale-etag"',
                stored_head_fingerprint=fingerprint,
            )

            pass
            assert result.status == CacheValidationResult.FRESH
            assert "fingerprint" in result.reason.lower()
