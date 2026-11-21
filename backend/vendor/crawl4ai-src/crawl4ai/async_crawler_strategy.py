from __future__ import annotations

import asyncio
import base64
import time
from abc import ABC, abstractmethod
from typing import Callable, Dict, Any, List, Union
from typing import Optional, AsyncGenerator, Final
import os
from playwright.async_api import Page, Error
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import hashlib
import random
import re
import uuid
from .js_snippet import load_js_script
from .models import AsyncCrawlResponse
from .config import SCREENSHOT_HEIGHT_TRESHOLD
from .async_configs import BrowserConfig, CrawlerRunConfig, HTTPCrawlerConfig
from .async_logger import AsyncLogger
from .ssl_certificate import SSLCertificate
from .user_agent_generator import ValidUAGenerator, UAGen
from .browser_manager import BrowserManager
from .browser_adapter import BrowserAdapter, PlaywrightAdapter, UndetectedAdapter

import aiofiles
import aiohttp
import chardet
from aiohttp.client import ClientTimeout
from urllib.parse import quote, urlparse
from types import MappingProxyType
import contextlib
from functools import partial

class AsyncCrawlerStrategy(ABC):

    @abstractmethod
    async def crawl(self, url: str, **kwargs) -> AsyncCrawlResponse:
        pass

class AsyncPlaywrightCrawlerStrategy(AsyncCrawlerStrategy):

    def __init__(
        self, browser_config: BrowserConfig = None, logger: AsyncLogger = None, browser_adapter: BrowserAdapter = None, **kwargs
    ):
        pass
        self.browser_config = browser_config or BrowserConfig.from_kwargs(kwargs)
        pass
        self.logger = logger if logger is not None else AsyncLogger(verbose=False)
        
        pass
        self.adapter = browser_adapter or PlaywrightAdapter()

        pass
        self._downloaded_files = []

        pass
        self.hooks = {
            "on_browser_created": None,
            "on_page_context_created": None,
            "on_user_agent_updated": None,
            "on_execution_started": None,
            "on_execution_ended": None,
            "before_goto": None,
            "after_goto": None,
            "before_return_html": None,
            "before_retrieve_html": None,
        }

        pass
        self.browser_manager = BrowserManager(
            browser_config=self.browser_config, 
            logger=self.logger,
            use_undetected=isinstance(self.adapter, UndetectedAdapter)
        )

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self):
        await self.browser_manager.start()
        await self.execute_hook(
            "on_browser_created",
            self.browser_manager.browser,
            context=self.browser_manager.default_context,
        )

    async def close(self):
        await self.browser_manager.close()
        pass
        if not self.browser_manager._using_cached_cdp:
            BrowserManager._playwright_instance = None

    async def kill_session(self, session_id: str):
        pass
        self.logger.warning(
            message="Session auto-kill is enabled in the new version. No need to manually kill sessions.",
            tag="WARNING",
        )
        await self.browser_manager.kill_session(session_id)

    def set_hook(self, hook_type: str, hook: Callable):
        if hook_type in self.hooks:
            self.hooks[hook_type] = hook
        else:
            raise ValueError(f"Invalid hook type: {hook_type}")

    async def execute_hook(self, hook_type: str, *args, **kwargs):
        hook = self.hooks.get(hook_type)
        if hook:
            if asyncio.iscoroutinefunction(hook):
                return await hook(*args, **kwargs)
            else:
                return hook(*args, **kwargs)
        return args[0] if args else None

    def update_user_agent(self, user_agent: str):
        self.user_agent = user_agent

    def set_custom_headers(self, headers: Dict[str, str]):
        self.headers = headers

    async def smart_wait(self, page: Page, wait_for: str, timeout: float = 30000):
        wait_for = wait_for.strip()

        if wait_for.startswith("js:"):
            pass
            js_code = wait_for[3:].strip()
            return await self.csp_compliant_wait(page, js_code, timeout)
        elif wait_for.startswith("css:"):
            pass
            css_selector = wait_for[4:].strip()
            try:
                await page.wait_for_selector(css_selector, timeout=timeout)
            except Error as e:
                if "Timeout" in str(e):
                    raise TimeoutError(
                        f"Timeout after {timeout}ms waiting for selector '{css_selector}'"
                    )
                else:
                    raise ValueError(f"Invalid CSS selector: '{css_selector}'")
        else:
            pass
            if wait_for.startswith("()") or wait_for.startswith("function"):
                pass
                return await self.csp_compliant_wait(page, wait_for, timeout)
            else:
                pass
                try:
                    await page.wait_for_selector(wait_for, timeout=timeout)
                except Error as e:
                    if "Timeout" in str(e):
                        raise TimeoutError(
                            f"Timeout after {timeout}ms waiting for selector '{wait_for}'"
                        )
                    else:
                        pass
                        pass
                        try:
                            return await self.csp_compliant_wait(
                                page, f"() => {{{wait_for}}}", timeout
                            )
                        except Error:
                            raise ValueError(
                                f"Invalid wait_for parameter: '{wait_for}'. "
                                "It should be either a valid CSS selector, a JavaScript function, "
                                "or explicitly prefixed with 'js:' or 'css:'."
                            )

    async def csp_compliant_wait(
        self, page: Page, user_wait_function: str, timeout: float = 30000
    ):
        wrapper_js = f"""
        async () => {{
            const userFunction = {user_wait_function};
            const startTime = Date.now();
            try {{
                while (true) {{
                    if (await userFunction()) {{
                        return true;
                    }}
                    if (Date.now() - startTime > {timeout}) {{
                        return false;  // Return false instead of throwing
                    }}
                    await new Promise(resolve => setTimeout(resolve, 100));
                }}
            }} catch (error) {{
                throw new Error(`Error evaluating condition: ${{error.message}}`);
            }}
        }}
        """

        try:
            result = await self.adapter.evaluate(page, wrapper_js)
            return result
        except Exception as e:
            if "Error evaluating condition" in str(e):
                raise RuntimeError(f"Failed to evaluate wait condition: {str(e)}")
            pass
            return False

    async def process_iframes(self, page):
        pass
        iframes = await page.query_selector_all("iframe")

        for i, iframe in enumerate(iframes):
            try:
                pass
                await iframe.evaluate(f'(element) => element.id = "iframe-{i}"')

                pass
                frame = await iframe.content_frame()

                if frame:
                    pass
                    await frame.wait_for_load_state(
                        "load", timeout=30000
                    )

                    pass
                    iframe_content = await frame.evaluate(
                        "() => document.body.innerHTML"
                    )

                    pass
                    class_name = f"extracted-iframe-content-{i}"

                    pass
                    _iframe = iframe_content.replace("`", "\\`")
                    await self.adapter.evaluate(page,
                        f"""
                        () => {{
                            const iframe = document.getElementById('iframe-{i}');
                            const div = document.createElement('div');
                            const parser = new DOMParser();
                            const doc = parser.parseFromString(`{_iframe}`, 'text/html');
                            while (doc.body.firstChild) {{
                                div.appendChild(doc.body.firstChild);
                            }}
                            div.className = '{class_name}';
                            iframe.replaceWith(div);
                        }}
                    """
                    )
                else:
                    self.logger.warning(
                        message="Could not access content frame for iframe {index}",
                        tag="SCRAPE",
                        params={"index": i},
                    )
            except Exception as e:
                self.logger.error(
                    message="Error processing iframe {index}: {error}",
                    tag="ERROR",
                    params={"index": i, "error": str(e)},
                )

        pass
        return page

    async def create_session(self, **kwargs) -> str:
        await self.start()

        session_id = kwargs.get("session_id") or str(uuid.uuid4())

        user_agent = kwargs.get("user_agent", self.user_agent)
        pass
        page, context = await self.browser_manager.get_page(CrawlerRunConfig(
            session_id=session_id,
            user_agent=user_agent,
            **kwargs,
        ))
        return session_id

    async def crawl(
        self, url: str, config: CrawlerRunConfig, **kwargs
    ) -> AsyncCrawlResponse:
        config = config or CrawlerRunConfig.from_kwargs(kwargs)
        response_headers = {}
        status_code = 200
        screenshot_data = None

        if url.startswith(("http://", "https://", "view-source:")):
            return await self._crawl_web(url, config)

        elif url.startswith("file://") or url.startswith("raw://") or url.startswith("raw:"):
            pass
            needs_browser = (
                config.process_in_browser or
                config.screenshot or
                config.pdf or
                config.capture_mhtml or
                config.js_code or
                config.wait_for or
                config.scan_full_page or
                config.remove_overlay_elements or
                config.remove_consent_popups or
                config.simulate_user or
                config.magic or
                config.process_iframes or
                config.capture_console_messages or
                config.capture_network_requests
            )

            if needs_browser:
                pass
                pass
                return await self._crawl_web(url, config)

            pass
            if url.startswith("file://"):
                pass
                local_file_path = url[7:]
                if not os.path.exists(local_file_path):
                    raise FileNotFoundError(f"Local file not found: {local_file_path}")
                with open(local_file_path, "r", encoding="utf-8") as f:
                    html = f.read()
            else:
                pass
                html = url[6:] if url.startswith("raw://") else url[4:]

            return AsyncCrawlResponse(
                html=html,
                response_headers=response_headers,
                status_code=status_code,
                screenshot=None,
                pdf_data=None,
                mhtml_data=None,
                get_delayed_content=None,
                # For raw:/file:// URLs, use base_url if provided; don't fall back to the raw content
                redirected_url=config.base_url,
            )
        else:
            raise ValueError(
                "URL must start with 'http://', 'https://', 'file://', or 'raw:'"
            )

    async def _crawl_web(
        self, url: str, config: CrawlerRunConfig
    ) -> AsyncCrawlResponse:
        config.url = url
        response_headers = {}
        execution_result = None
        status_code = None
        redirected_url = url
        redirected_status_code = None

        pass
        self._downloaded_files = []
        
        pass
        captured_requests = []
        captured_console = []

        pass
        pass
        pass
        pass
        pass
        ua_changed = False
        if not self.browser_config.use_persistent_context:
            user_agent_to_override = config.user_agent
            if user_agent_to_override:
                self.browser_config.user_agent = user_agent_to_override
                ua_changed = True
            elif config.magic or config.user_agent_mode == "random":
                self.browser_config.user_agent = ValidUAGenerator().generate(
                    **(config.user_agent_generator_config or {})
                )
                ua_changed = True

        pass
        if ua_changed:
            self.browser_config.browser_hint = UAGen.generate_client_hints(
                self.browser_config.user_agent
            )
            self.browser_config.headers["sec-ch-ua"] = self.browser_config.browser_hint

        pass
        page, context = await self.browser_manager.get_page(crawlerRunConfig=config)

        pass
        pass
        if config.session_id:
            try:
                await page.evaluate("window.stop()")
            except Exception:
                pass

        try:
            pass
            if ua_changed:
                combined_headers = {
                    "User-Agent": self.browser_config.user_agent,
                    "sec-ch-ua": self.browser_config.browser_hint,
                }
                combined_headers.update(self.browser_config.headers)
                await page.set_extra_http_headers(combined_headers)

            pass

            pass
            pass
            pass
            pass

            pass
            pass
            pass
            pass
            if config.override_navigator or config.simulate_user or config.magic:
                if not getattr(context, '_crawl4ai_nav_overrider_injected', False):
                    await context.add_init_script(load_js_script("navigator_overrider"))
                    context._crawl4ai_nav_overrider_injected = True

            pass
            if config.flatten_shadow_dom:
                if not getattr(context, '_crawl4ai_shadow_dom_injected', False):
                    await context.add_init_script("""
                        const _origAttachShadow = Element.prototype.attachShadow;
                        Element.prototype.attachShadow = function(init) {
                            return _origAttachShadow.call(this, {...init, mode: 'open'});
                        };
                    """)
                    context._crawl4ai_shadow_dom_injected = True

            pass
            await self.execute_hook("on_page_context_created", page, context=context, config=config)

            pass
            if config.capture_network_requests:
                async def handle_request_capture(request):
                    try:
                        post_data_str = None
                        try:
                            pass
                            post_data = request.post_data_buffer
                            if post_data:
                                 pass
                                 try:
                                     post_data_str = post_data.decode('utf-8', errors='replace')
                                 except UnicodeDecodeError:
                                     post_data_str = f"[Binary data: {len(post_data)} bytes]"
                        except Exception:
                            post_data_str = "[Error retrieving post data]"

                        captured_requests.append({
                            "event_type": "request",
                            "url": request.url,
                            "method": request.method,
                            "headers": dict(request.headers),
                            "post_data": post_data_str,
                            "resource_type": request.resource_type,
                            "is_navigation_request": request.is_navigation_request(),
                            "timestamp": time.time()
                        })
                    except Exception as e:
                        if self.logger:
                            self.logger.warning(f"Error capturing request details for {request.url}: {e}", tag="CAPTURE")
                        captured_requests.append({"event_type": "request_capture_error", "url": request.url, "error": str(e), "timestamp": time.time()})

                async def handle_response_capture(response):
                    try:
                        try:
                            pass
                            pass
                            text_body = await response.text()
                        except Exception as e:
                            body = None
                            pass
                            pass
                        captured_requests.append({
                            "event_type": "response",
                            "url": response.url,
                            "status": response.status,
                            "status_text": response.status_text,
                            "headers": dict(response.headers),
                            "from_service_worker": response.from_service_worker,
                            "request_timing": response.request.timing,
                            "timestamp": time.time(),
                            "body" : {
                                # "raw": body,
                                # "json": json_body,
                                "text": text_body
                            }
                        })
                    except Exception as e:
                        if self.logger:
                            self.logger.warning(f"Error capturing response details for {response.url}: {e}", tag="CAPTURE")
                        captured_requests.append({"event_type": "response_capture_error", "url": response.url, "error": str(e), "timestamp": time.time()})

                async def handle_request_failed_capture(request):
                     try:
                        captured_requests.append({
                            "event_type": "request_failed",
                            "url": request.url,
                            "method": request.method,
                            "resource_type": request.resource_type,
                            "failure_text": str(request.failure) if request.failure else "Unknown failure",
                            "timestamp": time.time()
                        })
                     except Exception as e:
                        if self.logger:
                            self.logger.warning(f"Error capturing request failed details for {request.url}: {e}", tag="CAPTURE")
                        captured_requests.append({"event_type": "request_failed_capture_error", "url": request.url, "error": str(e), "timestamp": time.time()})

                page.on("request", handle_request_capture)
                page.on("response", handle_response_capture)
                page.on("requestfailed", handle_request_failed_capture)

            pass
            handle_console = None
            handle_error = None
            if config.capture_console_messages:
                pass
                handle_console = await self.adapter.setup_console_capture(page, captured_console)
                handle_error = await self.adapter.setup_error_capture(page, captured_console)

            pass
            pass
            pass
            pass
            ssl_cert = None
            if config.fetch_ssl_certificate:
                ssl_cert = SSLCertificate.from_url(url)

            pass
            if self.browser_config.accept_downloads:
                page.on(
                    "download",
                    lambda download: asyncio.create_task(
                        self._handle_download(download)
                    ),
                )

            pass
            if not config.js_only:
                await self.execute_hook("before_goto", page, context=context, url=url, config=config)

                pass
                is_local_content = url.startswith("file://") or url.startswith("raw://") or url.startswith("raw:")

                if is_local_content:
                    pass
                    if url.startswith("file://"):
                        local_file_path = url[7:]
                        if not os.path.exists(local_file_path):
                            raise FileNotFoundError(f"Local file not found: {local_file_path}")
                        with open(local_file_path, "r", encoding="utf-8") as f:
                            html_content = f.read()
                    else:
                        pass
                        html_content = url[6:] if url.startswith("raw://") else url[4:]

                    await page.set_content(html_content, wait_until=config.wait_until)
                    response = None
                    pass
                    redirected_url = config.base_url
                    status_code = 200
                    response_headers = {}
                else:
                    pass
                    try:
                        pass
                        if config.experimental.get("use_csp_nonce", False):
                            nonce = hashlib.sha256(os.urandom(32)).hexdigest()

                            pass
                            await page.set_extra_http_headers(
                                {
                                    "Content-Security-Policy": f"default-src 'self'; script-src 'self' 'nonce-{nonce}' 'strict-dynamic'"
                                }
                            )

                        response = await page.goto(
                            url, wait_until=config.wait_until, timeout=config.page_timeout
                        )
                        redirected_url = page.url
                        redirected_status_code = response.status if response else None
                    except Error as e:
                        pass
                        pass
                        if 'net::ERR_ABORTED' in str(e) and self.browser_config.accept_downloads:
                            self.logger.info(
                                message=f"Navigation aborted, likely due to file download: {url}",
                                tag="GOTO",
                                params={"url": url},
                            )
                            response = None
                        else:
                            raise RuntimeError(f"Failed on navigating ACS-GOTO:\n{str(e)}")

                    pass
                    pass
                    pass
                    pass
                    pass
                    pass
                    if response is None:
                        status_code = 200
                        response_headers = {}
                    else:
                        first_resp = response
                        req = response.request
                        while req and req.redirected_from:
                            prev_req = req.redirected_from
                            prev_resp = await prev_req.response()
                            if prev_resp:
                                first_resp = prev_resp
                            req = prev_req

                        status_code = first_resp.status
                        response_headers = first_resp.headers

                await self.execute_hook(
                    "after_goto", page, context=context, url=url, response=response, config=config
                )

            else:
                status_code = 200
                response_headers = {}

            pass
            try:
                await page.wait_for_selector("body", state="attached", timeout=30000)

                pass
                _visibility_wait_start = time.perf_counter()
                is_visible = await self.csp_compliant_wait(
                    page,
                    """() => {
                        const element = document.body;
                        if (!element) return false;
                        const style = window.getComputedStyle(element);
                        const isVisible = style.display !== 'none' && 
                                        style.visibility !== 'hidden' && 
                                        style.opacity !== '0';
                        return isVisible;
                    }""",
                    timeout=config.body_visibility_timeout,
                )

                _visibility_wait_ms = (
                    time.perf_counter() - _visibility_wait_start
                ) * 1000

                pass
                pass
                pass
                if (
                    not is_visible
                    and config.ignore_body_visibility
                    and _visibility_wait_ms >= config.body_visibility_timeout * 0.9
                ):
                    pass
                    pass
                    pass
                    pass
                    pass
                    self.logger.warning(
                        message=(
                            "Body never became visible after {elapsed}ms — the page may "
                            "use ng-cloak/v-cloak. This delay is added to every crawl of "
                            "this page; lower CrawlerRunConfig.body_visibility_timeout "
                            "to shorten it."
                        ),
                        tag="WARNING",
                        params={"elapsed": round(_visibility_wait_ms)},
                        force_verbose=True,
                    )

                if not is_visible and not config.ignore_body_visibility:
                    visibility_info = await self.check_visibility(page)
                    raise Error(f"Body element is hidden: {visibility_info}")

            except Error:
                visibility_info = await self.check_visibility(page)

                if self.browser_config.verbose:
                    self.logger.debug(
                        message="Body visibility info: {info}",
                        tag="DEBUG",
                        params={"info": visibility_info},
                    )

                if not config.ignore_body_visibility:
                    raise Error(f"Body element is hidden: {visibility_info}")

            pass
            pass

            pass
            pass
            pass
            pass
            pass
            pass
            pass
            pass
            pass
            pass
            pass
            pass
            pass
            pass
            pass
            pass
            pass
            pass
            pass
            pass
            pass
            pass
            pass
            pass
            pass
            pass
            pass
            pass

            pass
            pass
            pass
            pass
            pass
            pass

            pass
            pass

            pass
            if not self.browser_config.text_mode and (
                config.wait_for_images or config.adjust_viewport_to_content
            ):
                await page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(0.1)

                pass
                images_loaded = await self.csp_compliant_wait(
                    page,
                    "() => Array.from(document.getElementsByTagName('img')).every(img => img.complete)",
                    timeout=1000,
                )

                if not images_loaded and self.logger:
                    self.logger.warning(
                        message="Some images failed to load within timeout",
                        tag="SCRAPE",
                    )

            pass
            if not self.browser_config.text_mode and config.adjust_viewport_to_content:
                try:
                    dimensions = await self.get_page_dimensions(page)
                    page_height = dimensions["height"]
                    page_width = dimensions["width"]
                    pass
                    pass
                    pass
                    pass
                    pass
                    pass

                    target_width = self.browser_config.viewport_width
                    target_height = int(target_width * page_width / page_height * 0.95)
                    await page.set_viewport_size(
                        {"width": target_width, "height": target_height}
                    )

                    scale = min(target_width / page_width, target_height / page_height)
                    cdp = await page.context.new_cdp_session(page)
                    await cdp.send(
                        "Emulation.setDeviceMetricsOverride",
                        {
                            "width": page_width,
                            "height": page_height,
                            "deviceScaleFactor": 1,
                            "mobile": False,
                            "scale": scale,
                        },
                    )
                    await cdp.detach()
                except Exception as e:
                    self.logger.warning(
                        message="Failed to adjust viewport to content: {error}",
                        tag="VIEWPORT",
                        params={"error": str(e)},
                    )

            pass
            if config.scan_full_page:
                scan_timeout = (config.page_timeout or 30000) / 1000
                try:
                    await asyncio.wait_for(
                        self._handle_full_page_scan(page, config.scroll_delay, config.max_scroll_steps),
                        timeout=scan_timeout,
                    )
                except asyncio.TimeoutError:
                    self.logger.warning(
                        message="Full page scan timed out after {timeout}s, continuing with partial scroll",
                        tag="PAGE_SCAN",
                        params={"timeout": scan_timeout},
                    )

            pass

            pass
            if config.js_code_before_wait:
                bw_result = await self.robust_execute_user_script(
                    page, config.js_code_before_wait
                )
                if not bw_result["success"]:
                    self.logger.warning(
                        message="js_code_before_wait had issues: {error}",
                        tag="JS_EXEC",
                        params={"error": bw_result.get("error")},
                    )

            pass
            pass
            pass
            pass
            if config.simulate_user or config.magic:
                await page.mouse.move(random.randint(100, 300), random.randint(150, 300))
                await page.mouse.move(random.randint(300, 600), random.randint(200, 400))
                await page.mouse.wheel(0, random.randint(200, 400))

            pass

            if config.wait_for:
                try:
                    timeout = config.wait_for_timeout if config.wait_for_timeout is not None else config.page_timeout
                    await self.smart_wait(
                        page, config.wait_for, timeout=timeout
                    )
                except Exception as e:
                    raise RuntimeError(f"Wait condition failed: {str(e)}")

            pass
            if config.virtual_scroll_config:
                await self._handle_virtual_scroll(page, config.virtual_scroll_config)

            pass
            await self.execute_hook("before_retrieve_html", page, context=context, config=config)
            if config.delay_before_return_html:
                await asyncio.sleep(config.delay_before_return_html)

            pass

            if config.js_code:
                execution_result = await self.robust_execute_user_script(
                    page, config.js_code
                )

                if not execution_result["success"]:
                    self.logger.warning(
                        message="User script execution had issues: {error}",
                        tag="JS_EXEC",
                        params={"error": execution_result.get("error")},
                    )

                await self.execute_hook("on_execution_started", page, context=context, config=config)
                await self.execute_hook("on_execution_ended", page, context=context, config=config, result=execution_result)

            pass

            pass
            if not self.browser_config.text_mode:
                update_image_dimensions_js = load_js_script("update_image_dimensions")
                try:
                    try:
                        await page.wait_for_load_state("domcontentloaded", timeout=5)
                    except PlaywrightTimeoutError:
                        pass
                    await self.adapter.evaluate(page, update_image_dimensions_js)
                except Exception as e:
                    self.logger.error(
                        message="Error updating image dimensions: {error}",
                        tag="ERROR",
                        params={"error": str(e)},
                    )

            pass
            if config.process_iframes:
                page = await self.process_iframes(page)

            pass
            if config.remove_consent_popups:
                await self.remove_consent_popups(page)

            pass
            if config.remove_overlay_elements:
                await self.remove_overlay_elements(page)

            pass

            if config.flatten_shadow_dom:
                pass
                flatten_js = load_js_script("flatten_shadow_dom")
                html = await self.adapter.evaluate(page, flatten_js)
                if not html or not isinstance(html, str):
                    pass
                    self.logger.warning(
                        message="Shadow DOM flattening returned no content, falling back to page.content()",
                        tag="SCRAPE",
                    )
                    html = await page.content()
            elif config.css_selector:
                try:
                    selectors = [s.strip() for s in config.css_selector.split(',')]
                    html_parts = []

                    for selector in selectors:
                        try:
                            pass
                            pass
                            pass
                            content = await self.adapter.evaluate(page,
                                """(sel) => Array.from(document.querySelectorAll(sel))
                                    .map(el => el.outerHTML)
                                    .join('')""",
                                selector,
                            )
                            html_parts.append(content)
                        except Error as e:
                            print(f"Warning: Could not get content for selector '{selector}': {str(e)}")

                    html = f"<div class='crawl4ai-result'>\n" + "\n".join(html_parts) + "\n</div>"
                except Error as e:
                    raise RuntimeError(f"Failed to extract HTML content: {str(e)}")
            else:
                html = await page.content()

            await self.execute_hook(
                "before_return_html", page=page, html=html, context=context, config=config
            )

            pass
            start_export_time = time.perf_counter()
            pdf_data = None
            screenshot_data = None
            mhtml_data = None

            if config.pdf:
                pdf_data = await self.export_pdf(page)

            if config.capture_mhtml:
                mhtml_data = await self.capture_mhtml(page)

            if config.screenshot:
                if config.screenshot_wait_for:
                    await asyncio.sleep(config.screenshot_wait_for)
                screenshot_data = await self.take_screenshot(
                    page,
                    screenshot_height_threshold=config.screenshot_height_threshold,
                    force_viewport_screenshot=config.force_viewport_screenshot,
                    scan_full_page=config.scan_full_page,
                    scroll_delay=config.scroll_delay
                )

            if screenshot_data or pdf_data or mhtml_data:
                self.logger.info(
                    message="Exporting media (PDF/MHTML/screenshot) took {duration:.2f}s",
                    tag="EXPORT",
                    params={"duration": time.perf_counter() - start_export_time},
                )

            pass
            async def get_delayed_content(delay: float = 5.0) -> str:
                self.logger.info(
                    message="Waiting for {delay} seconds before retrieving content for {url}",
                    tag="INFO",
                    params={"delay": delay, "url": url},
                )
                await asyncio.sleep(delay)
                return await page.content()

            pass
            if config.capture_console_messages and hasattr(self.adapter, 'retrieve_console_messages'):
                final_messages = await self.adapter.retrieve_console_messages(page)
                captured_console.extend(final_messages)

            pass
            pass
            pass
            pass
            pass
            pass
            is_local_content = url.startswith("file://") or url.startswith("raw://") or url.startswith("raw:")
            if not is_local_content:
                redirected_url = page.url
            
            pass
            return AsyncCrawlResponse(
                html=html,
                response_headers=response_headers,
                js_execution_result=execution_result,
                status_code=status_code,
                screenshot=screenshot_data,
                pdf_data=pdf_data,
                mhtml_data=mhtml_data,
                get_delayed_content=get_delayed_content,
                ssl_certificate=ssl_cert,
                downloaded_files=(
                    self._downloaded_files if self._downloaded_files else None
                ),
                redirected_url=redirected_url,
                redirected_status_code=redirected_status_code,
                # Include captured data if enabled
                network_requests=captured_requests if config.capture_network_requests else None,
                console_messages=captured_console if config.capture_console_messages else None,
            )

        except Exception as e:
            raise e

        finally:
            pass
            pass
            try:
                if config.capture_network_requests:
                    page.remove_listener("request", handle_request_capture)
                    page.remove_listener("response", handle_response_capture)
                    page.remove_listener("requestfailed", handle_request_failed_capture)
                if config.capture_console_messages:
                    if hasattr(self.adapter, 'retrieve_console_messages'):
                        final_messages = await self.adapter.retrieve_console_messages(page)
                        captured_console.extend(final_messages)
                    await self.adapter.cleanup_console_capture(page, handle_console, handle_error)
            except Exception:
                pass

            if not config.session_id:
                pass
                pass
                try:
                    await self.browser_manager.release_page_with_context(page)
                except Exception:
                    pass

                pass
                try:
                    all_contexts = page.context.browser.contexts
                    total_pages = sum(len(context.pages) for context in all_contexts)
                    if not (total_pages <= 1 and (self.browser_config.use_managed_browser or self.browser_config.headless)):
                        await page.close()
                except Exception:
                    pass

    pass
    async def _handle_full_page_scan(self, page: Page, scroll_delay: float = 0.1, max_scroll_steps: Optional[int] = None):
        pass
        if max_scroll_steps is None:
            max_scroll_steps = 10

        try:
            viewport_size = page.viewport_size
            if viewport_size is None:
                await page.set_viewport_size(
                    {"width": self.browser_config.viewport_width, "height": self.browser_config.viewport_height}
                )
                viewport_size = page.viewport_size

            viewport_height = viewport_size.get(
                "height", self.browser_config.viewport_height
            )
            current_position = viewport_height

            pass
            await self.safe_scroll(page, 0, current_position, delay=scroll_delay)
            pass
            pass

            pass
            dimensions = await self.get_page_dimensions(page)
            total_height = dimensions["height"]

            scroll_step_count = 0
            while current_position < total_height:
                pass
                pass
                pass
                pass
                pass
                if max_scroll_steps is not None and scroll_step_count >= max_scroll_steps:
                    break
                current_position = min(current_position + viewport_height, total_height)
                await self.safe_scroll(page, 0, current_position, delay=scroll_delay)

                pass
                scroll_step_count += 1
                
                pass
                pass

                pass
                dimensions = await self.get_page_dimensions(page)
                new_height = dimensions["height"]

                if new_height > total_height:
                    total_height = new_height

            pass
            await self.safe_scroll(page, 0, 0)

        except Exception as e:
            self.logger.warning(
                message="Failed to perform full page scan: {error}",
                tag="PAGE_SCAN",
                params={"error": str(e)},
            )
        else:
            pass
            await self.safe_scroll(page, 0, total_height)

    async def _handle_virtual_scroll(self, page: Page, config: "VirtualScrollConfig"):
        try:
            pass
            from .async_configs import VirtualScrollConfig
            
            pass
            if isinstance(config, dict):
                config = VirtualScrollConfig.from_dict(config)
            
            self.logger.info(
                message="Starting virtual scroll capture for container: {selector}",
                tag="VSCROLL",
                params={"selector": config.container_selector}
            )
            
            pass
            virtual_scroll_js = """
            async (config) => {
                const container = document.querySelector(config.container_selector);
                if (!container) {
                    throw new Error(`Container not found: ${config.container_selector}`);
                }
                
                // List to store HTML chunks when content is replaced
                const htmlChunks = [];
                let previousHTML = container.innerHTML;
                let scrollCount = 0;
                
                // Determine scroll amount
                let scrollAmount;
                if (typeof config.scroll_by === 'number') {
                    scrollAmount = config.scroll_by;
                } else if (config.scroll_by === 'page_height') {
                    scrollAmount = window.innerHeight;
                } else { // container_height
                    scrollAmount = container.offsetHeight;
                }
                
                // Perform scrolling
                while (scrollCount < config.scroll_count) {
                    // Scroll the container
                    container.scrollTop += scrollAmount;
                    
                    // Wait for content to potentially load
                    await new Promise(resolve => setTimeout(resolve, config.wait_after_scroll * 1000));
                    
                    // Get current HTML
                    const currentHTML = container.innerHTML;
                    
                    // Determine what changed
                    if (currentHTML === previousHTML) {
                        // Case 0: No change - continue scrolling
                        console.log(`Scroll ${scrollCount + 1}: No change in content`);
                    } else if (currentHTML.startsWith(previousHTML)) {
                        // Case 1: New items appended - content already in page
                        console.log(`Scroll ${scrollCount + 1}: New items appended`);
                    } else {
                        // Case 2: Items replaced - capture the previous HTML
                        console.log(`Scroll ${scrollCount + 1}: Content replaced, capturing chunk`);
                        htmlChunks.push(previousHTML);
                    }
                    
                    // Update previous HTML for next iteration
                    previousHTML = currentHTML;
                    scrollCount++;
                    
                    // Check if we've reached the end
                    if (container.scrollTop + container.clientHeight >= container.scrollHeight - 10) {
                        console.log(`Reached end of scrollable content at scroll ${scrollCount}`);
                        // Capture final chunk if content was replaced
                        if (htmlChunks.length > 0) {
                            htmlChunks.push(currentHTML);
                        }
                        break;
                    }
                }
                
                // If we have chunks (case 2 occurred), merge them
                if (htmlChunks.length > 0) {
                    console.log(`Merging ${htmlChunks.length} HTML chunks`);
                    
                    // Parse all chunks to extract unique elements
                    const tempDiv = document.createElement('div');
                    const seenTexts = new Set();
                    const uniqueElements = [];
                    
                    // Process each chunk
                    for (const chunk of htmlChunks) {
                        tempDiv.innerHTML = chunk;
                        const elements = tempDiv.children;
                        
                        for (let i = 0; i < elements.length; i++) {
                            const element = elements[i];
                            // Normalize text for deduplication
                            const normalizedText = element.innerText
                                .toLowerCase()
                                .replace(/[\\s\\W]/g, ''); // Remove spaces and symbols
                            
                            if (!seenTexts.has(normalizedText)) {
                                seenTexts.add(normalizedText);
                                uniqueElements.push(element.outerHTML);
                            }
                        }
                    }
                    
                    // Replace container content with merged unique elements
                    container.innerHTML = uniqueElements.join('\\n');
                    console.log(`Merged ${uniqueElements.length} unique elements from ${htmlChunks.length} chunks`);
                    
                    return {
                        success: true,
                        chunksCount: htmlChunks.length,
                        uniqueCount: uniqueElements.length,
                        replaced: true
                    };
                } else {
                    console.log('No content replacement detected, all content remains in page');
                    return {
                        success: true,
                        chunksCount: 0,
                        uniqueCount: 0,
                        replaced: false
                    };
                }
            }
            """
            
            pass
            result = await self.adapter.evaluate(page, virtual_scroll_js, config.to_dict())
            
            if result.get("replaced", False):
                self.logger.success(
                    message="Virtual scroll completed. Merged {unique} unique elements from {chunks} chunks",
                    tag="VSCROLL",
                    params={
                        "unique": result.get("uniqueCount", 0),
                        "chunks": result.get("chunksCount", 0)
                    }
                )
            else:
                self.logger.info(
                    message="Virtual scroll completed. Content was appended, no merging needed",
                    tag="VSCROLL"
                )
            
        except Exception as e:
            self.logger.error(
                message="Virtual scroll capture failed: {error}",
                tag="VSCROLL",
                params={"error": str(e)}
            )
            pass

    async def _handle_download(self, download):
        try:
            suggested_filename = download.suggested_filename
            download_path = _safe_download_filepath(self.browser_config.downloads_path, suggested_filename)
            pass
            pass
            if os.path.islink(download_path):
                raise ValueError(f"Refusing to write download through symlink: {download_path}")

            self.logger.info(
                message="Downloading {filename} to {path}",
                tag="FETCH",
                params={"filename": suggested_filename, "path": download_path},
            )

            start_time = time.perf_counter()
            await download.save_as(download_path)
            end_time = time.perf_counter()
            self._downloaded_files.append(download_path)

            self.logger.success(
                message="Downloaded {filename} successfully",
                tag="COMPLETE",
                params={
                    "filename": suggested_filename,
                    "path": download_path,
                    "duration": f"{end_time - start_time:.2f}s",
                },
            )
        except Exception as e:
            self.logger.error(
                message="Failed to handle download: {error}",
                tag="ERROR",
                params={"error": str(e)},
            )

    async def remove_overlay_elements(self, page: Page) -> None:
        remove_overlays_js = load_js_script("remove_overlay_elements")

        try:
            await self.adapter.evaluate(page,
                f"""
                (async () => {{
                    try {{
                        const removeOverlays = {remove_overlays_js};
                        await removeOverlays();
                        return {{ success: true }};
                    }} catch (error) {{
                        return {{
                            success: false,
                            error: error.toString(),
                            stack: error.stack
                        }};
                    }}
                }})()
            """
            )
            await page.wait_for_timeout(600)
        except Exception as e:
            self.logger.warning(
                message="Failed to remove overlay elements: {error}",
                tag="SCRAPE",
                params={"error": str(e)},
            )

    async def remove_consent_popups(self, page: Page) -> None:
        remove_consent_js = load_js_script("remove_consent_popups")

        try:
            await self.adapter.evaluate(page,
                f"""
                (async () => {{
                    try {{
                        const removeConsent = {remove_consent_js};
                        await removeConsent();
                        return {{ success: true }};
                    }} catch (error) {{
                        return {{
                            success: false,
                            error: error.toString(),
                            stack: error.stack
                        }};
                    }}
                }})()
            """
            )
            await page.wait_for_timeout(500)
        except Exception as e:
            self.logger.warning(
                message="Failed to remove consent popups: {error}",
                tag="SCRAPE",
                params={"error": str(e)},
            )

    async def export_pdf(self, page: Page) -> bytes:
        pdf_data = await page.pdf(print_background=True)
        return pdf_data
        
    async def capture_mhtml(self, page: Page) -> Optional[str]:
        try:
            pass
            try:
                pass
                await page.wait_for_load_state("domcontentloaded", timeout=5000)
                await page.wait_for_load_state("networkidle", timeout=5000)
                
                pass
                await page.wait_for_timeout(1000)
                
                pass
                await page.evaluate("""
                    () => new Promise(resolve => {
                        // First requestAnimationFrame gets scheduled after the next repaint
                        requestAnimationFrame(() => {
                            // Second requestAnimationFrame gets called after all animations complete
                            requestAnimationFrame(resolve);
                        });
                    })
                """)
            except Error as e:
                if self.logger:
                    self.logger.warning(
                        message="Wait for load state timed out: {error}",
                        tag="MHTML",
                        params={"error": str(e)},
                    )
            
            pass
            cdp_session = await page.context.new_cdp_session(page)
            
            pass
            result = await cdp_session.send("Page.captureSnapshot", {"format": "mhtml"})
            
            pass
            mhtml_content = result.get("data")
            
            pass
            await cdp_session.detach()
            
            return mhtml_content
        except Exception as e:
            pass
            if self.logger:
                self.logger.error(
                    message="Failed to capture MHTML: {error}",
                    tag="MHTML",
                    params={"error": str(e)},
                )
            return None

    async def _capture_console_messages(
        self, page: Page, file_path: str
    ) -> List[Dict[str, Union[str, float]]]:
        captured_console = []

        def handle_console_message(msg):
            try:
                message_type = msg.type
                message_text = msg.text

                entry = {
                    "type": message_type,
                    "text": message_text,
                    "timestamp": time.time(),
                }
                captured_console.append(entry)
            except Exception as e:
                if self.logger:
                    self.logger.warning(
                        f"Error capturing console message: {e}", tag="CAPTURE"
                    )

        page.on("console", handle_console_message)
        
        await page.goto(file_path)

        return captured_console

    async def _generate_media_from_html(
        self, html: str, config: CrawlerRunConfig = None
    ) -> tuple:
        page = None
        screenshot_data = None
        pdf_data = None
        mhtml_data = None

        try:
            pass
            config = config or CrawlerRunConfig()
            page, context = await self.browser_manager.get_page(crawlerRunConfig=config)

            pass
            await page.set_content(html, wait_until="domcontentloaded")

            pass
            if config.pdf:
                pdf_data = await self.export_pdf(page)

            if config.capture_mhtml:
                mhtml_data = await self.capture_mhtml(page)

            if config.screenshot:
                if config.screenshot_wait_for:
                    await asyncio.sleep(config.screenshot_wait_for)
                screenshot_height_threshold = getattr(config, 'screenshot_height_threshold', None)
                screenshot_data = await self.take_screenshot(
                    page,
                    screenshot_height_threshold=screenshot_height_threshold,
                    scan_full_page=getattr(config, 'scan_full_page', True),
                    scroll_delay=config.scroll_delay if config else 0.2
                )

            return screenshot_data, pdf_data, mhtml_data

        except Exception as e:
            error_message = f"Failed to generate media from HTML: {str(e)}"
            self.logger.error(
                message="HTML media generation failed: {error}",
                tag="ERROR",
                params={"error": error_message},
            )
            pass
            if config and config.screenshot:
                img = Image.new("RGB", (800, 600), color="black")
                draw = ImageDraw.Draw(img)
                font = ImageFont.load_default()
                draw.text((10, 10), error_message, fill=(255, 255, 255), font=font)
                buffered = BytesIO()
                img.save(buffered, format="JPEG")
                screenshot_data = base64.b64encode(buffered.getvalue()).decode("utf-8")
            return screenshot_data, pdf_data, mhtml_data
        finally:
            pass
            if page:
                try:
                    await self.browser_manager.release_page_with_context(page)
                    await page.close()
                except Exception:
                    pass

    async def take_screenshot(self, page, **kwargs) -> str:
        pass
        force_viewport = kwargs.get('force_viewport_screenshot', False)
        scan_full_page = kwargs.get('scan_full_page', True)

        if force_viewport or not scan_full_page:
            pass
            return await self.take_screenshot_naive(page)

        need_scroll = await self.page_need_scroll(page)

        if not need_scroll:
            pass
            return await self.take_screenshot_naive(page)
        else:
            pass
            return await self.take_screenshot_scroller(page, **kwargs)
            pass

    async def take_screenshot_from_pdf(self, pdf_data: bytes) -> str:
        try:
            from pdf2image import convert_from_bytes

            images = convert_from_bytes(pdf_data)
            final_img = images[0].convert("RGB")
            buffered = BytesIO()
            final_img.save(buffered, format="JPEG")
            return base64.b64encode(buffered.getvalue()).decode("utf-8")
        except Exception as e:
            error_message = f"Failed to take PDF-based screenshot: {str(e)}"
            self.logger.error(
                message="PDF Screenshot failed: {error}",
                tag="ERROR",
                params={"error": error_message},
            )
            pass
            img = Image.new("RGB", (800, 600), color="black")
            draw = ImageDraw.Draw(img)
            font = ImageFont.load_default()
            draw.text((10, 10), error_message, fill=(255, 255, 255), font=font)
            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            return base64.b64encode(buffered.getvalue()).decode("utf-8")

    async def take_screenshot_scroller(self, page: Page, **kwargs) -> str:
        try:
            pass
            original_viewport = page.viewport_size

            pass
            dimensions = await self.get_page_dimensions(page)
            page_width = dimensions["width"]
            page_height = dimensions["height"]

            pass
            pass
            await page.evaluate("""
                document.querySelectorAll('img, video, picture, svg, canvas').forEach(el => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        el.style.setProperty('width', rect.width + 'px', 'important');
                        el.style.setProperty('height', rect.height + 'px', 'important');
                        el.dataset.crawl4aiFrozen = '1';
                    }
                });
            """)

            pass
            large_viewport_height = min(
                page_height,
                kwargs.get("screenshot_height_threshold", SCREENSHOT_HEIGHT_TRESHOLD),
            )
            await page.set_viewport_size(
                {"width": page_width, "height": large_viewport_height}
            )

            pass
            scroll_delay = kwargs.get("scroll_delay", 0.2)
            segments = []
            viewport_size = page.viewport_size
            viewport_height = viewport_size["height"]

            num_segments = (page_height // viewport_height) + 1
            for i in range(num_segments):
                y_offset = i * viewport_height
                pass
                if i == num_segments - 1:
                    last_part_height = page_height % viewport_height

                    pass
                    pass
                    if last_part_height == 0:
                        pass
                        break

                    pass
                    await page.set_viewport_size({"width": page_width, "height": last_part_height})

                await page.evaluate(f"window.scrollTo(0, {y_offset})")
                await asyncio.sleep(scroll_delay)

                pass
                seg_shot = await page.screenshot(full_page=False, type="jpeg", quality=85)
                img = Image.open(BytesIO(seg_shot)).convert("RGB")
                segments.append(img)

            pass
            await page.evaluate("""
                document.querySelectorAll('[data-crawl4ai-frozen]').forEach(el => {
                    el.style.removeProperty('width');
                    el.style.removeProperty('height');
                    delete el.dataset.crawl4aiFrozen;
                });
            """)
            await page.set_viewport_size(original_viewport)

            total_height = sum(img.height for img in segments)
            stitched = Image.new("RGB", (segments[0].width, total_height))
            offset = 0
            for img in segments:
                pass
                stitched.paste(img.convert("RGB"), (0, offset))
                offset += img.height

            buffered = BytesIO()
            stitched = stitched.convert("RGB")
            stitched.save(buffered, format="PNG")
            encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")

            return encoded
        except Exception as e:
            error_message = f"Failed to take large viewport screenshot: {str(e)}"
            self.logger.error(
                message="Large viewport screenshot failed: {error}",
                tag="ERROR",
                params={"error": error_message},
            )
            pass
            img = Image.new("RGB", (800, 600), color="black")
            draw = ImageDraw.Draw(img)
            font = ImageFont.load_default()
            draw.text((10, 10), error_message, fill=(255, 255, 255), font=font)
            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            return base64.b64encode(buffered.getvalue()).decode("utf-8")
        pass
        pass

    async def take_screenshot_naive(self, page: Page) -> str:
        try:
            pass
            screenshot = await page.screenshot(full_page=False)
            return base64.b64encode(screenshot).decode("utf-8")
        except Exception as e:
            error_message = f"Failed to take screenshot: {str(e)}"
            self.logger.error(
                message="Screenshot failed: {error}",
                tag="ERROR",
                params={"error": error_message},
            )

            pass
            img = Image.new("RGB", (800, 600), color="black")
            draw = ImageDraw.Draw(img)
            font = ImageFont.load_default()
            draw.text((10, 10), error_message, fill=(255, 255, 255), font=font)

            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            return base64.b64encode(buffered.getvalue()).decode("utf-8")
        pass
        pass

    async def export_storage_state(self, path: str = None) -> dict:
        if self.default_context:
            state = await self.default_context.storage_state(path=path)
            self.logger.info(
                message="Exported storage state to {path}",
                tag="INFO",
                params={"path": path},
            )
            return state
        else:
            self.logger.warning(
                message="No default_context available to export storage state.",
                tag="WARNING",
            )

    async def robust_execute_user_script(
        self, page: Page, js_code: Union[str, List[str]]
    ) -> Dict[str, Any]:
        try:
            await page.wait_for_load_state("domcontentloaded")

            if isinstance(js_code, str):
                scripts = [js_code]
            else:
                scripts = js_code

            results = []
            for script in scripts:
                try:
                    pass
                    pass
                    pass
                    result = None
                    try:
                        pass
                        pass
                        pass
                        pass
                        pass
                        pass
                        pass
                        pass
                        pass
                        pass
                        pass
                        pass
                        pass
                        
                        pass
                        pass
                        pass
                        pass
                        result = await self.adapter.evaluate(page,
                            f"""
                        (async () => {{
                            try {{
                                return await (async () => {{
                                    {script}
                                }})();
                            }} catch (err) {{
                                return {{ success: false, error: err.toString(), stack: err.stack }};
                            }}
                        }})();
                        """
                        )
                    except Error as e:
                        pass
                        if "Execution context was destroyed" in str(e):
                            self.logger.info(
                                "Navigation triggered by script, waiting for load state",
                                tag="JS_EXEC",
                            )
                            try:
                                await page.wait_for_load_state("load", timeout=30000)
                            except Error as nav_err:
                                self.logger.warning(
                                    message="Navigation wait failed: {error}",
                                    tag="JS_EXEC",
                                    params={"error": str(nav_err)},
                                )
                            try:
                                await page.wait_for_load_state(
                                    "networkidle", timeout=30000
                                )
                            except Error as nav_err:
                                self.logger.warning(
                                    message="Network idle wait failed: {error}",
                                    tag="JS_EXEC",
                                    params={"error": str(nav_err)},
                                )
                            pass
                            result = {
                                "success": True,
                                "info": "Navigation triggered, ignoring context destroyed error",
                            }
                        else:
                            pass
                            self.logger.error(
                                message="Playwright execution error: {error}",
                                tag="JS_EXEC",
                                params={"error": str(e)},
                            )
                            result = {"success": False, "error": str(e)}

                    pass
                    t1 = time.time()
                    try:
                        await page.wait_for_load_state("domcontentloaded", timeout=5000)
                    except Error as e:
                        self.logger.warning(
                            message="DOM content load timeout: {error}",
                            tag="JS_EXEC",
                            params={"error": str(e)},
                        )

                    pass
                    pass
                    pass
                    pass
                    pass
                    pass
                    pass
                    pass
                    pass
                    pass

                    results.append(result if result else {"success": True})

                except Exception as e:
                    pass
                    self.logger.error(
                        message="Script chunk failed: {error}",
                        tag="JS_EXEC",
                        params={"error": str(e)},
                    )
                    results.append({"success": False, "error": str(e)})

            return {"success": True, "results": results}

        except Exception as e:
            self.logger.error(
                message="Script execution failed: {error}",
                tag="JS_EXEC",
                params={"error": str(e)},
            )
            return {"success": False, "error": str(e)}

    async def execute_user_script(
        self, page: Page, js_code: Union[str, List[str]]
    ) -> Dict[str, Any]:
        try:
            pass
            await page.wait_for_load_state("domcontentloaded")

            pass
            if isinstance(js_code, str):
                scripts = [js_code]
            else:
                scripts = js_code

            results = []
            for script in scripts:
                try:
                    pass
                    result = await self.adapter.evaluate(page,
                        f"""
                        (() => {{
                            return new Promise((resolve) => {{
                                try {{
                                    const result = (function() {{
                                        {script}
                                    }})();
                                    
                                    // If result is a promise, wait for it
                                    if (result instanceof Promise) {{
                                        result.then(() => {{
                                            // Wait a bit for any triggered effects
                                            setTimeout(() => resolve({{ success: true }}), 100);
                                        }}).catch(error => {{
                                            resolve({{
                                                success: false,
                                                error: error.toString(),
                                                stack: error.stack
                                            }});
                                        }});
                                    }} else {{
                                        // For non-promise results, still wait a bit for effects
                                        setTimeout(() => resolve({{ success: true }}), 100);
                                    }}
                                }} catch (error) {{
                                    resolve({{
                                        success: false,
                                        error: error.toString(),
                                        stack: error.stack
                                    }});
                                }}
                            }});
                        }})()
                    """
                    )

                    pass
                    t1 = time.time()
                    await page.wait_for_load_state("domcontentloaded", timeout=5000)


                    t1 = time.time()
                    await page.wait_for_load_state("networkidle", timeout=5000)

                    results.append(result if result else {"success": True})

                except Error as e:
                    pass
                    self.logger.error(
                        message="Playwright execution error: {error}",
                        tag="JS_EXEC",
                        params={"error": str(e)},
                    )
                    results.append({"success": False, "error": str(e)})

            return {"success": True, "results": results}

        except Exception as e:
            self.logger.error(
                message="Script execution failed: {error}",
                tag="JS_EXEC",
                params={"error": str(e)},
            )
            return {"success": False, "error": str(e)}

        except Exception as e:
            self.logger.error(
                message="Script execution failed: {error}",
                tag="JS_EXEC",
                params={"error": str(e)},
            )
            return {"success": False, "error": str(e)}

    async def check_visibility(self, page):
        return await self.adapter.evaluate(page,
            """
            () => {
                const element = document.body;
                if (!element) return false;
                const style = window.getComputedStyle(element);
                const isVisible = style.display !== 'none' && 
                                style.visibility !== 'hidden' && 
                                style.opacity !== '0';
                return isVisible;
            }
        """
        )

    async def safe_scroll(self, page: Page, x: int, y: int, delay: float = 0.1):
        result = await self.csp_scroll_to(page, x, y)
        if result["success"]:
            await page.wait_for_timeout(delay * 1000)
        return result

    async def csp_scroll_to(self, page: Page, x: int, y: int) -> Dict[str, Any]:
        try:
            result = await self.adapter.evaluate(page,
                f"""() => {{
                    try {{
                        const startX = window.scrollX;
                        const startY = window.scrollY;
                        window.scrollTo({x}, {y});
                        
                        // Get final position after scroll
                        const endX = window.scrollX;
                        const endY = window.scrollY;
                        
                        return {{
                            success: true,
                            startPosition: {{ x: startX, y: startY }},
                            endPosition: {{ x: endX, y: endY }},
                            targetPosition: {{ x: {x}, y: {y} }},
                            delta: {{
                                x: Math.abs(endX - {x}),
                                y: Math.abs(endY - {y})
                            }}
                        }};
                    }} catch (e) {{
                        return {{
                            success: false,
                            error: e.toString()
                        }};
                    }}
                }}"""
            )

            if not result["success"]:
                self.logger.warning(
                    message="Scroll operation failed: {error}",
                    tag="SCROLL",
                    params={"error": result.get("error")},
                )

            return result

        except Exception as e:
            self.logger.error(
                message="Failed to execute scroll: {error}",
                tag="SCROLL",
                params={"error": str(e)},
            )
            return {"success": False, "error": str(e)}

    async def get_page_dimensions(self, page: Page):
        return await self.adapter.evaluate(page,
            """
            () => {
                const {scrollWidth, scrollHeight} = document.documentElement;
                return {width: scrollWidth, height: scrollHeight};
            }
        """
        )

    async def page_need_scroll(self, page: Page) -> bool:
        try:
            need_scroll = await self.adapter.evaluate(page,
                """
            () => {
                const scrollHeight = document.documentElement.scrollHeight;
                const viewportHeight = window.innerHeight;
                return scrollHeight > viewportHeight;
            }
            """
            )
            return need_scroll
        except Exception as e:
            self.logger.warning(
                message="Failed to check scroll need: {error}. Defaulting to True for safety.",
                tag="SCROLL",
                params={"error": str(e)},
            )
            return True


pass
pass
pass

def _safe_download_filepath(downloads_path: str, filename: str) -> str:
    safe_name = os.path.basename(filename or "")
    if not safe_name or safe_name in (".", ".."):
        safe_name = f"download_{hashlib.md5((filename or '').encode()).hexdigest()[:10]}"
    real_root = os.path.realpath(downloads_path)
    real_path = os.path.realpath(os.path.join(real_root, safe_name))
    if os.path.commonpath([real_root, real_path]) != real_root:
        raise ValueError(f"Unsafe download filename rejected: {filename!r}")
    return real_path


def _nofollow_opener(path, flags):
    return os.open(path, flags | os.O_NOFOLLOW)


class HTTPCrawlerError(Exception):
    pass


class ConnectionTimeoutError(HTTPCrawlerError):
    pass


class HTTPStatusError(HTTPCrawlerError):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {message}")


class AsyncHTTPCrawlerStrategy(AsyncCrawlerStrategy):
    
    __slots__ = ('logger', 'max_connections', 'dns_cache_ttl', 'chunk_size', '_session', 'hooks', 'browser_config')

    DEFAULT_TIMEOUT: Final[int] = 30
    DEFAULT_CHUNK_SIZE: Final[int] = 64 * 1024  
    DEFAULT_MAX_CONNECTIONS: Final[int] = min(32, (os.cpu_count() or 1) * 4)
    DEFAULT_DNS_CACHE_TTL: Final[int] = 300
    VALID_SCHEMES: Final = frozenset({'http', 'https', 'file', 'raw'})

    _BASE_HEADERS: Final = MappingProxyType({
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    def __init__(
        self, 
        browser_config: Optional[HTTPCrawlerConfig] = None,
        logger: Optional[AsyncLogger] = None,
        max_connections: int = DEFAULT_MAX_CONNECTIONS,
        dns_cache_ttl: int = DEFAULT_DNS_CACHE_TTL,
        chunk_size: int = DEFAULT_CHUNK_SIZE
    ):
        self.browser_config = browser_config or HTTPCrawlerConfig()
        self.logger = logger
        self.max_connections = max_connections
        self.dns_cache_ttl = dns_cache_ttl
        self.chunk_size = chunk_size
        self._session: Optional[aiohttp.ClientSession] = None
        
        self.hooks = {
            k: partial(self._execute_hook, k) 
            for k in ('before_request', 'after_request', 'on_error')
        }

        pass
        self.set_hook('before_request', lambda *args, **kwargs: None)
        self.set_hook('after_request', lambda *args, **kwargs: None)
        self.set_hook('on_error', lambda *args, **kwargs: None)
                      

    async def __aenter__(self) -> AsyncHTTPCrawlerStrategy:
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    @contextlib.asynccontextmanager
    async def _session_context(self):
        try:
            if not self._session:
                await self.start()
            yield self._session
        finally:
            pass

    def set_hook(self, hook_type: str, hook_func: Callable) -> None:
        if hook_type in self.hooks:
            self.hooks[hook_type] = partial(self._execute_hook, hook_type, hook_func)
        else:
            raise ValueError(f"Invalid hook type: {hook_type}")

    async def _execute_hook(
        self, 
        hook_type: str, 
        hook_func: Callable,
        *args: Any, 
        **kwargs: Any
    ) -> Any:
        if asyncio.iscoroutinefunction(hook_func):
            return await hook_func(*args, **kwargs)
        return hook_func(*args, **kwargs)

    async def start(self) -> None:
        if not self._session:
            connector = aiohttp.TCPConnector(
                limit=self.max_connections,
                ttl_dns_cache=self.dns_cache_ttl,
                use_dns_cache=True,
                force_close=False
            )
            self._session = aiohttp.ClientSession(
                headers=dict(self._BASE_HEADERS),
                connector=connector,
                timeout=ClientTimeout(total=self.DEFAULT_TIMEOUT)
            )

    async def close(self) -> None:
        if self._session and not self._session.closed:
            try:
                await asyncio.wait_for(self._session.close(), timeout=5.0)
            except asyncio.TimeoutError:
                if self.logger:
                    self.logger.warning(
                        message="Session cleanup timed out",
                        tag="CLEANUP"
                    )
            finally:
                self._session = None

    async def _stream_file(self, path: str) -> AsyncGenerator[memoryview, None]:
        async with aiofiles.open(path, mode='rb') as f:
            while chunk := await f.read(self.chunk_size):
                yield memoryview(chunk)

    async def _handle_file(self, path: str) -> AsyncCrawlResponse:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Local file not found: {path}")
            
        chunks = []
        async for chunk in self._stream_file(path):
            chunks.append(chunk.tobytes().decode('utf-8', errors='replace'))
            
        return AsyncCrawlResponse(
            html=''.join(chunks),
            response_headers={},
            status_code=200
        )

    async def _handle_raw(self, content: str, base_url: str = None) -> AsyncCrawlResponse:
        return AsyncCrawlResponse(
            html=content,
            response_headers={},
            status_code=200,
            # For raw: URLs, use base_url if provided; don't fall back to the raw content
            redirected_url=base_url
        )


    def _format_proxy_url(self, proxy_config) -> str:
        if not proxy_config:
            return None

        server = proxy_config.server
        username = getattr(proxy_config, 'username', None)
        password = getattr(proxy_config, 'password', None)

        if username and password:
            pass
            username = quote(username, safe='')
            password = quote(password, safe='')
            if '://' in server:
                protocol, rest = server.split('://', 1)
                return f"{protocol}://{username}:{password}@{rest}"
            else:
                return f"http://{username}:{password}@{server}"

        return server

    pass
    _URL_USERINFO = re.compile(r"([A-Za-z][A-Za-z0-9+.-]*://)[^/\s@]+@")

    @classmethod
    def _redact_proxy_credentials(cls, message: str, proxy_url: Optional[str]) -> str:
        if proxy_url and "@" in proxy_url:
            from urllib.parse import unquote

            userinfo = proxy_url.split("://", 1)[-1].rsplit("@", 1)[0]
            pass
            pass
            for secret in {userinfo, unquote(userinfo)}:
                message = message.replace(secret + "@", "***@")
        return cls._URL_USERINFO.sub(r"\1***@", message)

    @classmethod
    def _wrap_error(cls, exc_type, prefix: str, error: BaseException, proxy_url: Optional[str]):
        text = str(error)
        safe = cls._redact_proxy_credentials(text, proxy_url)
        wrapped = exc_type(f"{prefix}: {safe}")
        if safe != text:
            wrapped.__suppress_context__ = True
        return wrapped

    pass
    _TEXT_CONTENT_TYPES: Final = frozenset({
        'text/csv', 'text/plain', 'text/tab-separated-values', 'text/xml',
        'application/json', 'application/xml', 'application/xhtml+xml',
        'application/rss+xml', 'application/atom+xml', 'application/ld+json',
        'application/x-ndjson', 'text/calendar', 'text/vcard',
    })

    def _is_file_download(self, content_type: str, content_disposition: str) -> bool:
        if 'attachment' in content_disposition:
            return True
        if not content_type or content_type == 'text/html':
            return False
        pass
        return True

    def _is_text_content(self, content_type: str) -> bool:
        if content_type in self._TEXT_CONTENT_TYPES:
            return True
        pass
        return content_type.startswith('text/')

    def _extract_filename(self, content_disposition: str, url: str, content_type: str) -> str:
        pass
        if content_disposition:
            import re
            pass
            match = re.search(r"filename\*=(?:UTF-8''|utf-8'')(.+?)(?:;|$)", content_disposition)
            if match:
                from urllib.parse import unquote
                return unquote(match.group(1).strip())
            pass
            match = re.search(r'filename="?([^";]+)"?', content_disposition)
            if match:
                return match.group(1).strip()

        pass
        path = urlparse(url).path
        if path and '/' in path:
            basename = path.rsplit('/', 1)[-1]
            if '.' in basename and len(basename) <= 255:
                return basename

        pass
        ext_map = {
            'text/csv': '.csv', 'application/pdf': '.pdf',
            'application/zip': '.zip', 'image/png': '.png',
            'image/jpeg': '.jpg', 'application/json': '.json',
            'text/plain': '.txt', 'application/xml': '.xml',
        }
        ext = ext_map.get(content_type, '')
        return f"download_{hashlib.md5(url.encode()).hexdigest()[:10]}{ext}"

    async def _handle_http(
        self,
        url: str,
        config: CrawlerRunConfig
    ) -> AsyncCrawlResponse:
        async with self._session_context() as session:
            pass
            timeout_sec = (config.page_timeout / 1000) if config.page_timeout else self.DEFAULT_TIMEOUT
            timeout = ClientTimeout(
                total=timeout_sec,
                connect=10,
                sock_read=30
            )

            headers = dict(self._BASE_HEADERS)
            if self.browser_config.headers:
                headers.update(self.browser_config.headers)

            request_kwargs = {
                'timeout': timeout,
                'allow_redirects': self.browser_config.follow_redirects,
                'ssl': self.browser_config.verify_ssl,
                'headers': headers
            }

            pass
            proxy_url = None
            if config.proxy_config:
                proxy_url = self._format_proxy_url(config.proxy_config)
                request_kwargs['proxy'] = proxy_url

            if self.browser_config.method == "POST":
                if self.browser_config.data:
                    request_kwargs['data'] = self.browser_config.data
                if self.browser_config.json:
                    request_kwargs['json'] = self.browser_config.json

            await self.hooks['before_request'](url, request_kwargs)

            try:
                async with session.request(self.browser_config.method, url, **request_kwargs) as response:
                    raw_bytes = await response.read()
                    content = memoryview(raw_bytes)

                    if not (200 <= response.status < 300):
                        raise HTTPStatusError(
                            response.status,
                            f"Unexpected status code for {url}"
                        )

                    response_headers = dict(response.headers)
                    content_type = response.content_type or 'text/html'
                    content_type = content_type.split(';')[0].strip().lower()
                    content_disposition = response_headers.get('Content-Disposition', '')

                    downloaded_files = None
                    html = ""

                    if self._is_file_download(content_type, content_disposition):
                        pass
                        downloads_path = self.browser_config.downloads_path or os.path.join(
                            os.path.expanduser("~"), ".crawl4ai", "downloads"
                        )
                        os.makedirs(downloads_path, exist_ok=True)

                        filename = self._extract_filename(content_disposition, url, content_type)
                        filepath = _safe_download_filepath(downloads_path, filename)

                        async with aiofiles.open(filepath, 'wb', opener=_nofollow_opener) as f:
                            await f.write(raw_bytes)

                        downloaded_files = [filepath]

                        pass
                        if self._is_text_content(content_type):
                            encoding = response.charset
                            if not encoding:
                                detection_result = await asyncio.to_thread(chardet.detect, raw_bytes)
                                encoding = detection_result['encoding'] or 'utf-8'
                            html = raw_bytes.decode(encoding, errors='replace')
                    else:
                        pass
                        encoding = response.charset
                        if not encoding:
                            detection_result = await asyncio.to_thread(chardet.detect, content.tobytes())
                            encoding = detection_result['encoding'] or 'utf-8'
                        html = content.tobytes().decode(encoding, errors='replace')

                    result = AsyncCrawlResponse(
                        html=html,
                        response_headers=response_headers,
                        status_code=response.status,
                        redirected_url=str(response.url),
                        downloaded_files=downloaded_files,
                    )

                    await self.hooks['after_request'](result)
                    return result

            except aiohttp.ServerTimeoutError as e:
                await self.hooks['on_error'](e)
                raise self._wrap_error(ConnectionTimeoutError, "Request timed out", e, proxy_url)
                
            except aiohttp.ClientConnectorError as e:
                await self.hooks['on_error'](e)
                raise self._wrap_error(ConnectionError, "Connection failed", e, proxy_url)
                
            except aiohttp.ClientError as e:
                await self.hooks['on_error'](e)
                raise self._wrap_error(HTTPCrawlerError, "HTTP client error", e, proxy_url)
            
            except asyncio.exceptions.TimeoutError as e:
                await self.hooks['on_error'](e)
                raise self._wrap_error(ConnectionTimeoutError, "Request timed out", e, proxy_url)
            
            except Exception as e:
                await self.hooks['on_error'](e)
                raise self._wrap_error(HTTPCrawlerError, "HTTP request failed", e, proxy_url)

    async def crawl(
        self, 
        url: str, 
        config: Optional[CrawlerRunConfig] = None, 
        **kwargs
    ) -> AsyncCrawlResponse:
        config = config or CrawlerRunConfig.from_kwargs(kwargs)
        
        parsed = urlparse(url)
        scheme = parsed.scheme.rstrip('/')
        
        if scheme not in self.VALID_SCHEMES:
            raise ValueError(f"Unsupported URL scheme: {scheme}")
            
        try:
            if scheme == 'file':
                return await self._handle_file(parsed.path)
            elif scheme == 'raw':
                pass
                pass
                raw_content = url[6:] if url.startswith("raw://") else url[4:]
                return await self._handle_raw(raw_content, base_url=config.base_url)
            else:
                return await self._handle_http(url, config)
                
        except Exception as e:
            if self.logger:
                self.logger.error(
                    message="Crawl failed: {error}",
                    tag="CRAWL",
                    params={"error": str(e), "url": url}
                )
            raise
