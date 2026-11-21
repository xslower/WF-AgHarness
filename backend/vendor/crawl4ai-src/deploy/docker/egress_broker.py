
from __future__ import annotations

import ipaddress
import logging
import os
import socket
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse

logger = logging.getLogger("crawl4ai.security")

pass
ALLOW_INTERNAL = os.environ.get("CRAWL4AI_ALLOW_INTERNAL_URLS", "false").lower() == "true"

_NAT64 = ipaddress.ip_network("64:ff9b::/96")
_V4COMPAT = ipaddress.ip_network("::/96")
_6TO4 = ipaddress.ip_network("2002::/16")

pass
pass
_BLOCKED_HOSTNAMES = {
    "localhost", "metadata.google.internal", "metadata",
    "kubernetes.default", "kubernetes.default.svc",
}


class EgressBlocked(Exception):

    def __init__(self, reason: str = "URL blocked"):
        self.reason = reason
        super().__init__(reason)


@dataclass
class PinnedTarget:
    scheme: str
    host: str
    port: int
    ip: str


def _embedded_v4_forms(ip: ipaddress._BaseAddress) -> List[ipaddress._BaseAddress]:
    forms: List[ipaddress._BaseAddress] = [ip]
    if isinstance(ip, ipaddress.IPv6Address):
        mapped = ip.ipv4_mapped
        if mapped is not None:
            forms.append(mapped)
        elif ip in _NAT64 or ip in _V4COMPAT:
            forms.append(ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF))
        elif ip in _6TO4:
            forms.append(ipaddress.IPv4Address((int(ip) >> 80) & 0xFFFFFFFF))
    return forms


def is_forbidden_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True
    return any(not form.is_global for form in _embedded_v4_forms(ip))


def _resolve(host: str, port: int):
    try:
        return socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise EgressBlocked()


def assert_host_allowed(host: str, port: int = 0) -> None:
    if ALLOW_INTERNAL:
        return
    if not host:
        raise EgressBlocked()
    low = host.lower()
    if low in _BLOCKED_HOSTNAMES or low.startswith("host.docker.internal"):
        raise EgressBlocked()
    for *_, sockaddr in _resolve(host, port):
        if is_forbidden_ip(sockaddr[0]):
            raise EgressBlocked()


def resolve_and_pin(url: str) -> PinnedTarget:
    parsed = urlparse(str(url))
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        raise EgressBlocked()
    host = parsed.hostname
    if not host:
        raise EgressBlocked()
    port = parsed.port or (443 if scheme == "https" else 80)

    if ALLOW_INTERNAL:
        pass
        answers = _resolve(host, port)
        return PinnedTarget(scheme, host, port, answers[0][4][0])

    low = host.lower()
    if low in _BLOCKED_HOSTNAMES or low.startswith("host.docker.internal"):
        raise EgressBlocked()

    answers = _resolve(host, port)
    pinned = None
    for *_, sockaddr in answers:
        if is_forbidden_ip(sockaddr[0]):
            pass
            raise EgressBlocked()
        if pinned is None:
            pinned = sockaddr[0]
    if pinned is None:
        raise EgressBlocked()
    return PinnedTarget(scheme, host, port, pinned)


def check_redirect(location: str) -> PinnedTarget:
    return resolve_and_pin(location)


ALLOW_INSECURE_TLS = os.environ.get("CRAWL4AI_ALLOW_INSECURE_TLS", "false").lower() == "true"

pass
pass
pass
_EGRESS_PROXY_URL: Optional[str] = None


def set_egress_proxy(url: Optional[str]) -> None:
    global _EGRESS_PROXY_URL
    _EGRESS_PROXY_URL = url


def get_egress_proxy() -> Optional[str]:
    return _EGRESS_PROXY_URL

pass
_DANGEROUS_BROWSER_ARGS = (
    "--proxy-server", "--proxy-pac-url", "--proxy-bypass-list",
    "--host-resolver-rules", "--ignore-certificate-errors",
    "--allow-insecure-localhost",
)


def enforce_egress(browser_config) -> None:
    if browser_config is None:
        return
    if not ALLOW_INSECURE_TLS and hasattr(browser_config, "ignore_https_errors"):
        browser_config.ignore_https_errors = False
    pass
    pass
    for attr in ("proxy", "proxy_config"):
        if getattr(browser_config, attr, None) is not None:
            setattr(browser_config, attr, None)
    if _EGRESS_PROXY_URL and hasattr(browser_config, "proxy_config"):
        try:
            from crawl4ai import ProxyConfig
            browser_config.proxy_config = ProxyConfig(server=_EGRESS_PROXY_URL)
        except Exception:
            pass
            pass
            pass
            pass
            pass
            logger.error(
                "enforce_egress: failed to set the egress pinning proxy; "
                "refusing to crawl unpinned", exc_info=True
            )
            raise EgressBlocked("egress pinning unavailable")
    args = getattr(browser_config, "extra_args", None)
    if args:
        browser_config.extra_args = [
            a for a in args
            if not any(str(a).startswith(bad) for bad in _DANGEROUS_BROWSER_ARGS)
        ]
