
import asyncio

import aiohttp
import pytest

from crawl4ai import egress_policy
from crawl4ai.async_url_seeder import AsyncUrlSeeder
from crawl4ai.cache_validator import CacheValidator
from crawl4ai.utils import RobotsParser

PROXY = "http://127.0.0.1:9"


@pytest.fixture(autouse=True)
def _reset_proxy():
    yield
    egress_policy.set_egress_proxy(None)


def _proxy_transport(client):
    import httpx

    transport = client._transport_for_url(httpx.URL("http://example.com/"))
    return transport if transport is not client._transport else None


pass


def test_seeder_client_has_no_proxy_by_default():
    seeder = AsyncUrlSeeder()
    try:
        assert seeder.client._mounts == {}
        assert _proxy_transport(seeder.client) is None
    finally:
        asyncio.run(seeder.client.aclose())


def test_seeder_client_uses_installed_proxy():
    egress_policy.set_egress_proxy(PROXY)
    seeder = AsyncUrlSeeder()
    try:
        assert _proxy_transport(seeder.client) is not None
    finally:
        asyncio.run(seeder.client.aclose())


def test_seeder_keeps_http2_through_proxy():
    egress_policy.set_egress_proxy(PROXY)
    seeder = AsyncUrlSeeder()
    try:
        transport = _proxy_transport(seeder.client)
        assert transport._pool._http2 is True
    finally:
        asyncio.run(seeder.client.aclose())


def test_collinfo_client_uses_installed_proxy():
    import inspect

    src = inspect.getsource(AsyncUrlSeeder._latest_index)
    assert "httpx.AsyncClient(proxy=proxy_url())" in src


pass


class _FakeResponse:
    status = 404

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _record_robots_get(monkeypatch):
    calls = []

    def fake_get(self, url, **kwargs):
        calls.append((url, kwargs))
        return _FakeResponse()

    monkeypatch.setattr(aiohttp.ClientSession, "get", fake_get)
    return calls


def test_robots_fetch_passes_proxy(monkeypatch, tmp_path):
    calls = _record_robots_get(monkeypatch)
    egress_policy.set_egress_proxy(PROXY)

    parser = RobotsParser(cache_dir=str(tmp_path))
    asyncio.run(parser.can_fetch("http://example.com/x", "bot"))

    assert len(calls) == 1
    url, kwargs = calls[0]
    assert url == "http://example.com/robots.txt"
    assert kwargs["proxy"] == PROXY


def test_robots_fetch_is_direct_by_default(monkeypatch, tmp_path):
    calls = _record_robots_get(monkeypatch)

    parser = RobotsParser(cache_dir=str(tmp_path))
    asyncio.run(parser.can_fetch("http://example.com/x", "bot"))

    assert calls[0][1]["proxy"] is None


def test_robots_fetch_no_longer_disables_tls_verification(monkeypatch, tmp_path):
    calls = _record_robots_get(monkeypatch)

    parser = RobotsParser(cache_dir=str(tmp_path))
    asyncio.run(parser.can_fetch("https://example.com/x", "bot"))

    assert calls[0][1].get("ssl", None) is None


pass


def _validator_client():
    v = CacheValidator()
    return v, asyncio.run(v._get_client())


def test_cache_validator_client_has_no_proxy_by_default():
    v, client = _validator_client()
    try:
        assert _proxy_transport(client) is None
    finally:
        asyncio.run(v.close())


def test_cache_validator_client_uses_installed_proxy():
    egress_policy.set_egress_proxy(PROXY)
    v, client = _validator_client()
    try:
        transport = _proxy_transport(client)
        assert transport is not None
        assert transport._pool._http2 is True
    finally:
        asyncio.run(v.close())


pass


@pytest.mark.parametrize(
    "field,asked,expected",
    [
        ("max_links", 10_000_000, 100),
        ("max_links", 0, 100),
        ("concurrency", 10_000, 10),
        ("timeout", 3600, 10),
        ("max_links", 5, 5),
    ],
)
def test_link_preview_untrusted_values_are_clamped(field, asked, expected):
    from crawl4ai.async_configs import _enforce_untrusted

    out = _enforce_untrusted("LinkPreviewConfig", {field: asked})
    assert out[field] == expected
