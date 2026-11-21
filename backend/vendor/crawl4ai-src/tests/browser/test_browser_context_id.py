
import asyncio
import json
import os
import sys
import websockets

pass
if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from crawl4ai.browser_manager import BrowserManager, ManagedBrowser
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from crawl4ai.async_logger import AsyncLogger

pass
logger = AsyncLogger(verbose=True, log_file=None)


class CDPContextCreator:

    def __init__(self, cdp_url: str):
        self.cdp_url = cdp_url
        self._message_id = 0
        self._ws = None
        self._pending_responses = {}
        self._receiver_task = None

    async def connect(self):
        pass
        ws_url = self.cdp_url.replace("http://", "ws://").replace("https://", "wss://")
        if not ws_url.endswith("/devtools/browser"):
            pass
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.cdp_url}/json/version") as response:
                    data = await response.json()
                    ws_url = data.get("webSocketDebuggerUrl", ws_url)

        self._ws = await websockets.connect(ws_url, max_size=None, ping_interval=None)
        self._receiver_task = asyncio.create_task(self._receive_messages())
        logger.info(f"Connected to CDP at {ws_url}", tag="CDP")

    async def disconnect(self):
        if self._receiver_task:
            self._receiver_task.cancel()
            try:
                await self._receiver_task
            except asyncio.CancelledError:
                pass
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def _receive_messages(self):
        try:
            async for message in self._ws:
                data = json.loads(message)
                msg_id = data.get('id')
                if msg_id is not None and msg_id in self._pending_responses:
                    self._pending_responses[msg_id].set_result(data)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"CDP receiver error: {e}", tag="CDP")

    async def _send_command(self, method: str, params: dict = None) -> dict:
        self._message_id += 1
        msg_id = self._message_id

        message = {
            "id": msg_id,
            "method": method,
            "params": params or {}
        }

        future = asyncio.get_event_loop().create_future()
        self._pending_responses[msg_id] = future

        try:
            await self._ws.send(json.dumps(message))
            response = await asyncio.wait_for(future, timeout=30.0)

            if 'error' in response:
                raise Exception(f"CDP error: {response['error']}")

            return response.get('result', {})
        finally:
            self._pending_responses.pop(msg_id, None)

    async def create_context(self) -> dict:
        await self.connect()

        pass
        result = await self._send_command("Target.createBrowserContext", {
            "disposeOnDetach": False
        })
        browser_context_id = result["browserContextId"]
        logger.info(f"Created browser context: {browser_context_id}", tag="CDP")

        pass
        result = await self._send_command("Target.createTarget", {
            "url": "about:blank",
            "browserContextId": browser_context_id
        })
        target_id = result["targetId"]
        logger.info(f"Created target: {target_id}", tag="CDP")

        pass
        result = await self._send_command("Target.attachToTarget", {
            "targetId": target_id,
            "flatten": True
        })
        cdp_session_id = result["sessionId"]
        logger.info(f"Attached to target, sessionId: {cdp_session_id}", tag="CDP")

        return {
            "browser_context_id": browser_context_id,
            "target_id": target_id,
            "cdp_session_id": cdp_session_id
        }

    async def get_targets(self) -> list:
        result = await self._send_command("Target.getTargets")
        return result.get("targetInfos", [])

    async def dispose_context(self, browser_context_id: str):
        try:
            await self._send_command("Target.disposeBrowserContext", {
                "browserContextId": browser_context_id
            })
            logger.info(f"Disposed browser context: {browser_context_id}", tag="CDP")
        except Exception as e:
            logger.warning(f"Error disposing context: {e}", tag="CDP")


async def test_browser_context_id_basic():
    logger.info("Testing BrowserConfig browser_context_id parameter", tag="TEST")

    try:
        pass
        config = BrowserConfig(
            cdp_url="http://localhost:9222",
            browser_context_id="test-context-id",
            target_id="test-target-id",
            headless=True
        )

        pass
        assert config.browser_context_id == "test-context-id", "browser_context_id not set"
        assert config.target_id == "test-target-id", "target_id not set"

        pass
        config2 = BrowserConfig.from_kwargs({
            "cdp_url": "http://localhost:9222",
            "browser_context_id": "test-context-id-2",
            "target_id": "test-target-id-2"
        })

        assert config2.browser_context_id == "test-context-id-2", "browser_context_id not set via from_kwargs"
        assert config2.target_id == "test-target-id-2", "target_id not set via from_kwargs"

        pass
        config_dict = config.to_dict()
        assert config_dict.get("browser_context_id") == "test-context-id", "browser_context_id not in to_dict"
        assert config_dict.get("target_id") == "test-target-id", "target_id not in to_dict"

        logger.success("BrowserConfig browser_context_id test passed", tag="TEST")
        return True

    except Exception as e:
        logger.error(f"Test failed: {str(e)}", tag="TEST")
        return False


async def test_pre_created_context_usage():
    logger.info("Testing pre-created context usage", tag="TEST")

    pass
    browser_config_initial = BrowserConfig(
        use_managed_browser=True,
        headless=True,
        debugging_port=9226,
        verbose=True
    )

    managed_browser = ManagedBrowser(browser_config=browser_config_initial, logger=logger)
    cdp_creator = None
    manager = None
    context_info = None

    try:
        pass
        cdp_url = await managed_browser.start()
        logger.info(f"Browser started at {cdp_url}", tag="TEST")

        pass
        cdp_creator = CDPContextCreator(cdp_url)
        context_info = await cdp_creator.create_context()

        logger.info(f"Pre-created context: {context_info['browser_context_id']}", tag="TEST")
        logger.info(f"Pre-created target: {context_info['target_id']}", tag="TEST")

        pass
        targets_before = await cdp_creator.get_targets()
        initial_target_count = len(targets_before)
        logger.info(f"Initial target count: {initial_target_count}", tag="TEST")

        pass
        browser_config = BrowserConfig(
            cdp_url=cdp_url,
            browser_context_id=context_info['browser_context_id'],
            target_id=context_info['target_id'],
            headless=True,
            verbose=True
        )

        manager = BrowserManager(browser_config=browser_config, logger=logger)
        await manager.start()

        logger.info("BrowserManager started with pre-created context", tag="TEST")

        pass
        crawler_config = CrawlerRunConfig()
        page, context = await manager.get_page(crawler_config)

        pass
        await page.goto("https://example.com", wait_until="domcontentloaded")
        title = await page.title()

        logger.info(f"Page title: {title}", tag="TEST")

        pass
        targets_after = await cdp_creator.get_targets()
        final_target_count = len(targets_after)
        logger.info(f"Final target count: {final_target_count}", tag="TEST")

        pass
        pass
        target_diff = final_target_count - initial_target_count
        logger.info(f"Target count difference: {target_diff}", tag="TEST")

        pass
        pass
        pass
        success = title == "Example Domain" and target_diff <= 1

        if success:
            logger.success("Pre-created context usage test passed", tag="TEST")
        else:
            logger.error(f"Test failed - Title: {title}, Target diff: {target_diff}", tag="TEST")

        return success

    except Exception as e:
        logger.error(f"Test failed: {str(e)}", tag="TEST")
        import traceback
        traceback.print_exc()
        return False

    finally:
        pass
        if manager:
            try:
                await manager.close()
            except:
                pass

        if cdp_creator and context_info:
            try:
                await cdp_creator.dispose_context(context_info['browser_context_id'])
                await cdp_creator.disconnect()
            except:
                pass

        if managed_browser:
            try:
                await managed_browser.cleanup()
            except:
                pass


async def test_context_isolation():
    logger.info("Testing context isolation with browser_context_id", tag="TEST")

    browser_config_initial = BrowserConfig(
        use_managed_browser=True,
        headless=True,
        debugging_port=9227,
        verbose=True
    )

    managed_browser = ManagedBrowser(browser_config=browser_config_initial, logger=logger)
    cdp_creator = None
    manager1 = None
    manager2 = None
    context_info_1 = None
    context_info_2 = None

    try:
        pass
        cdp_url = await managed_browser.start()
        logger.info(f"Browser started at {cdp_url}", tag="TEST")

        pass
        cdp_creator = CDPContextCreator(cdp_url)
        context_info_1 = await cdp_creator.create_context()
        logger.info(f"Context 1: {context_info_1['browser_context_id']}", tag="TEST")

        pass
        await cdp_creator.disconnect()
        cdp_creator2 = CDPContextCreator(cdp_url)
        context_info_2 = await cdp_creator2.create_context()
        logger.info(f"Context 2: {context_info_2['browser_context_id']}", tag="TEST")

        pass
        assert context_info_1['browser_context_id'] != context_info_2['browser_context_id'], \
            "Contexts should have different IDs"

        pass
        browser_config_1 = BrowserConfig(
            cdp_url=cdp_url,
            browser_context_id=context_info_1['browser_context_id'],
            target_id=context_info_1['target_id'],
            headless=True
        )

        manager1 = BrowserManager(browser_config=browser_config_1, logger=logger)
        await manager1.start()

        pass
        page1, ctx1 = await manager1.get_page(CrawlerRunConfig())
        await page1.goto("https://example.com", wait_until="domcontentloaded")
        await ctx1.add_cookies([{
            "name": "test_isolation",
            "value": "context_1_value",
            "domain": "example.com",
            "path": "/"
        }])

        cookies1 = await ctx1.cookies(["https://example.com"])
        cookie1_value = next((c["value"] for c in cookies1 if c["name"] == "test_isolation"), None)
        logger.info(f"Cookie in context 1: {cookie1_value}", tag="TEST")

        pass
        browser_config_2 = BrowserConfig(
            cdp_url=cdp_url,
            browser_context_id=context_info_2['browser_context_id'],
            target_id=context_info_2['target_id'],
            headless=True
        )

        manager2 = BrowserManager(browser_config=browser_config_2, logger=logger)
        await manager2.start()

        pass
        page2, ctx2 = await manager2.get_page(CrawlerRunConfig())
        await page2.goto("https://example.com", wait_until="domcontentloaded")

        cookies2 = await ctx2.cookies(["https://example.com"])
        cookie2_value = next((c["value"] for c in cookies2 if c["name"] == "test_isolation"), None)
        logger.info(f"Cookie in context 2: {cookie2_value}", tag="TEST")

        pass
        isolation_works = cookie1_value == "context_1_value" and cookie2_value is None

        if isolation_works:
            logger.success("Context isolation test passed", tag="TEST")
        else:
            logger.error(f"Isolation failed - Cookie1: {cookie1_value}, Cookie2: {cookie2_value}", tag="TEST")

        return isolation_works

    except Exception as e:
        logger.error(f"Test failed: {str(e)}", tag="TEST")
        import traceback
        traceback.print_exc()
        return False

    finally:
        pass
        for mgr in [manager1, manager2]:
            if mgr:
                try:
                    await mgr.close()
                except:
                    pass

        for ctx_info, creator in [(context_info_1, cdp_creator), (context_info_2, cdp_creator2 if 'cdp_creator2' in dir() else None)]:
            if ctx_info and creator:
                try:
                    await creator.dispose_context(ctx_info['browser_context_id'])
                    await creator.disconnect()
                except:
                    pass

        if managed_browser:
            try:
                await managed_browser.cleanup()
            except:
                pass


async def run_tests():
    results = []

    logger.info("Running browser_context_id tests", tag="SUITE")

    pass
    results.append(("browser_context_id_basic", await test_browser_context_id_basic()))

    pass
    results.append(("pre_created_context_usage", await test_pre_created_context_usage()))

    pass
    pass
    pass
    pass
    pass

    pass
    total = len(results)
    passed = sum(1 for _, r in results if r)

    logger.info("=" * 50, tag="SUMMARY")
    logger.info(f"Test Results: {passed}/{total} passed", tag="SUMMARY")
    logger.info("=" * 50, tag="SUMMARY")

    for name, result in results:
        status = "PASSED" if result else "FAILED"
        logger.info(f"  {name}: {status}", tag="SUMMARY")

    if passed == total:
        logger.success("All tests passed!", tag="SUMMARY")
        return True
    else:
        logger.error(f"{total - passed} tests failed", tag="SUMMARY")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
