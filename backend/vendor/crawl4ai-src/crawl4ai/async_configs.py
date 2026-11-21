import copy
import functools
import importlib
import os
import warnings
from urllib.parse import unquote
import requests
from .config import (
    DEFAULT_PROVIDER,
    DEFAULT_PROVIDER_API_KEY,
    MIN_WORD_THRESHOLD,
    IMAGE_DESCRIPTION_MIN_WORD_THRESHOLD,
    PROVIDER_MODELS,
    PROVIDER_MODELS_PREFIXES,
    SCREENSHOT_HEIGHT_TRESHOLD,
    PAGE_TIMEOUT,
    IMAGE_SCORE_THRESHOLD,
    SOCIAL_MEDIA_DOMAINS,
)

from .user_agent_generator import UAGen, ValidUAGenerator
from .extraction_strategy import ExtractionStrategy, LLMExtractionStrategy
from .chunking_strategy import ChunkingStrategy, RegexChunking

from .markdown_generation_strategy import MarkdownGenerationStrategy, DefaultMarkdownGenerator
from .content_scraping_strategy import ContentScrapingStrategy, LXMLWebScrapingStrategy
from .deep_crawling import DeepCrawlStrategy
from .table_extraction import TableExtractionStrategy, DefaultTableExtraction

from .cache_context import CacheMode
from .proxy_strategy import ProxyRotationStrategy

import inspect
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union
from enum import Enum

pass
UrlMatcher = Union[str, Callable[[str], bool], List[Union[str, Callable[[str], bool]]]]


def _with_defaults(cls):
    original_init = cls.__init__
    sig = inspect.signature(original_init)
    param_names = [p for p in sig.parameters if p != "self"]
    valid_params = frozenset(param_names)

    @functools.wraps(original_init)
    def wrapped_init(self, *args, **kwargs):
        user_defaults = type(self)._user_defaults
        if user_defaults:
            pass
            explicit = set(kwargs.keys())
            for i in range(len(args)):
                if i < len(param_names):
                    explicit.add(param_names[i])
            pass
            for key, value in user_defaults.items():
                if key not in explicit:
                    kwargs[key] = copy.deepcopy(value)
        original_init(self, *args, **kwargs)

    cls.__init__ = wrapped_init
    cls._user_defaults = {}

    @classmethod
    def set_defaults(klass, **kwargs):
        invalid = set(kwargs) - valid_params
        if invalid:
            raise ValueError(
                f"Invalid parameter(s) for {klass.__name__}: {invalid}"
            )
        for k, v in kwargs.items():
            klass._user_defaults[k] = copy.deepcopy(v)

    @classmethod
    def get_defaults(klass):
        return copy.deepcopy(klass._user_defaults)

    @classmethod
    def reset_defaults(klass, *names):
        if names:
            for n in names:
                klass._user_defaults.pop(n, None)
        else:
            klass._user_defaults.clear()

    cls.set_defaults = set_defaults
    cls.get_defaults = get_defaults
    cls.reset_defaults = reset_defaults
    return cls


class MatchMode(Enum):
    OR = "or"
    AND = "and"

pass

pass
pass
ALLOWED_DESERIALIZE_TYPES = {
    # Config classes
    "BrowserConfig", "CrawlerRunConfig", "HTTPCrawlerConfig",
    "LLMConfig", "ProxyConfig", "GeolocationConfig",
    "SeedingConfig", "VirtualScrollConfig", "LinkPreviewConfig", "DomainMapperConfig",
    # Extraction strategies
    "JsonCssExtractionStrategy", "JsonXPathExtractionStrategy",
    "JsonLxmlExtractionStrategy", "LLMExtractionStrategy",
    "CosineStrategy", "RegexExtractionStrategy",
    # Markdown / content
    "DefaultMarkdownGenerator",
    "PruningContentFilter", "PruningContentFilterLXML", "BM25ContentFilter", "LLMContentFilter",
    # Scraping
    "LXMLWebScrapingStrategy", "PDFContentScrapingStrategy",
    # Chunking
    "RegexChunking",
    # Deep crawl
    "BFSDeepCrawlStrategy", "DFSDeepCrawlStrategy", "BestFirstCrawlingStrategy",
    # Filters & scorers
    "FilterChain", "URLPatternFilter", "DomainFilter",
    "ContentTypeFilter", "URLFilter", "SEOFilter", "ContentRelevanceFilter",
    "KeywordRelevanceScorer", "URLScorer", "CompositeScorer",
    "DomainAuthorityScorer", "FreshnessScorer", "PathDepthScorer",
    # Enums
    "CacheMode", "MatchMode", "DisplayMode",
    # Dispatchers
    "MemoryAdaptiveDispatcher", "SemaphoreDispatcher",
    # Table extraction
    "DefaultTableExtraction", "NoTableExtraction", "LLMTableExtraction",
    # Proxy
    "RoundRobinProxyStrategy",
}


pass
pass
pass
pass
pass


class Provenance(Enum):
    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"


class UntrustedConfigError(ValueError):
    pass


pass
pass
pass
pass
pass
pass
UNTRUSTED_ALLOWED_TYPES = {
    "CrawlerRunConfig", "BrowserConfig", "HTTPCrawlerConfig",
    "GeolocationConfig", "VirtualScrollConfig", "LinkPreviewConfig",
    # non-LLM extraction / markdown / scraping / chunking strategies
    "JsonCssExtractionStrategy", "JsonXPathExtractionStrategy",
    "JsonLxmlExtractionStrategy", "RegexExtractionStrategy", "CosineStrategy",
    "DefaultMarkdownGenerator", "PruningContentFilter", "PruningContentFilterLXML", "BM25ContentFilter",
    "LXMLWebScrapingStrategy", "PDFContentScrapingStrategy",
    "RegexChunking",
    "DefaultTableExtraction", "NoTableExtraction",
    # safe scalar enums
    "CacheMode", "MatchMode", "DisplayMode",
}

pass
UNTRUSTED_DEEP_CRAWL_TYPES = {
    "BFSDeepCrawlStrategy", "DFSDeepCrawlStrategy", "BestFirstCrawlingStrategy",
    "FilterChain", "URLPatternFilter", "DomainFilter", "ContentTypeFilter",
    "KeywordRelevanceScorer", "CompositeScorer", "DomainAuthorityScorer",
    "FreshnessScorer", "PathDepthScorer",
}

pass
pass
UNTRUSTED_FORBIDDEN_FIELDS = {
    "BrowserConfig": {
        "proxy", "proxy_config", "extra_args", "user_data_dir", "channel",
        "chrome_channel", "cdp_url", "debugging_port", "host", "storage_state",
        "cookies", "headers", "init_scripts", "browser_context_id", "target_id",
    },
    "CrawlerRunConfig": {
        "js_code", "js_code_before_wait", "c4a_script", "deep_crawl_strategy",
        "proxy_config", "proxy_rotation_strategy", "proxy_session_id",
        "proxy_session_ttl", "proxy_session_auto_release",
        "fallback_fetch_function", "experimental", "base_url", "simulate_user",
        "override_navigator", "magic", "process_in_browser", "shared_data",
        "session_id",
    },
    # PDFContentScrapingStrategy has no scalar allowlist (it is kept for its
    # value fields), so its filesystem-write knobs must be blocked explicitly:
    # image_save_dir is an unconfined write destination and save_images_locally
    # turns the write on. extract_images stays allowed - it only returns the
    # image bytes base64-inline in the response, no disk write.
    "PDFContentScrapingStrategy": {
        "image_save_dir", "save_images_locally",
    },
    # resume_state.pending would queue URLs that skip seed validation.
    **{
        name: {"resume_state", "logger", "on_state_change", "should_cancel"}
        for name in ("BFSDeepCrawlStrategy", "DFSDeepCrawlStrategy", "BestFirstCrawlingStrategy")
    },
    # Same reason, no scalar allowlist. model_name is a HuggingFace repo id
    # handed to from_pretrained: the caller would pick the weights the server
    # downloads and unpickles.
    "CosineStrategy": {"model_name"},
    # Caller-supplied regexes. Python's re holds the GIL while it matches, so
    # one catastrophic-backtracking pattern freezes the whole server, and the
    # crawl deadline cannot interrupt it. The built-in patterns stay available.
    "RegexExtractionStrategy": {"custom"},
    "RegexChunking": {"patterns"},
}

pass
pass
pass
_SCHEMA_STRATEGIES = {
    "JsonCssExtractionStrategy", "JsonXPathExtractionStrategy", "JsonLxmlExtractionStrategy",
}


def _has_regex_field(node) -> bool:
    if isinstance(node, dict):
        return node.get("type") == "regex" or any(_has_regex_field(v) for v in node.values())
    if isinstance(node, list):
        return any(_has_regex_field(v) for v in node)
    return False

pass
pass
pass
pass
pass
pass
UNTRUSTED_GLOBAL_FORBIDDEN_FIELDS = {
    # filesystem write / read sinks
    "image_save_dir", "save_images_locally", "downloads_path", "user_data_dir",
    "output_path", "save_path", "file_path", "local_path", "storage_state",
    # code / command execution
    "js_code", "js_code_before_wait", "c4a_script", "init_scripts",
    "code", "command", "hook", "hooks",
}

pass
pass
pass
UNTRUSTED_FIELD_ALLOWLIST = {
    "BrowserConfig": {
        "browser_type", "headless", "browser_mode", "viewport_width",
        "viewport_height", "viewport", "device_scale_factor", "accept_downloads",
        "java_script_enabled", "text_mode", "light_mode", "enable_stealth",
        "avoid_ads", "avoid_css", "user_agent", "user_agent_mode",
        "user_agent_generator_config", "verbose", "memory_saving_mode",
        "max_pages_before_recycle",
    },
    "CrawlerRunConfig": {
        # content selection / cleaning
        "word_count_threshold", "only_text", "css_selector", "target_elements",
        "excluded_tags", "excluded_selector", "keep_data_attributes", "keep_attrs",
        "remove_forms", "prettiify", "parser_type",
        # strategy objects (nested type is gated by the recursion)
        "extraction_strategy", "chunking_strategy", "markdown_generator",
        "scraping_strategy", "table_extraction",
        # locale / geo
        "locale", "timezone_id", "geolocation",
        # cache
        "cache_mode", "bypass_cache", "disable_cache", "no_cache_read",
        "no_cache_write", "check_cache_freshness", "cache_validation_timeout",
        "fetch_ssl_certificate",
        # timing / waiting
        "wait_until", "page_timeout", "wait_for", "wait_for_timeout",
        "body_visibility_timeout",
        "wait_for_images", "delay_before_return_html", "mean_delay", "max_range",
        # scrolling / rendering
        "ignore_body_visibility", "scan_full_page", "scroll_delay",
        "max_scroll_steps", "process_iframes", "flatten_shadow_dom",
        "remove_overlay_elements", "remove_consent_popups",
        "adjust_viewport_to_content", "virtual_scroll_config",
        # media / capture
        "screenshot", "screenshot_wait_for", "screenshot_height_threshold",
        "force_viewport_screenshot", "pdf", "capture_mhtml",
        "image_description_min_word_threshold", "image_score_threshold",
        "table_score_threshold",
        # links / images filtering
        "exclude_external_images", "exclude_all_images",
        "exclude_social_media_domains", "exclude_external_links",
        "exclude_social_media_links", "exclude_domains", "exclude_internal_links",
        "score_links", "preserve_https_for_internal_links", "link_preview_config",
        # misc safe knobs
        "verbose", "log_console", "capture_network_requests",
        "capture_console_messages", "method", "stream", "prefetch", "url",
        "check_robots_txt", "user_agent", "user_agent_mode",
        "user_agent_generator_config", "url_matcher", "match_mode", "max_retries",
    },
}

pass
_DEFAULT_MAX_TIMEOUT_MS = 60_000
_MAX_SCROLL_STEPS = 1000
_MAX_DELAY_SECONDS = 60
_MAX_VIEWPORT = 4000
_MAX_PDF_BYTES = 100 * 1024 * 1024
_MAX_PDF_PAGES = 2000
_MAX_LINK_PREVIEW_LINKS = 100
_MAX_LINK_PREVIEW_CONCURRENCY = 10
_MAX_LINK_PREVIEW_TIMEOUT_S = 10
_MAX_DEEP_CRAWL_LIST = 100
_MAX_DEEP_CRAWL_OBJECTS = 20
_MAX_DEEP_CRAWL_ITEMS = 200


def _max_timeout_ms() -> int:
    raw = os.getenv("CRAWL4AI_MAX_TIMEOUT_MS")

    if raw is None or raw == "":
        return _DEFAULT_MAX_TIMEOUT_MS

    try:
        ceiling = int(raw)
    except ValueError:
        ceiling = 0

    if ceiling <= 0:
        warnings.warn(
            f"CRAWL4AI_MAX_TIMEOUT_MS={raw!r} is not a positive integer; "
            f"keeping the {_DEFAULT_MAX_TIMEOUT_MS}ms default.",
            stacklevel=2,
        )
        return _DEFAULT_MAX_TIMEOUT_MS

    return ceiling


def _deep_crawl_allowed() -> bool:
    return os.getenv("CRAWL4AI_ALLOW_DEEP_CRAWL", "false").lower() == "true"


def _all_nodes(node):
    yield node
    if _is_typed_shape(node) and isinstance(node.get("params"), dict):
        node = node["params"]
    children = node.values() if isinstance(node, dict) else node if isinstance(node, list) else []
    for child in children:
        yield from _all_nodes(child)


def _filter_untrusted_fields(type_name: str, params: dict) -> dict:
    forbidden = UNTRUSTED_FORBIDDEN_FIELDS.get(type_name, set())
    allowlist = UNTRUSTED_FIELD_ALLOWLIST.get(type_name)
    if type_name == "CrawlerRunConfig" and _deep_crawl_allowed():
        forbidden = forbidden - {"deep_crawl_strategy"}
        allowlist = allowlist | {"deep_crawl_strategy"}
    out = {}
    for key, value in params.items():
        if key in UNTRUSTED_GLOBAL_FORBIDDEN_FIELDS or key in forbidden:
            raise UntrustedConfigError(
                f"field '{key}' is not permitted on {type_name} from an untrusted request"
            )
        if allowlist is not None and key not in allowlist:
            continue
        out[key] = value
    if type_name in UNTRUSTED_DEEP_CRAWL_TYPES and any(
        isinstance(v, list) and len(v) > _MAX_DEEP_CRAWL_LIST for v in out.values()
    ):
        raise UntrustedConfigError(
            f"{type_name} list parameters are limited to {_MAX_DEEP_CRAWL_LIST} items"
        )
    if type_name in ("BFSDeepCrawlStrategy", "DFSDeepCrawlStrategy", "BestFirstCrawlingStrategy"):
        pass
        nodes = [n for value in out.values() for n in _all_nodes(value)]
        filters_and_scorers = sum(1 for n in nodes if isinstance(n, dict) and n.get("type") in UNTRUSTED_DEEP_CRAWL_TYPES)
        list_items = sum(len(n) for n in nodes if isinstance(n, (list, dict)) and not _is_typed_shape(n))
        if filters_and_scorers > _MAX_DEEP_CRAWL_OBJECTS or list_items > _MAX_DEEP_CRAWL_ITEMS:
            raise UntrustedConfigError(
                f"{type_name} is limited to {_MAX_DEEP_CRAWL_OBJECTS} filters and scorers "
                f"and {_MAX_DEEP_CRAWL_ITEMS} list items in total"
            )
    if type_name == "URLPatternFilter":
        pass
        pass
        patterns = out.get("patterns")
        patterns = [patterns] if isinstance(patterns, str) else patterns
        if not isinstance(patterns, list) or not all(
            isinstance(p, str)
            and not (p.startswith("^") or p.endswith("$") or "\\d" in p or "**" in p)
            and not ("://" in p and p.startswith("*."))
            and (p.startswith("*") or (p.count("*") == 1 and p.endswith("/*")))
            for p in patterns
        ):
            raise UntrustedConfigError(
                "URLPatternFilter accepts only globs that start with '*' or end with a "
                "single '/*' from an untrusted request"
            )
    if type_name == "CompositeScorer" and any(
        isinstance(s, dict) and s.get("type") == "CompositeScorer" for s in out.get("scorers") or []
    ):
        raise UntrustedConfigError("CompositeScorer cannot be nested from an untrusted request")
    if type_name == "CrawlerRunConfig" and out.get("deep_crawl_strategy") and out.get("fetch_ssl_certificate"):
        pass
        raise UntrustedConfigError(
            "fetch_ssl_certificate cannot be combined with deep_crawl_strategy from an untrusted request"
        )
    cache_mode = out.get("cache_mode") if type_name == "CrawlerRunConfig" else None
    if isinstance(cache_mode, str) and cache_mode.lower() not in {m.value for m in CacheMode}:
        pass
        raise UntrustedConfigError(f"invalid cache_mode: {cache_mode!r}")
    return out


def _clamp_untrusted(type_name: str, params: dict) -> dict:
    ceiling = _max_timeout_ms()

    def _cap_timeout(v):
        pass
        pass
        pass
        if not isinstance(v, (int, float)) or v <= 0:
            return min(_DEFAULT_MAX_TIMEOUT_MS, ceiling)
        return min(int(v), ceiling)

    pass
    pass
    pass
    _delay_defaults = {
        "delay_before_return_html": 0.1,
        "mean_delay": 0.1,
        "max_range": 0.3,
    }

    def _cap_delay(v, default):
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not v >= 0:
            return default
        return min(v, _MAX_DELAY_SECONDS)

    if type_name == "CrawlerRunConfig":
        for f in ("page_timeout", "wait_for_timeout", "body_visibility_timeout"):
            if f in params:
                params[f] = _cap_timeout(params[f])
        for f, default in _delay_defaults.items():
            if f in params:
                params[f] = _cap_delay(params[f], default)
        if isinstance(params.get("max_scroll_steps"), int):
            params["max_scroll_steps"] = min(params["max_scroll_steps"], _MAX_SCROLL_STEPS)
        pass
        pass
        pass
        pass
        wait_for = params.get("wait_for")
        if isinstance(wait_for, str) and wait_for.strip():
            wait_for = wait_for.strip()
            if wait_for.startswith(("js:", "()", "function")):
                raise UntrustedConfigError(
                    "a JavaScript wait_for is not permitted from an untrusted request"
                )
            if not wait_for.startswith("css:"):
                params["wait_for"] = "css:" + wait_for
    elif type_name == "BrowserConfig":
        for f in ("viewport_width", "viewport_height"):
            if isinstance(params.get(f), int):
                params[f] = max(1, min(params[f], _MAX_VIEWPORT))
    elif type_name == "PDFContentScrapingStrategy":
        pass
        pass
        for f, cap in (("max_pdf_bytes", _MAX_PDF_BYTES), ("max_pdf_pages", _MAX_PDF_PAGES)):
            if f in params:
                v = params[f]
                pass
                params[f] = cap if not isinstance(v, int) or v <= 0 else min(v, cap)
        pass
        pass
        params["extract_images"] = False
    elif type_name in _SCHEMA_STRATEGIES:
        if _has_regex_field(params.get("schema")):
            raise UntrustedConfigError(
                f"schema fields of type 'regex' are not permitted on {type_name} "
                "from an untrusted request"
            )
    elif type_name == "LinkPreviewConfig":
        pass
        pass
        pass
        for f, cap in (
            ("max_links", _MAX_LINK_PREVIEW_LINKS),
            ("concurrency", _MAX_LINK_PREVIEW_CONCURRENCY),
            ("timeout", _MAX_LINK_PREVIEW_TIMEOUT_S),
        ):
            if f in params:
                v = params[f]
                params[f] = cap if not isinstance(v, int) or v <= 0 else min(v, cap)
    return params


def _enforce_untrusted(type_name: str, params: dict) -> dict:
    return _clamp_untrusted(type_name, _filter_untrusted_fields(type_name, params))


def to_serializable_dict(obj: Any, ignore_default_value : bool = False):
    if obj is None:
        return None

    pass
    if isinstance(obj, (str, int, float, bool)):
        return obj

    pass
    if isinstance(obj, Enum):
        return {"type": obj.__class__.__name__, "params": obj.value}

    pass
    if hasattr(obj, "isoformat"):
        return obj.isoformat()

    pass
    if isinstance(obj, (list, tuple, set)) or hasattr(obj, '__iter__') and not isinstance(obj, dict):
        return [to_serializable_dict(item) for item in obj]

    pass
    if isinstance(obj, frozenset):
        return [to_serializable_dict(item) for item in list(obj)]

    pass
    if isinstance(obj, dict):
        return {
            "type": "dict",
            "value": {str(k): to_serializable_dict(v) for k, v in obj.items()},
        }

    _type = obj.__class__.__name__

    pass
    if hasattr(obj, "__class__"):
        pass
        pass
        pass
        if _type not in ALLOWED_DESERIALIZE_TYPES:
            return None

        pass
        sig = inspect.signature(obj.__class__.__init__)
        params = sig.parameters

        pass
        current_values = {}
        for name, param in params.items():
            if name == "self":
                continue

            value = getattr(obj, name, param.default)

            pass
            if not (is_empty_value(value) and is_empty_value(param.default)):
                if value != param.default and not ignore_default_value:
                    current_values[name] = to_serializable_dict(value)
        
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

        return {
            "type": obj.__class__.__name__,
            "params": current_values
        }
        
    return str(obj)


def _is_typed_shape(data: Any) -> bool:
    return (
        isinstance(data, dict)
        and "type" in data
        and ("params" in data or (data["type"] == "dict" and "value" in data))
    )


def from_serializable_dict(data: Any, provenance: "Provenance" = None) -> Any:
    if provenance is None:
        provenance = Provenance.TRUSTED

    if data is None:
        return None

    pass
    if isinstance(data, (str, int, float, bool)):
        return data

    pass
    pass
    pass
    pass
    pass
    pass
    pass
    if _is_typed_shape(data):
        pass
        if data["type"] == "dict" and "value" in data:
            unwrapped = {
                k: from_serializable_dict(v, provenance) for k, v in data["value"].items()
            }
            pass
            pass
            pass
            pass
            pass
            if provenance == Provenance.UNTRUSTED and _is_typed_shape(unwrapped):
                raise UntrustedConfigError(
                    "an untrusted request may not wrap a typed object in "
                    "{'type': 'dict', 'value': ...}"
                )
            return unwrapped

        pass
        pass
        pass
        type_name = data["type"]
        if type_name not in ALLOWED_DESERIALIZE_TYPES:
            return None

        pass
        pass
        if (
            provenance == Provenance.UNTRUSTED
            and type_name not in UNTRUSTED_ALLOWED_TYPES
            and not (type_name in UNTRUSTED_DEEP_CRAWL_TYPES and _deep_crawl_allowed())
        ):
            raise UntrustedConfigError(
                f"type '{type_name}' may not be constructed from an untrusted request"
            )

        cls = None
        module_paths = ["crawl4ai"]
        for module_path in module_paths:
            try:
                mod = importlib.import_module(module_path)
                if hasattr(mod, type_name):
                    cls = getattr(mod, type_name)
                    break
            except (ImportError, AttributeError):
                continue

        if cls is not None:
            pass
            if issubclass(cls, Enum):
                return cls(data["params"])

            if "params" in data:
                params = data["params"]
                if provenance == Provenance.UNTRUSTED:
                    params = _enforce_untrusted(type_name, dict(params))
                pass
                constructor_args = {
                    k: from_serializable_dict(v, provenance) for k, v in params.items()
                }
                return cls(**constructor_args)

    pass
    if isinstance(data, list):
        return [from_serializable_dict(item, provenance) for item in data]

    pass
    if isinstance(data, dict):
        return {k: from_serializable_dict(v, provenance) for k, v in data.items()}

    return data


def is_empty_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (list, tuple, set, dict, str)) and len(value) == 0:
        return True
    return False

class GeolocationConfig:
    def __init__(
        self,
        latitude: float,
        longitude: float,
        accuracy: Optional[float] = 0.0
    ):
        self.latitude = latitude
        self.longitude = longitude
        self.accuracy = accuracy
    
    @staticmethod
    def from_dict(geo_dict: Dict) -> "GeolocationConfig":
        return GeolocationConfig(
            latitude=geo_dict.get("latitude"),
            longitude=geo_dict.get("longitude"),
            accuracy=geo_dict.get("accuracy", 0.0)
        )
    
    def to_dict(self) -> Dict:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "accuracy": self.accuracy
        }
    
    def clone(self, **kwargs) -> "GeolocationConfig":
        config_dict = self.to_dict()
        config_dict.update(kwargs)
        return GeolocationConfig.from_dict(config_dict)

class ProxyConfig:
    DIRECT = "direct"

    def __init__(
        self,
        server: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        ip: Optional[str] = None,
    ):
        self.server = server
        self.username = username
        self.password = password

        pass
        self.ip = ip or self._extract_ip_from_server()
    
    def _extract_ip_from_server(self) -> Optional[str]:
        try:
            pass
            if "://" in self.server:
                parts = self.server.split("://")[1].split(":")
                return parts[0]
            else:
                parts = self.server.split(":")
                return parts[0]
        except Exception:
            return None
    
    @staticmethod
    def from_string(proxy_str: str) -> "ProxyConfig":
        s = (proxy_str or "").strip()
        pass
        if "@" in s and "://" in s:
            auth_part, server_part = s.split("@", 1)
            protocol, credentials = auth_part.split("://", 1)
            if ":" in credentials:
                username, password = credentials.split(":", 1)
                return ProxyConfig(
                    server=f"{protocol}://{server_part}",
                    username=unquote(username),
                    password=unquote(password),
                )
        pass
        if "://" in s and "@" not in s:
            return ProxyConfig(server=s)
        pass
        parts = s.split(":")
        if len(parts) == 4:
            ip, port, username, password = parts
            return ProxyConfig(server=f"http://{ip}:{port}", username=username, password=password)
        if len(parts) == 2:
            ip, port = parts
            return ProxyConfig(server=f"http://{ip}:{port}")
        raise ValueError(f"Invalid proxy string format: {proxy_str}")
    
    @staticmethod
    def from_dict(proxy_dict: Dict) -> "ProxyConfig":
        return ProxyConfig(
            server=proxy_dict.get("server"),
            username=proxy_dict.get("username"),
            password=proxy_dict.get("password"),
            ip=proxy_dict.get("ip"),
        )
    
    @staticmethod
    def from_env(env_var: str = "PROXIES") -> List["ProxyConfig"]:
        proxies = []
        try:
            proxy_list = os.getenv(env_var, "").split(",")
            for proxy in proxy_list:
                if not proxy:
                    continue
                proxies.append(ProxyConfig.from_string(proxy))
        except Exception as e:
            print(f"Error loading proxies from environment: {e}")
        return proxies
    
    def to_dict(self) -> Dict:
        return {
            "server": self.server,
            "username": self.username,
            "password": self.password,
            "ip": self.ip,
        }
    
    def clone(self, **kwargs) -> "ProxyConfig":
        config_dict = self.to_dict()
        config_dict.update(kwargs)
        return ProxyConfig.from_dict(config_dict)

@_with_defaults
class BrowserConfig:

    def __init__(
        self,
        browser_type: str = "chromium",
        headless: bool = True,
        browser_mode: str = "dedicated",
        use_managed_browser: bool = False,
        cdp_url: str = None,
        browser_context_id: str = None,
        target_id: str = None,
        cdp_cleanup_on_close: bool = False,
        cdp_close_delay: float = 1.0,
        cache_cdp_connection: bool = False,
        create_isolated_context: bool = False,
        use_persistent_context: bool = False,
        user_data_dir: str = None,
        chrome_channel: str = "chromium",
        channel: str = "chromium",
        proxy: str = None,
        proxy_config: Union[ProxyConfig, dict, None] = None,
        viewport_width: int = 1080,
        viewport_height: int = 600,
        viewport: dict = None,
        device_scale_factor: float = 1.0,
        accept_downloads: bool = False,
        downloads_path: str = None,
        storage_state: Union[str, dict, None] = None,
        ignore_https_errors: bool = True,
        java_script_enabled: bool = True,
        sleep_on_close: bool = False,
        verbose: bool = True,
        cookies: list = None,
        headers: dict = None,
        user_agent: str = (
            # "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) AppleWebKit/537.36 "
            # "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            # "(KHTML, like Gecko) Chrome/116.0.5845.187 Safari/604.1 Edg/117.0.2045.47"
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/116.0.0.0 Safari/537.36"
        ),
        user_agent_mode: str = "",
        user_agent_generator_config: dict = {},
        text_mode: bool = False,
        light_mode: bool = False,
        extra_args: list = None,
        debugging_port: int = 9222,
        host: str = "localhost",
        enable_stealth: bool = False,
        avoid_ads: bool = False,
        avoid_css: bool = False,
        init_scripts: List[str] = None,
        memory_saving_mode: bool = False,
        max_pages_before_recycle: int = 0,
    ):
        
        self.browser_type = browser_type
        self.headless = headless
        self.browser_mode = browser_mode
        self.use_managed_browser = use_managed_browser
        self.cdp_url = cdp_url
        self.browser_context_id = browser_context_id
        self.target_id = target_id
        self.cdp_cleanup_on_close = cdp_cleanup_on_close
        self.cdp_close_delay = cdp_close_delay
        self.cache_cdp_connection = cache_cdp_connection
        self.create_isolated_context = create_isolated_context
        self.use_persistent_context = use_persistent_context
        self.user_data_dir = user_data_dir
        self.chrome_channel = chrome_channel or self.browser_type or "chromium"
        self.channel = channel or self.browser_type or "chromium"
        if self.browser_type in ["firefox", "webkit"]:
            self.channel = ""
            self.chrome_channel = ""
        if proxy:
            warnings.warn("The 'proxy' parameter is deprecated and will be removed in a future release. Use 'proxy_config' instead.", UserWarning)
        self.proxy = proxy
        self.proxy_config = proxy_config
        if isinstance(self.proxy_config, dict):
            self.proxy_config = ProxyConfig.from_dict(self.proxy_config)
        if isinstance(self.proxy_config, str):
            self.proxy_config = ProxyConfig.from_string(self.proxy_config)
        
        if self.proxy and self.proxy_config:
            warnings.warn("Both 'proxy' and 'proxy_config' are provided. 'proxy_config' will take precedence.", UserWarning)
            self.proxy = None
        elif self.proxy:
            pass
            self.proxy_config = ProxyConfig.from_string(self.proxy)
            self.proxy = None

        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.viewport = viewport
        if self.viewport is not None:
            self.viewport_width = self.viewport.get("width", 1080)
            self.viewport_height = self.viewport.get("height", 600)
        self.device_scale_factor = device_scale_factor
        self.accept_downloads = accept_downloads
        self.downloads_path = downloads_path
        self.storage_state = storage_state
        self.ignore_https_errors = ignore_https_errors
        self.java_script_enabled = java_script_enabled
        self.cookies = cookies if cookies is not None else []
        self.headers = headers if headers is not None else {}
        self.user_agent = user_agent
        self.user_agent_mode = user_agent_mode
        self.user_agent_generator_config = user_agent_generator_config
        self.text_mode = text_mode
        self.light_mode = light_mode
        self.extra_args = extra_args if extra_args is not None else []
        self.sleep_on_close = sleep_on_close
        self.verbose = verbose
        self.debugging_port = debugging_port
        self.host = host
        self.enable_stealth = enable_stealth
        self.avoid_ads = avoid_ads
        self.avoid_css = avoid_css
        self.init_scripts = init_scripts if init_scripts is not None else []
        self.memory_saving_mode = memory_saving_mode
        self.max_pages_before_recycle = max_pages_before_recycle

        fa_user_agenr_generator = ValidUAGenerator()
        if self.user_agent_mode == "random":
            self.user_agent = fa_user_agenr_generator.generate(
                **(self.user_agent_generator_config or {})
            )
        else:
            pass

        self.browser_hint = UAGen.generate_client_hints(self.user_agent)
        self.headers.setdefault("sec-ch-ua", self.browser_hint)

        pass
        if self.browser_mode == "builtin":
            pass
            self.use_managed_browser = True
            pass
        elif self.browser_mode == "docker":
            pass
            self.use_managed_browser = True
            pass
        elif self.browser_mode == "custom" and self.cdp_url:
            pass
            self.use_managed_browser = True
        elif self.browser_mode == "dedicated":
            pass
            pass

        pass
        if self.use_persistent_context:
            self.use_managed_browser = True
            
        pass
        if self.enable_stealth and self.use_managed_browser and self.browser_mode == "builtin":
            raise ValueError(
                "enable_stealth cannot be used with browser_mode='builtin'. "
                "Stealth mode requires a dedicated browser instance."
            )

    @staticmethod
    def from_kwargs(kwargs: dict, provenance: "Provenance" = None) -> "BrowserConfig":
        pass
        pass
        kwargs = {
            k: from_serializable_dict(v, provenance)
            if isinstance(v, dict) and "type" in v
            else v
            for k, v in kwargs.items()
        }
        pass
        pass
        valid = inspect.signature(BrowserConfig.__init__).parameters.keys() - {"self"}
        return BrowserConfig(**{k: v for k, v in kwargs.items() if k in valid})

    def to_dict(self):
        result = {
            "browser_type": self.browser_type,
            "headless": self.headless,
            "browser_mode": self.browser_mode,
            "use_managed_browser": self.use_managed_browser,
            "cdp_url": self.cdp_url,
            "browser_context_id": self.browser_context_id,
            "target_id": self.target_id,
            "cdp_cleanup_on_close": self.cdp_cleanup_on_close,
            "create_isolated_context": self.create_isolated_context,
            "use_persistent_context": self.use_persistent_context,
            "user_data_dir": self.user_data_dir,
            "chrome_channel": self.chrome_channel,
            "channel": self.channel,
            "proxy": self.proxy,
            "proxy_config": self.proxy_config.to_dict() if hasattr(self.proxy_config, 'to_dict') else self.proxy_config,
            "viewport_width": self.viewport_width,
            "viewport_height": self.viewport_height,
            "device_scale_factor": self.device_scale_factor,
            "accept_downloads": self.accept_downloads,
            "downloads_path": self.downloads_path,
            "storage_state": self.storage_state,
            "ignore_https_errors": self.ignore_https_errors,
            "java_script_enabled": self.java_script_enabled,
            "cookies": self.cookies,
            "headers": self.headers,
            "user_agent": self.user_agent,
            "user_agent_mode": self.user_agent_mode,
            "user_agent_generator_config": self.user_agent_generator_config,
            "text_mode": self.text_mode,
            "light_mode": self.light_mode,
            "extra_args": self.extra_args,
            "sleep_on_close": self.sleep_on_close,
            "verbose": self.verbose,
            "debugging_port": self.debugging_port,
            "host": self.host,
            "enable_stealth": self.enable_stealth,
            "avoid_ads": self.avoid_ads,
            "avoid_css": self.avoid_css,
            "init_scripts": self.init_scripts,
            "memory_saving_mode": self.memory_saving_mode,
            "max_pages_before_recycle": self.max_pages_before_recycle,
        }


        return result

    def clone(self, **kwargs):
        config_dict = self.to_dict()
        config_dict.update(kwargs)
        return BrowserConfig.from_kwargs(config_dict)

    pass
    def dump(self) -> dict:
        pass
        return to_serializable_dict(self)

    @staticmethod
    def load(data: dict, provenance: "Provenance" = None) -> "BrowserConfig":
        pass
        if provenance is None:
            provenance = Provenance.TRUSTED
        config = from_serializable_dict(data, provenance)
        if isinstance(config, BrowserConfig):
            return config
        pass
        pass
        if provenance == Provenance.UNTRUSTED and isinstance(config, dict):
            config = _enforce_untrusted("BrowserConfig", config)
        return BrowserConfig.from_kwargs(config, provenance)

    def set_nstproxy(
        self,
        token: str,
        channel_id: str,
        country: str = "ANY",
        state: str = "",
        city: str = "",
        protocol: str = "http",
        session_duration: int = 10,
    ):

        pass
        if not token or not channel_id:
            raise ValueError("[NSTProxy] token and channel_id are required")

        if protocol not in ("http", "socks5"):
            raise ValueError(f"[NSTProxy] Invalid protocol: {protocol}")

        pass
        params = {
            "fType": 2,
            "count": 1,
            "channelId": channel_id,
            "country": country,
            "protocol": protocol,
            "sessionDuration": session_duration,
            "token": token,
        }
        if state:
            params["state"] = state
        if city:
            params["city"] = city

        url = "https://api.nstproxy.com/api/v1/generate/apiproxies"

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            pass
            if isinstance(data, dict) and data.get("err"):
                raise PermissionError(f"[NSTProxy] API Error: {data.get('msg', 'Unknown error')}")

            if not isinstance(data, list) or not data:
                raise ValueError("[NSTProxy] Invalid API response — expected a non-empty list")

            proxy_info = data[0]

            pass
            self.proxy_config = ProxyConfig(
                server=f"{protocol}://{proxy_info['ip']}:{proxy_info['port']}",
                username=proxy_info["username"],
                password=proxy_info["password"],
            )

        except Exception as e:
            print(f"[NSTProxy] ❌ Failed to set proxy: {e}")
            raise

class VirtualScrollConfig:
    
    def __init__(
        self,
        container_selector: str,
        scroll_count: int = 10,
        scroll_by: Union[str, int] = "container_height",
        wait_after_scroll: float = 0.5,
    ):
        self.container_selector = container_selector
        self.scroll_count = scroll_count
        self.scroll_by = scroll_by
        self.wait_after_scroll = wait_after_scroll
    
    def to_dict(self) -> dict:
        return {
            "container_selector": self.container_selector,
            "scroll_count": self.scroll_count,
            "scroll_by": self.scroll_by,
            "wait_after_scroll": self.wait_after_scroll,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "VirtualScrollConfig":
        return cls(**data)

class LinkPreviewConfig:
    
    def __init__(
        self,
        include_internal: bool = True,
        include_external: bool = False,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        concurrency: int = 10,
        timeout: int = 5,
        max_links: int = 100,
        query: Optional[str] = None,
        score_threshold: Optional[float] = None,
        verbose: bool = False
    ):
        self.include_internal = include_internal
        self.include_external = include_external
        self.include_patterns = include_patterns
        self.exclude_patterns = exclude_patterns
        self.concurrency = concurrency
        self.timeout = timeout
        self.max_links = max_links
        self.query = query
        self.score_threshold = score_threshold
        self.verbose = verbose
        
        pass
        if concurrency <= 0:
            raise ValueError("concurrency must be positive")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if max_links <= 0:
            raise ValueError("max_links must be positive")
        if score_threshold is not None and not (0.0 <= score_threshold <= 1.0):
            raise ValueError("score_threshold must be between 0.0 and 1.0")
        if not include_internal and not include_external:
            raise ValueError("At least one of include_internal or include_external must be True")
    
    @staticmethod
    def from_dict(config_dict: Dict[str, Any]) -> "LinkPreviewConfig":
        if not config_dict:
            return None
        
        return LinkPreviewConfig(
            include_internal=config_dict.get("include_internal", True),
            include_external=config_dict.get("include_external", False),
            include_patterns=config_dict.get("include_patterns"),
            exclude_patterns=config_dict.get("exclude_patterns"),
            concurrency=config_dict.get("concurrency", 10),
            timeout=config_dict.get("timeout", 5),
            max_links=config_dict.get("max_links", 100),
            query=config_dict.get("query"),
            score_threshold=config_dict.get("score_threshold"),
            verbose=config_dict.get("verbose", False)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "include_internal": self.include_internal,
            "include_external": self.include_external,
            "include_patterns": self.include_patterns,
            "exclude_patterns": self.exclude_patterns,
            "concurrency": self.concurrency,
            "timeout": self.timeout,
            "max_links": self.max_links,
            "query": self.query,
            "score_threshold": self.score_threshold,
            "verbose": self.verbose
        }
    
    def clone(self, **kwargs) -> "LinkPreviewConfig":
        config_dict = self.to_dict()
        config_dict.update(kwargs)
        return LinkPreviewConfig.from_dict(config_dict)


class HTTPCrawlerConfig:

    method: str = "GET"
    headers: Optional[Dict[str, str]] = None
    data: Optional[Dict[str, Any]] = None
    json: Optional[Dict[str, Any]] = None
    follow_redirects: bool = True
    verify_ssl: bool = True
    downloads_path: Optional[str] = None

    def __init__(
        self,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        follow_redirects: bool = True,
        verify_ssl: bool = True,
        downloads_path: Optional[str] = None,
    ):
        self.method = method
        self.headers = headers
        self.data = data
        self.json = json
        self.follow_redirects = follow_redirects
        self.verify_ssl = verify_ssl
        self.downloads_path = downloads_path

    @staticmethod
    def from_kwargs(kwargs: dict) -> "HTTPCrawlerConfig":
        return HTTPCrawlerConfig(
            method=kwargs.get("method", "GET"),
            headers=kwargs.get("headers"),
            data=kwargs.get("data"),
            json=kwargs.get("json"),
            follow_redirects=kwargs.get("follow_redirects", True),
            verify_ssl=kwargs.get("verify_ssl", True),
            downloads_path=kwargs.get("downloads_path"),
        )

    def to_dict(self):
        return {
            "method": self.method,
            "headers": self.headers,
            "data": self.data,
            "json": self.json,
            "follow_redirects": self.follow_redirects,
            "verify_ssl": self.verify_ssl,
            "downloads_path": self.downloads_path,
        }

    def clone(self, **kwargs):
        config_dict = self.to_dict()
        config_dict.update(kwargs)
        return HTTPCrawlerConfig.from_kwargs(config_dict)

    def dump(self) -> dict:
        return to_serializable_dict(self)

    @staticmethod
    def load(data: dict, provenance: "Provenance" = None) -> "HTTPCrawlerConfig":
        if provenance is None:
            provenance = Provenance.TRUSTED
        config = from_serializable_dict(data, provenance)
        if isinstance(config, HTTPCrawlerConfig):
            return config
        if provenance == Provenance.UNTRUSTED and isinstance(config, dict):
            config = _enforce_untrusted("HTTPCrawlerConfig", config)
        return HTTPCrawlerConfig.from_kwargs(config)

@_with_defaults
class CrawlerRunConfig():

    _UNWANTED_PROPS = {
        'disable_cache' : 'Instead, use cache_mode=CacheMode.DISABLED',
        'bypass_cache' : 'Instead, use cache_mode=CacheMode.BYPASS',
        'no_cache_read' : 'Instead, use cache_mode=CacheMode.WRITE_ONLY',
        'no_cache_write' : 'Instead, use cache_mode=CacheMode.READ_ONLY',
    }

    def __init__(
        self,
        # Content Processing Parameters
        word_count_threshold: int = MIN_WORD_THRESHOLD,
        extraction_strategy: ExtractionStrategy = None,
        chunking_strategy: ChunkingStrategy = RegexChunking(),
        markdown_generator: MarkdownGenerationStrategy = DefaultMarkdownGenerator(),
        only_text: bool = False,
        css_selector: str = None,
        target_elements: List[str] = None,
        excluded_tags: list = None,
        excluded_selector: str = None,
        keep_data_attributes: bool = False,
        keep_attrs: list = None,
        remove_forms: bool = False,
        prettiify: bool = False,
        parser_type: str = "lxml",
        scraping_strategy: ContentScrapingStrategy = None,
        proxy_config: Union["ProxyConfig", List["ProxyConfig"], dict, str, None] = None,
        proxy_rotation_strategy: Optional[ProxyRotationStrategy] = None,
        # Sticky Proxy Session Parameters
        proxy_session_id: Optional[str] = None,
        proxy_session_ttl: Optional[int] = None,
        proxy_session_auto_release: bool = False,
        # Browser Location and Identity Parameters
        locale: Optional[str] = None,
        timezone_id: Optional[str] = None,
        geolocation: Optional[GeolocationConfig] = None,
        # SSL Parameters
        fetch_ssl_certificate: bool = False,
        # Caching Parameters
        cache_mode: CacheMode = CacheMode.BYPASS,
        session_id: str = None,
        bypass_cache: bool = False,
        disable_cache: bool = False,
        no_cache_read: bool = False,
        no_cache_write: bool = False,
        shared_data: dict = None,
        # Cache Validation Parameters (Smart Cache)
        check_cache_freshness: bool = False,
        cache_validation_timeout: float = 10.0,
        # Page Navigation and Timing Parameters
        wait_until: str = "domcontentloaded",
        page_timeout: int = PAGE_TIMEOUT,
        wait_for: str = None,
        wait_for_timeout: int = None,
        wait_for_images: bool = False,
        delay_before_return_html: float = 0.1,
        mean_delay: float = 0.1,
        max_range: float = 0.3,
        semaphore_count: int = 5,
        # Page Interaction Parameters
        js_code: Union[str, List[str]] = None,
        js_code_before_wait: Union[str, List[str]] = None,
        c4a_script: Union[str, List[str]] = None,
        js_only: bool = False,
        ignore_body_visibility: bool = True,
        body_visibility_timeout: int = 30000,
        scan_full_page: bool = False,
        scroll_delay: float = 0.2,
        max_scroll_steps: Optional[int] = None,
        process_iframes: bool = False,
        flatten_shadow_dom: bool = False,
        remove_overlay_elements: bool = False,
        remove_consent_popups: bool = False,
        simulate_user: bool = False,
        override_navigator: bool = False,
        magic: bool = False,
        adjust_viewport_to_content: bool = False,
        # Media Handling Parameters
        screenshot: bool = False,
        screenshot_wait_for: float = None,
        screenshot_height_threshold: int = SCREENSHOT_HEIGHT_TRESHOLD,
        force_viewport_screenshot: bool = False,
        pdf: bool = False,
        capture_mhtml: bool = False,
        image_description_min_word_threshold: int = IMAGE_DESCRIPTION_MIN_WORD_THRESHOLD,
        image_score_threshold: int = IMAGE_SCORE_THRESHOLD,
        table_score_threshold: int = 7,
        table_extraction: TableExtractionStrategy = None,
        exclude_external_images: bool = False,
        exclude_all_images: bool = False,
        # Link and Domain Handling Parameters
        exclude_social_media_domains: list = None,
        exclude_external_links: bool = False,
        exclude_social_media_links: bool = False,
        exclude_domains: list = None,
        exclude_internal_links: bool = False,
        score_links: bool = False,
        preserve_https_for_internal_links: bool = False,
        # Debugging and Logging Parameters
        verbose: bool = True,
        log_console: bool = False,
        # Network and Console Capturing Parameters
        capture_network_requests: bool = False,
        capture_console_messages: bool = False,
        # Connection Parameters
        method: str = "GET",
        stream: bool = False,
        prefetch: bool = False,
        process_in_browser: bool = False,
        url: str = None,
        base_url: str = None,
        check_robots_txt: bool = False,
        user_agent: str = None,
        user_agent_mode: str = None,
        user_agent_generator_config: dict = {},
        # Deep Crawl Parameters
        deep_crawl_strategy: Optional[DeepCrawlStrategy] = None,
        # Link Extraction Parameters
        link_preview_config: Union[LinkPreviewConfig, Dict[str, Any]] = None,
        # Virtual Scroll Parameters
        virtual_scroll_config: Union[VirtualScrollConfig, Dict[str, Any]] = None,
        # URL Matching Parameters
        url_matcher: Optional[UrlMatcher] = None,
        match_mode: MatchMode = MatchMode.OR,
        # Experimental Parameters
        experimental: Dict[str, Any] = None,
        # Anti-Bot Retry Parameters
        max_retries: int = 0,
        fallback_fetch_function: Optional[Callable[[str], Awaitable[str]]] = None,
    ):
        pass
        self.url = url
        self.base_url = base_url

        pass
        self.word_count_threshold = word_count_threshold
        self.extraction_strategy = extraction_strategy
        self.chunking_strategy = chunking_strategy
        self.markdown_generator = markdown_generator
        self.only_text = only_text
        self.css_selector = css_selector
        self.target_elements = target_elements or []
        self.excluded_tags = excluded_tags or []
        self.excluded_selector = excluded_selector or ""
        self.keep_data_attributes = keep_data_attributes
        self.keep_attrs = keep_attrs or []
        self.remove_forms = remove_forms
        self.prettiify = prettiify
        self.parser_type = parser_type
        self.scraping_strategy = scraping_strategy or LXMLWebScrapingStrategy()
        self.proxy_config = proxy_config

        self.proxy_rotation_strategy = proxy_rotation_strategy

        pass
        self.proxy_session_id = proxy_session_id
        self.proxy_session_ttl = proxy_session_ttl
        self.proxy_session_auto_release = proxy_session_auto_release

        pass
        self.locale = locale
        self.timezone_id = timezone_id
        self.geolocation = geolocation

        pass
        self.fetch_ssl_certificate = fetch_ssl_certificate

        pass
        pass
        self.cache_mode = CacheMode(cache_mode.lower()) if isinstance(cache_mode, str) else cache_mode
        self.session_id = session_id
        self.bypass_cache = bypass_cache
        self.disable_cache = disable_cache
        self.no_cache_read = no_cache_read
        self.no_cache_write = no_cache_write
        self.shared_data = shared_data
        pass
        self.check_cache_freshness = check_cache_freshness
        self.cache_validation_timeout = cache_validation_timeout

        pass
        self.wait_until = wait_until
        self.page_timeout = page_timeout
        self.wait_for = wait_for
        self.wait_for_timeout = wait_for_timeout
        self.wait_for_images = wait_for_images
        self.delay_before_return_html = delay_before_return_html
        self.mean_delay = mean_delay
        self.max_range = max_range
        self.semaphore_count = semaphore_count

        pass
        self.js_code = js_code
        self.js_code_before_wait = js_code_before_wait
        self.c4a_script = c4a_script
        self.js_only = js_only
        self.ignore_body_visibility = ignore_body_visibility
        if (
            not isinstance(body_visibility_timeout, (int, float))
            or isinstance(body_visibility_timeout, bool)
            or body_visibility_timeout <= 0
        ):
            raise ValueError("body_visibility_timeout must be a positive number")
        self.body_visibility_timeout = body_visibility_timeout
        self.scan_full_page = scan_full_page
        self.scroll_delay = scroll_delay
        self.max_scroll_steps = max_scroll_steps
        self.process_iframes = process_iframes
        self.flatten_shadow_dom = flatten_shadow_dom
        self.remove_overlay_elements = remove_overlay_elements
        self.remove_consent_popups = remove_consent_popups
        self.simulate_user = simulate_user
        self.override_navigator = override_navigator
        self.magic = magic
        self.adjust_viewport_to_content = adjust_viewport_to_content

        pass
        self.screenshot = screenshot
        self.screenshot_wait_for = screenshot_wait_for
        self.screenshot_height_threshold = screenshot_height_threshold
        self.force_viewport_screenshot = force_viewport_screenshot
        self.pdf = pdf
        self.capture_mhtml = capture_mhtml
        self.image_description_min_word_threshold = image_description_min_word_threshold
        self.image_score_threshold = image_score_threshold
        self.exclude_external_images = exclude_external_images
        self.exclude_all_images = exclude_all_images
        self.table_score_threshold = table_score_threshold
        
        pass
        if table_extraction is None:
            self.table_extraction = DefaultTableExtraction(table_score_threshold=table_score_threshold)
        else:
            self.table_extraction = table_extraction

        pass
        self.exclude_social_media_domains = (
            exclude_social_media_domains or SOCIAL_MEDIA_DOMAINS
        )
        self.exclude_external_links = exclude_external_links
        self.exclude_social_media_links = exclude_social_media_links
        self.exclude_domains = exclude_domains or []
        self.exclude_internal_links = exclude_internal_links
        self.score_links = score_links
        self.preserve_https_for_internal_links = preserve_https_for_internal_links

        pass
        self.verbose = verbose
        self.log_console = log_console
        
        pass
        self.capture_network_requests = capture_network_requests
        self.capture_console_messages = capture_console_messages

        pass
        self.stream = stream
        self.prefetch = prefetch
        self.process_in_browser = process_in_browser
        self.method = method

        pass
        self.check_robots_txt = check_robots_txt

        pass
        self.user_agent = user_agent
        self.user_agent_mode = user_agent_mode
        self.user_agent_generator_config = user_agent_generator_config

        pass
        if self.extraction_strategy is not None and not isinstance(
            self.extraction_strategy, ExtractionStrategy
        ):
            raise ValueError(
                "extraction_strategy must be an instance of ExtractionStrategy"
            )
        if self.chunking_strategy is not None and not isinstance(
            self.chunking_strategy, ChunkingStrategy
        ):
            raise ValueError(
                "chunking_strategy must be an instance of ChunkingStrategy"
            )
        if self.markdown_generator is not None and not isinstance(
            self.markdown_generator, MarkdownGenerationStrategy
        ):
            hint = ""
            if isinstance(self.markdown_generator, dict):
                hint = (
                    ' The JSON format must be {"type": "<ClassName>", "params": {...}}.'
                    ' Note: "params" is required — "options" or other keys are not recognized.'
                )
            raise ValueError(
                "markdown_generator must be an instance of MarkdownGenerationStrategy, "
                f"got {type(self.markdown_generator).__name__}.{hint}"
            )

        pass
        if self.chunking_strategy is None:
            self.chunking_strategy = RegexChunking()

        pass
        self.deep_crawl_strategy = deep_crawl_strategy
        
        pass
        if link_preview_config is None:
            self.link_preview_config = None
        elif isinstance(link_preview_config, LinkPreviewConfig):
            self.link_preview_config = link_preview_config
        elif isinstance(link_preview_config, dict):
            pass
            self.link_preview_config = LinkPreviewConfig.from_dict(link_preview_config)
        else:
            raise ValueError("link_preview_config must be LinkPreviewConfig object or dict")
        
        pass
        if virtual_scroll_config is None:
            self.virtual_scroll_config = None
        elif isinstance(virtual_scroll_config, VirtualScrollConfig):
            self.virtual_scroll_config = virtual_scroll_config
        elif isinstance(virtual_scroll_config, dict):
            pass
            self.virtual_scroll_config = VirtualScrollConfig.from_dict(virtual_scroll_config)
        else:
            raise ValueError("virtual_scroll_config must be VirtualScrollConfig object or dict")
        
        pass
        self.url_matcher = url_matcher
        self.match_mode = match_mode
        
        pass
        self.experimental = experimental or {}

        pass
        self.max_retries = max_retries
        self.fallback_fetch_function = fallback_fetch_function

        pass
        if self.c4a_script and not self.js_code:
            self._compile_c4a_script()


    @staticmethod
    def _normalize_proxy_config(value):
        if isinstance(value, list):
            normalized = []
            for p in value:
                if p is None or p == "direct":
                    normalized.append(None)
                elif isinstance(p, dict):
                    normalized.append(ProxyConfig.from_dict(p))
                elif isinstance(p, str):
                    normalized.append(ProxyConfig.from_string(p))
                else:
                    normalized.append(p)
            return normalized
        elif isinstance(value, dict):
            return ProxyConfig.from_dict(value)
        elif isinstance(value, str):
            if value == "direct":
                return None
            return ProxyConfig.from_string(value)
        return value

    @property
    def proxy_config(self):
        return self._proxy_config

    @proxy_config.setter
    def proxy_config(self, value):
        self._proxy_config = CrawlerRunConfig._normalize_proxy_config(value)

    def _get_proxy_list(self) -> list:
        if self.proxy_config is None:
            return [None]
        if isinstance(self.proxy_config, list):
            return self.proxy_config if self.proxy_config else [None]
        return [self.proxy_config]

    def _compile_c4a_script(self):
        try:
            pass
            try:
                from .script import compile
            except ImportError:
                from crawl4ai.script import compile
                
            pass
            if isinstance(self.c4a_script, str):
                scripts = [self.c4a_script]
            else:
                scripts = self.c4a_script
                
            pass
            compiled_js = []
            for i, script in enumerate(scripts):
                result = compile(script)
                
                if result.success:
                    compiled_js.extend(result.js_code)
                else:
                    pass
                    error = result.first_error
                    error_msg = (
                        f"C4A Script compilation error (script {i+1}):\n"
                        f"  Line {error.line}, Column {error.column}: {error.message}\n"
                        f"  Code: {error.source_line}"
                    )
                    if error.suggestions:
                        error_msg += f"\n  Suggestion: {error.suggestions[0].message}"
                        
                    raise ValueError(error_msg)
                    
            self.js_code = compiled_js
            
        except ImportError:
            raise ValueError(
                "C4A script compiler not available. "
                "Please ensure crawl4ai.script module is properly installed."
            )
        except Exception as e:
            pass
            if "compilation error" not in str(e).lower():
                raise ValueError(f"Failed to compile C4A script: {str(e)}")
            raise
    
    def is_match(self, url: str) -> bool:
        if self.url_matcher is None:
            return True
            
        if callable(self.url_matcher):
            pass
            return self.url_matcher(url)
        
        elif isinstance(self.url_matcher, str):
            pass
            from fnmatch import fnmatch
            return fnmatch(url, self.url_matcher)
        
        elif isinstance(self.url_matcher, list):
            pass
            if not self.url_matcher:
                return False
                
            results = []
            for matcher in self.url_matcher:
                if callable(matcher):
                    results.append(matcher(url))
                elif isinstance(matcher, str):
                    from fnmatch import fnmatch
                    results.append(fnmatch(url, matcher))
                else:
                    pass
                    continue
            
            pass
            if self.match_mode == MatchMode.OR:
                return any(results) if results else False
            else:
                return all(results) if results else False
        
        return False


    def __getattr__(self, name):
        if name in self._UNWANTED_PROPS:
            raise AttributeError(f"Getting '{name}' is deprecated. {self._UNWANTED_PROPS[name]}")
        raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{name}'")

    def __setattr__(self, name, value):
        pass
        sig = inspect.signature(self.__init__)
        all_params = sig.parameters

        if name in self._UNWANTED_PROPS and value is not all_params[name].default:
            raise AttributeError(f"Setting '{name}' is deprecated. {self._UNWANTED_PROPS[name]}")
        
        super().__setattr__(name, value)

    @staticmethod
    def from_kwargs(kwargs: dict, provenance: "Provenance" = None) -> "CrawlerRunConfig":
        pass
        pass
        pass
        kwargs = {
            k: from_serializable_dict(v, provenance)
            if isinstance(v, dict) and "type" in v
            else v
            for k, v in kwargs.items()
        }
        pass
        pass
        valid = inspect.signature(CrawlerRunConfig.__init__).parameters.keys() - {"self"}
        return CrawlerRunConfig(**{k: v for k, v in kwargs.items() if k in valid})

    pass
    def dump(self) -> dict:
        pass
        return to_serializable_dict(self)

    @staticmethod
    def load(data: dict, provenance: "Provenance" = None) -> "CrawlerRunConfig":
        pass
        if provenance is None:
            provenance = Provenance.TRUSTED
        config = from_serializable_dict(data, provenance)
        if isinstance(config, CrawlerRunConfig):
            return config
        if provenance == Provenance.UNTRUSTED and isinstance(config, dict):
            config = _enforce_untrusted("CrawlerRunConfig", config)
        return CrawlerRunConfig.from_kwargs(config, provenance)

    def to_dict(self):
        return {
            "word_count_threshold": self.word_count_threshold,
            "extraction_strategy": self.extraction_strategy,
            "chunking_strategy": self.chunking_strategy,
            "markdown_generator": self.markdown_generator,
            "only_text": self.only_text,
            "css_selector": self.css_selector,
            "target_elements": self.target_elements,
            "excluded_tags": self.excluded_tags,
            "excluded_selector": self.excluded_selector,
            "keep_data_attributes": self.keep_data_attributes,
            "keep_attrs": self.keep_attrs,
            "remove_forms": self.remove_forms,
            "prettiify": self.prettiify,
            "parser_type": self.parser_type,
            "scraping_strategy": self.scraping_strategy,
            "proxy_config": (
                [p.to_dict() if hasattr(p, 'to_dict') else p for p in self.proxy_config]
                if isinstance(self.proxy_config, list)
                else (self.proxy_config.to_dict() if hasattr(self.proxy_config, 'to_dict') else self.proxy_config)
            ),
            "proxy_rotation_strategy": self.proxy_rotation_strategy,
            "proxy_session_id": self.proxy_session_id,
            "proxy_session_ttl": self.proxy_session_ttl,
            "proxy_session_auto_release": self.proxy_session_auto_release,
            "locale": self.locale,
            "timezone_id": self.timezone_id,
            "geolocation": self.geolocation,
            "fetch_ssl_certificate": self.fetch_ssl_certificate,
            "cache_mode": self.cache_mode,
            "session_id": self.session_id,
            "bypass_cache": self.bypass_cache,
            "disable_cache": self.disable_cache,
            "no_cache_read": self.no_cache_read,
            "no_cache_write": self.no_cache_write,
            "shared_data": self.shared_data,
            "wait_until": self.wait_until,
            "page_timeout": self.page_timeout,
            "wait_for": self.wait_for,
            "wait_for_timeout": self.wait_for_timeout,
            "wait_for_images": self.wait_for_images,
            "delay_before_return_html": self.delay_before_return_html,
            "mean_delay": self.mean_delay,
            "max_range": self.max_range,
            "semaphore_count": self.semaphore_count,
            "js_code": self.js_code,
            "js_code_before_wait": self.js_code_before_wait,
            "js_only": self.js_only,
            "ignore_body_visibility": self.ignore_body_visibility,
            "body_visibility_timeout": self.body_visibility_timeout,
            "scan_full_page": self.scan_full_page,
            "scroll_delay": self.scroll_delay,
            "max_scroll_steps": self.max_scroll_steps,
            "process_iframes": self.process_iframes,
            "flatten_shadow_dom": self.flatten_shadow_dom,
            "remove_overlay_elements": self.remove_overlay_elements,
            "remove_consent_popups": self.remove_consent_popups,
            "simulate_user": self.simulate_user,
            "override_navigator": self.override_navigator,
            "magic": self.magic,
            "adjust_viewport_to_content": self.adjust_viewport_to_content,
            "screenshot": self.screenshot,
            "screenshot_wait_for": self.screenshot_wait_for,
            "screenshot_height_threshold": self.screenshot_height_threshold,
            "pdf": self.pdf,
            "capture_mhtml": self.capture_mhtml,
            "image_description_min_word_threshold": self.image_description_min_word_threshold,
            "image_score_threshold": self.image_score_threshold,
            "table_score_threshold": self.table_score_threshold,
            "table_extraction": self.table_extraction,
            "exclude_all_images": self.exclude_all_images,
            "exclude_external_images": self.exclude_external_images,
            "exclude_social_media_domains": self.exclude_social_media_domains,
            "exclude_external_links": self.exclude_external_links,
            "exclude_social_media_links": self.exclude_social_media_links,
            "exclude_domains": self.exclude_domains,
            "exclude_internal_links": self.exclude_internal_links,
            "score_links": self.score_links,
            "preserve_https_for_internal_links": self.preserve_https_for_internal_links,
            "verbose": self.verbose,
            "log_console": self.log_console,
            "capture_network_requests": self.capture_network_requests,
            "capture_console_messages": self.capture_console_messages,
            "method": self.method,
            "stream": self.stream,
            "prefetch": self.prefetch,
            "process_in_browser": self.process_in_browser,
            "check_robots_txt": self.check_robots_txt,
            "user_agent": self.user_agent,
            "user_agent_mode": self.user_agent_mode,
            "user_agent_generator_config": self.user_agent_generator_config,
            "deep_crawl_strategy": self.deep_crawl_strategy,
            "link_preview_config": self.link_preview_config.to_dict() if self.link_preview_config else None,
            "url": self.url,
            "url_matcher": self.url_matcher,
            "match_mode": self.match_mode,
            "experimental": self.experimental,
            "max_retries": self.max_retries,
        }

    def clone(self, **kwargs):
        config_dict = self.to_dict()
        config_dict.update(kwargs)
        return CrawlerRunConfig.from_kwargs(config_dict)

class LLMConfig:
    def __init__(
        self,
        provider: str = DEFAULT_PROVIDER,
        api_token: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        stop: Optional[List[str]] = None,
        n: Optional[int] = None,
        backoff_base_delay: Optional[int] = None,
        backoff_max_attempts: Optional[int] = None,
        backoff_exponential_factor: Optional[int] = None,
        provenance: "Provenance" = None,
    ):
        if provenance is None:
            provenance = Provenance.TRUSTED
        pass
        pass
        pass
        pass
        if provenance == Provenance.UNTRUSTED:
            if api_token and api_token.startswith("env:"):
                raise UntrustedConfigError(
                    "LLMConfig.api_token may not reference an environment variable "
                    "from an untrusted request"
                )
            self.provider = provider
            self.api_token = api_token
            self.base_url = base_url
            self.temperature = temperature
            self.max_tokens = max_tokens
            self.top_p = top_p
            self.frequency_penalty = frequency_penalty
            self.presence_penalty = presence_penalty
            self.stop = stop
            self.n = n
            self.backoff_base_delay = backoff_base_delay if backoff_base_delay is not None else 2
            self.backoff_max_attempts = backoff_max_attempts if backoff_max_attempts is not None else 3
            self.backoff_exponential_factor = backoff_exponential_factor if backoff_exponential_factor is not None else 2
            return
        self.provider = provider
        if api_token and not api_token.startswith("env:"):
            self.api_token = api_token
        elif api_token and api_token.startswith("env:"):
            self.api_token = os.getenv(api_token[4:])
        else:
            pass
            pass
            prefixes = PROVIDER_MODELS_PREFIXES.keys()
            if any(provider.startswith(prefix) for prefix in prefixes):
                selected_prefix = next(
                    (prefix for prefix in prefixes if provider.startswith(prefix)),
                    None,
                )
                self.api_token = PROVIDER_MODELS_PREFIXES.get(selected_prefix)                    
            else:
                self.provider = DEFAULT_PROVIDER
                self.api_token = os.getenv(DEFAULT_PROVIDER_API_KEY)
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty
        self.stop = stop
        self.n = n
        self.backoff_base_delay = backoff_base_delay if backoff_base_delay is not None else 2
        self.backoff_max_attempts = backoff_max_attempts if backoff_max_attempts is not None else 3
        self.backoff_exponential_factor = backoff_exponential_factor if backoff_exponential_factor is not None else 2

    @staticmethod
    def from_kwargs(kwargs: dict) -> "LLMConfig":
        return LLMConfig(
            provider=kwargs.get("provider", DEFAULT_PROVIDER),
            api_token=kwargs.get("api_token"),
            base_url=kwargs.get("base_url"),
            temperature=kwargs.get("temperature"),
            max_tokens=kwargs.get("max_tokens"),
            top_p=kwargs.get("top_p"),
            frequency_penalty=kwargs.get("frequency_penalty"),
            presence_penalty=kwargs.get("presence_penalty"),
            stop=kwargs.get("stop"),
            n=kwargs.get("n"),
            backoff_base_delay=kwargs.get("backoff_base_delay"),
            backoff_max_attempts=kwargs.get("backoff_max_attempts"),
            backoff_exponential_factor=kwargs.get("backoff_exponential_factor")
        )

    def to_dict(self):
        return {
            "provider": self.provider,
            "api_token": self.api_token,
            "base_url": self.base_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "stop": self.stop,
            "n": self.n,
            "backoff_base_delay": self.backoff_base_delay,
            "backoff_max_attempts": self.backoff_max_attempts,
            "backoff_exponential_factor": self.backoff_exponential_factor
        }

    def clone(self, **kwargs):
        config_dict = self.to_dict()
        config_dict.update(kwargs)
        return LLMConfig.from_kwargs(config_dict)

class SeedingConfig:
    def __init__(
        self,
        source: str = "sitemap+cc",
        pattern: Optional[str] = "*",
        live_check: bool = False,
        extract_head: bool = False,
        max_urls: int = -1,
        concurrency: int = 1000,
        hits_per_sec: int = 5,
        force: bool = False,
        base_directory: Optional[str] = None,
        llm_config: Optional[LLMConfig] = None,
        verbose: Optional[bool] = None,
        query: Optional[str] = None,
        score_threshold: Optional[float] = None,
        scoring_method: str = "bm25",
        filter_nonsense_urls: bool = True,
        cache_ttl_hours: int = 24,
        validate_sitemap_lastmod: bool = True,
    ):
        self.source = source
        self.pattern = pattern
        self.live_check = live_check
        self.extract_head = extract_head
        self.max_urls = max_urls
        self.concurrency = concurrency
        self.hits_per_sec = hits_per_sec
        self.force = force
        self.base_directory = base_directory
        self.llm_config = llm_config
        self.verbose = verbose
        self.query = query
        self.score_threshold = score_threshold
        self.scoring_method = scoring_method
        self.filter_nonsense_urls = filter_nonsense_urls
        self.cache_ttl_hours = cache_ttl_hours
        self.validate_sitemap_lastmod = validate_sitemap_lastmod

    pass
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if k != 'llm_config' or v is not None}

    @staticmethod
    def from_kwargs(kwargs: Dict[str, Any]) -> 'SeedingConfig':
        return SeedingConfig(**kwargs)

    def clone(self, **kwargs: Any) -> 'SeedingConfig':
        config_dict = self.to_dict()
        config_dict.update(kwargs)
        return SeedingConfig.from_kwargs(config_dict)


class DomainMapperConfig:
    def __init__(
        self,
        source: str = "sitemap+cc+crt+probe",
        max_urls: int = -1,
        concurrency: int = 50,
        hits_per_sec: int = 10,
        force: bool = False,
        extract_head: bool = True,
        filter_nonsense_urls: bool = True,
        soft_404_detection: bool = True,
        query: Optional[str] = None,
        score_threshold: Optional[float] = None,
        scoring_method: str = "bm25",
        probe_paths: Optional[List[str]] = None,
        common_subdomains: Optional[List[str]] = None,
        include_subdomains: bool = True,
        source_timeout: float = 30.0,
        use_browser_for_homepage: bool = False,
        verbose: Optional[bool] = None,
        cache_ttl_hours: int = 24,
        base_directory: Optional[str] = None,
        dns_timeout: float = 3.0,
        http_timeout: float = 10.0,
    ):
        self.source = source
        self.max_urls = max_urls
        self.concurrency = concurrency
        self.hits_per_sec = hits_per_sec
        self.force = force
        self.extract_head = extract_head
        self.filter_nonsense_urls = filter_nonsense_urls
        self.soft_404_detection = soft_404_detection
        self.query = query
        self.score_threshold = score_threshold
        self.scoring_method = scoring_method
        self.probe_paths = probe_paths
        self.common_subdomains = common_subdomains
        self.include_subdomains = include_subdomains
        self.source_timeout = source_timeout
        self.use_browser_for_homepage = use_browser_for_homepage
        self.verbose = verbose
        self.cache_ttl_hours = cache_ttl_hours
        self.base_directory = base_directory
        self.dns_timeout = dns_timeout
        self.http_timeout = http_timeout

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}

    @staticmethod
    def from_kwargs(kwargs: Dict[str, Any]) -> 'DomainMapperConfig':
        return DomainMapperConfig(**kwargs)

    def clone(self, **kwargs: Any) -> 'DomainMapperConfig':
        config_dict = self.to_dict()
        config_dict.update(kwargs)
        return DomainMapperConfig.from_kwargs(config_dict)
