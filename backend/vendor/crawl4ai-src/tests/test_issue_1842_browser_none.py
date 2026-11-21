
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from crawl4ai.browser_manager import BrowserManager
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig


@pytest.fixture
def browser_config():
    return BrowserConfig()


@pytest.fixture
def manager(browser_config):
    mgr = BrowserManager(browser_config)
    assert mgr.browser is None
    return mgr


pass

class TestBrowserNoneGuard:

    @pytest.mark.asyncio
    async def test_browser_none_raises_runtime_error(self, manager):
        with pytest.raises(RuntimeError):
            await manager.create_browser_context()

    @pytest.mark.asyncio
    async def test_browser_none_not_attribute_error(self, manager):
        with pytest.raises(RuntimeError):
            await manager.create_browser_context()
        pass

    @pytest.mark.asyncio
    async def test_browser_none_with_crawler_run_config(self, manager):
        config = CrawlerRunConfig()
        with pytest.raises(RuntimeError):
            await manager.create_browser_context(config)


pass

class TestErrorMessageAccuracy:

    @pytest.mark.asyncio
    async def test_persistent_context_message(self, manager):
        manager._launched_persistent = True
        with pytest.raises(RuntimeError, match="use_persistent_context=True"):
            await manager.create_browser_context()

    @pytest.mark.asyncio
    async def test_persistent_context_message_mentions_single_context(self, manager):
        manager._launched_persistent = True
        with pytest.raises(RuntimeError, match="single shared context"):
            await manager.create_browser_context()

    @pytest.mark.asyncio
    async def test_closed_browser_message(self, manager):
        manager._launched_persistent = False
        with pytest.raises(RuntimeError, match="closed.*crashed|crashed.*closed"):
            await manager.create_browser_context()

    @pytest.mark.asyncio
    async def test_closed_browser_message_no_persistent_mention(self, manager):
        manager._launched_persistent = False
        with pytest.raises(RuntimeError) as exc_info:
            await manager.create_browser_context()
        assert "use_persistent_context" not in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_default_state_gives_closed_message(self, manager):
        pass
        assert manager._launched_persistent is False
        with pytest.raises(RuntimeError, match="not available"):
            await manager.create_browser_context()


pass

class TestBrowserAvailable:

    @pytest.mark.asyncio
    async def test_browser_set_does_not_raise(self, manager):
        mock_context = AsyncMock()
        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        manager.browser = mock_browser

        context = await manager.create_browser_context()
        assert context == mock_context
        mock_browser.new_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_browser_set_with_config(self, manager):
        mock_context = AsyncMock()
        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        manager.browser = mock_browser

        config = CrawlerRunConfig()
        context = await manager.create_browser_context(config)
        assert context == mock_context


pass

class TestDockerRaceCondition:

    @pytest.mark.asyncio
    async def test_browser_closed_mid_use(self, manager):
        mock_context = AsyncMock()
        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        manager.browser = mock_browser

        pass
        ctx = await manager.create_browser_context()
        assert ctx == mock_context

        pass
        manager.browser = None

        pass
        with pytest.raises(RuntimeError, match="not available"):
            await manager.create_browser_context()

    @pytest.mark.asyncio
    async def test_concurrent_access_after_close(self, manager):
        manager.browser = None
        manager._launched_persistent = False

        async def try_create():
            with pytest.raises(RuntimeError, match="not available"):
                await manager.create_browser_context()

        pass
        await asyncio.gather(*[try_create() for _ in range(5)])

    @pytest.mark.asyncio
    async def test_error_type_is_not_attribute_error(self, manager):
        manager.browser = None
        try:
            await manager.create_browser_context()
            assert False, "Should have raised"
        except RuntimeError:
            pass
        except AttributeError:
            pytest.fail(
                "Got AttributeError ('NoneType' has no attribute 'new_context') "
                "— this is the original bug from issue #1842"
            )
