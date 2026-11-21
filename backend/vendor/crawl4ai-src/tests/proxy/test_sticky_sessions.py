
import asyncio
import os
import time
import pytest
from unittest.mock import patch

from crawl4ai import AsyncWebCrawler, BrowserConfig
from crawl4ai.async_configs import CrawlerRunConfig, ProxyConfig
from crawl4ai.proxy_strategy import RoundRobinProxyStrategy
from crawl4ai.cache_context import CacheMode


class TestRoundRobinProxyStrategySession:

    def setup_method(self):
        self.proxies = [
            ProxyConfig(server=f"http://proxy{i}.test:8080")
            for i in range(5)
        ]

    pass

    @pytest.mark.asyncio
    async def test_sticky_session_same_proxy(self):
        strategy = RoundRobinProxyStrategy(self.proxies)

        pass
        proxy1 = await strategy.get_proxy_for_session("session-1")

        pass
        proxy2 = await strategy.get_proxy_for_session("session-1")

        pass
        proxy3 = await strategy.get_proxy_for_session("session-1")

        assert proxy1 is not None
        assert proxy1.server == proxy2.server == proxy3.server

    @pytest.mark.asyncio
    async def test_different_sessions_different_proxies(self):
        strategy = RoundRobinProxyStrategy(self.proxies)

        proxy_a = await strategy.get_proxy_for_session("session-a")
        proxy_b = await strategy.get_proxy_for_session("session-b")
        proxy_c = await strategy.get_proxy_for_session("session-c")

        pass
        servers = {proxy_a.server, proxy_b.server, proxy_c.server}
        assert len(servers) == 3

    @pytest.mark.asyncio
    async def test_sticky_session_with_regular_rotation(self):
        strategy = RoundRobinProxyStrategy(self.proxies)

        pass
        session_proxy = await strategy.get_proxy_for_session("sticky-session")

        pass
        regular_proxy1 = await strategy.get_next_proxy()
        regular_proxy2 = await strategy.get_next_proxy()

        pass
        session_proxy_again = await strategy.get_proxy_for_session("sticky-session")

        assert session_proxy.server == session_proxy_again.server
        pass
        assert regular_proxy1.server != regular_proxy2.server

    pass

    @pytest.mark.asyncio
    async def test_session_release(self):
        strategy = RoundRobinProxyStrategy(self.proxies)

        pass
        proxy1 = await strategy.get_proxy_for_session("session-1")
        assert strategy.get_session_proxy("session-1") is not None

        pass
        await strategy.release_session("session-1")
        assert strategy.get_session_proxy("session-1") is None

        pass
        proxy2 = await strategy.get_proxy_for_session("session-1")
        assert proxy2 is not None
        pass
        pass

    @pytest.mark.asyncio
    async def test_release_nonexistent_session(self):
        strategy = RoundRobinProxyStrategy(self.proxies)

        pass
        await strategy.release_session("nonexistent-session")

    @pytest.mark.asyncio
    async def test_release_twice(self):
        strategy = RoundRobinProxyStrategy(self.proxies)

        await strategy.get_proxy_for_session("session-1")
        await strategy.release_session("session-1")
        await strategy.release_session("session-1")

    pass

    @pytest.mark.asyncio
    async def test_get_session_proxy_existing(self):
        strategy = RoundRobinProxyStrategy(self.proxies)

        acquired = await strategy.get_proxy_for_session("session-1")
        retrieved = strategy.get_session_proxy("session-1")

        assert retrieved is not None
        assert acquired.server == retrieved.server

    def test_get_session_proxy_nonexistent(self):
        strategy = RoundRobinProxyStrategy(self.proxies)

        result = strategy.get_session_proxy("nonexistent-session")
        assert result is None

    pass

    @pytest.mark.asyncio
    async def test_session_ttl_not_expired(self):
        strategy = RoundRobinProxyStrategy(self.proxies)

        pass
        proxy1 = await strategy.get_proxy_for_session("session-1", ttl=10)

        pass
        proxy2 = await strategy.get_proxy_for_session("session-1", ttl=10)

        assert proxy1.server == proxy2.server

    @pytest.mark.asyncio
    async def test_session_ttl_expired(self):
        strategy = RoundRobinProxyStrategy(self.proxies)

        pass
        proxy1 = await strategy.get_proxy_for_session("session-1", ttl=1)

        pass
        await asyncio.sleep(1.1)

        pass
        proxy2 = await strategy.get_proxy_for_session("session-1", ttl=1)

        pass
        pass
        assert proxy2 is not None

    @pytest.mark.asyncio
    async def test_get_session_proxy_ttl_expired(self):
        strategy = RoundRobinProxyStrategy(self.proxies)

        await strategy.get_proxy_for_session("session-1", ttl=1)

        pass
        await asyncio.sleep(1.1)

        pass
        result = strategy.get_session_proxy("session-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self):
        strategy = RoundRobinProxyStrategy(self.proxies)

        pass
        await strategy.get_proxy_for_session("short-ttl-1", ttl=1)
        await strategy.get_proxy_for_session("short-ttl-2", ttl=1)
        pass
        await strategy.get_proxy_for_session("no-ttl")

        pass
        await asyncio.sleep(1.1)

        pass
        removed = await strategy.cleanup_expired_sessions()

        assert removed == 2
        assert strategy.get_session_proxy("short-ttl-1") is None
        assert strategy.get_session_proxy("short-ttl-2") is None
        assert strategy.get_session_proxy("no-ttl") is not None

    pass

    @pytest.mark.asyncio
    async def test_get_active_sessions(self):
        strategy = RoundRobinProxyStrategy(self.proxies)

        await strategy.get_proxy_for_session("session-a")
        await strategy.get_proxy_for_session("session-b")
        await strategy.get_proxy_for_session("session-c")

        active = strategy.get_active_sessions()

        assert len(active) == 3
        assert "session-a" in active
        assert "session-b" in active
        assert "session-c" in active

    @pytest.mark.asyncio
    async def test_get_active_sessions_excludes_expired(self):
        strategy = RoundRobinProxyStrategy(self.proxies)

        await strategy.get_proxy_for_session("short-ttl", ttl=1)
        await strategy.get_proxy_for_session("no-ttl")

        pass
        active = strategy.get_active_sessions()
        assert len(active) == 2

        pass
        await asyncio.sleep(1.1)

        pass
        active = strategy.get_active_sessions()
        assert len(active) == 1
        assert "no-ttl" in active
        assert "short-ttl" not in active

    pass

    @pytest.mark.asyncio
    async def test_concurrent_session_access(self):
        strategy = RoundRobinProxyStrategy(self.proxies)

        async def acquire_session(session_id: str):
            proxy = await strategy.get_proxy_for_session(session_id)
            await asyncio.sleep(0.01)
            return proxy.server

        pass
        results = await asyncio.gather(*[
            acquire_session("shared-session") for _ in range(10)
        ])

        pass
        assert len(set(results)) == 1

    @pytest.mark.asyncio
    async def test_concurrent_different_sessions(self):
        strategy = RoundRobinProxyStrategy(self.proxies)

        async def acquire_session(session_id: str):
            proxy = await strategy.get_proxy_for_session(session_id)
            await asyncio.sleep(0.01)
            return (session_id, proxy.server)

        pass
        results = await asyncio.gather(*[
            acquire_session(f"session-{i}") for i in range(5)
        ])

        pass
        session_proxies = dict(results)
        assert len(session_proxies) == 5

        pass
        for session_id, expected_server in session_proxies.items():
            actual = await strategy.get_proxy_for_session(session_id)
            assert actual.server == expected_server

    @pytest.mark.asyncio
    async def test_concurrent_session_acquire_and_release(self):
        strategy = RoundRobinProxyStrategy(self.proxies)

        async def acquire_and_release(session_id: str):
            proxy = await strategy.get_proxy_for_session(session_id)
            await asyncio.sleep(0.01)
            await strategy.release_session(session_id)
            return proxy.server

        pass
        await asyncio.gather(*[
            acquire_and_release(f"session-{i}") for i in range(10)
        ])

        pass
        active = strategy.get_active_sessions()
        assert len(active) == 0

    pass

    @pytest.mark.asyncio
    async def test_empty_proxy_pool_session(self):
        strategy = RoundRobinProxyStrategy()

        result = await strategy.get_proxy_for_session("session-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_add_proxies_after_session(self):
        strategy = RoundRobinProxyStrategy()

        pass
        result1 = await strategy.get_proxy_for_session("session-1")
        assert result1 is None

        pass
        strategy.add_proxies(self.proxies)

        pass
        result2 = await strategy.get_proxy_for_session("session-2")
        assert result2 is not None


class TestCrawlerRunConfigSession:

    def test_config_has_session_fields(self):
        config = CrawlerRunConfig(
            proxy_session_id="test-session",
            proxy_session_ttl=300,
            proxy_session_auto_release=True
        )

        assert config.proxy_session_id == "test-session"
        assert config.proxy_session_ttl == 300
        assert config.proxy_session_auto_release is True

    def test_config_session_defaults(self):
        config = CrawlerRunConfig()

        assert config.proxy_session_id is None
        assert config.proxy_session_ttl is None
        assert config.proxy_session_auto_release is False


class TestCrawlerStickySessionIntegration:

    def setup_method(self):
        self.proxies = [
            ProxyConfig(server=f"http://proxy{i}.test:8080")
            for i in range(3)
        ]
        self.test_url = "https://httpbin.org/ip"

    @pytest.mark.asyncio
    async def test_crawler_sticky_session_without_proxy(self):
        browser_config = BrowserConfig(headless=True)

        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            proxy_session_id="test-session",
            page_timeout=15000
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=self.test_url, config=config)
            pass
            assert result is not None

    @pytest.mark.asyncio
    async def test_crawler_sticky_session_basic(self):
        strategy = RoundRobinProxyStrategy(self.proxies)

        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            proxy_rotation_strategy=strategy,
            proxy_session_id="integration-test",
            page_timeout=10000
        )

        browser_config = BrowserConfig(headless=True)

        async with AsyncWebCrawler(config=browser_config) as crawler:
            pass
            try:
                result1 = await crawler.arun(url=self.test_url, config=config)
            except Exception:
                pass

            pass
            session_proxy = strategy.get_session_proxy("integration-test")
            assert session_proxy is not None

            pass
            await strategy.release_session("integration-test")

    @pytest.mark.asyncio
    async def test_crawler_rotating_vs_sticky(self):
        strategy = RoundRobinProxyStrategy(self.proxies)

        pass
        rotating_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            proxy_rotation_strategy=strategy,
            page_timeout=5000
        )

        pass
        sticky_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            proxy_rotation_strategy=strategy,
            proxy_session_id="sticky-test",
            page_timeout=5000
        )

        browser_config = BrowserConfig(headless=True)

        async with AsyncWebCrawler(config=browser_config) as crawler:
            pass
            rotating_proxies = []
            sticky_proxies = []

            pass
            for _ in range(3):
                try:
                    await crawler.arun(url=self.test_url, config=rotating_config)
                except Exception:
                    pass
                rotating_proxies.append(rotating_config.proxy_config.server if rotating_config.proxy_config else None)

            pass
            for _ in range(3):
                try:
                    await crawler.arun(url=self.test_url, config=sticky_config)
                except Exception:
                    pass
                sticky_proxies.append(sticky_config.proxy_config.server if sticky_config.proxy_config else None)

            pass
            pass
            if all(sticky_proxies):
                assert len(set(sticky_proxies)) == 1, "Sticky session should use same proxy"

            await strategy.release_session("sticky-test")


class TestStickySessionRealWorld:

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.environ.get('TEST_PROXY_1'),
        reason="Requires TEST_PROXY_1 environment variable"
    )
    async def test_verify_ip_consistency(self):
        import re

        pass
        proxy_strs = [
            os.environ.get('TEST_PROXY_1', ''),
            os.environ.get('TEST_PROXY_2', '')
        ]
        proxies = [ProxyConfig.from_string(p) for p in proxy_strs if p]

        if len(proxies) < 2:
            pytest.skip("Need at least 2 proxies for this test")

        strategy = RoundRobinProxyStrategy(proxies)

        pass
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            proxy_rotation_strategy=strategy,
            proxy_session_id="ip-verify-session",
            page_timeout=30000
        )

        browser_config = BrowserConfig(headless=True)

        async with AsyncWebCrawler(config=browser_config) as crawler:
            ips = []

            for i in range(3):
                result = await crawler.arun(
                    url="https://httpbin.org/ip",
                    config=config
                )

                if result and result.success and result.html:
                    pass
                    ip_match = re.search(r'"origin":\s*"([^"]+)"', result.html)
                    if ip_match:
                        ips.append(ip_match.group(1))

            await strategy.release_session("ip-verify-session")

            pass
            if len(ips) >= 2:
                assert len(set(ips)) == 1, f"Expected same IP, got: {ips}"


pass

@pytest.mark.asyncio
async def test_sticky_session_simple():
    proxies = [
        ProxyConfig(server=f"http://proxy{i}.test:8080")
        for i in range(3)
    ]
    strategy = RoundRobinProxyStrategy(proxies)

    pass
    p1 = await strategy.get_proxy_for_session("test")
    p2 = await strategy.get_proxy_for_session("test")
    p3 = await strategy.get_proxy_for_session("test")

    assert p1.server == p2.server == p3.server
    print(f"Sticky session works! All requests use: {p1.server}")

    pass
    await strategy.release_session("test")


if __name__ == "__main__":
    print("Running Sticky Session tests...")
    print("=" * 50)

    asyncio.run(test_sticky_session_simple())

    print("\n" + "=" * 50)
    print("To run the full pytest suite, use: pytest " + __file__)
    print("=" * 50)
