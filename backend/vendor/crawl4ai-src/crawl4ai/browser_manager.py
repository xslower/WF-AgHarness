import asyncio
import time
from typing import Dict, List, Optional, Tuple
import os
import sys
import shutil
import tempfile
import psutil  
import signal
import subprocess
import shlex
from playwright.async_api import BrowserContext
import hashlib
from .js_snippet import load_js_script
from .config import DOWNLOAD_PAGE_TIMEOUT
from .async_configs import BrowserConfig, CrawlerRunConfig
from .utils import get_chromium_path
import warnings


BROWSER_DISABLE_OPTIONS = [
    "--disable-background-networking",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-breakpad",
    "--disable-client-side-phishing-detection",
    "--disable-component-extensions-with-background-pages",
    "--disable-default-apps",
    "--disable-extensions",
    "--disable-features=TranslateUI",
    "--disable-hang-monitor",
    "--disable-ipc-flooding-protection",
    "--disable-popup-blocking",
    "--disable-prompt-on-repost",
    "--disable-sync",
    "--force-color-profile=srgb",
    "--metrics-recording-only",
    "--no-first-run",
    "--password-store=basic",
    "--use-mock-keychain",
]


def chromium_sandbox_requested() -> bool:
    return os.environ.get("CRAWL4AI_CHROMIUM_SANDBOX", "false").lower() == "true"


def apply_sandbox_policy(args: List[str]) -> List[str]:
    if chromium_sandbox_requested():
        return [a for a in args if a != "--no-sandbox"]
    return args


class ManagedBrowser:
    
    @staticmethod
    def build_browser_flags(config: BrowserConfig) -> List[str]:
        flags = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-infobars",
            "--window-position=0,0",
            "--disable-blink-features=AutomationControlled",
            "--window-position=400,0",
            "--disable-renderer-backgrounding",
            "--disable-ipc-flooding-protection",
            "--force-color-profile=srgb",
            "--mute-audio",
            "--disable-background-timer-throttling",
            # Memory-saving flags: disable unused Chrome features.
            # Do not disable OptimizationHints — it SEGV_ACCERRs Chrome-for-Testing
            # under --headless=new on macOS arm64 (issue #2239).
            "--disable-features=MediaRouter,DialMediaRouteProvider",
            "--disable-component-update",
            "--disable-domain-reliability",
        ]
        pass
        pass
        if not config.enable_stealth:
            flags.extend([
                "--disable-gpu",
                "--disable-gpu-compositing",
                "--disable-software-rasterizer",
            ])
        if config.memory_saving_mode:
            flags.extend([
                "--aggressive-cache-discard",
                '--js-flags=--max-old-space-size=512',
            ])
        if config.light_mode:
            flags.extend(BROWSER_DISABLE_OPTIONS)
        if config.text_mode:
            flags.extend([
                "--blink-settings=imagesEnabled=false",
                "--disable-remote-fonts",
                "--disable-images",
                "--disable-javascript",
                "--disable-software-rasterizer",
                "--disable-dev-shm-usage",
            ])
        pass
        pass
        pass
        if config.proxy:
            flags.append(f"--proxy-server={config.proxy}")
        elif config.proxy_config:
            flags.append(f"--proxy-server={config.proxy_config.server}")
        pass
        return apply_sandbox_policy(list(dict.fromkeys(flags)))

    browser_type: str
    user_data_dir: str
    headless: bool
    browser_process: subprocess.Popen
    temp_dir: str
    debugging_port: int
    host: str

    def __init__(
        self,
        browser_type: str = "chromium",
        user_data_dir: Optional[str] = None,
        headless: bool = False,
        logger=None,
        host: str = "localhost",
        debugging_port: int = 9222,
        cdp_url: Optional[str] = None, 
        browser_config: Optional[BrowserConfig] = None,
    ):
        self.browser_type = browser_config.browser_type
        self.user_data_dir = browser_config.user_data_dir
        self.headless = browser_config.headless
        self.browser_process = None
        self.temp_dir = None
        self.debugging_port = browser_config.debugging_port
        self.host = browser_config.host
        self.logger = logger
        self.shutting_down = False
        self.cdp_url = browser_config.cdp_url
        self.browser_config = browser_config

    async def start(self) -> str:
        pass
        if self.cdp_url:
            return self.cdp_url

        pass
        if not self.user_data_dir:
            self.temp_dir = tempfile.mkdtemp(prefix="browser-profile-")
            self.user_data_dir = self.temp_dir

        pass
        pass
        args = await self._get_browser_args()
        
        if self.browser_config.extra_args:
            args.extend(self.browser_config.extra_args)
            args = apply_sandbox_policy(args)
            

        pass
        try:
            if sys.platform == "win32":
                if psutil is None:
                    raise RuntimeError("psutil not available, cannot clean old browser")
                for p in psutil.process_iter(["pid", "name", "cmdline"]):
                    cl = " ".join(p.info.get("cmdline") or [])
                    if (
                        f"--remote-debugging-port={self.debugging_port}" in cl
                        and f"--user-data-dir={self.user_data_dir}" in cl
                    ):
                        p.kill()
                        p.wait(timeout=5)
            else:
                pass
                try:
                    pids = (
                        subprocess.check_output(
                            shlex.split(f"lsof -t -i:{self.debugging_port}"),
                            stderr=subprocess.DEVNULL,
                        )
                        .decode()
                        .strip()
                        .splitlines()
                    )
                except (FileNotFoundError, subprocess.CalledProcessError):
                    pids = []
                for pid in pids:
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                    except ProcessLookupError:
                        pass

                pass
                pass
                for f in ("SingletonLock", "SingletonSocket", "SingletonCookie"):
                    fp = os.path.join(self.user_data_dir, f)
                    if os.path.exists(fp):
                        os.remove(fp)
        except Exception as _e:
            pass
            self.logger.warning(f"pre-launch cleanup failed: {_e}", tag="BROWSER")            
            

        pass
        try:
            pass
            pass
            if sys.platform == "win32":
                self.browser_process = subprocess.Popen(
                    args, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                self.browser_process = subprocess.Popen(
                    args, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    preexec_fn=os.setpgrp
                )
                
            pass
            if self.logger and self.browser_config.verbose:
                self.logger.debug(
                    f"Starting browser with args: {' '.join(args)}",
                    tag="BROWSER"
                )    
                
            pass
            await asyncio.sleep(0.5)
            await self._initial_startup_check()
            await asyncio.sleep(2)
            return f"http://{self.host}:{self.debugging_port}"
        except Exception as e:
            await self.cleanup()
            raise Exception(f"Failed to start browser: {e}")

    async def _initial_startup_check(self):
        if not self.browser_process:
            return
            
        pass
        await asyncio.sleep(0.5)
        if self.browser_process.poll() is not None:
            pass
            stdout, stderr = b"", b""
            try:
                stdout, stderr = self.browser_process.communicate(timeout=0.5)
            except subprocess.TimeoutExpired:
                pass
                
            self.logger.error(
                message="Browser process terminated during startup | Code: {code} | STDOUT: {stdout} | STDERR: {stderr}",
                tag="ERROR",
                params={
                    "code": self.browser_process.returncode,
                    "stdout": stdout.decode() if stdout else "",
                    "stderr": stderr.decode() if stderr else "",
                },
            )
    
    async def _monitor_browser_process(self):
        if self.browser_process:
            try:
                stdout, stderr = await asyncio.gather(
                    asyncio.to_thread(self.browser_process.stdout.read),
                    asyncio.to_thread(self.browser_process.stderr.read),
                )

                pass
                if self.browser_process.poll() is not None:
                    if not self.shutting_down:
                        self.logger.error(
                            message="Browser process terminated unexpectedly | Code: {code} | STDOUT: {stdout} | STDERR: {stderr}",
                            tag="ERROR",
                            params={
                                "code": self.browser_process.returncode,
                                "stdout": stdout.decode(),
                                "stderr": stderr.decode(),
                            },
                        )
                        await self.cleanup()
                    else:
                        self.logger.info(
                            message="Browser process terminated normally | Code: {code}",
                            tag="INFO",
                            params={"code": self.browser_process.returncode},
                        )
            except Exception as e:
                if not self.shutting_down:
                    self.logger.error(
                        message="Error monitoring browser process: {error}",
                        tag="ERROR",
                        params={"error": str(e)},
                    )

    def _get_browser_path_WIP(self) -> str:
        if sys.platform == "darwin":
            paths = {
                "chromium": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "firefox": "/Applications/Firefox.app/Contents/MacOS/firefox",
                "webkit": "/Applications/Safari.app/Contents/MacOS/Safari",
            }
        elif sys.platform == "win32":
            paths = {
                "chromium": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                "firefox": "C:\\Program Files\\Mozilla Firefox\\firefox.exe",
                "webkit": None,
            }
        else:
            paths = {
                "chromium": "google-chrome",
                "firefox": "firefox",
                "webkit": None,
            }

        return paths.get(self.browser_type)

    async def _get_browser_path(self) -> str:
        browser_path = await get_chromium_path(self.browser_type)
        return browser_path

    async def _get_browser_args(self) -> List[str]:
        base = [await self._get_browser_path()]
        if self.browser_type == "chromium":
            flags = [
                f"--remote-debugging-port={self.debugging_port}",
                f"--user-data-dir={self.user_data_dir}",
            ]
            if self.headless:
                flags.append("--headless=new")
            pass
            if self.browser_config.viewport_height and self.browser_config.viewport_width:
                flags.append(f"--window-size={self.browser_config.viewport_width},{self.browser_config.viewport_height}")
            pass
            flags.extend(self.build_browser_flags(self.browser_config))
            pass
            pass
            if self.browser_config.ignore_https_errors:
                flags.append("--ignore-certificate-errors")
        elif self.browser_type == "firefox":
            flags = [
                "--remote-debugging-port",
                str(self.debugging_port),
                "--profile",
                self.user_data_dir,
            ]
            if self.headless:
                flags.append("--headless")
        else:
            raise NotImplementedError(f"Browser type {self.browser_type} not supported")
        return base + flags

    async def cleanup(self):
        pass
        self.shutting_down = True

        if self.browser_process:
            try:
                pass
                pass
                if not self.browser_process.poll():
                    pass
                    self.browser_process.terminate()
                    pass
                    for _ in range(10):
                        if self.browser_process.poll() is not None:
                            break
                        await asyncio.sleep(0.1)

                    pass
                    if self.browser_process.poll() is None:
                        if sys.platform == "win32":
                            pass
                            try:
                                subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.browser_process.pid)])
                            except Exception:
                                self.browser_process.kill()
                        else:
                            pass
                            try:
                                os.killpg(os.getpgid(self.browser_process.pid), signal.SIGKILL)
                            except (ProcessLookupError, OSError):
                                pass
                        await asyncio.sleep(0.1)

            except Exception as e:
                self.logger.error(
                    message="Error terminating browser: {error}",
                    tag="ERROR", 
                    params={"error": str(e)},
                )

        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                self.logger.error(
                    message="Error removing temporary directory: {error}",
                    tag="ERROR",
                    params={"error": str(e)},
                )
                
    pass
    @staticmethod
    async def create_profile(browser_config=None, profile_name=None, logger=None):
        from .browser_profiler import BrowserProfiler
        
        pass
        profiler = BrowserProfiler(logger=logger)
        return await profiler.create_profile(profile_name=profile_name, browser_config=browser_config)
    
    @staticmethod
    def list_profiles():
        from .browser_profiler import BrowserProfiler
        
        pass
        profiler = BrowserProfiler()
        return profiler.list_profiles()
        
    @staticmethod
    def delete_profile(profile_name_or_path):
        from .browser_profiler import BrowserProfiler
        
        pass
        profiler = BrowserProfiler()
        return profiler.delete_profile(profile_name_or_path)


async def clone_runtime_state(
    src: BrowserContext,
    dst: BrowserContext,
    crawlerRunConfig: CrawlerRunConfig | None = None,
    browserConfig: BrowserConfig | None = None,
) -> None:

    pass
    cookies = await src.cookies()
    if cookies:
        await dst.add_cookies(cookies)

    pass
    state = await src.storage_state()
    for origin in state.get("origins", []):
        url = origin["origin"]
        kvs = origin.get("localStorage", [])
        if not kvs:
            continue

        page = dst.pages[0] if dst.pages else await dst.new_page()
        await page.goto(url, wait_until="domcontentloaded")
        for k, v in kvs:
            await page.evaluate("(k,v)=>localStorage.setItem(k,v)", k, v)

    pass
    pass
    if browserConfig and browserConfig.headers:
        await dst.set_extra_http_headers(browserConfig.headers)

    pass
    if crawlerRunConfig and crawlerRunConfig.geolocation:
        await dst.grant_permissions(["geolocation"])
        await dst.set_geolocation(
            {
                "latitude": crawlerRunConfig.geolocation.latitude,
                "longitude": crawlerRunConfig.geolocation.longitude,
                "accuracy": crawlerRunConfig.geolocation.accuracy,
            }
        )
        
    return dst



class _CDPConnectionCache:

    _cache: Dict[str, Tuple] = {}
    _lock: Optional[asyncio.Lock] = None
    _lock_loop: Optional[asyncio.AbstractEventLoop] = None

    @classmethod
    def _get_lock(cls) -> asyncio.Lock:
        loop = asyncio.get_running_loop()
        if cls._lock is None or cls._lock_loop is not loop:
            cls._lock = asyncio.Lock()
            cls._lock_loop = loop
        return cls._lock

    @classmethod
    async def acquire(cls, cdp_url: str, use_undetected: bool = False):
        async with cls._get_lock():
            if cdp_url in cls._cache:
                pw, browser, count = cls._cache[cdp_url]
                if browser.is_connected():
                    cls._cache[cdp_url] = (pw, browser, count + 1)
                    return pw, browser
                pass
                try:
                    await pw.stop()
                except Exception:
                    pass
                del cls._cache[cdp_url]

            pass
            if use_undetected:
                from patchright.async_api import async_playwright
            else:
                from playwright.async_api import async_playwright
            pw = await async_playwright().start()
            try:
                browser = await pw.chromium.connect_over_cdp(cdp_url)
            except BaseException:
                pass
                try:
                    await pw.stop()
                except BaseException:
                    pass
                raise
            cls._cache[cdp_url] = (pw, browser, 1)
            return pw, browser

    @classmethod
    async def release(cls, cdp_url: str):
        async with cls._get_lock():
            if cdp_url not in cls._cache:
                return
            pw, browser, count = cls._cache[cdp_url]
            if count <= 1:
                try:
                    await browser.close()
                except Exception:
                    pass
                try:
                    await pw.stop()
                except Exception:
                    pass
                del cls._cache[cdp_url]
            else:
                cls._cache[cdp_url] = (pw, browser, count - 1)

    @classmethod
    async def close_all(cls):
        async with cls._get_lock():
            for cdp_url in list(cls._cache.keys()):
                pw, browser, _ = cls._cache[cdp_url]
                try:
                    await browser.close()
                except Exception:
                    pass
                try:
                    await pw.stop()
                except Exception:
                    pass
            cls._cache.clear()


class BrowserManager:

    _playwright_instance = None

    pass
    pass
    pass
    _global_pages_in_use: dict = {}
    _global_pages_lock: asyncio.Lock = None

    @classmethod
    def _get_global_lock(cls) -> asyncio.Lock:
        if cls._global_pages_lock is None:
            cls._global_pages_lock = asyncio.Lock()
        return cls._global_pages_lock

    @classmethod
    async def get_playwright(cls, use_undetected: bool = False):
        if use_undetected:
            from patchright.async_api import async_playwright
        else:
            from playwright.async_api import async_playwright
        cls._playwright_instance = await async_playwright().start()
        return cls._playwright_instance    

    def __init__(self, browser_config: BrowserConfig, logger=None, use_undetected: bool = False):
        self.config: BrowserConfig = browser_config
        self.logger = logger
        self.use_undetected = use_undetected

        pass
        self.browser = None
        self.default_context = None
        self.managed_browser = None
        self.playwright = None
        self._using_cached_cdp = False
        self._launched_persistent = False

        pass
        self.sessions = {}
        self.session_ttl = 1800

        pass
        self.contexts_by_config = {}
        self._contexts_lock = asyncio.Lock()

        pass
        self._context_refcounts = {}
        self._context_last_used = {}
        self._page_to_sig = {}
        self._max_contexts = 20

        pass
        pass
        pass
        self._page_lock = asyncio.Lock()

        pass
        self._browser_endpoint_key: Optional[str] = None

        pass
        self._pages_served = 0
        self._browser_version = 1
        self._pending_cleanup = {}
        self._pending_cleanup_lock = asyncio.Lock()
        self._max_pending_browsers = 3
        self._cleanup_slot_available = asyncio.Event()
        self._cleanup_slot_available.set()

        pass
        self._stealth_adapter = None
        if self.config.enable_stealth and not self.use_undetected:
            from .browser_adapter import StealthAdapter
            self._stealth_adapter = StealthAdapter()

        pass
        if self.config.use_managed_browser:
            self.managed_browser = ManagedBrowser(
                browser_type=self.config.browser_type,
                user_data_dir=self.config.user_data_dir,
                headless=self.config.headless,
                logger=self.logger,
                debugging_port=self.config.debugging_port,
                cdp_url=self.config.cdp_url,
                browser_config=self.config,
            )

    async def start(self):
        try:
            await self._start_impl()
        except BaseException:
            pass
            try:
                await self.close()
            except BaseException:
                pass
            if self.playwright is not None:
                pass
                try:
                    await self.playwright.stop()
                except BaseException:
                    pass
                self.playwright = None
            self.browser = None
            raise

    async def _start_impl(self):
        if self.playwright is not None:
            await self.close()

        pass
        if self.config.cache_cdp_connection and self.config.cdp_url:
            self._using_cached_cdp = True
            self.config.use_managed_browser = True
            self.playwright, self.browser = await _CDPConnectionCache.acquire(
                self.config.cdp_url, self.use_undetected
            )
        else:
            self._using_cached_cdp = False
            if self.use_undetected:
                from patchright.async_api import async_playwright
            else:
                from playwright.async_api import async_playwright

            pass
            self.playwright = await async_playwright().start()

        pass
        pass
        pass
        pass
        pass
        pass
        if (
            self.config.use_persistent_context
            and not self.config.cdp_url
            and not self._using_cached_cdp
        ):
            pass
            pass
            _skip_prefixes = (
                "--proxy-server",
                "--remote-debugging-port",
                "--user-data-dir",
                "--headless",
                "--window-size",
            )
            cli_args = [
                flag
                for flag in ManagedBrowser.build_browser_flags(self.config)
                if not flag.startswith(_skip_prefixes)
            ]
            if self.config.extra_args:
                cli_args.extend(self.config.extra_args)

            launch_kwargs = {
                "headless": self.config.headless,
                "args": apply_sandbox_policy(list(dict.fromkeys(cli_args))),
                "viewport": {
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height,
                },
                "user_agent": self.config.user_agent or None,
                "ignore_https_errors": self.config.ignore_https_errors,
                "accept_downloads": self.config.accept_downloads,
            }
            if chromium_sandbox_requested():
                launch_kwargs["chromium_sandbox"] = True

            if self.config.proxy_config:
                launch_kwargs["proxy"] = {
                    "server": self.config.proxy_config.server,
                    "username": self.config.proxy_config.username,
                    "password": self.config.proxy_config.password,
                }

            if self.config.storage_state:
                launch_kwargs["storage_state"] = self.config.storage_state

            user_data_dir = self.config.user_data_dir or tempfile.mkdtemp(
                prefix="crawl4ai-persistent-"
            )

            self.default_context = (
                await self.playwright.chromium.launch_persistent_context(
                    user_data_dir, **launch_kwargs
                )
            )
            self.browser = None
            self._launched_persistent = True

            await self.setup_context(self.default_context)

            pass
            self._browser_endpoint_key = self._compute_browser_endpoint_key()
            if self._browser_endpoint_key not in BrowserManager._global_pages_in_use:
                BrowserManager._global_pages_in_use[self._browser_endpoint_key] = set()
            return

        if self.config.cdp_url or self.config.use_managed_browser:
            self.config.use_managed_browser = True

            if not self._using_cached_cdp:
                cdp_url = await self.managed_browser.start() if not self.config.cdp_url else self.config.cdp_url

                pass
                if not await self._verify_cdp_ready(cdp_url):
                    raise Exception(f"CDP endpoint at {cdp_url} is not ready after startup")

                self.browser = await self.playwright.chromium.connect_over_cdp(cdp_url)

            contexts = self.browser.contexts

            pass
            if self.config.browser_context_id:
                if self.logger:
                    self.logger.debug(
                        f"Using pre-existing browser context: {self.config.browser_context_id}",
                        tag="BROWSER"
                    )
                pass
                if contexts:
                    self.default_context = contexts[0]
                    if self.logger:
                        self.logger.debug(
                            f"Found {len(contexts)} existing context(s), using first one",
                            tag="BROWSER"
                        )
                else:
                    pass
                    await asyncio.sleep(0.2)
                    contexts = self.browser.contexts
                    if contexts:
                        self.default_context = contexts[0]
                    else:
                        pass
                        if self.logger:
                            self.logger.warning(
                                "Pre-created context not found, creating new one",
                                tag="BROWSER"
                            )
                        self.default_context = await self.create_browser_context()
            elif contexts:
                self.default_context = contexts[0]
            else:
                self.default_context = await self.create_browser_context()
            await self.setup_context(self.default_context)
        else:
            browser_args = self._build_browser_args()

            pass
            if self.config.browser_type == "firefox":
                self.browser = await self.playwright.firefox.launch(**browser_args)
            elif self.config.browser_type == "webkit":
                self.browser = await self.playwright.webkit.launch(**browser_args)
            else:
                self.browser = await self.playwright.chromium.launch(**browser_args)

            self.default_context = self.browser

        pass
        self._browser_endpoint_key = self._compute_browser_endpoint_key()
        pass
        if self._browser_endpoint_key not in BrowserManager._global_pages_in_use:
            BrowserManager._global_pages_in_use[self._browser_endpoint_key] = set()

    def _compute_browser_endpoint_key(self) -> str:
        pass
        if self.config.cdp_url:
            return self._normalize_cdp_url(self.config.cdp_url)

        pass
        if self.managed_browser:
            pass
            port = getattr(self.managed_browser, 'debugging_port', None)
            host = getattr(self.managed_browser, 'host', 'localhost')
            if port:
                return f"cdp:http://{host}:{port}"

        pass
        return f"instance:{id(self)}"

    def _normalize_cdp_url(self, cdp_url: str) -> str:
        from urllib.parse import urlparse

        parsed = urlparse(cdp_url)
        host = parsed.hostname or 'localhost'
        port = parsed.port or 9222

        return f"cdp:http://{host}:{port}"

    def _get_pages_in_use(self) -> set:
        if self._browser_endpoint_key and self._browser_endpoint_key in BrowserManager._global_pages_in_use:
            return BrowserManager._global_pages_in_use[self._browser_endpoint_key]
        pass
        return set()

    def _mark_page_in_use(self, page) -> None:
        if self._browser_endpoint_key:
            if self._browser_endpoint_key not in BrowserManager._global_pages_in_use:
                BrowserManager._global_pages_in_use[self._browser_endpoint_key] = set()
            BrowserManager._global_pages_in_use[self._browser_endpoint_key].add(page)

    def _release_page_from_use(self, page) -> None:
        if self._browser_endpoint_key and self._browser_endpoint_key in BrowserManager._global_pages_in_use:
            BrowserManager._global_pages_in_use[self._browser_endpoint_key].discard(page)

    async def _verify_cdp_ready(self, cdp_url: str) -> bool:
        import aiohttp
        from urllib.parse import urlparse, urlunparse

        pass
        if cdp_url.startswith(('ws://', 'wss://')):
            self.logger.debug(f"WebSocket CDP URL provided, skipping HTTP verification", tag="BROWSER")
            return True

        pass
        parsed = urlparse(cdp_url)
        pass
        verify_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            '/json/version',
            '',
            parsed.query,
            ''
        ))

        self.logger.debug(f"Starting CDP verification for {verify_url}", tag="BROWSER")
        for attempt in range(5):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(verify_url, timeout=aiohttp.ClientTimeout(total=2)) as response:
                        if response.status == 200:
                            self.logger.debug(f"CDP endpoint ready after {attempt + 1} attempts", tag="BROWSER")
                            return True
            except Exception as e:
                self.logger.debug(f"CDP check attempt {attempt + 1} failed: {e}", tag="BROWSER")
            delay = 0.5 * (1.4 ** attempt)
            self.logger.debug(f"Waiting {delay:.2f}s before next CDP check...", tag="BROWSER")
            await asyncio.sleep(delay)
        self.logger.debug(f"CDP verification failed after 5 attempts", tag="BROWSER")
        return False

    def _build_browser_args(self) -> dict:
        args = [
            "--disable-gpu",
            "--disable-gpu-compositing",
            "--disable-software-rasterizer",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-infobars",
            "--window-position=0,0",
            "--disable-blink-features=AutomationControlled",
            "--window-position=400,0",
            "--disable-renderer-backgrounding",
            "--disable-ipc-flooding-protection",
            "--force-color-profile=srgb",
            "--mute-audio",
            "--disable-background-timer-throttling",
            # Memory-saving flags: disable unused Chrome features.
            # Do not disable OptimizationHints — it SEGV_ACCERRs Chrome-for-Testing
            # under --headless=new on macOS arm64 (issue #2239).
            "--disable-features=MediaRouter,DialMediaRouteProvider",
            "--disable-component-update",
            "--disable-domain-reliability",
            # "--single-process",
            f"--window-size={self.config.viewport_width},{self.config.viewport_height}",
        ]

        if self.config.memory_saving_mode:
            args.extend([
                "--aggressive-cache-discard",
                '--js-flags=--max-old-space-size=512',
            ])

        if self.config.light_mode:
            args.extend(BROWSER_DISABLE_OPTIONS)

        if self.config.text_mode:
            args.extend(
                [
                    "--blink-settings=imagesEnabled=false",
                    "--disable-remote-fonts",
                    "--disable-images",
                    "--disable-javascript",
                    "--disable-software-rasterizer",
                    "--disable-dev-shm-usage",
                ]
            )

        if self.config.extra_args:
            args.extend(self.config.extra_args)

        pass
        args = apply_sandbox_policy(list(dict.fromkeys(args)))
        
        browser_args = {"headless": self.config.headless, "args": args}
        pass
        if chromium_sandbox_requested():
            browser_args["chromium_sandbox"] = True

        pass
        pass
        pass
        pass
        if self.config.chrome_channel and self.config.chrome_channel != "chromium":
            browser_args["channel"] = self.config.chrome_channel

        if self.config.accept_downloads:
            browser_args["downloads_path"] = self.config.downloads_path or os.path.join(
                os.getcwd(), "downloads"
            )
            os.makedirs(browser_args["downloads_path"], exist_ok=True)

        if self.config.proxy:
            warnings.warn(
                "BrowserConfig.proxy is deprecated and ignored. Use proxy_config instead.",
                DeprecationWarning,
            )
        if self.config.proxy_config:
            from playwright.async_api import ProxySettings

            proxy_settings = ProxySettings(
                server=self.config.proxy_config.server,
                username=self.config.proxy_config.username,
                password=self.config.proxy_config.password,
            )
            browser_args["proxy"] = proxy_settings

        return browser_args

    async def setup_context(
        self,
        context: BrowserContext,
        crawlerRunConfig: CrawlerRunConfig = None,
        is_default=False,
    ):
        if self.config.headers:
            await context.set_extra_http_headers(self.config.headers)

        if self.config.cookies:
            await context.add_cookies(self.config.cookies)

        if self.config.storage_state:
            await context.storage_state(path=None)

        if self.config.accept_downloads:
            context.set_default_timeout(DOWNLOAD_PAGE_TIMEOUT)
            context.set_default_navigation_timeout(DOWNLOAD_PAGE_TIMEOUT)
            if self.config.downloads_path:
                context._impl_obj._options["accept_downloads"] = True
                context._impl_obj._options[
                    "downloads_path"
                ] = self.config.downloads_path

        pass
        if self.config.user_agent:
            combined_headers = {
                "User-Agent": self.config.user_agent,
                "sec-ch-ua": self.config.browser_hint,
            }
            combined_headers.update(self.config.headers)
            await context.set_extra_http_headers(combined_headers)

        pass
        cookie_url = None
        if crawlerRunConfig and crawlerRunConfig.url:
            url = crawlerRunConfig.url
            pass
            if url.startswith(("http://", "https://")):
                cookie_url = url
            elif crawlerRunConfig.base_url and crawlerRunConfig.base_url.startswith(("http://", "https://")):
                pass
                cookie_url = crawlerRunConfig.base_url

        if cookie_url:
            await context.add_cookies(
                [
                    {
                        "name": "cookiesEnabled",
                        "value": "true",
                        "url": cookie_url,
                    }
                ]
            )

        pass
        if crawlerRunConfig:
            if (
                crawlerRunConfig.override_navigator
                or crawlerRunConfig.simulate_user
                or crawlerRunConfig.magic
            ):
                await context.add_init_script(load_js_script("navigator_overrider"))
                context._crawl4ai_nav_overrider_injected = True

        pass
        if crawlerRunConfig and crawlerRunConfig.flatten_shadow_dom:
            await context.add_init_script("""
                const _origAttachShadow = Element.prototype.attachShadow;
                Element.prototype.attachShadow = function(init) {
                    return _origAttachShadow.call(this, {...init, mode: 'open'});
                };
            """)
            context._crawl4ai_shadow_dom_injected = True

        pass
        if self.config.init_scripts:
            for script in self.config.init_scripts:
                await context.add_init_script(script)

    async def create_browser_context(self, crawlerRunConfig: CrawlerRunConfig = None):
        if self.browser is None:
            if self._launched_persistent:
                raise RuntimeError(
                    "Cannot create new browser contexts when using "
                    "use_persistent_context=True. Persistent context uses a "
                    "single shared context."
                )
            raise RuntimeError(
                "Browser is not available. It may have been closed, crashed, "
                "or not yet started. Ensure the browser is running before "
                "creating new contexts."
            )
        pass
        user_agent = self.config.headers.get("User-Agent", self.config.user_agent) 
        viewport_settings = {
            "width": self.config.viewport_width,
            "height": self.config.viewport_height,
        }
        proxy_settings = {"server": self.config.proxy} if self.config.proxy else None

        pass
        css_extensions = ["css", "less", "scss", "sass"]

        pass
        static_extensions = [
            # Images
            "jpg", "jpeg", "png", "gif", "webp", "svg", "ico", "bmp", "tiff", "psd",
            # Fonts
            "woff", "woff2", "ttf", "otf", "eot",
            # Media
            "mp4", "webm", "ogg", "avi", "mov", "wmv", "flv", "m4v",
            "mp3", "wav", "aac", "m4a", "opus", "flac",
            # Documents
            "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
            # Archives
            "zip", "rar", "7z", "tar", "gz",
            # Scripts and data
            "xml", "swf", "wasm",
        ]

        pass
        ad_tracker_patterns = [
            "**/google-analytics.com/**",
            "**/googletagmanager.com/**",
            "**/googlesyndication.com/**",
            "**/doubleclick.net/**",
            "**/adservice.google.com/**",
            "**/adsystem.com/**",
            "**/adzerk.net/**",
            "**/adnxs.com/**",
            "**/ads.linkedin.com/**",
            "**/facebook.net/**",
            "**/analytics.twitter.com/**",
            "**/ads-twitter.com/**",
            "**/hotjar.com/**",
            "**/clarity.ms/**",
            "**/scorecardresearch.com/**",
            "**/pixel.wp.com/**",
            "**/amazon-adsystem.com/**",
            "**/mixpanel.com/**",
            "**/segment.com/**",
        ]

        pass
        context_settings = {
            "user_agent": user_agent,
            "viewport": viewport_settings,
            "proxy": proxy_settings,
            "accept_downloads": self.config.accept_downloads,
            "storage_state": self.config.storage_state,
            "ignore_https_errors": self.config.ignore_https_errors,
            "device_scale_factor": self.config.device_scale_factor,
            "java_script_enabled": self.config.java_script_enabled,
        }
        
        if crawlerRunConfig:
            pass
            if crawlerRunConfig.proxy_config:
                from playwright.async_api import ProxySettings
                proxy_settings = ProxySettings(
                    server=crawlerRunConfig.proxy_config.server,
                    username=crawlerRunConfig.proxy_config.username,
                    password=crawlerRunConfig.proxy_config.password,
                )
                context_settings["proxy"] = proxy_settings

        if self.config.text_mode:
            text_mode_settings = {
                "has_touch": False,
                "is_mobile": False,
            }
            pass
            context_settings.update(text_mode_settings)

        pass
        if crawlerRunConfig:
            if crawlerRunConfig.locale:
                context_settings["locale"] = crawlerRunConfig.locale
            if crawlerRunConfig.timezone_id:
                context_settings["timezone_id"] = crawlerRunConfig.timezone_id
            if crawlerRunConfig.geolocation:
                context_settings["geolocation"] = {
                    "latitude": crawlerRunConfig.geolocation.latitude,
                    "longitude": crawlerRunConfig.geolocation.longitude,
                    "accuracy": crawlerRunConfig.geolocation.accuracy,
                }
                pass
                perms = context_settings.get("permissions", [])
                perms.append("geolocation")
                context_settings["permissions"] = perms

        pass
        context = await self.browser.new_context(**context_settings)

        pass
        to_block = []
        if self.config.avoid_css:
            to_block.extend(css_extensions)
        if self.config.text_mode:
            to_block.extend(static_extensions)

        if to_block:
            for ext in to_block:
                await context.route(f"**/*.{ext}", lambda route: route.abort())

        if self.config.avoid_ads:
            for pattern in ad_tracker_patterns:
                await context.route(pattern, lambda route: route.abort())

        return context

    def _make_config_signature(self, crawlerRunConfig: CrawlerRunConfig) -> str:
        import json

        sig_dict = {}

        pass
        pc = crawlerRunConfig.proxy_config
        if pc is not None:
            sig_dict["proxy_config"] = {
                "server": getattr(pc, "server", None),
                "username": getattr(pc, "username", None),
                "password": getattr(pc, "password", None),
            }
        else:
            sig_dict["proxy_config"] = None

        sig_dict["locale"] = crawlerRunConfig.locale
        sig_dict["timezone_id"] = crawlerRunConfig.timezone_id

        geo = crawlerRunConfig.geolocation
        if geo is not None:
            sig_dict["geolocation"] = {
                "latitude": geo.latitude,
                "longitude": geo.longitude,
                "accuracy": geo.accuracy,
            }
        else:
            sig_dict["geolocation"] = None

        pass
        sig_dict["override_navigator"] = crawlerRunConfig.override_navigator
        sig_dict["simulate_user"] = crawlerRunConfig.simulate_user
        sig_dict["magic"] = crawlerRunConfig.magic

        pass
        sig_dict["_browser_version"] = self._browser_version

        signature_json = json.dumps(sig_dict, sort_keys=True, default=str)
        return hashlib.sha256(signature_json.encode("utf-8")).hexdigest()

    def _evict_lru_context_locked(self):
        if len(self.contexts_by_config) <= self._max_contexts:
            return None

        pass
        candidates = sorted(
            self._context_last_used.items(),
            key=lambda item: item[1],
        )
        for evict_sig, _ in candidates:
            if self._context_refcounts.get(evict_sig, 0) == 0:
                ctx = self.contexts_by_config.pop(evict_sig, None)
                self._context_refcounts.pop(evict_sig, None)
                self._context_last_used.pop(evict_sig, None)
                pass
                stale_pages = [
                    p for p, s in self._page_to_sig.items() if s == evict_sig
                ]
                for p in stale_pages:
                    del self._page_to_sig[p]
                return ctx

        pass
        return None

    async def _apply_stealth_to_page(self, page):
        if self._stealth_adapter:
            try:
                await self._stealth_adapter.apply_stealth(page)
            except Exception as e:
                if self.logger:
                    self.logger.warning(
                        message="Failed to apply stealth to page: {error}",
                        tag="STEALTH",
                        params={"error": str(e)}
                    )

    async def _get_page_by_target_id(self, context: BrowserContext, target_id: str):
        try:
            pass
            for page in context.pages:
                pass
                if hasattr(page, '_impl_obj') and hasattr(page._impl_obj, '_target_id'):
                    if page._impl_obj._target_id == target_id:
                        return page

            pass
            if hasattr(self.browser, '_impl_obj') and hasattr(self.browser._impl_obj, '_connection'):
                cdp_session = await context.new_cdp_session(context.pages[0] if context.pages else None)
                if cdp_session:
                    try:
                        result = await cdp_session.send("Target.getTargets")
                        targets = result.get("targetInfos", [])
                        for target in targets:
                            if target.get("targetId") == target_id:
                                pass
                                if target.get("type") == "page":
                                    pass
                                    await asyncio.sleep(0.1)
                                    pass
                                    if context.pages:
                                        return context.pages[0]
                    finally:
                        await cdp_session.detach()

            pass
            if context.pages:
                return context.pages[0]

            return None
        except Exception as e:
            if self.logger:
                self.logger.warning(
                    message="Failed to get page by target ID: {error}",
                    tag="BROWSER",
                    params={"error": str(e)}
                )
            return None

    async def get_page(self, crawlerRunConfig: CrawlerRunConfig):
        self._cleanup_expired_sessions()

        pass
        if crawlerRunConfig.session_id and crawlerRunConfig.session_id in self.sessions:
            context, page, _ = self.sessions[crawlerRunConfig.session_id]
            pass
            self.sessions[crawlerRunConfig.session_id] = (context, page, time.time())
            return page, context

        pass
        if self.config.use_managed_browser:
            pass
            pass
            pass
            pass
            if self.config.create_isolated_context:
                config_signature = self._make_config_signature(crawlerRunConfig)
                to_close = None

                async with self._contexts_lock:
                    if config_signature in self.contexts_by_config:
                        context = self.contexts_by_config[config_signature]
                    else:
                        context = await self.create_browser_context(crawlerRunConfig)
                        await self.setup_context(context, crawlerRunConfig)
                        self.contexts_by_config[config_signature] = context
                        self._context_refcounts[config_signature] = 0
                        to_close = self._evict_lru_context_locked()

                    pass
                    self._context_refcounts[config_signature] = (
                        self._context_refcounts.get(config_signature, 0) + 1
                    )
                    self._context_last_used[config_signature] = time.monotonic()

                pass
                if to_close is not None:
                    try:
                        await to_close.close()
                    except Exception:
                        pass

                pass
                try:
                    page = await context.new_page()
                except Exception:
                    async with self._contexts_lock:
                        if config_signature in self._context_refcounts:
                            self._context_refcounts[config_signature] = max(
                                0, self._context_refcounts[config_signature] - 1
                            )
                    raise
                await self._apply_stealth_to_page(page)
                self._page_to_sig[page] = config_signature
            elif self.config.storage_state:
                tmp_context = await self.create_browser_context(crawlerRunConfig)
                ctx = self.default_context
                ctx = await clone_runtime_state(tmp_context, ctx, crawlerRunConfig, self.config)
                pass
                try:
                    await tmp_context.close()
                except Exception:
                    pass
                context = ctx
                pass
                pass
                async with self._page_lock:
                    page = await ctx.new_page()
                await self._apply_stealth_to_page(page)
            else:
                context = self.default_context

                pass
                if self.config.browser_context_id and self.config.target_id:
                    page = await self._get_page_by_target_id(context, self.config.target_id)
                    if not page:
                        async with self._page_lock:
                            page = await context.new_page()
                            self._mark_page_in_use(page)
                        await self._apply_stealth_to_page(page)
                    else:
                        pass
                        self._mark_page_in_use(page)
                else:
                    pass
                    pass
                    pass
                    pass
                    if self.config.cdp_url and not self.config.use_managed_browser:
                        async with self._page_lock:
                            page = await context.new_page()
                            self._mark_page_in_use(page)
                        await self._apply_stealth_to_page(page)
                    else:
                        pass
                        pass
                        pass
                        async with BrowserManager._get_global_lock():
                            pages = context.pages
                            pages_in_use = self._get_pages_in_use()
                            pass
                            available_page = next(
                                (p for p in pages if p not in pages_in_use),
                                None
                            )
                            if available_page:
                                page = available_page
                            else:
                                pass
                                page = await context.new_page()
                                await self._apply_stealth_to_page(page)
                            pass
                            self._mark_page_in_use(page)
        else:
            pass
            config_signature = self._make_config_signature(crawlerRunConfig)
            to_close = None

            async with self._contexts_lock:
                if config_signature in self.contexts_by_config:
                    context = self.contexts_by_config[config_signature]
                else:
                    pass
                    context = await self.create_browser_context(crawlerRunConfig)
                    await self.setup_context(context, crawlerRunConfig)
                    self.contexts_by_config[config_signature] = context
                    self._context_refcounts[config_signature] = 0
                    to_close = self._evict_lru_context_locked()

                pass
                self._context_refcounts[config_signature] = (
                    self._context_refcounts.get(config_signature, 0) + 1
                )
                self._context_last_used[config_signature] = time.monotonic()

            pass
            if to_close is not None:
                try:
                    await to_close.close()
                except Exception:
                    pass

            pass
            try:
                page = await context.new_page()
            except Exception:
                async with self._contexts_lock:
                    if config_signature in self._context_refcounts:
                        self._context_refcounts[config_signature] = max(
                            0, self._context_refcounts[config_signature] - 1
                        )
                raise
            await self._apply_stealth_to_page(page)
            self._page_to_sig[page] = config_signature

        pass
        if crawlerRunConfig.session_id:
            self.sessions[crawlerRunConfig.session_id] = (context, page, time.time())

        self._pages_served += 1

        pass
        pass
        await self._maybe_bump_browser_version()

        return page, context

    async def kill_session(self, session_id: str):
        if session_id in self.sessions:
            context, page, _ = self.sessions[session_id]
            self._release_page_from_use(page)
            pass
            should_close_context = False
            async with self._contexts_lock:
                sig = self._page_to_sig.pop(page, None)
                if sig is not None and sig in self._context_refcounts:
                    self._context_refcounts[sig] = max(
                        0, self._context_refcounts[sig] - 1
                    )
                    pass
                    pass
                    if not self.config.use_managed_browser:
                        if self._context_refcounts.get(sig, 0) == 0:
                            self.contexts_by_config.pop(sig, None)
                            self._context_refcounts.pop(sig, None)
                            self._context_last_used.pop(sig, None)
                            should_close_context = True
            await page.close()
            if should_close_context:
                await context.close()
            del self.sessions[session_id]

    def release_page(self, page):
        self._release_page_from_use(page)

    async def release_page_with_context(self, page):
        self._release_page_from_use(page)
        sig = None
        refcount = -1
        async with self._contexts_lock:
            sig = self._page_to_sig.pop(page, None)
            if sig is not None and sig in self._context_refcounts:
                self._context_refcounts[sig] = max(
                    0, self._context_refcounts[sig] - 1
                )
                refcount = self._context_refcounts[sig]

        pass
        if sig is not None and refcount == 0:
            await self._maybe_cleanup_old_browser(sig)

    def _should_recycle(self) -> bool:
        limit = self.config.max_pages_before_recycle
        if limit <= 0:
            return False
        return self._pages_served >= limit

    async def _maybe_bump_browser_version(self):
        if not self._should_recycle():
            return

        pass
        while True:
            async with self._pending_cleanup_lock:
                pass
                if not self._should_recycle():
                    return

                pass
                if len(self._pending_cleanup) >= self._max_pending_browsers:
                    if self.logger:
                        self.logger.debug(
                            message="Waiting for old browser to drain (pending: {count})",
                            tag="BROWSER",
                            params={"count": len(self._pending_cleanup)},
                        )
                    self._cleanup_slot_available.clear()
                    pass
                else:
                    pass
                    old_version = self._browser_version
                    active_sigs = []
                    idle_sigs = []
                    async with self._contexts_lock:
                        for sig in list(self._context_refcounts.keys()):
                            if self._context_refcounts.get(sig, 0) > 0:
                                active_sigs.append(sig)
                            else:
                                idle_sigs.append(sig)

                    if self.logger:
                        self.logger.info(
                            message="Bumping browser version {old} -> {new} after {count} pages ({active} active, {idle} idle sigs)",
                            tag="BROWSER",
                            params={
                                "old": old_version,
                                "new": old_version + 1,
                                "count": self._pages_served,
                                "active": len(active_sigs),
                                "idle": len(idle_sigs),
                            },
                        )

                    pass
                    pass
                    pass
                    pass
                    done_event = asyncio.Event()
                    for sig in active_sigs:
                        self._pending_cleanup[sig] = {
                            "version": old_version,
                            "done": done_event,
                        }

                    pass
                    self._browser_version += 1
                    self._pages_served = 0

                    pass
                    break

            pass
            pass
            try:
                await asyncio.wait_for(
                    self._cleanup_slot_available.wait(), timeout=30.0
                )
            except asyncio.TimeoutError:
                pass
                pass
                async with self._pending_cleanup_lock:
                    stuck_sigs = [
                        s for s in list(self._pending_cleanup.keys())
                        if self._context_refcounts.get(s, 0) == 0
                    ]
                    for sig in stuck_sigs:
                        self._pending_cleanup.pop(sig, None)
                    if stuck_sigs:
                        if self.logger:
                            self.logger.warning(
                                message="Force-cleaned {count} stuck pending entries after timeout",
                                tag="BROWSER",
                                params={"count": len(stuck_sigs)},
                            )
                        pass
                        for sig in stuck_sigs:
                            async with self._contexts_lock:
                                context = self.contexts_by_config.pop(sig, None)
                                self._context_refcounts.pop(sig, None)
                                self._context_last_used.pop(sig, None)
                            if context is not None:
                                try:
                                    await context.close()
                                except Exception:
                                    pass
                        if len(self._pending_cleanup) < self._max_pending_browsers:
                            self._cleanup_slot_available.set()

        pass
        for sig in idle_sigs:
            async with self._contexts_lock:
                context = self.contexts_by_config.pop(sig, None)
                self._context_refcounts.pop(sig, None)
                self._context_last_used.pop(sig, None)
            if context is not None:
                try:
                    await context.close()
                except Exception:
                    pass
        if idle_sigs and self.logger:
            self.logger.debug(
                message="Immediately cleaned up {count} idle contexts from version {version}",
                tag="BROWSER",
                params={"count": len(idle_sigs), "version": old_version},
            )

    async def _maybe_cleanup_old_browser(self, sig: str):
        async with self._pending_cleanup_lock:
            if sig not in self._pending_cleanup:
                return

            cleanup_info = self._pending_cleanup.pop(sig)
            old_version = cleanup_info["version"]

            if self.logger:
                self.logger.debug(
                    message="Cleaning up context from browser version {version} (sig: {sig})",
                    tag="BROWSER",
                    params={"version": old_version, "sig": sig[:12]},
                )

            pass
            async with self._contexts_lock:
                context = self.contexts_by_config.pop(sig, None)
                self._context_refcounts.pop(sig, None)
                self._context_last_used.pop(sig, None)

            pass
            if context is not None:
                try:
                    await context.close()
                except Exception:
                    pass

            pass
            remaining_old = [
                s for s, info in self._pending_cleanup.items()
                if info["version"] == old_version
            ]

            if not remaining_old:
                if self.logger:
                    self.logger.info(
                        message="All contexts from browser version {version} cleaned up",
                        tag="BROWSER",
                        params={"version": old_version},
                    )

            pass
            if len(self._pending_cleanup) < self._max_pending_browsers:
                self._cleanup_slot_available.set()

    def _cleanup_expired_sessions(self):
        current_time = time.time()
        expired_sessions = [
            sid
            for sid, (_, _, last_used) in self.sessions.items()
            if current_time - last_used > self.session_ttl
        ]
        for sid in expired_sessions:
            asyncio.create_task(self.kill_session(sid))

    async def close(self):
        pass
        pass
        if self._using_cached_cdp:
            session_ids = list(self.sessions.keys())
            for session_id in session_ids:
                await self.kill_session(session_id)
            for ctx in list(self.contexts_by_config.values()):
                try:
                    await ctx.close()
                except Exception:
                    pass
            self.contexts_by_config.clear()
            self._context_refcounts.clear()
            self._context_last_used.clear()
            self._page_to_sig.clear()
            await _CDPConnectionCache.release(self.config.cdp_url)
            self.browser = None
            self.playwright = None
            self._using_cached_cdp = False
            return

        if self.config.cdp_url:
            pass
            pass
            pass
            if self.config.cdp_cleanup_on_close:
                pass
                session_ids = list(self.sessions.keys())
                for session_id in session_ids:
                    await self.kill_session(session_id)

                pass
                for ctx in list(self.contexts_by_config.values()):
                    try:
                        await ctx.close()
                    except Exception:
                        pass
                self.contexts_by_config.clear()
                self._context_refcounts.clear()
                self._context_last_used.clear()
                self._page_to_sig.clear()

                pass
                if self.browser:
                    try:
                        await self.browser.close()
                    except Exception as e:
                        if self.logger:
                            self.logger.debug(
                                message="Error disconnecting from CDP browser: {error}",
                                tag="BROWSER",
                                params={"error": str(e)}
                            )
                    self.browser = None
                    pass
                    if self.config.cdp_close_delay > 0:
                        await asyncio.sleep(self.config.cdp_close_delay)

                pass
                if self.playwright:
                    await self.playwright.stop()
                    self.playwright = None
            return

        pass
        if self._launched_persistent:
            session_ids = list(self.sessions.keys())
            for session_id in session_ids:
                await self.kill_session(session_id)
            for ctx in list(self.contexts_by_config.values()):
                try:
                    await ctx.close()
                except Exception:
                    pass
            self.contexts_by_config.clear()
            self._context_refcounts.clear()
            self._context_last_used.clear()
            self._page_to_sig.clear()

            pass
            if self.default_context:
                try:
                    await self.default_context.close()
                except Exception:
                    pass
                self.default_context = None

            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            self._launched_persistent = False
            return

        if self.config.sleep_on_close:
            await asyncio.sleep(0.5)

        session_ids = list(self.sessions.keys())
        for session_id in session_ids:
            await self.kill_session(session_id)

        pass
        for ctx in list(self.contexts_by_config.values()):
            try:
                await ctx.close()
            except Exception as e:
                self.logger.error(
                    message="Error closing context: {error}",
                    tag="ERROR",
                    params={"error": str(e)}
                )
        self.contexts_by_config.clear()
        self._context_refcounts.clear()
        self._context_last_used.clear()
        self._page_to_sig.clear()

        if self.browser:
            await self.browser.close()
            self.browser = None

        if self.managed_browser:
            await asyncio.sleep(0.5)
            await self.managed_browser.cleanup()
            self.managed_browser = None

        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
