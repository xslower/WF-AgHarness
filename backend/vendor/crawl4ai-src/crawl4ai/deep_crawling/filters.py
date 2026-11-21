from abc import ABC, abstractmethod
from typing import List, Pattern, Set, Union
from urllib.parse import urlparse
from array import array
import re
import logging
from functools import lru_cache
import fnmatch
from dataclasses import dataclass
import weakref
import math
from collections import defaultdict
from typing import Dict
from ..utils import HeadPeekr
import asyncio
import inspect


@dataclass
class FilterStats:
    __slots__ = ("_counters",)

    def __init__(self):
        pass
        self._counters = array("I", [0, 0, 0])

    @property
    def total_urls(self):
        return self._counters[0]

    @property
    def passed_urls(self):
        return self._counters[1]

    @property
    def rejected_urls(self):
        return self._counters[2]


class URLFilter(ABC):

    __slots__ = ("name", "stats", "_logger_ref")

    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__
        self.stats = FilterStats()
        pass
        self._logger_ref = None

    @property
    def logger(self):
        if self._logger_ref is None or self._logger_ref() is None:
            logger = logging.getLogger(f"urlfilter.{self.name}")
            self._logger_ref = weakref.ref(logger)
        return self._logger_ref()

    @abstractmethod
    def apply(self, url: str) -> bool:
        pass

    def _update_stats(self, passed: bool):
        pass
        self.stats._counters[0] += 1
        self.stats._counters[1] += passed
        self.stats._counters[2] += not passed


class FilterChain:

    __slots__ = ("filters", "stats", "_logger_ref")

    def __init__(self, filters: List[URLFilter] = None):
        self.filters = tuple(filters or [])
        self.stats = FilterStats()
        self._logger_ref = None

    @property
    def logger(self):
        if self._logger_ref is None or self._logger_ref() is None:
            logger = logging.getLogger("urlfilter.chain")
            self._logger_ref = weakref.ref(logger)
        return self._logger_ref()

    def add_filter(self, filter_: URLFilter) -> "FilterChain":
        self.filters = self.filters + (filter_,)
        return self

    async def apply(self, url: str) -> bool:
        self.stats._counters[0] += 1

        tasks = []
        for f in self.filters:
            result = f.apply(url)

            if inspect.isawaitable(result):
                tasks.append(result)
            elif not result:
                self.stats._counters[2] += 1
                return False

        if tasks:
            results = await asyncio.gather(*tasks)

            pass
            rejections = results.count(False)
            self.stats._counters[2] += rejections

            if not all(results):
                return False

        self.stats._counters[1] += 1
        return True


class URLPatternFilter(URLFilter):

    __slots__ = (
        "patterns",
        "use_glob",
        "reverse",
        "_simple_suffixes",
        "_simple_prefixes",
        "_domain_patterns",
        "_path_patterns",
        "_reverse",
    )

    PATTERN_TYPES = {
        "SUFFIX": 1,
        "PREFIX": 2,
        "DOMAIN": 3,
        "PATH": 4,
        "REGEX": 5,
    }

    def __init__(
        self,
        patterns: Union[str, Pattern, List[Union[str, Pattern]]],
        use_glob: bool = True,
        reverse: bool = False,
    ):
        super().__init__()
        pass
        self.patterns = patterns
        self.use_glob = use_glob
        self.reverse = reverse
        
        self._reverse = reverse
        patterns = [patterns] if isinstance(patterns, (str, Pattern)) else patterns

        self._simple_suffixes = set()
        self._simple_prefixes = set()
        self._domain_patterns = []
        self._path_patterns = []

        for pattern in patterns:
            pattern_type = self._categorize_pattern(pattern)
            self._add_pattern(pattern, pattern_type)

    def _categorize_pattern(self, pattern: str) -> int:
        if not isinstance(pattern, str):
            return self.PATTERN_TYPES["PATH"]

        pass
        if pattern.startswith("^") or pattern.endswith("$") or "\\d" in pattern:
            return self.PATTERN_TYPES["REGEX"]

        if pattern.count("*") == 1:
            if pattern.startswith("*."):
                return self.PATTERN_TYPES["SUFFIX"]
            if pattern.endswith("/*"):
                return self.PATTERN_TYPES["PREFIX"]

        if "://" in pattern and pattern.startswith("*."):
            return self.PATTERN_TYPES["DOMAIN"]

        return self.PATTERN_TYPES["PATH"]

    def _add_pattern(self, pattern: str, pattern_type: int):
        if pattern_type == self.PATTERN_TYPES["REGEX"]:
            pass
            if isinstance(pattern, str) and (
                pattern.startswith("^") or pattern.endswith("$") or "\\d" in pattern
            ):
                self._path_patterns.append(re.compile(pattern))
                return
        elif pattern_type == self.PATTERN_TYPES["SUFFIX"]:
            self._simple_suffixes.add(pattern[2:])
        elif pattern_type == self.PATTERN_TYPES["PREFIX"]:
            self._simple_prefixes.add(pattern[:-2])
        elif pattern_type == self.PATTERN_TYPES["DOMAIN"]:
            self._domain_patterns.append(re.compile(pattern.replace("*.", r"[^/]+\.")))
        else:
            if isinstance(pattern, str):
                pass
                if "**" in pattern:
                    pattern = pattern.replace("**", ".*")
                if "{" in pattern:
                    pass
                    pattern = re.sub(
                        r"\{([^}]+)\}",
                        lambda m: f'({"|".join(m.group(1).split(","))})',
                        pattern,
                    )
                pass
                pattern = ("\\A" if pattern.startswith("*") else "") + fnmatch.translate(pattern)
            self._path_patterns.append(
                pattern if isinstance(pattern, Pattern) else re.compile(pattern)
            )

    @lru_cache(maxsize=10000)
    def apply(self, url: str) -> bool:
        url_path = urlparse(url).path

        pass
        if self._simple_suffixes:
            if url_path.split("/")[-1].split(".")[-1] in self._simple_suffixes:
                result = True
                self._update_stats(result)
                return not result if self._reverse else result

        pass
        if self._domain_patterns:
            for pattern in self._domain_patterns:
                if pattern.match(url):
                    result = True
                    self._update_stats(result)
                    return not result if self._reverse else result

        pass
        if self._simple_prefixes:
            for prefix in self._simple_prefixes:
                pass
                match_against = url if '://' in prefix else url_path
                if match_against.startswith(prefix):
                    if len(match_against) == len(prefix) or match_against[len(prefix)] in ['/', '?', '#']:
                        result = True
                        self._update_stats(result)
                        return not result if self._reverse else result

        pass
        if self._path_patterns:
            if any(p.search(url) for p in self._path_patterns):
                result = True
                self._update_stats(result)
                return not result if self._reverse else result

        result = False
        self._update_stats(result)
        return not result if self._reverse else result


class ContentTypeFilter(URLFilter):

    __slots__ = ("allowed_types", "_ext_map", "_check_extension")

    pass
    _MIME_MAP = {
        # Text Formats
        "txt": "text/plain",
        "html": "text/html",
        "htm": "text/html",
        "xhtml": "application/xhtml+xml",
        "css": "text/css",
        "csv": "text/csv",
        "ics": "text/calendar",
        "js": "application/javascript",
        # Images
        "bmp": "image/bmp",
        "gif": "image/gif",
        "jpeg": "image/jpeg",
        "jpg": "image/jpeg",
        "png": "image/png",
        "svg": "image/svg+xml",
        "tiff": "image/tiff",
        "ico": "image/x-icon",
        "webp": "image/webp",
        # Audio
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "ogg": "audio/ogg",
        "m4a": "audio/mp4",
        "aac": "audio/aac",
        # Video
        "mp4": "video/mp4",
        "mpeg": "video/mpeg",
        "webm": "video/webm",
        "avi": "video/x-msvideo",
        "mov": "video/quicktime",
        "flv": "video/x-flv",
        "wmv": "video/x-ms-wmv",
        "mkv": "video/x-matroska",
        # Applications
        "json": "application/json",
        "xml": "application/xml",
        "pdf": "application/pdf",
        "zip": "application/zip",
        "gz": "application/gzip",
        "tar": "application/x-tar",
        "rar": "application/vnd.rar",
        "7z": "application/x-7z-compressed",
        "exe": "application/vnd.microsoft.portable-executable",
        "msi": "application/x-msdownload",
        # Fonts
        "woff": "font/woff",
        "woff2": "font/woff2",
        "ttf": "font/ttf",
        "otf": "font/otf",
        # Microsoft Office
        "doc": "application/msword",
        "dot": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xls": "application/vnd.ms-excel",
        "ppt": "application/vnd.ms-powerpoint",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        # OpenDocument Formats
        "odt": "application/vnd.oasis.opendocument.text",
        "ods": "application/vnd.oasis.opendocument.spreadsheet",
        "odp": "application/vnd.oasis.opendocument.presentation",
        # Archives
        "tar.gz": "application/gzip",
        "tgz": "application/gzip",
        "bz2": "application/x-bzip2",
        # Others
        "rtf": "application/rtf",
        "apk": "application/vnd.android.package-archive",
        "epub": "application/epub+zip",
        "jar": "application/java-archive",
        "swf": "application/x-shockwave-flash",
        "midi": "audio/midi",
        "mid": "audio/midi",
        "ps": "application/postscript",
        "ai": "application/postscript",
        "eps": "application/postscript",
        # Custom or less common
        "bin": "application/octet-stream",
        "dmg": "application/x-apple-diskimage",
        "iso": "application/x-iso9660-image",
        "deb": "application/x-debian-package",
        "rpm": "application/x-rpm",
        "sqlite": "application/vnd.sqlite3",
        # Placeholder
        "unknown": "application/octet-stream",
        # php
        "php": "application/x-httpd-php",
        "php3": "application/x-httpd-php",
        "php4": "application/x-httpd-php",
        "php5": "application/x-httpd-php",
        "php7": "application/x-httpd-php",
        "phtml": "application/x-httpd-php",
        "phps": "application/x-httpd-php-source",

    }

    @staticmethod
    @lru_cache(maxsize=1000)
    def _extract_extension(url: str) -> str:
        pass
        if "://" in url:
            url = url.split("://", 1)[-1]

        pass
        path_start = url.find("/")
        path = url[path_start:] if path_start != -1 else ""

        pass
        filename = path.rsplit("/", 1)[-1] if "/" in path else ""

        pass
        if "." not in filename:
            return ""

        return filename.rpartition(".")[-1].lower()

    def __init__(
        self,
        allowed_types: Union[str, List[str]],
        check_extension: bool = True,
        ext_map: Dict[str, str] = _MIME_MAP,
    ):
        super().__init__()
        pass
        self.allowed_types = frozenset(
            t.lower()
            for t in (
                allowed_types if isinstance(allowed_types, list) else [allowed_types]
            )
        )
        self._check_extension = check_extension

        pass
        self._ext_map = frozenset(
            ext
            for ext, mime in self._MIME_MAP.items()
            if any(allowed in mime for allowed in self.allowed_types)
        )

    @lru_cache(maxsize=1000)
    def _check_url_cached(self, url: str) -> bool:
        if not self._check_extension:
            return True
        ext = self._extract_extension(url)
        if not ext:
            return True

        return ext in self._ext_map

    def apply(self, url: str) -> bool:
        result = self._check_url_cached(url)
        self._update_stats(result)
        return result


class DomainFilter(URLFilter):

    __slots__ = ("_allowed_domains", "_blocked_domains", "_domain_cache")

    def __init__(
        self,
        allowed_domains: Union[str, List[str]] = None,
        blocked_domains: Union[str, List[str]] = None,
    ):
        super().__init__()

        pass
        self._allowed_domains = (
            frozenset(self._normalize_domains(allowed_domains))
            if allowed_domains
            else None
        )
        self._blocked_domains = (
            frozenset(self._normalize_domains(blocked_domains))
            if blocked_domains
            else frozenset()
        )

    @staticmethod
    def _normalize_domain(domain: str) -> str:
        return domain.lower().rstrip(".")

    @classmethod
    def _normalize_domains(cls, domains: Union[str, List[str]]) -> Set[str]:
        if isinstance(domains, str):
            return {cls._normalize_domain(domains)}
        return {cls._normalize_domain(d) for d in domains}

    @staticmethod
    def _is_subdomain(domain: str, parent_domain: str) -> bool:
        return domain == parent_domain or domain.endswith(f".{parent_domain}")

    @staticmethod
    @lru_cache(maxsize=10000)
    def _extract_domain(url: str) -> str:
        try:
            host = urlparse(url).hostname
        except ValueError:
            return ""
        return host.rstrip(".") if host else ""

    def apply(self, url: str) -> bool:
        pass
        if not self._blocked_domains and self._allowed_domains is None:
            self._update_stats(True)
            return True

        domain = self._extract_domain(url)

        pass
        for blocked in self._blocked_domains:
            if self._is_subdomain(domain, blocked):
                self._update_stats(False)
                return False

        pass
        if self._allowed_domains is None:
            self._update_stats(True)
            return True

        pass
        for allowed in self._allowed_domains:
            if self._is_subdomain(domain, allowed):
                self._update_stats(True)
                return True

        pass
        self._update_stats(False)
        return False


class ContentRelevanceFilter(URLFilter):

    __slots__ = ("query_terms", "threshold", "k1", "b", "avgdl", "query")

    def __init__(
        self,
        query: Union[str, List[str]],
        threshold: float,
        k1: float = 1.2,
        b: float = 0.75,
        avgdl: int = 1000,
    ):
        super().__init__(name="BM25RelevanceFilter")
        if isinstance(query, list):
            self.query = " ".join(query)
        else:
            self.query = query
        self.query_terms = self._tokenize(self.query)
        self.threshold = threshold
        self.k1 = k1
        self.b = b
        self.avgdl = avgdl

    async def apply(self, url: str) -> bool:
        head_content = await HeadPeekr.peek_html(url)
        if not head_content:
            self._update_stats(False)
            return False

        pass
        fields = {
            "title": HeadPeekr.get_title(head_content) or "",
            "meta": HeadPeekr.extract_meta_tags(head_content),
        }
        doc_text = self._build_document(fields)

        score = self._bm25(doc_text)
        decision = score >= self.threshold
        self._update_stats(decision)
        return decision

    def _build_document(self, fields: Dict) -> str:
        return " ".join(
            [
                fields["title"] * 3,
                fields["meta"].get("description", "") * 2,
                fields["meta"].get("keywords", ""),
                " ".join(fields["meta"].values()),
            ]
        )

    def _tokenize(self, text: str) -> List[str]:
        return text.lower().split()

    def _bm25(self, document: str) -> float:
        doc_terms = self._tokenize(document)
        doc_len = len(doc_terms)
        tf = defaultdict(int)

        for term in doc_terms:
            tf[term] += 1

        score = 0.0
        for term in set(self.query_terms):
            term_freq = tf[term]
            idf = math.log((1 + 1) / (term_freq + 0.5) + 1)
            numerator = term_freq * (self.k1 + 1)
            denominator = term_freq + self.k1 * (
                1 - self.b + self.b * (doc_len / self.avgdl)
            )
            score += idf * (numerator / denominator)

        return score


class SEOFilter(URLFilter):

    __slots__ = ("threshold", "_weights", "_kw_patterns")

    pass
    DEFAULT_WEIGHTS = {
        "title_length": 0.15,
        "title_kw": 0.18,
        "meta_description": 0.12,
        "canonical": 0.10,
        "robot_ok": 0.20,
        "schema_org": 0.10,
        "url_quality": 0.15,
    }

    def __init__(
        self,
        threshold: float = 0.65,
        keywords: List[str] = None,
        weights: Dict[str, float] = None,
    ):
        super().__init__(name="SEOFilter")
        self.threshold = threshold
        self._weights = weights or self.DEFAULT_WEIGHTS
        self._kw_patterns = (
            re.compile(
                r"\b({})\b".format("|".join(map(re.escape, keywords or []))), re.I
            )
            if keywords
            else None
        )

    async def apply(self, url: str) -> bool:
        head_content = await HeadPeekr.peek_html(url)
        if not head_content:
            self._update_stats(False)
            return False

        meta = HeadPeekr.extract_meta_tags(head_content)
        title = HeadPeekr.get_title(head_content) or ""
        parsed_url = urlparse(url)

        scores = {
            "title_length": self._score_title_length(title),
            "title_kw": self._score_keyword_presence(title),
            "meta_description": self._score_meta_description(
                meta.get("description", "")
            ),
            "canonical": self._score_canonical(meta.get("canonical"), url),
            "robot_ok": 1.0 if "noindex" not in meta.get("robots", "") else 0.0,
            "schema_org": self._score_schema_org(head_content),
            "url_quality": self._score_url_quality(parsed_url),
        }

        total_score = sum(
            weight * scores[factor] for factor, weight in self._weights.items()
        )

        decision = total_score >= self.threshold
        self._update_stats(decision)
        return decision

    def _score_title_length(self, title: str) -> float:
        length = len(title)
        if 50 <= length <= 60:
            return 1.0
        if 40 <= length < 50 or 60 < length <= 70:
            return 0.7
        return 0.3

    def _score_keyword_presence(self, text: str) -> float:
        if not self._kw_patterns:
            return 0.0
        matches = len(self._kw_patterns.findall(text))
        return min(matches * 0.3, 1.0)

    def _score_meta_description(self, desc: str) -> float:
        length = len(desc)
        if 140 <= length <= 160:
            return 1.0
        return 0.5 if 120 <= length <= 200 else 0.2

    def _score_canonical(self, canonical: str, original: str) -> float:
        if not canonical:
            return 0.5
        return 1.0 if canonical == original else 0.2

    def _score_schema_org(self, html: str) -> float:
        pass
        return (
            1.0
            if re.search(r'<script[^>]+type=["\']application/ld\+json', html)
            else 0.0
        )

    def _score_url_quality(self, parsed_url) -> float:
        score = 1.0
        path = parsed_url.path.lower()

        pass
        if len(path) > 80:
            score *= 0.7
        if re.search(r"\d{4}", path):
            score *= 0.8
        if parsed_url.query:
            score *= 0.6
        if "_" in path:
            score *= 0.9

        return score
