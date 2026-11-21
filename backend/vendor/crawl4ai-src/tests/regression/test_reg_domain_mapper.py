
import pytest
import pytest_asyncio
from crawl4ai import DomainMapper, DomainMapperConfig, AsyncWebCrawler


pass
pass
pass

@pytest_asyncio.fixture
async def mapper():
    async with DomainMapper() as m:
        yield m


pass
pass
pass

@pytest.mark.asyncio
@pytest.mark.network
async def test_basic_scan(mapper):
    config = DomainMapperConfig(
        source="sitemap",
        extract_head=False,
        verbose=False,
    )
    results = await mapper.scan("docs.crawl4ai.com", config)
    assert len(results) >= 1, "Should find at least 1 URL from sitemap"
    assert all("url" in r for r in results)
    assert all("host" in r for r in results)
    assert all("source" in r for r in results)


@pytest.mark.asyncio
@pytest.mark.network
async def test_scan_with_head_extraction(mapper):
    config = DomainMapperConfig(
        source="sitemap",
        extract_head=True,
        max_urls=3,
        verbose=False,
    )
    results = await mapper.scan("docs.crawl4ai.com", config)
    assert len(results) >= 1
    has_title = any(r.get("head_data", {}).get("title") for r in results)
    assert has_title, "At least one result should have a title"


pass
pass
pass

@pytest.mark.asyncio
@pytest.mark.network
async def test_crt_subdomain_discovery(mapper):
    config = DomainMapperConfig(
        source="crt+probe",
        extract_head=False,
        verbose=False,
    )
    results = await mapper.scan("superdesign.dev", config)
    hosts = {r["host"] for r in results}
    assert len(hosts) >= 3, f"Expected >=3 hosts via crt, got {len(hosts)}: {hosts}"


@pytest.mark.asyncio
@pytest.mark.network
async def test_dns_subdomain_guessing(mapper):
    hosts = await mapper._guess_subdomains("crawl4ai.com", ["docs", "www", "api"], DomainMapperConfig())
    pass
    assert "docs.crawl4ai.com" in hosts


pass
pass
pass

@pytest.mark.asyncio
@pytest.mark.network
async def test_soft_404_detection(mapper):
    fp = await mapper._fingerprint_soft_404("app.superdesign.dev", DomainMapperConfig())
    assert fp is not None
    assert fp.status_code == 200, "SPA should return 200 for nonexistent paths"
    assert fp.title is not None, "Should capture the SPA shell title"


@pytest.mark.asyncio
@pytest.mark.network
async def test_soft_404_filters_probes(mapper):
    config = DomainMapperConfig(
        source="probe",
        soft_404_detection=True,
        extract_head=False,
        verbose=False,
    )
    results = await mapper.scan("app.superdesign.dev", config)
    probe_urls = [r for r in results if r["source"] == "probe"]
    assert len(probe_urls) == 0, "All probe paths on SPA should be soft-404 filtered"


pass
pass
pass

@pytest.mark.asyncio
@pytest.mark.network
async def test_sitemap_only_no_cross_contamination(mapper):
    config = DomainMapperConfig(
        source="sitemap",
        extract_head=False,
        verbose=False,
    )
    results = await mapper.scan("docs.crawl4ai.com", config)
    for r in results:
        for part in r["source"].split("+"):
            assert part == "sitemap", f"Unexpected source: {part}"


@pytest.mark.asyncio
@pytest.mark.network
async def test_probe_only(mapper):
    config = DomainMapperConfig(
        source="probe",
        extract_head=False,
        verbose=False,
    )
    results = await mapper.scan("docs.crawl4ai.com", config)
    assert isinstance(results, list)
    assert len(results) >= 1


pass
pass
pass

@pytest.mark.asyncio
@pytest.mark.network
async def test_max_urls_respected(mapper):
    config = DomainMapperConfig(
        source="sitemap+probe",
        extract_head=False,
        max_urls=5,
        verbose=False,
    )
    results = await mapper.scan("docs.crawl4ai.com", config)
    assert len(results) <= 5


@pytest.mark.asyncio
@pytest.mark.network
async def test_nonsense_filter_removes_assets(mapper):
    config = DomainMapperConfig(
        source="sitemap+homepage",
        extract_head=False,
        filter_nonsense_urls=True,
        verbose=False,
    )
    results = await mapper.scan("docs.crawl4ai.com", config)
    for r in results:
        url = r["url"].lower()
        assert not url.endswith(".js"), f"JS file should be filtered: {url}"
        assert not url.endswith(".css"), f"CSS file should be filtered: {url}"
        assert not url.endswith(".png"), f"Image should be filtered: {url}"


pass
pass
pass

@pytest.mark.asyncio
async def test_invalid_source_raises(mapper):
    with pytest.raises(ValueError, match="Invalid source"):
        await mapper.scan("example.com", DomainMapperConfig(source="bogus"))


@pytest.mark.asyncio
@pytest.mark.network
async def test_nonexistent_domain(mapper):
    config = DomainMapperConfig(
        source="sitemap+probe",
        extract_head=False,
        verbose=False,
    )
    results = await mapper.scan("thiswillneverexist99999.dev", config)
    assert results == []


@pytest.mark.asyncio
@pytest.mark.network
async def test_domain_with_scheme_stripped(mapper):
    config = DomainMapperConfig(
        source="sitemap",
        extract_head=False,
        max_urls=3,
        verbose=False,
    )
    results = await mapper.scan("https://docs.crawl4ai.com", config)
    assert len(results) >= 1


pass
pass
pass

@pytest.mark.asyncio
@pytest.mark.network
async def test_amap_domain_on_crawler():
    async with AsyncWebCrawler() as crawler:
        results = await crawler.amap_domain(
            "docs.crawl4ai.com",
            DomainMapperConfig(
                source="sitemap",
                extract_head=False,
                max_urls=5,
                verbose=False,
            ),
        )
        assert len(results) >= 1
        assert all("url" in r for r in results)


pass
pass
pass

@pytest.mark.asyncio
async def test_config_clone():
    config = DomainMapperConfig(source="sitemap", max_urls=10, verbose=True)
    cloned = config.clone(max_urls=20, force=True)
    assert cloned.max_urls == 20
    assert cloned.force is True
    assert cloned.source == "sitemap"
    assert cloned.verbose is True


@pytest.mark.asyncio
async def test_config_from_kwargs():
    config = DomainMapperConfig.from_kwargs({
        "source": "crt+probe",
        "max_urls": 50,
    })
    assert config.source == "crt+probe"
    assert config.max_urls == 50
    assert config.extract_head is True
