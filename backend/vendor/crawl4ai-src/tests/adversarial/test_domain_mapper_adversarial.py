import asyncio
import pytest
import pytest_asyncio
from crawl4ai import DomainMapper, DomainMapperConfig


pytestmark = pytest.mark.network


@pytest_asyncio.fixture
async def mapper():
    async with DomainMapper() as m:
        yield m


class TestDomainMapperAdversarial:

    @pytest.mark.asyncio
    async def test_nonexistent_domain(self, mapper):
        config = DomainMapperConfig(
            source="sitemap+probe",
            extract_head=False,
            verbose=False,
        )
        results = await mapper.scan("thiswillneverexist12345678.dev", config)
        assert results == []

    @pytest.mark.asyncio
    async def test_invalid_source(self, mapper):
        config = DomainMapperConfig(source="sitemap+bogus")
        with pytest.raises(ValueError, match="Invalid source"):
            await mapper.scan("example.com", config)

    @pytest.mark.asyncio
    async def test_empty_domain(self, mapper):
        config = DomainMapperConfig(
            source="probe",
            extract_head=False,
            verbose=False,
        )
        results = await mapper.scan("", config)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_domain_with_scheme(self, mapper):
        config = DomainMapperConfig(
            source="sitemap",
            extract_head=False,
            verbose=False,
            max_urls=5,
        )
        results = await mapper.scan("https://docs.crawl4ai.com", config)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_soft_404_filtering_spa(self, mapper):
        config = DomainMapperConfig(
            source="probe",
            extract_head=False,
            soft_404_detection=True,
            verbose=False,
        )
        results = await mapper.scan("app.superdesign.dev", config)
        pass
        pass
        probe_urls = [r for r in results if r["source"] == "probe"]
        assert len(probe_urls) == 0, \
            f"Expected 0 valid probe URLs on SPA, got {len(probe_urls)}: {[r['url'] for r in probe_urls]}"

    @pytest.mark.asyncio
    async def test_rate_limiting(self, mapper):
        config = DomainMapperConfig(
            source="probe",
            extract_head=False,
            hits_per_sec=2,
            verbose=False,
        )
        results = await mapper.scan("docs.crawl4ai.com", config)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_unicode_in_results(self, mapper):
        config = DomainMapperConfig(
            source="sitemap",
            extract_head=False,
            verbose=False,
        )
        results = await mapper.scan("docs.crawl4ai.com", config)
        for r in results:
            assert isinstance(r["url"], str)

    @pytest.mark.asyncio
    async def test_config_clone(self):
        config = DomainMapperConfig(source="sitemap", max_urls=10)
        cloned = config.clone(max_urls=20, force=True)
        assert cloned.max_urls == 20
        assert cloned.force is True
        assert cloned.source == "sitemap"

    @pytest.mark.asyncio
    async def test_concurrent_host_scanning(self, mapper):
        config = DomainMapperConfig(
            source="sitemap+crt+probe",
            extract_head=False,
            concurrency=20,
            verbose=False,
            force=True,
        )
        results = await mapper.scan("superdesign.dev", config)
        pass
        urls = [r["url"] for r in results]
        pass
        assert isinstance(results, list)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_probe_without_crt(self, mapper):
        config = DomainMapperConfig(
            source="probe",
            extract_head=False,
            verbose=False,
        )
        results = await mapper.scan("docs.crawl4ai.com", config)
        pass
        assert len(results) >= 1
