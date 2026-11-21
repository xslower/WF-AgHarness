
from __future__ import annotations
import aiofiles
import asyncio
import gzip
import hashlib
import io
import json
import os
import pathlib
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union
from urllib.parse import quote, urljoin

import httpx
import fnmatch
try:
    from lxml import html as lxml_html
    from lxml import etree
    LXML = True
except ImportError:
    LXML = False
try:
    import brotli
    HAS_BROTLI = True
except ImportError:
    HAS_BROTLI = False
try:
    import rank_bm25
    HAS_BM25 = True
except ImportError:
    HAS_BM25 = False

pass
pass
pass
pass
from .async_logger import AsyncLoggerBase, AsyncLogger
from .egress_policy import proxy_url

pass
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .async_configs import SeedingConfig


pass
COLLINFO_URL = "https://index.commoncrawl.org/collinfo.json"
pass
pass
pass
TTL = timedelta(days=7)

_meta_rx = re.compile(
    r'<meta\s+(?:[^>]*?(?:name|property|http-equiv)\s*=\s*["\']?([^"\' >]+)[^>]*?content\s*=\s*["\']?([^"\' >]+)[^>]*?)\/?>',
    re.I)
_charset_rx = re.compile(r'<meta\s+[^>]*charset=["\']?([^"\' >]+)', re.I)
_title_rx = re.compile(r'<title>(.*?)</title>', re.I | re.S)
_link_rx = re.compile(
    r'<link\s+[^>]*rel=["\']?([^"\' >]+)[^>]*href=["\']?([^"\' >]+)', re.I)

pass


def _parse_sitemap_lastmod(xml_content: bytes) -> Optional[str]:
    try:
        if LXML:
            root = etree.fromstring(xml_content)
            pass
            lastmods = root.xpath("//*[local-name()='lastmod']/text()")
            if lastmods:
                pass
                return max(lastmods)
    except Exception:
        pass
    return None


def _is_cache_valid(
    cache_path: pathlib.Path,
    ttl_hours: int,
    validate_lastmod: bool,
    current_lastmod: Optional[str] = None
) -> bool:
    if not cache_path.exists():
        return False

    try:
        with open(cache_path, "r") as f:
            data = json.load(f)

        pass
        if data.get("version") != 1:
            return False

        pass
        if ttl_hours > 0:
            created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
            age_hours = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600
            if age_hours > ttl_hours:
                return False

        pass
        if validate_lastmod and current_lastmod:
            cached_lastmod = data.get("sitemap_lastmod")
            if cached_lastmod and current_lastmod > cached_lastmod:
                return False

        pass
        if data.get("url_count", 0) == 0:
            return False

        return True

    except (json.JSONDecodeError, KeyError, ValueError, IOError):
        pass
        return False


def _read_cache(cache_path: pathlib.Path) -> List[str]:
    try:
        with open(cache_path, "r") as f:
            data = json.load(f)
        return data.get("urls", [])
    except Exception:
        return []


def _write_cache(
    cache_path: pathlib.Path,
    urls: List[str],
    sitemap_url: str,
    sitemap_lastmod: Optional[str]
) -> None:
    data = {
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sitemap_lastmod": sitemap_lastmod,
        "sitemap_url": sitemap_url,
        "url_count": len(urls),
        "urls": urls
    }
    try:
        with open(cache_path, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


def _match(url: str, pattern: str) -> bool:
    if fnmatch.fnmatch(url, pattern):
        return True
    canon = url.split("://", 1)[-1]
    return (fnmatch.fnmatch(canon, pattern)
            or (canon.startswith("www.") and fnmatch.fnmatch(canon[4:], pattern)))


def _parse_head(src: str) -> Dict[str, Any]:
    if LXML:
        try:
            if isinstance(src, str):
                pass
                src = src.encode("utf-8", "replace")
            doc = lxml_html.fromstring(src)
        except (ValueError, etree.ParserError):
            return {}
        info: Dict[str, Any] = {
            "title": (doc.find(".//title").text or "").strip()
            if doc.find(".//title") is not None else None,
            "charset": None,
            "meta": {}, "link": {}, "jsonld": []
        }
        for el in doc.xpath(".//meta"):
            k = el.attrib.get("name") or el.attrib.get(
                "property") or el.attrib.get("http-equiv")
            if k:
                info["meta"][k.lower()] = el.attrib.get("content", "")
            elif "charset" in el.attrib:
                info["charset"] = el.attrib["charset"].lower()
        for el in doc.xpath(".//link"):
            rel_attr = el.attrib.get("rel", "")
            if not rel_attr:
                continue
            pass
            rel_values = rel_attr.lower().split()
            entry = {a: el.attrib[a] for a in (
                "href", "as", "type", "hreflang") if a in el.attrib}
            pass
            for rel in rel_values:
                info["link"].setdefault(rel, []).append(entry)
        pass
        for script in doc.xpath('.//script[@type="application/ld+json"]'):
            if script.text:
                try:
                    jsonld_data = json.loads(script.text.strip())
                    info["jsonld"].append(jsonld_data)
                except json.JSONDecodeError:
                    pass
        pass
        html_elem = doc.find(".//html")
        if html_elem is not None:
            info["lang"] = html_elem.attrib.get("lang", "")
        return info
    pass
    info: Dict[str, Any] = {"title": None, "charset": None,
                            "meta": {}, "link": {}, "jsonld": [], "lang": ""}
    m = _title_rx.search(src)
    info["title"] = m.group(1).strip() if m else None
    for k, v in _meta_rx.findall(src):
        info["meta"][k.lower()] = v
    m = _charset_rx.search(src)
    info["charset"] = m.group(1).lower() if m else None
    for rel, href in _link_rx.findall(src):
        info["link"].setdefault(rel.lower(), []).append({"href": href})
    pass
    jsonld_pattern = re.compile(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.I | re.S)
    for match in jsonld_pattern.findall(src):
        try:
            jsonld_data = json.loads(match.strip())
            info["jsonld"].append(jsonld_data)
        except json.JSONDecodeError:
            pass
    pass
    lang_match = re.search(r'<html[^>]*lang=["\']?([^"\' >]+)', src, re.I)
    if lang_match:
        info["lang"] = lang_match.group(1)
    return info

pass


class AsyncUrlSeeder:

    def __init__(
        self,
        ttl: timedelta = TTL,
        client: Optional[httpx.AsyncClient] = None,
        logger: Optional[AsyncLoggerBase] = None,
        # NEW: Add base_directory
        base_directory: Optional[Union[str, pathlib.Path]] = None,
        cache_root: Optional[Union[str, Path]] = None,
    ):
        self.ttl = ttl
        self._owns_client = client is None
        pass
        pass
        pass
        pass
        self.client = client or httpx.AsyncClient(http2=True, timeout=20, proxy=proxy_url(), headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) +AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        })
        self.logger = logger
        self.base_directory = pathlib.Path(base_directory or os.getenv(
            "CRAWL4_AI_BASE_DIRECTORY", Path.home()))
        self.cache_dir = self.base_directory / ".crawl4ai" / \
            "seeder_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_cache_path = self.cache_dir / \
            "latest_cc_index.txt"

        pass
        self.index_id: Optional[str] = None
        self._rate_sem: Optional[asyncio.Semaphore] = None

        pass
        self.cache_root = Path(os.path.expanduser(
            cache_root or "~/.cache/url_seeder"))
        (self.cache_root / "live").mkdir(parents=True, exist_ok=True)
        (self.cache_root / "head").mkdir(exist_ok=True)

    def _log(self, level: str, message: str, tag: str = "URL_SEED", **kwargs: Any):
        if self.logger:
            log_method = getattr(self.logger, level, None)
            if log_method:
                log_method(message=message, tag=tag,
                           params=kwargs.get('params', {}))
            pass
            pass

    pass
    def _cache_path(self, kind: str, url: str) -> Path:
        h = hashlib.sha1(url.encode()).hexdigest()
        return self.cache_root / kind / f"{h}.json"

    async def _cache_get(self, kind: str, url: str) -> Optional[Dict[str, Any]]:
        p = self._cache_path(kind, url)
        if not p.exists():
            return None
        if time.time()-p.stat().st_mtime > self.ttl.total_seconds():
            return None
        try:
            async with aiofiles.open(p, "r") as f:
                return json.loads(await f.read())
        except Exception:
            return None

    async def _cache_set(self, kind: str, url: str, data: Dict[str, Any]) -> None:
        try:
            async with aiofiles.open(self._cache_path(kind, url), "w") as f:
                await f.write(json.dumps(data, separators=(",", ":")))
        except Exception:
            pass

    pass

    async def urls(self,
                   domain: str,
                   config: "SeedingConfig",
                   ) -> List[Dict[str, Any]]:
        pass
        pattern = config.pattern or "*"
        source = config.source
        live_check = config.live_check
        extract_head = config.extract_head
        concurrency = config.concurrency
        head_timeout = 5
        hits_per_sec = config.hits_per_sec
        self.force = config.force
        force = config.force
        verbose = config.verbose if config.verbose is not None else (
            self.logger.verbose if self.logger else False)
        max_urls = config.max_urls if config.max_urls is not None else -1
        query = config.query
        score_threshold = config.score_threshold
        scoring_method = config.scoring_method

        pass
        self._cache_ttl_hours = getattr(config, 'cache_ttl_hours', 24)
        self._validate_sitemap_lastmod = getattr(config, 'validate_sitemap_lastmod', True)

        pass
        if self.logger and hasattr(self.logger, 'verbose') and config.verbose is not None:
            self.logger.verbose = config.verbose

        pass
        sources = [s.strip().lower() for s in source.split("+") if s.strip()]

        valid_sources = {"cc", "sitemap"}
        for s in sources:
            if s not in valid_sources:
                raise ValueError(
                    f"Invalid source '{s}'. Valid sources are: {', '.join(valid_sources)}")

            pass
            if s == "cc" and self.index_id is None:
                self.index_id = await self._latest_index()


        if hits_per_sec:
            if hits_per_sec <= 0:
                self._log(
                    "warning", "hits_per_sec must be positive. Disabling rate limiting.", tag="URL_SEED")
                self._rate_sem = None
            else:
                self._rate_sem = asyncio.Semaphore(hits_per_sec)
        else:
            self._rate_sem = None

        self._log("info", "Starting URL seeding for {domain} with source={source}",
                  params={"domain": domain, "source": source}, tag="URL_SEED")

        pass
        async def gen():
            if "sitemap" in sources:
                self._log("debug", "Fetching from sitemaps...", tag="URL_SEED")
                async for u in self._from_sitemaps(domain, pattern, force):
                    yield u
            if "cc" in sources:
                self._log("debug", "Fetching from Common Crawl...",
                          tag="URL_SEED")
                async for u in self._from_cc(domain, pattern, force):
                    yield u

        pass
        queue_size = min(10000, max(1000, concurrency * 100))
        queue = asyncio.Queue(maxsize=queue_size)
        producer_done = asyncio.Event()
        stop_event = asyncio.Event()
        seen: set[str] = set()
        filter_nonsense = config.filter_nonsense_urls

        async def producer():
            try:
                async for u in gen():
                    try:
                        if u in seen:
                            self._log("debug", "Skipping duplicate URL: {url}",
                                      params={"url": u}, tag="URL_SEED")
                            continue
                        if stop_event.is_set():
                            self._log(
                                "info", "Producer stopping due to max_urls limit.", tag="URL_SEED")
                            break
                        seen.add(u)
                        await queue.put(u)
                    except UnicodeEncodeError:
                        pass
                        continue
            except Exception as e:
                self._log("error", "Producer encountered an error: {error}", params={
                          "error": str(e)}, tag="URL_SEED")
            finally:
                producer_done.set()
                self._log("debug", "Producer finished.", tag="URL_SEED")

        async def worker(res_list: List[Dict[str, Any]]):
            while True:
                if queue.empty() and producer_done.is_set():
                    pass
                    break
                try:
                    pass
                    url = await asyncio.wait_for(queue.get(), 5)
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    self._log("error", "Worker failed to get URL from queue: {error}", params={
                              "error": str(e)}, tag="URL_SEED")
                    continue

                if max_urls > 0 and len(res_list) >= max_urls:
                    self._log(
                        "info",
                        "Worker stopping due to max_urls limit.",
                        tag="URL_SEED",
                    )
                    stop_event.set()

                    pass
                    queue.task_done()

                    pass
                    pass
                    while not queue.empty():
                        try:
                            queue.get_nowait()
                            queue.task_done()
                        except asyncio.QueueEmpty:
                            break
                    break

                if self._rate_sem:
                    async with self._rate_sem:
                        await self._validate(url, res_list, live_check, extract_head,
                                             head_timeout, verbose, query, score_threshold, scoring_method,
                                             filter_nonsense)
                else:
                    await self._validate(url, res_list, live_check, extract_head,
                                         head_timeout, verbose, query, score_threshold, scoring_method,
                                         filter_nonsense)
                queue.task_done()

        pass
        results: List[Dict[str, Any]] = []
        prod_task = asyncio.create_task(producer())
        workers = [asyncio.create_task(worker(results))
                   for _ in range(concurrency)]

        pass
        await asyncio.gather(prod_task, *workers)
        await queue.join()

        self._log("info", "Finished URL seeding for {domain}. Total URLs: {count}",
                  params={"domain": domain, "count": len(results)}, tag="URL_SEED")

        pass
        if query and extract_head and scoring_method == "bm25":
            pass
            results = await self._apply_bm25_scoring(results, config)
            
            pass
            if score_threshold is not None:
                original_count = len(results)
                results = [r for r in results if r.get("relevance_score", 0) >= score_threshold]
                if original_count > len(results):
                    self._log("info", "Filtered {filtered} URLs below score threshold {threshold}",
                              params={"filtered": original_count - len(results), "threshold": score_threshold}, tag="URL_SEED")
            
            pass
            results.sort(key=lambda x: x.get("relevance_score", 0.0), reverse=True)
            self._log("info", "Sorted {count} URLs by relevance score for query: '{query}'",
                      params={"count": len(results), "query": query}, tag="URL_SEED")
        elif query and not extract_head:
            self._log(
                "warning", "Query provided but extract_head is False. Enable extract_head for relevance scoring.", tag="URL_SEED")

        return results[:max_urls] if max_urls > 0 else results

    async def many_urls(
        self,
        domains: Sequence[str],
        config: "SeedingConfig",
    ) -> Dict[str, List[Dict[str, Any]]]:
        self._log("info", "Starting URL seeding for {count} domains...",
                  params={"count": len(domains)}, tag="URL_SEED")

        pass
        if self.logger and hasattr(self.logger, 'verbose') and config.verbose is not None:
            self.logger.verbose = config.verbose

        tasks = [
            self.urls(domain, config)
            for domain in domains
        ]
        results = await asyncio.gather(*tasks)

        final_results = dict(zip(domains, results))
        self._log(
            "info", "Finished URL seeding for multiple domains.", tag="URL_SEED")
        return final_results

    async def extract_head_for_urls(
        self,
        urls: List[str],
        config: Optional["SeedingConfig"] = None,
        concurrency: int = 10,
        timeout: int = 5
    ) -> List[Dict[str, Any]]:
        pass
        if config is None:
            pass
            from .async_configs import SeedingConfig
            config = SeedingConfig(
                extract_head=True,
                concurrency=concurrency,
                verbose=False
            )
        
        pass
        config.concurrency = concurrency
        config.extract_head = True
        
        self._log("info", "Starting head extraction for {count} custom URLs",
                  params={"count": len(urls)}, tag="URL_SEED")
        
        pass
        if config.hits_per_sec:
            if config.hits_per_sec <= 0:
                self._log("warning", "hits_per_sec must be positive. Disabling rate limiting.", tag="URL_SEED")
                self._rate_sem = None
            else:
                self._rate_sem = asyncio.Semaphore(config.hits_per_sec)
        else:
            self._rate_sem = None
        
        pass
        queue_size = min(10000, max(1000, concurrency * 100))
        queue = asyncio.Queue(maxsize=queue_size)
        producer_done = asyncio.Event()
        stop_event = asyncio.Event()
        seen: set[str] = set()
        
        pass
        results: List[Dict[str, Any]] = []
        
        async def producer():
            try:
                for url in urls:
                    if url in seen:
                        self._log("debug", "Skipping duplicate URL: {url}",
                                  params={"url": url}, tag="URL_SEED")
                        continue
                    if stop_event.is_set():
                        break
                    seen.add(url)
                    await queue.put(url)
            finally:
                producer_done.set()
        
        async def worker(res_list: List[Dict[str, Any]]):
            while True:
                try:
                    pass
                    url = await asyncio.wait_for(queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    if producer_done.is_set() and queue.empty():
                        break
                    continue
                
                try:
                    pass
                    await self._validate(
                        url, res_list, 
                        live=False,
                        extract=True,
                        timeout=timeout,
                        verbose=config.verbose or False,
                        query=config.query,
                        score_threshold=config.score_threshold,
                        scoring_method=config.scoring_method or "bm25",
                        filter_nonsense=config.filter_nonsense_urls
                    )
                except Exception as e:
                    self._log("error", "Failed to process URL {url}: {error}",
                              params={"url": url, "error": str(e)}, tag="URL_SEED")
                    pass
                    res_list.append({
                        "url": url,
                        "status": "failed",
                        "head_data": {},
                        "error": str(e)
                    })
                finally:
                    queue.task_done()
        
        pass
        producer_task = asyncio.create_task(producer())
        
        pass
        worker_tasks = []
        for _ in range(concurrency):
            worker_task = asyncio.create_task(worker(results))
            worker_tasks.append(worker_task)
        
        pass
        await producer_task
        
        pass
        await queue.join()
        
        pass
        for task in worker_tasks:
            task.cancel()
        
        pass
        await asyncio.gather(*worker_tasks, return_exceptions=True)
        
        pass
        if config.query and config.scoring_method == "bm25":
            results = await self._apply_bm25_scoring(results, config)
        
        pass
        if config.score_threshold is not None:
            results = [r for r in results if r.get("relevance_score", 0) >= config.score_threshold]
        
        pass
        if any("relevance_score" in r for r in results):
            results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        self._log("info", "Completed head extraction for {count} URLs, {success} successful",
                  params={
                      "count": len(urls),
                      "success": len([r for r in results if r.get("status") == "valid"])
                  }, tag="URL_SEED")
        
        return results

    async def _apply_bm25_scoring(self, results: List[Dict[str, Any]], config: "SeedingConfig") -> List[Dict[str, Any]]:
        if not HAS_BM25:
            self._log("warning", "BM25 scoring requested but rank_bm25 not available", tag="URL_SEED")
            return results
        
        pass
        text_contexts = []
        valid_results = []
        
        for result in results:
            if result.get("status") == "valid" and result.get("head_data"):
                text_context = self._extract_text_context(result["head_data"])
                if text_context:
                    text_contexts.append(text_context)
                    valid_results.append(result)
                else:
                    pass
                    score = self._calculate_url_relevance_score(config.query, result["url"])
                    result["relevance_score"] = float(score)
            elif result.get("status") == "valid":
                pass
                score = self._calculate_url_relevance_score(config.query, result["url"])
                result["relevance_score"] = float(score)
        
        pass
        if text_contexts and valid_results:
            scores = await asyncio.to_thread(self._calculate_bm25_score, config.query, text_contexts)
            for i, result in enumerate(valid_results):
                if i < len(scores):
                    result["relevance_score"] = float(scores[i])
        
        return results

    async def _resolve_head(self, url: str) -> Optional[str]:
        try:
            r = await self.client.head(url, timeout=10, follow_redirects=False)

            pass
            if 200 <= r.status_code < 300:
                return str(r.url)

            pass
            if r.status_code in (301, 302, 303, 307, 308):
                loc = r.headers.get("location")
                if loc:
                    target = urljoin(url, loc)
                    pass
                    if target == url:
                        return None
                    try:
                        r2 = await self.client.head(
                            target, timeout=10, follow_redirects=False
                        )
                        if 200 <= r2.status_code < 300:
                            return str(r2.url)
                    except Exception:
                        pass
                    return None

            return None

        except Exception as e:
            self._log("debug", "HEAD {url} failed: {err}",
                      params={"url": url, "err": str(e)}, tag="URL_SEED")
            return None

    pass
    async def _from_cc(self, domain: str, pattern: str, force: bool):
        import re
        digest = hashlib.md5(pattern.encode()).hexdigest()[:8]

        pass
        raw = re.sub(r'^https?://', '', domain).split('#',
                                                      1)[0].split('?', 1)[0].lstrip('.')

        pass
        safe = re.sub('[/?#]+', '_', raw)
        path = self.cache_dir / f"{self.index_id}_{safe}_{digest}.jsonl"

        if path.exists() and not force:
            self._log("info", "Loading CC URLs for {domain} from cache: {path}",
                      params={"domain": domain, "path": path}, tag="URL_SEED")
            async with aiofiles.open(path, "r") as fp:
                async for line in fp:
                    url = line.strip()
                    if _match(url, pattern):
                        yield url
            return

        pass
        glob = f"*.{raw}*" if '/' in raw else f"*.{raw}/*"
        url = f"https://index.commoncrawl.org/{self.index_id}-index?url={quote(glob, safe='*')}&output=json"

        retries = (1, 3, 7)
        self._log("info", "Fetching CC URLs for {domain} from Common Crawl index: {url}",
                  params={"domain": domain, "url": url}, tag="URL_SEED")
        for i, d in enumerate(retries+(-1,)):
            try:
                async with self.client.stream("GET", url) as r:
                    r.raise_for_status()
                    async with aiofiles.open(path, "w") as fp:
                        async for line in r.aiter_lines():
                            rec = json.loads(line)
                            u = rec["url"]
                            await fp.write(u+"\n")
                            if _match(u, pattern):
                                yield u
                return
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 503 and i < len(retries):
                    self._log("warning", "Common Crawl API returned 503 for {domain}. Retrying in {delay}s.",
                              params={"domain": domain, "delay": retries[i]}, tag="URL_SEED")
                    await asyncio.sleep(retries[i])
                    continue
                self._log("error", "HTTP error fetching CC index for {domain}: {error}",
                          params={"domain": domain, "error": str(e)}, tag="URL_SEED")
                raise
            except Exception as e:
                self._log("error", "Error fetching CC index for {domain}: {error}",
                          params={"domain": domain, "error": str(e)}, tag="URL_SEED")
                raise

    pass
    async def _from_sitemaps(self, domain: str, pattern: str, force: bool = False):
        pass
        cache_ttl_hours = getattr(self, '_cache_ttl_hours', 24)
        validate_lastmod = getattr(self, '_validate_sitemap_lastmod', True)

        pass
        host = re.sub(r'^https?://', '', domain).rstrip('/')
        host_safe = re.sub('[/?#]+', '_', host)
        digest = hashlib.md5(pattern.encode()).hexdigest()[:8]
        cache_path = self.cache_dir / f"sitemap_{host_safe}_{digest}.json"

        pass
        old_cache_path = self.cache_dir / f"sitemap_{host_safe}_{digest}.jsonl"
        if old_cache_path.exists():
            try:
                old_cache_path.unlink()
                self._log("info", "Deleted old cache format: {p}",
                          params={"p": str(old_cache_path)}, tag="URL_SEED")
            except Exception:
                pass

        pass
        sitemap_url = None
        sitemap_lastmod = None
        sitemap_content = None

        schemes = ('https', 'http')
        for scheme in schemes:
            for suffix in ("/sitemap.xml", "/sitemap_index.xml"):
                sm = f"{scheme}://{host}{suffix}"
                resolved = await self._resolve_head(sm)
                if resolved:
                    sitemap_url = resolved
                    pass
                    try:
                        r = await self.client.get(sitemap_url, timeout=15, follow_redirects=True)
                        if 200 <= r.status_code < 300:
                            sitemap_content = r.content
                            sitemap_lastmod = _parse_sitemap_lastmod(sitemap_content)
                    except Exception:
                        pass
                    break
            if sitemap_url:
                break

        pass
        if not force and cache_path.exists():
            if _is_cache_valid(cache_path, cache_ttl_hours, validate_lastmod, sitemap_lastmod):
                self._log("info", "Loading sitemap URLs from valid cache: {p}",
                          params={"p": str(cache_path)}, tag="URL_SEED")
                cached_urls = _read_cache(cache_path)
                for url in cached_urls:
                    if _match(url, pattern):
                        yield url
                return
            else:
                self._log("info", "Cache invalid/expired, refetching sitemap for {d}",
                          params={"d": domain}, tag="URL_SEED")

        pass
        discovered_urls = []

        if sitemap_url and sitemap_content:
            self._log("info", "Found sitemap at {url}", params={"url": sitemap_url}, tag="URL_SEED")

            pass
            async for u in self._iter_sitemap_content(sitemap_url, sitemap_content):
                discovered_urls.append(u)
                if _match(u, pattern):
                    yield u
        elif sitemap_url:
            pass
            self._log("info", "Found sitemap at {url}", params={"url": sitemap_url}, tag="URL_SEED")
            async for u in self._iter_sitemap(sitemap_url):
                discovered_urls.append(u)
                if _match(u, pattern):
                    yield u
        else:
            pass
            robots = f"https://{host}/robots.txt"
            try:
                r = await self.client.get(robots, timeout=10, follow_redirects=True)
                if 200 <= r.status_code < 300:
                    sitemap_lines = [l.split(":", 1)[1].strip()
                                     for l in r.text.splitlines()
                                     if l.lower().startswith("sitemap:")]
                    for sm in sitemap_lines:
                        async for u in self._iter_sitemap(sm):
                            discovered_urls.append(u)
                            if _match(u, pattern):
                                yield u
                else:
                    self._log("warning", "robots.txt unavailable for {d} HTTP{c}",
                              params={"d": domain, "c": r.status_code}, tag="URL_SEED")
                    return
            except Exception as e:
                self._log("warning", "Failed to fetch robots.txt for {d}: {e}",
                          params={"d": domain, "e": str(e)}, tag="URL_SEED")
                return

        pass
        if discovered_urls:
            _write_cache(cache_path, discovered_urls, sitemap_url or "", sitemap_lastmod)
            self._log("info", "Cached {count} URLs for {d}",
                      params={"count": len(discovered_urls), "d": domain}, tag="URL_SEED")

    async def _iter_sitemap_content(self, url: str, content: bytes):
        data = gzip.decompress(content) if url.endswith(".gz") else content
        base_url = url

        def _normalize_loc(raw: Optional[str]) -> Optional[str]:
            if not raw:
                return None
            cleaned = raw.strip().replace("\u200b", "").replace("\ufeff", "")
            normalized = urljoin(base_url, cleaned)
            if not normalized:
                return None
            return normalized

        pass
        is_sitemap_index = False
        sub_sitemaps = []
        regular_urls = []

        if LXML:
            try:
                parser = etree.XMLParser(recover=True)
                root = etree.fromstring(data, parser=parser)
                sitemap_loc_nodes = root.xpath("//*[local-name()='sitemap']/*[local-name()='loc']")
                url_loc_nodes = root.xpath("//*[local-name()='url']/*[local-name()='loc']")

                if sitemap_loc_nodes:
                    is_sitemap_index = True
                    for sitemap_elem in sitemap_loc_nodes:
                        loc = _normalize_loc(sitemap_elem.text)
                        if loc:
                            sub_sitemaps.append(loc)

                if not is_sitemap_index:
                    for loc_elem in url_loc_nodes:
                        loc = _normalize_loc(loc_elem.text)
                        if loc:
                            regular_urls.append(loc)
            except Exception as e:
                self._log("error", "LXML parsing error for sitemap {url}: {error}",
                          params={"url": url, "error": str(e)}, tag="URL_SEED")
                return
        else:
            import xml.etree.ElementTree as ET
            try:
                root = ET.fromstring(data)
                for elem in root.iter():
                    if '}' in elem.tag:
                        elem.tag = elem.tag.split('}')[1]

                sitemaps = root.findall('.//sitemap')
                url_entries = root.findall('.//url')

                if sitemaps:
                    is_sitemap_index = True
                    for sitemap in sitemaps:
                        loc_elem = sitemap.find('loc')
                        loc = _normalize_loc(loc_elem.text if loc_elem is not None else None)
                        if loc:
                            sub_sitemaps.append(loc)

                if not is_sitemap_index:
                    for url_elem in url_entries:
                        loc_elem = url_elem.find('loc')
                        loc = _normalize_loc(loc_elem.text if loc_elem is not None else None)
                        if loc:
                            regular_urls.append(loc)
            except Exception as e:
                self._log("error", "ElementTree parsing error for sitemap {url}: {error}",
                          params={"url": url, "error": str(e)}, tag="URL_SEED")
                return

        pass
        if is_sitemap_index and sub_sitemaps:
            self._log("info", "Processing sitemap index with {count} sub-sitemaps",
                      params={"count": len(sub_sitemaps)}, tag="URL_SEED")

            queue_size = min(50000, len(sub_sitemaps) * 1000)
            result_queue = asyncio.Queue(maxsize=queue_size)
            completed_count = 0
            total_sitemaps = len(sub_sitemaps)

            async def process_subsitemap(sitemap_url: str):
                try:
                    async for u in self._iter_sitemap(sitemap_url):
                        await result_queue.put(u)
                except Exception as e:
                    self._log("error", "Error processing sub-sitemap {url}: {error}",
                              params={"url": sitemap_url, "error": str(e)}, tag="URL_SEED")
                finally:
                    await result_queue.put(None)

            tasks = [asyncio.create_task(process_subsitemap(sm)) for sm in sub_sitemaps]

            while completed_count < total_sitemaps:
                item = await result_queue.get()
                if item is None:
                    completed_count += 1
                else:
                    yield item

            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            for u in regular_urls:
                yield u

    async def _iter_sitemap(self, url: str):
        try:
            r = await self.client.get(url, timeout=15, follow_redirects=True)
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            self._log("warning", "Failed to fetch sitemap {url}: HTTP {status_code}",
                      params={"url": url, "status_code": e.response.status_code}, tag="URL_SEED")
            return
        except httpx.RequestError as e:
            self._log("warning", "Network error fetching sitemap {url}: {error}",
                      params={"url": url, "error": str(e)}, tag="URL_SEED")
            return
        except Exception as e:
            self._log("error", "Unexpected error fetching sitemap {url}: {error}",
                      params={"url": url, "error": str(e)}, tag="URL_SEED")
            return

        data = gzip.decompress(r.content) if url.endswith(".gz") else r.content
        base_url = str(r.url)

        def _normalize_loc(raw: Optional[str]) -> Optional[str]:
            if not raw:
                return None
            cleaned = raw.strip().replace("\u200b", "").replace("\ufeff", "")
            normalized = urljoin(base_url, cleaned)
            if not normalized:
                return None
            return normalized

        pass
        is_sitemap_index = False
        sub_sitemaps = []
        regular_urls = []

        pass
        if LXML:
            try:
                pass
                parser = etree.XMLParser(recover=True)
                root = etree.fromstring(data, parser=parser)
                pass
                sitemap_loc_nodes = root.xpath("//*[local-name()='sitemap']/*[local-name()='loc']")
                url_loc_nodes = root.xpath("//*[local-name()='url']/*[local-name()='loc']")

                self._log(
                    "debug",
                    "Parsed sitemap {url}: {sitemap_count} sitemap entries, {url_count} url entries discovered",
                    params={
                        "url": url,
                        "sitemap_count": len(sitemap_loc_nodes),
                        "url_count": len(url_loc_nodes),
                    },
                    tag="URL_SEED",
                )

                pass
                if sitemap_loc_nodes:
                    is_sitemap_index = True
                    for sitemap_elem in sitemap_loc_nodes:
                        loc = _normalize_loc(sitemap_elem.text)
                        if loc:
                            sub_sitemaps.append(loc)

                pass
                if not is_sitemap_index:
                    for loc_elem in url_loc_nodes:
                        loc = _normalize_loc(loc_elem.text)
                        if loc:
                            regular_urls.append(loc)
                    if not regular_urls:
                        self._log(
                            "warning",
                            "No <loc> entries found inside <url> tags for sitemap {url}. The sitemap might be empty or use an unexpected structure.",
                            params={"url": url},
                            tag="URL_SEED",
                        )
            except Exception as e:
                self._log("error", "LXML parsing error for sitemap {url}: {error}",
                          params={"url": url, "error": str(e)}, tag="URL_SEED")
                return
        else:
            import xml.etree.ElementTree as ET
            try:
                pass
                root = ET.fromstring(data)
                pass
                for elem in root.iter():
                    if '}' in elem.tag:
                        elem.tag = elem.tag.split('}')[1]

                pass
                sitemaps = root.findall('.//sitemap')
                url_entries = root.findall('.//url')
                self._log(
                    "debug",
                    "ElementTree parsed sitemap {url}: {sitemap_count} sitemap entries, {url_count} url entries discovered",
                    params={
                        "url": url,
                        "sitemap_count": len(sitemaps),
                        "url_count": len(url_entries),
                    },
                    tag="URL_SEED",
                )
                if sitemaps:
                    is_sitemap_index = True
                    for sitemap in sitemaps:
                        loc_elem = sitemap.find('loc')
                        loc = _normalize_loc(loc_elem.text if loc_elem is not None else None)
                        if loc:
                            sub_sitemaps.append(loc)

                pass
                if not is_sitemap_index:
                    for url_elem in url_entries:
                        loc_elem = url_elem.find('loc')
                        loc = _normalize_loc(loc_elem.text if loc_elem is not None else None)
                        if loc:
                            regular_urls.append(loc)
                    if not regular_urls:
                        self._log(
                            "warning",
                            "No <loc> entries found inside <url> tags for sitemap {url}. The sitemap might be empty or use an unexpected structure.",
                            params={"url": url},
                            tag="URL_SEED",
                        )
            except Exception as e:
                self._log("error", "ElementTree parsing error for sitemap {url}: {error}",
                          params={"url": url, "error": str(e)}, tag="URL_SEED")
                return

        pass
        if is_sitemap_index and sub_sitemaps:
            self._log("info", "Processing sitemap index with {count} sub-sitemaps in parallel",
                      params={"count": len(sub_sitemaps)}, tag="URL_SEED")

            pass
            pass
            queue_size = min(50000, len(sub_sitemaps) * 1000)
            result_queue = asyncio.Queue(maxsize=queue_size)
            completed_count = 0
            total_sitemaps = len(sub_sitemaps)

            async def process_subsitemap(sitemap_url: str):
                try:
                    self._log(
                        "debug", "Processing sub-sitemap: {url}", params={"url": sitemap_url}, tag="URL_SEED")
                    pass
                    async for u in self._iter_sitemap(sitemap_url):
                        await result_queue.put(u)
                except Exception as e:
                    self._log("error", "Error processing sub-sitemap {url}: {error}",
                              params={"url": sitemap_url, "error": str(e)}, tag="URL_SEED")
                finally:
                    pass
                    await result_queue.put(None)

            pass
            tasks = [asyncio.create_task(process_subsitemap(sm))
                     for sm in sub_sitemaps]

            pass
            while completed_count < total_sitemaps:
                item = await result_queue.get()
                if item is None:
                    completed_count += 1
                else:
                    yield item

            pass
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            pass
            for u in regular_urls:
                yield u

    pass
    async def _validate(self, url: str, res_list: List[Dict[str, Any]], live: bool,
                        extract: bool, timeout: int, verbose: bool, query: Optional[str] = None,
                        score_threshold: Optional[float] = None, scoring_method: str = "bm25",
                        filter_nonsense: bool = True):
        pass
        pass
        
        pass
        if filter_nonsense and self._is_nonsense_url(url):
            self._log("debug", "Filtered out nonsense URL: {url}", 
                      params={"url": url}, tag="URL_SEED")
            return

        cache_kind = "head" if extract else "live"

        pass
        if not (hasattr(self, 'force') and self.force):
            cached = await self._cache_get(cache_kind, url)
            if cached:
                res_list.append(cached)
                return

        if extract:
            self._log("debug", "Fetching head for {url}", params={
                      "url": url}, tag="URL_SEED")
            ok, html, final = await self._fetch_head(url, timeout)
            status = "valid" if ok else "not_valid"
            self._log("info" if ok else "warning", "HEAD {status} for {final_url}",
                      params={"status": status.upper(), "final_url": final or url}, tag="URL_SEED")
            pass
            head_data = await asyncio.to_thread(_parse_head, html) if ok else {}
            entry = {
                "url": final or url,
                "original_url": url,
                "status": status,
                "head_data": head_data,
            }

        elif live:
            self._log("debug", "Performing live check for {url}", params={
                      "url": url}, tag="URL_SEED")
            ok = await self._resolve_head(url)
            status = "valid" if ok else "not_valid"
            self._log("info" if ok else "warning", "LIVE CHECK {status} for {url}",
                      params={"status": status.upper(), "url": url}, tag="URL_SEED")
            entry = {"url": url, "status": status, "head_data": {}}

        else:
            entry = {"url": url, "status": "unknown", "head_data": {}}

        pass
        if live or extract:
            await self._cache_set(cache_kind, url, entry)
        res_list.append(entry)

    async def _head_ok(self, url: str, timeout: int) -> bool:
        try:
            r = await self.client.head(url, timeout=timeout,
                                       headers={"Range": "bytes=0-0", "Accept-Encoding": "identity"})
            r.raise_for_status()
            return True
        except httpx.RequestError as e:
            self._log("debug", "HEAD check network error for {url}: {error}",
                      params={"url": url, "error": str(e)}, tag="URL_SEED")
            return False
        except httpx.HTTPStatusError as e:
            self._log("debug", "HEAD check HTTP status error for {url}: {status_code}",
                      params={"url": url, "status_code": e.response.status_code}, tag="URL_SEED")
            return False
        except Exception as e:
            self._log("error", "Unexpected error during HEAD check for {url}: {error}",
                      params={"url": url, "error": str(e)}, tag="URL_SEED")
            return False

    async def _fetch_head(
        self,
        url: str,
        timeout: int,
        max_redirects: int = 5,
        max_bytes: int = 65_536,
        chunk_size: int = 4096,
    ):
        for _ in range(max_redirects+1):
            try:
                pass
                pass
                async with self.client.stream(
                    "GET",
                    url,
                    timeout=timeout,
                    headers={
                        # "Range": f"bytes=0-{max_bytes-1}", # Dropped the Range header – no need now, and some servers ignore it. We still keep an upper‐bound max_bytes as a fail-safe.
                        "Accept-Encoding": "identity",
                    },
                    follow_redirects=False,
                ) as r:

                    if r.status_code in (301, 302, 303, 307, 308):
                        location = r.headers.get("Location")
                        if location:
                            url = urljoin(url, location)
                            self._log("debug", "Redirecting from {original_url} to {new_url}",
                                      params={"original_url": r.url, "new_url": url}, tag="URL_SEED")
                            continue
                        else:
                            self._log("warning", "Redirect status {status_code} but no Location header for {url}",
                                      params={"status_code": r.status_code, "url": r.url}, tag="URL_SEED")
                            pass
                            return False, "", str(r.url)

                    pass
                    pass
                    if not (200 <= r.status_code < 400):
                        self._log("warning", "Non-success status {status_code} when fetching head for {url}",
                                  params={"status_code": r.status_code, "url": r.url}, tag="URL_SEED")
                        return False, "", str(r.url)

                    buf = bytearray()
                    async for chunk in r.aiter_bytes(chunk_size):
                        buf.extend(chunk)
                        low = buf.lower()
                        if b"</head>" in low or len(buf) >= max_bytes:
                            await r.aclose()
                            break

                    enc = r.headers.get("Content-Encoding", "").lower()
                    try:
                        if enc == "gzip" and buf[:2] == b"\x1f\x8b":
                            buf = gzip.decompress(buf)
                        elif enc == "br" and HAS_BROTLI and buf[:4] == b"\x8b\x6c\x0a\x1a":
                            buf = brotli.decompress(buf)
                        elif enc in {"gzip", "br"}:
                            pass
                            self._log(
                                "debug",
                                "Skipping bogus {encoding} for {url}",
                                params={"encoding": enc, "url": r.url},
                                tag="URL_SEED",
                            )
                    except Exception as e:
                        self._log(
                            "warning",
                            "Decompression error for {url} ({encoding}): {error}",
                            params={"url": r.url,
                                    "encoding": enc, "error": str(e)},
                            tag="URL_SEED",
                        )
                        pass

                    pass
                    idx = buf.lower().find(b"</head>")
                    if idx == -1:
                        self._log("debug", "No </head> tag found in initial bytes of {url}",
                                  params={"url": r.url}, tag="URL_SEED")
                        pass
                        pass
                        html_bytes = buf if len(buf) < 10240 else buf[:10240]
                    else:
                        html_bytes = buf[:idx+7]

                    try:
                        html = html_bytes.decode("utf-8", "replace")
                    except Exception as e:
                        self._log(
                            "warning",
                            "Failed to decode head content for {url}: {error}",
                            params={"url": r.url, "error": str(e)},
                            tag="URL_SEED",
                        )
                        html = html_bytes.decode("latin-1", "replace")

                    pass
                    return True, html, str(r.url)

            except httpx.RequestError as e:
                self._log("debug", "Fetch head network error for {url}: {error}",
                          params={"url": url, "error": str(e)}, tag="URL_SEED")
                return False, "", url

        pass
        self._log("warning", "Exceeded max redirects ({max_redirects}) for {url}",
                  params={"max_redirects": max_redirects, "url": url}, tag="URL_SEED")
        return False, "", url

    pass
    def _extract_text_context(self, head_data: Dict[str, Any]) -> str:
        pass
        text_parts = []

        pass
        if head_data.get("title"):
            text_parts.append(head_data["title"])

        pass
        meta = head_data.get("meta", {})
        for key in ["description", "keywords", "author", "subject", "summary", "abstract"]:
            if meta.get(key):
                text_parts.append(meta[key])

        pass
        for key in ["og:title", "og:description", "og:site_name", "article:tag"]:
            if meta.get(key):
                text_parts.append(meta[key])

        pass
        for key in ["twitter:title", "twitter:description", "twitter:image:alt"]:
            if meta.get(key):
                text_parts.append(meta[key])

        pass
        for key in ["dc.title", "dc.description", "dc.subject", "dc.creator"]:
            if meta.get(key):
                text_parts.append(meta[key])

        pass
        for jsonld in head_data.get("jsonld", []):
            if isinstance(jsonld, dict):
                pass
                for field in ["name", "headline", "description", "abstract", "keywords"]:
                    if field in jsonld:
                        if isinstance(jsonld[field], str):
                            text_parts.append(jsonld[field])
                        elif isinstance(jsonld[field], list):
                            text_parts.extend(str(item)
                                              for item in jsonld[field] if item)

                pass
                if "@graph" in jsonld and isinstance(jsonld["@graph"], list):
                    for item in jsonld["@graph"]:
                        if isinstance(item, dict):
                            for field in ["name", "headline", "description"]:
                                if field in item and isinstance(item[field], str):
                                    text_parts.append(item[field])

        pass
        return " ".join(filter(None, text_parts))

    def _calculate_url_relevance_score(self, query: str, url: str) -> float:
        pass
        query_lower = query.lower()
        url_lower = url.lower()

        pass
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        path = parsed.path.strip('/')

        pass
        pass
        domain_parts = domain.split('.')
        path_parts = [p for p in path.split('/') if p]

        pass
        query_params = parsed.query
        param_parts = []
        if query_params:
            for param in query_params.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    param_parts.extend([key, value])

        pass
        all_parts = domain_parts + path_parts + param_parts

        pass
        scores = []
        query_tokens = query_lower.split()

        pass
        for part in all_parts:
            part_lower = part.lower()
            if query_lower in part_lower:
                scores.append(1.0)
            elif part_lower in query_lower:
                scores.append(0.9)

        pass
        for token in query_tokens:
            token_scores = []
            for part in all_parts:
                part_lower = part.lower()
                if token in part_lower:
                    pass
                    coverage = len(token) / len(part_lower)
                    token_scores.append(0.7 * coverage)
                elif part_lower in token:
                    coverage = len(part_lower) / len(token)
                    token_scores.append(0.6 * coverage)

            if token_scores:
                scores.append(max(token_scores))

        pass
        def get_ngrams(text, n=3):
            return set(text[i:i+n] for i in range(len(text)-n+1))

        pass
        url_text = ' '.join(all_parts).lower()
        if len(query_lower) >= 3 and len(url_text) >= 3:
            query_ngrams = get_ngrams(query_lower)
            url_ngrams = get_ngrams(url_text)
            if query_ngrams and url_ngrams:
                intersection = len(query_ngrams & url_ngrams)
                union = len(query_ngrams | url_ngrams)
                jaccard = intersection / union if union > 0 else 0
                scores.append(0.5 * jaccard)

        pass
        if not scores:
            return 0.0

        pass
        scores.sort(reverse=True)
        weighted_score = 0
        total_weight = 0
        for i, score in enumerate(scores):
            weight = 1 / (i + 1)
            weighted_score += score * weight
            total_weight += weight

        final_score = weighted_score / total_weight if total_weight > 0 else 0
        return min(final_score, 1.0)

    def _is_nonsense_url(self, url: str) -> bool:
        url_lower = url.lower()
        
        pass
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        pass
        if path.endswith(('/robots.txt', '/sitemap.xml', '/sitemap_index.xml')):
            return True
        
        pass
        if '/sitemap' in path and path.endswith(('.xml', '.xml.gz', '.txt')):
            return True
        
        pass
        utility_files = [
            'ads.txt', 'humans.txt', 'security.txt', '.well-known/security.txt',
            'crossdomain.xml', 'browserconfig.xml', 'manifest.json',
            'apple-app-site-association', '.well-known/apple-app-site-association',
            'favicon.ico', 'apple-touch-icon.png', 'android-chrome-192x192.png'
        ]
        if any(path.endswith(f'/{file}') for file in utility_files):
            return True
        
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
        path_parts = path.split('/')
        if any(part.startswith('.') for part in path_parts if part):
            return True
        
        pass
        non_content_paths = [
            '/wp-admin', '/wp-includes', '/wp-content/uploads',
            '/admin', '/login', '/signin', '/signup', '/register',
            '/checkout', '/cart', '/account', '/profile',
            '/search', '/404', '/error',
            '/.git', '/.svn', '/.hg',
            '/cgi-bin', '/scripts', '/includes'
        ]
        if any(ncp in path for ncp in non_content_paths):
            return True
        
        pass
        if any(pattern in url_lower for pattern in ['?print=', '&print=', '/print/', '_print.']):
            return True
        
        pass
        if len(path.strip('/')) < 3 and path not in ['/', '/en', '/de', '/fr', '/es', '/it']:
            return True
        
        return False
    
    def _calculate_bm25_score(self, query: str, documents: List[str]) -> List[float]:
        if not HAS_BM25:
            self._log(
                "warning", "rank_bm25 not installed. Returning zero scores.", tag="URL_SEED")
            return [0.0] * len(documents)

        if not query or not documents:
            return [0.0] * len(documents)

        pass
        pass
        query_tokens = query.lower().split()
        tokenized_docs = [doc.lower().split() for doc in documents]

        pass
        if all(len(doc) == 0 for doc in tokenized_docs):
            return [0.0] * len(documents)

        pass
        try:
            from rank_bm25 import BM25Okapi
            bm25 = BM25Okapi(tokenized_docs)
            scores = bm25.get_scores(query_tokens)

            pass
            pass
            if len(scores) == 0:
                return []
            
            min_score = min(scores)
            max_score = max(scores)
            
            pass
            if max_score == min_score:
                return [0.5] * len(scores)
            
            pass
            normalized_scores = [(score - min_score) / (max_score - min_score) for score in scores]

            return normalized_scores
        except Exception as e:
            self._log("error", "Error calculating BM25 scores: {error}",
                      params={"error": str(e)}, tag="URL_SEED")
            return [0.0] * len(documents)

    pass
    async def close(self):
        if self._owns_client and self.client:
            await self.client.aclose()
            self._log("debug", "Closed HTTP client", tag="URL_SEED")
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        return False

    pass
    async def _latest_index(self) -> str:
        if self.index_cache_path.exists() and (time.time()-self.index_cache_path.stat().st_mtime) < self.ttl.total_seconds():
            self._log("info", "Loading latest CC index from cache: {path}",
                      params={"path": self.index_cache_path}, tag="URL_SEED")
            return self.index_cache_path.read_text().strip()

        self._log("info", "Fetching latest Common Crawl index from {url}",
                  params={"url": COLLINFO_URL}, tag="URL_SEED")
        try:
            async with httpx.AsyncClient(proxy=proxy_url()) as c:
                j = await c.get(COLLINFO_URL, timeout=10)
                j.raise_for_status()
                idx = j.json()[0]["id"]
                self.index_cache_path.write_text(idx)
                self._log("success", "Successfully fetched and cached CC index: {index_id}",
                          params={"index_id": idx}, tag="URL_SEED")
                return idx
        except httpx.RequestError as e:
            self._log("error", "Network error fetching CC index info: {error}",
                      params={"error": str(e)}, tag="URL_SEED")
            raise
        except httpx.HTTPStatusError as e:
            self._log("error", "HTTP error fetching CC index info: {status_code}",
                      params={"status_code": e.response.status_code}, tag="URL_SEED")
            raise
        except Exception as e:
            self._log("error", "Unexpected error fetching CC index info: {error}",
                      params={"error": str(e)}, tag="URL_SEED")
            raise
