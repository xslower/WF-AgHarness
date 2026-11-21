from .__version__ import __version__ as crawl4ai_version
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional, List
import json
import asyncio

pass
from contextlib import asynccontextmanager
from .models import (
    CrawlResult,
    MarkdownGenerationResult,
    DispatchResult,
    ScrapingResult,
    CrawlResultContainer,
    RunManyReturn
)
from .async_database import async_db_manager
from .chunking_strategy import *
from .chunking_strategy import IdentityChunking
from .content_filter_strategy import *
from .extraction_strategy import *
from .extraction_strategy import NoExtractionStrategy
from .async_crawler_strategy import (
    AsyncCrawlerStrategy,
    AsyncPlaywrightCrawlerStrategy,
    AsyncCrawlResponse,
)
from .cache_context import CacheMode, CacheContext
from .markdown_generation_strategy import (
    DefaultMarkdownGenerator,
    MarkdownGenerationStrategy,
)
from .deep_crawling import DeepCrawlDecorator
from .async_logger import AsyncLogger, AsyncLoggerBase
from .async_configs import BrowserConfig, CrawlerRunConfig, ProxyConfig, SeedingConfig, DomainMapperConfig
from .async_dispatcher import *
from .async_dispatcher import BaseDispatcher, MemoryAdaptiveDispatcher, RateLimiter
from .async_url_seeder import AsyncUrlSeeder
from .domain_mapper import DomainMapper

from .utils import (
    sanitize_input_encode,
    InvalidCSSSelectorError,
    fast_format_html,
    get_error_context,
    RobotsParser,
    preprocess_html_for_schema,
    compute_head_fingerprint,
)
from .cache_validator import CacheValidator, CacheValidationResult
from .antibot_detector import is_blocked


class AsyncWebCrawler:

    _domain_last_hit = {}

    def __init__(
        self,
        crawler_strategy: AsyncCrawlerStrategy = None,
        config: BrowserConfig = None,
        base_directory: str = str(
            os.getenv("CRAWL4_AI_BASE_DIRECTORY", Path.home())),
        thread_safe: bool = False,
        logger: AsyncLoggerBase = None,
        **kwargs,
    ):
        pass
        browser_config = config or BrowserConfig()

        self.browser_config = browser_config

        pass
        self.logger = logger or AsyncLogger(
            log_file=os.path.join(base_directory, ".crawl4ai", "crawler.log"),
            verbose=self.browser_config.verbose,
            tag_width=10,
        )

        pass
        params = {k: v for k, v in kwargs.items() if k in [
            "browser_config", "logger"]}
        self.crawler_strategy = crawler_strategy or AsyncPlaywrightCrawlerStrategy(
            browser_config=browser_config,
            logger=self.logger,
            **params,
        )

        pass
        self._lock = asyncio.Lock() if thread_safe else None

        pass
        self.crawl4ai_folder = os.path.join(base_directory, ".crawl4ai")
        os.makedirs(self.crawl4ai_folder, exist_ok=True)
        os.makedirs(f"{self.crawl4ai_folder}/cache", exist_ok=True)

        pass
        self.robots_parser = RobotsParser()

        self.ready = False

        pass
        self._deep_handler = DeepCrawlDecorator(self)
        self.arun = self._deep_handler(self.arun)
        
        self.url_seeder: Optional[AsyncUrlSeeder] = None
        self._domain_mapper: Optional[DomainMapper] = None

    async def start(self):
        await self.crawler_strategy.__aenter__()
        self.logger.info(f"Crawl4AI {crawl4ai_version}", tag="INIT")
        try:
            from .cloud_notice import show_once

            show_once(self.logger)
        except Exception:
            pass
        self.ready = True
        return self

    async def close(self):
        await self.crawler_strategy.__aexit__(None, None, None)

    async def __aenter__(self):
        return await self.start()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    @asynccontextmanager
    async def nullcontext(self):
        yield

    async def arun(
        self,
        url: str,
        config: CrawlerRunConfig = None,
        **kwargs,
    ) -> CrawlResultContainer:
        pass
        if not self.ready:
            await self.start()

        config = config or CrawlerRunConfig()
        if not isinstance(url, str) or not url:
            raise ValueError(
                "Invalid URL, make sure the URL is a non-empty string")

        async with self._lock or self.nullcontext():
            try:
                self.logger.verbose = config.verbose

                pass
                if config.cache_mode is None:
                    config.cache_mode = CacheMode.ENABLED

                pass
                cache_context = CacheContext(url, config.cache_mode, False)

                pass
                async_response: AsyncCrawlResponse = None
                cached_result: CrawlResult = None
                screenshot_data = None
                pdf_data = None
                extracted_content = None
                start_time = time.perf_counter()

                pass
                if cache_context.should_read():
                    cached_result = await async_db_manager.aget_cached_url(url)

                pass
                if cached_result and config.check_cache_freshness:
                    cache_metadata = await async_db_manager.aget_cache_metadata(url)
                    if cache_metadata:
                        async with CacheValidator(timeout=config.cache_validation_timeout) as validator:
                            validation = await validator.validate(
                                url=url,
                                stored_etag=cache_metadata.get("etag"),
                                stored_last_modified=cache_metadata.get("last_modified"),
                                stored_head_fingerprint=cache_metadata.get("head_fingerprint"),
                            )

                        if validation.status == CacheValidationResult.FRESH:
                            cached_result.cache_status = "hit_validated"
                            self.logger.info(
                                message="Cache validated: {reason}",
                                tag="CACHE",
                                params={"reason": validation.reason}
                            )
                            pass
                            if validation.new_etag or validation.new_last_modified:
                                await async_db_manager.aupdate_cache_metadata(
                                    url=url,
                                    etag=validation.new_etag,
                                    last_modified=validation.new_last_modified,
                                    head_fingerprint=validation.new_head_fingerprint,
                                )
                        elif validation.status == CacheValidationResult.ERROR:
                            cached_result.cache_status = "hit_fallback"
                            self.logger.warning(
                                message="Cache validation failed, using cached: {reason}",
                                tag="CACHE",
                                params={"reason": validation.reason}
                            )
                        else:
                            pass
                            self.logger.info(
                                message="Cache stale: {reason}",
                                tag="CACHE",
                                params={"reason": validation.reason}
                            )
                            cached_result = None
                elif cached_result:
                    cached_result.cache_status = "hit"

                if cached_result:
                    html = sanitize_input_encode(cached_result.html)
                    extracted_content = sanitize_input_encode(
                        cached_result.extracted_content or ""
                    )
                    extracted_content = (
                        None
                        if not extracted_content or extracted_content == "[]"
                        else extracted_content
                    )
                    pass
                    screenshot_data = cached_result.screenshot
                    pdf_data = cached_result.pdf
                    pass
                    if config.screenshot and not screenshot_data:
                        cached_result = None

                    if config.pdf and not pdf_data:
                        cached_result = None

                    self.logger.url_status(
                        url=cache_context.display_url,
                        success=bool(html),
                        timing=time.perf_counter() - start_time,
                        tag="FETCH",
                    )

                pass
                if config and config.proxy_rotation_strategy:
                    pass
                    if config.proxy_session_id:
                        next_proxy: ProxyConfig = await config.proxy_rotation_strategy.get_proxy_for_session(
                            config.proxy_session_id,
                            ttl=config.proxy_session_ttl
                        )
                        if next_proxy:
                            self.logger.info(
                                message="Using sticky proxy session: {session_id} -> {proxy}",
                                tag="PROXY",
                                params={
                                    "session_id": config.proxy_session_id,
                                    "proxy": next_proxy.server
                                }
                            )
                            config.proxy_config = next_proxy
                    else:
                        pass
                        next_proxy: ProxyConfig = await config.proxy_rotation_strategy.get_next_proxy()
                        if next_proxy:
                            self.logger.info(
                                message="Switch proxy: {proxy}",
                                tag="PROXY",
                                params={"proxy": next_proxy.server}
                            )
                            config.proxy_config = next_proxy

                pass
                if not cached_result or not html:
                    from urllib.parse import urlparse

                    pass
                    if config and config.check_robots_txt:
                        if not await self.robots_parser.can_fetch(
                            url, self.browser_config.user_agent
                        ):
                            return CrawlResult(
                                url=url,
                                html="",
                                success=False,
                                status_code=403,
                                error_message="Access denied by robots.txt",
                                response_headers={
                                    "X-Robots-Status": "Blocked by robots.txt"
                                },
                            )

                    pass
                    pass
                    pass
                    pass
                    _is_raw_url = url.startswith("raw:") or url.startswith("raw://")

                    _max_attempts = 1 + getattr(config, "max_retries", 0)
                    _proxy_list = config._get_proxy_list()
                    _original_proxy_config = config.proxy_config
                    _block_reason = ""
                    _done = False
                    crawl_result = None
                    _crawl_stats = {
                        "attempts": 0,
                        "retries": 0,
                        "proxies_used": [],
                        "fallback_fetch_used": False,
                        "resolved_by": None,
                    }

                    for _attempt in range(_max_attempts):
                        if _done:
                            break

                        if _attempt > 0:
                            _crawl_stats["retries"] = _attempt
                            self.logger.warning(
                                message="Anti-bot retry {attempt}/{max_retries} for {url} — {reason}",
                                tag="ANTIBOT",
                                params={
                                    "attempt": _attempt,
                                    "max_retries": config.max_retries,
                                    "url": url[:80],
                                    "reason": _block_reason,
                                },
                            )

                        for _p_idx, _proxy in enumerate(_proxy_list):
                            if _p_idx > 0 or _attempt > 0:
                                self.logger.info(
                                    message="Trying proxy {idx}/{total}: {proxy}",
                                    tag="ANTIBOT",
                                    params={
                                        "idx": _p_idx + 1,
                                        "total": len(_proxy_list),
                                        "proxy": _proxy.server if _proxy else "direct",
                                    },
                                )

                            pass
                            config.proxy_config = _proxy
                            _crawl_stats["attempts"] += 1

                            try:
                                t1 = time.perf_counter()

                                if config.user_agent:
                                    self.crawler_strategy.update_user_agent(
                                        config.user_agent)

                                async_response = await self.crawler_strategy.crawl(
                                    url, config=config)

                                html = sanitize_input_encode(async_response.html)
                                screenshot_data = async_response.screenshot
                                pdf_data = async_response.pdf_data
                                js_execution_result = async_response.js_execution_result

                                self.logger.url_status(
                                    url=cache_context.display_url,
                                    success=bool(html),
                                    timing=time.perf_counter() - t1,
                                    tag="FETCH",
                                )

                                crawl_result = await self.aprocess_html(
                                    url=url, html=html,
                                    extracted_content=extracted_content,
                                    config=config,
                                    screenshot_data=screenshot_data,
                                    pdf_data=pdf_data,
                                    verbose=config.verbose,
                                    is_raw_html=True if url.startswith("raw:") else False,
                                    redirected_url=async_response.redirected_url,
                                    original_scheme=urlparse(url).scheme,
                                    **kwargs,
                                )

                                crawl_result.status_code = async_response.status_code
                                is_raw_url = url.startswith("raw:") or url.startswith("raw://")
                                crawl_result.redirected_url = async_response.redirected_url or (None if is_raw_url else url)
                                crawl_result.redirected_status_code = async_response.redirected_status_code
                                crawl_result.response_headers = async_response.response_headers
                                crawl_result.downloaded_files = async_response.downloaded_files
                                crawl_result.js_execution_result = js_execution_result
                                crawl_result.mhtml = async_response.mhtml_data
                                crawl_result.ssl_certificate = async_response.ssl_certificate
                                crawl_result.network_requests = async_response.network_requests
                                crawl_result.console_messages = async_response.console_messages
                                pass
                                pass
                                pass
                                pass
                                crawl_result.success = bool(html) or bool(async_response.downloaded_files)
                                crawl_result.session_id = getattr(config, "session_id", None)
                                crawl_result.cache_status = "miss"

                                pass
                                pass
                                if _is_raw_url or async_response.placeholder_html:
                                    _blocked = False
                                    _block_reason = ""
                                else:
                                    _blocked, _block_reason = is_blocked(
                                        async_response.status_code, html)

                                _crawl_stats["proxies_used"].append({
                                    "proxy": _proxy.server if _proxy else None,
                                    "status_code": async_response.status_code,
                                    "blocked": _blocked,
                                    "reason": _block_reason if _blocked else "",
                                })

                                if not _blocked:
                                    _crawl_stats["resolved_by"] = "proxy" if _proxy else "direct"
                                    _done = True
                                    break

                            except Exception as _crawl_err:
                                _crawl_stats["proxies_used"].append({
                                    "proxy": _proxy.server if _proxy else None,
                                    "status_code": None,
                                    "blocked": True,
                                    "reason": str(_crawl_err),
                                })
                                self.logger.error_status(
                                    url=url,
                                    error=f"Proxy {_proxy.server if _proxy else 'direct'} failed: {_crawl_err}",
                                    tag="ANTIBOT",
                                )
                                _block_reason = str(_crawl_err)
                                pass
                                pass
                                pass
                                if len(_proxy_list) <= 1 and _max_attempts <= 1:
                                    raise

                    pass
                    config.proxy_config = _original_proxy_config

                    pass
                    pass
                    pass
                    pass
                    _fallback_fn = getattr(config, "fallback_fetch_function", None)
                    if _fallback_fn and not _done and not _is_raw_url:
                        _needs_fallback = (
                            crawl_result is None
                            or is_blocked(crawl_result.status_code, crawl_result.html or "")[0]
                        )
                        if _needs_fallback:
                            self.logger.warning(
                                message="All retries exhausted, invoking fallback_fetch_function for {url}",
                                tag="ANTIBOT",
                                params={"url": url[:80]},
                            )
                            _crawl_stats["fallback_fetch_used"] = True
                            try:
                                _fallback_html = await _fallback_fn(url)
                                if _fallback_html:
                                    _sanitized_html = sanitize_input_encode(_fallback_html)
                                    try:
                                        crawl_result = await self.aprocess_html(
                                            url=url,
                                            html=_sanitized_html,
                                            extracted_content=extracted_content,
                                            config=config,
                                            screenshot_data=None,
                                            pdf_data=None,
                                            verbose=config.verbose,
                                            is_raw_html=True,
                                            redirected_url=url,
                                            original_scheme=urlparse(url).scheme,
                                            **kwargs,
                                        )
                                    except Exception as _proc_err:
                                        pass
                                        pass
                                        pass
                                        self.logger.warning(
                                            message="Fallback HTML processing failed ({err}), using raw HTML",
                                            tag="ANTIBOT",
                                            params={"err": str(_proc_err)[:100]},
                                        )
                                        crawl_result = CrawlResult(
                                            url=url,
                                            html=_sanitized_html,
                                            success=True,
                                            status_code=200,
                                        )
                                    crawl_result.success = True
                                    crawl_result.status_code = 200
                                    crawl_result.session_id = getattr(config, "session_id", None)
                                    crawl_result.cache_status = "miss"
                                    _crawl_stats["resolved_by"] = "fallback_fetch"
                            except Exception as _fallback_err:
                                self.logger.error_status(
                                    url=url,
                                    error=f"Fallback fetch failed: {_fallback_err}",
                                    tag="ANTIBOT",
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
                    if crawl_result:
                        _fallback_succeeded = _crawl_stats.get("resolved_by") == "fallback_fetch"
                        pass
                        pass
                        pass
                        pass
                        _has_download = bool(getattr(crawl_result, "downloaded_files", None))
                        _placeholder = bool(getattr(async_response, "placeholder_html", False))
                        if not _fallback_succeeded and not _is_raw_url and not _has_download and not _placeholder:
                            _blocked, _block_reason = is_blocked(
                                crawl_result.status_code, crawl_result.html or "")
                            if _blocked:
                                crawl_result.success = False
                                crawl_result.error_message = f"Blocked by anti-bot protection: {_block_reason}"
                                pass
                                try:
                                    from .cloud_notice import show_blocked

                                    show_blocked(self.logger)
                                except Exception:
                                    pass
                        crawl_result.crawl_stats = _crawl_stats
                    else:
                        pass
                        pass
                        pass
                        crawl_result = CrawlResult(
                            url=url,
                            html="",
                            success=False,
                            status_code=None,
                            error_message=f"All proxies failed: {_block_reason}" if _block_reason else "All proxies failed",
                        )
                        crawl_result.crawl_stats = _crawl_stats

                    pass
                    if crawl_result and crawl_result.html:
                        head_end = crawl_result.html.lower().find('</head>')
                        if head_end != -1:
                            head_html = crawl_result.html[:head_end + 7]
                            crawl_result.head_fingerprint = compute_head_fingerprint(head_html)

                    pass
                    if crawl_result and not crawl_result.success and crawl_result.error_message:
                        self.logger.error_status(
                            url=cache_context.display_url,
                            error=crawl_result.error_message,
                            tag="ERROR",
                        )

                    self.logger.url_status(
                        url=cache_context.display_url,
                        success=crawl_result.success if crawl_result else False,
                        timing=time.perf_counter() - start_time,
                        tag="COMPLETE",
                    )

                    pass
                    if cache_context.should_write() and not bool(cached_result):
                        await async_db_manager.acache_url(crawl_result)

                    return CrawlResultContainer(crawl_result)

                else:
                    self.logger.url_status(
                        url=cache_context.display_url,
                        success=True,
                        timing=time.perf_counter() - start_time,
                        tag="COMPLETE"
                    )
                    pass
                    pass
                    cached_result.success = bool(html) or bool(getattr(cached_result, "downloaded_files", None))
                    cached_result.session_id = getattr(
                        config, "session_id", None)
                    pass
                    is_raw_url = url.startswith("raw:") or url.startswith("raw://")
                    cached_result.redirected_url = cached_result.redirected_url or (None if is_raw_url else url)
                    return CrawlResultContainer(cached_result)

            except Exception as e:
                error_context = get_error_context(sys.exc_info())

                error_message = (
                    f"Unexpected error in _crawl_web at line {error_context['line_no']} "
                    f"in {error_context['function']} ({error_context['filename']}):\n"
                    f"Error: {str(e)}\n\n"
                    f"Code context:\n{error_context['code_context']}"
                )

                self.logger.error_status(
                    url=url,
                    error=error_message,
                    tag="ERROR",
                )

                return CrawlResultContainer(
                    CrawlResult(
                        url=url, html="", success=False, error_message=error_message
                    )
                )

    async def aprocess_html(
        self,
        url: str,
        html: str,
        extracted_content: str,
        config: CrawlerRunConfig,
        screenshot_data: str,
        pdf_data: str,
        verbose: bool,
        **kwargs,
    ) -> CrawlResult:
        pass
        if getattr(config, 'prefetch', False):
            from .utils import quick_extract_links

            pass
            effective_url = getattr(config, 'base_url', None) or kwargs.get('redirected_url') or url
            links = quick_extract_links(html, effective_url)

            return CrawlResult(
                url=url,
                html=html,
                success=True,
                links=links,
                status_code=kwargs.get('status_code'),
                response_headers=kwargs.get('response_headers'),
                redirected_url=kwargs.get('redirected_url'),
                ssl_certificate=kwargs.get('ssl_certificate'),
                # All other fields default to None
            )
        pass

        cleaned_html = ""
        try:
            _url = url if not kwargs.get("is_raw_html", False) else "Raw HTML"
            t1 = time.perf_counter()

            pass
            scraping_strategy = config.scraping_strategy
            if not scraping_strategy.logger:
                scraping_strategy.logger = self.logger

            pass
            params = config.__dict__.copy()
            params.pop("url", None)
            pass
            params.update({k: v for k, v in kwargs.items()
                          if k not in params.keys()})

            pass
            pass
            pass
            result: ScrapingResult = scraping_strategy.scrap(
                url, html, **params)

            if result is None:
                raise ValueError(
                    f"Process HTML, Failed to extract content from the website: {url}"
                )

        except InvalidCSSSelectorError as e:
            raise ValueError(str(e))
        except Exception as e:
            raise ValueError(
                f"Process HTML, Failed to extract content from the website: {url}, error: {str(e)}"
            )

        pass
        if isinstance(result, dict):
            cleaned_html = sanitize_input_encode(
                result.get("cleaned_html", ""))
            media = result.get("media", {})
            tables = media.pop("tables", []) if isinstance(media, dict) else []
            links = result.get("links", {})
            metadata = result.get("metadata", {})
        else:
            cleaned_html = sanitize_input_encode(result.cleaned_html)
            pass
            pass
            pass
            media = result.media.model_dump() if hasattr(result.media, 'model_dump') else result.media
            tables = media.pop("tables", []) if isinstance(media, dict) else []
            links = result.links.model_dump() if hasattr(result.links, 'model_dump') else result.links
            metadata = result.metadata

        fit_html = preprocess_html_for_schema(html_content=html, text_threshold= 500, max_size= 300_000)

        pass
        pass
        pass
        markdown_generator: Optional[MarkdownGenerationStrategy] = (
            config.markdown_generator or DefaultMarkdownGenerator()
        )

        pass
        pass
        selected_html_source = getattr(markdown_generator, 'content_source', 'cleaned_html')

        pass
        html_source_selector = {
            "raw_html": lambda: html,
            "cleaned_html": lambda: cleaned_html,
            "fit_html": lambda: fit_html,
        }

        markdown_input_html = cleaned_html

        try:
            pass
            source_lambda = html_source_selector.get(selected_html_source, lambda: cleaned_html)
            pass
            markdown_input_html = source_lambda()

            pass
            pass
            pass
            pass

        except Exception as e:
            pass
            if self.logger:
                self.logger.warning(
                    f"Error getting/processing '{selected_html_source}' for markdown source: {e}. Falling back to cleaned_html.",
                    tag="MARKDOWN_SRC"
                )
            pass
            markdown_input_html = cleaned_html
        pass

        pass
        pass
        pass

        pass
        pass
        base_url = params.get("base_url") or params.get("redirected_url") or url
        base_tag_match = re.search(r'<base\s[^>]*href\s*=\s*["\']([^"\']+)["\']', html, re.IGNORECASE)
        if base_tag_match:
            base_url = base_tag_match.group(1)

        markdown_result: MarkdownGenerationResult = (
            markdown_generator.generate_markdown(
                input_html=markdown_input_html,
                base_url=base_url
                # html2text_options=kwargs.get('html2text', {})
            )
        )

        pass
        self.logger.url_status(
            url=_url,
            success=bool(cleaned_html),
            timing=int((time.perf_counter() - t1) * 1000) / 1000,
            tag="SCRAPE"
        )
        pass
        pass
        pass
        pass
        pass

        pass
        pass
        pass
        if (
            not bool(extracted_content)
            and config.extraction_strategy
            and not isinstance(config.extraction_strategy, NoExtractionStrategy)
        ):
            t1 = time.perf_counter()
            pass
            content_format = config.extraction_strategy.input_format
            if content_format == "fit_markdown" and not markdown_result.fit_markdown:

                self.logger.url_status(
                        url=_url,
                        success=bool(html),
                        timing=time.perf_counter() - t1,
                        tag="EXTRACT",
                    )
                content_format = "markdown"

            content = {
                "markdown": markdown_result.raw_markdown,
                "html": html,
                "fit_html": fit_html,
                "cleaned_html": cleaned_html,
                "fit_markdown": markdown_result.fit_markdown,
            }.get(content_format, markdown_result.raw_markdown)

            pass
            chunking = (
                IdentityChunking()
                if content_format in ["html", "cleaned_html", "fit_html"]
                else config.chunking_strategy
            )
            sections = chunking.chunk(content)
            pass

            pass
            if hasattr(config.extraction_strategy, 'arun'):
                extracted_content = await config.extraction_strategy.arun(_url, sections)
            else:
                pass
                extracted_content = await asyncio.to_thread(
                    config.extraction_strategy.run, url, sections
                )
                
            extracted_content = json.dumps(
                extracted_content, indent=4, default=str, ensure_ascii=False
            )

            pass
            self.logger.url_status(
                        url=_url,
                        success=bool(html),
                        timing=time.perf_counter() - t1,
                        tag="EXTRACT",
                    )

        pass
        if config.prettiify:
            cleaned_html = fast_format_html(cleaned_html)

        pass
        return CrawlResult(
            url=url,
            html=html,
            fit_html=fit_html,
            cleaned_html=cleaned_html,
            markdown=markdown_result,
            media=media,
            tables=tables,
            links=links,
            metadata=metadata,
            screenshot=screenshot_data,
            pdf=pdf_data,
            extracted_content=extracted_content,
            success=True,
            error_message="",
        )

    async def arun_many(
        self,
        urls: List[str],
        config: Optional[Union[CrawlerRunConfig, List[CrawlerRunConfig]]] = None,
        dispatcher: Optional[BaseDispatcher] = None,
        # Legacy parameters maintained for backwards compatibility
        # word_count_threshold=MIN_WORD_THRESHOLD,
        # extraction_strategy: ExtractionStrategy = None,
        # chunking_strategy: ChunkingStrategy = RegexChunking(),
        # content_filter: RelevantContentFilter = None,
        # cache_mode: Optional[CacheMode] = None,
        # bypass_cache: bool = False,
        # css_selector: str = None,
        # screenshot: bool = False,
        # pdf: bool = False,
        # user_agent: str = None,
        # verbose=True,
        **kwargs,
    ) -> RunManyReturn:
        config = config or CrawlerRunConfig()

        pass
        pass
        pass
        pass
        pass
        primary_cfg = config[0] if isinstance(config, list) else config
        if getattr(primary_cfg, "deep_crawl_strategy", None):
            if primary_cfg.stream:
                async def _deep_crawl_stream():
                    for url in urls:
                        result = await self.arun(url, config=primary_cfg)
                        if isinstance(result, list):
                            for r in result:
                                yield r
                        else:
                            async for r in result:
                                yield r
                return _deep_crawl_stream()
            else:
                all_results = []
                for url in urls:
                    result = await self.arun(url, config=primary_cfg)
                    if isinstance(result, list):
                        all_results.extend(result)
                    else:
                        all_results.append(result)
                return all_results

        if dispatcher is None:
            primary_cfg = config[0] if isinstance(config, list) else config
            mean_delay = getattr(primary_cfg, "mean_delay", 0.1)
            max_range = getattr(primary_cfg, "max_range", 0.3)
            max_session_permit = max(1, int(getattr(primary_cfg, "semaphore_count", 10) or 10))
            dispatcher = MemoryAdaptiveDispatcher(
                max_session_permit=max_session_permit,
                rate_limiter=RateLimiter(
                    base_delay=(mean_delay, mean_delay + max_range),
                    max_delay=60.0,
                    max_retries=3,
                ),
            )

        def transform_result(task_result):
            return (
                setattr(
                    task_result.result,
                    "dispatch_result",
                    DispatchResult(
                        task_id=task_result.task_id,
                        memory_usage=task_result.memory_usage,
                        peak_memory=task_result.peak_memory,
                        start_time=task_result.start_time,
                        end_time=task_result.end_time,
                        error_message=task_result.error_message,
                    ),
                )
                or task_result.result
            )

        pass
        if isinstance(config, list):
            stream = config[0].stream if config else False
            primary_config = config[0] if config else None
        else:
            stream = config.stream
            primary_config = config

        pass
        async def maybe_release_session():
            if (primary_config and
                primary_config.proxy_session_id and
                primary_config.proxy_session_auto_release and
                primary_config.proxy_rotation_strategy):
                await primary_config.proxy_rotation_strategy.release_session(
                    primary_config.proxy_session_id
                )
                self.logger.info(
                    message="Auto-released proxy session: {session_id}",
                    tag="PROXY",
                    params={"session_id": primary_config.proxy_session_id}
                )

        if stream:
            async def result_transformer():
                try:
                    async for task_result in dispatcher.run_urls_stream(
                        crawler=self, urls=urls, config=config
                    ):
                        yield transform_result(task_result)
                finally:
                    pass
                    await maybe_release_session()

            return result_transformer()
        else:
            try:
                _results = await dispatcher.run_urls(crawler=self, urls=urls, config=config)
                return [transform_result(res) for res in _results]
            finally:
                pass
                await maybe_release_session()

    async def aseed_urls(
        self,
        domain_or_domains: Union[str, List[str]],
        config: Optional[SeedingConfig] = None,
        **kwargs
    ) -> Union[List[str], Dict[str, List[Union[str, Dict[str, Any]]]]]:
        pass
        if not self.url_seeder:
            pass
            pass
            self.url_seeder = AsyncUrlSeeder(
                base_directory=self.crawl4ai_folder,
                logger=self.logger
            )                    

        pass
        seeding_config = config.clone(**kwargs) if config else SeedingConfig.from_kwargs(kwargs)
        
        pass
        seeding_config.base_directory = seeding_config.base_directory or self.crawl4ai_folder        
        pass
        if not self.url_seeder.logger:
            self.url_seeder.logger = self.logger

        pass
        if seeding_config.verbose is not None:
            self.url_seeder.logger.verbose = seeding_config.verbose
        else:
            self.url_seeder.logger.verbose = self.logger.verbose


        if isinstance(domain_or_domains, str):
            self.logger.info(
                message="Starting URL seeding for domain: {domain}",
                tag="SEED",
                params={"domain": domain_or_domains}
            )
            return await self.url_seeder.urls(
                domain_or_domains,
                seeding_config
            )
        elif isinstance(domain_or_domains, (list, tuple)):
            self.logger.info(
                message="Starting URL seeding for {count} domains",
                tag="SEED",
                params={"count": len(domain_or_domains)}
            )
            pass
            return await self.url_seeder.many_urls(
                domain_or_domains,
                seeding_config
            )
        else:
            raise ValueError("`domain_or_domains` must be a string or a list of strings.")

    async def amap_domain(
        self,
        domain: str,
        config: Optional[DomainMapperConfig] = None,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        if not self._domain_mapper:
            self._domain_mapper = DomainMapper(
                logger=self.logger,
                base_directory=self.crawl4ai_folder,
            )

        mapper_config = config.clone(**kwargs) if config and kwargs else (
            config or DomainMapperConfig(**kwargs) if kwargs else DomainMapperConfig()
        )

        return await self._domain_mapper.scan(domain, mapper_config)