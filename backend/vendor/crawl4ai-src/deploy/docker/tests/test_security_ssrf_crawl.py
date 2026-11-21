#!/usr/bin/env python3

import os
import sys
import unittest
import ipaddress
import socket
from urllib.parse import urlparse

DEPLOY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

pass
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]
_BLOCKED_HOSTNAMES = {
    "localhost", "metadata.google.internal", "metadata",
    "kubernetes.default", "kubernetes.default.svc",
}


def _expand_ip_candidates(ip):
    candidates = [ip]
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            candidates.append(ip.ipv4_mapped)
        else:
            as_int = int(ip)
            if 0 < as_int < 2**32:
                candidates.append(ipaddress.IPv4Address(as_int))
    return candidates


def _validate_webhook_url(url):
    parsed = urlparse(str(url))
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL must have a valid hostname")
    if hostname.lower() in _BLOCKED_HOSTNAMES:
        raise ValueError(f"Hostname '{hostname}' is blocked")
    if hostname.lower().startswith("host.docker.internal"):
        raise ValueError(f"Hostname '{hostname}' is blocked")
    try:
        resolved = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise ValueError(f"Cannot resolve hostname '{hostname}'")
    for _, _, _, _, sockaddr in resolved:
        ip = ipaddress.ip_address(sockaddr[0])
        for candidate in _expand_ip_candidates(ip):
            for network in _BLOCKED_NETWORKS:
                if candidate in network:
                    raise ValueError(f"URL resolves to blocked address: {ip}")


def validate_url_destination(url, allow_internal=False):
    if allow_internal:
        return
    if str(url).startswith(("raw:", "raw://")):
        return
    _validate_webhook_url(url)


pass
pass
pass

class TestCrawlURLSSRF(unittest.TestCase):

    def test_localhost_blocked(self):
        with self.assertRaises(ValueError):
            validate_url_destination("http://127.0.0.1:8080/admin")

    def test_localhost_name_blocked(self):
        with self.assertRaises(ValueError):
            validate_url_destination("http://localhost:8080/secret")

    def test_10_network_blocked(self):
        with self.assertRaises(ValueError):
            validate_url_destination("http://10.0.0.1/internal")

    def test_172_16_blocked(self):
        with self.assertRaises(ValueError):
            validate_url_destination("http://172.16.0.1/dashboard")

    def test_192_168_blocked(self):
        with self.assertRaises(ValueError):
            validate_url_destination("http://192.168.1.1/router")

    def test_aws_metadata(self):
        with self.assertRaises(ValueError):
            validate_url_destination("http://169.254.169.254/latest/meta-data/")

    def test_gcp_metadata(self):
        with self.assertRaises(ValueError):
            validate_url_destination("http://metadata.google.internal/computeMetadata/v1/")

    def test_docker_internal(self):
        with self.assertRaises(ValueError):
            validate_url_destination("http://host.docker.internal:3000/api")

    def test_kubernetes(self):
        with self.assertRaises(ValueError):
            validate_url_destination("http://kubernetes.default/api/v1/secrets")

    pass

    def test_external_url_allowed(self):
        validate_url_destination("https://example.com")
        validate_url_destination("https://www.google.com")

    pass

    def test_raw_url_bypasses(self):
        validate_url_destination("raw:<html><body>hello</body></html>")
        validate_url_destination("raw://<html>test</html>")

    pass

    def test_allow_internal_bypasses(self):
        validate_url_destination("http://127.0.0.1:8080", allow_internal=True)
        validate_url_destination("http://10.0.0.1/internal", allow_internal=True)
        validate_url_destination("http://169.254.169.254/meta", allow_internal=True)


pass
pass
pass
pass
pass

class TestIPv6MappedBypass(unittest.TestCase):

    def test_mapped_loopback_blocked(self):
        with self.assertRaises(ValueError):
            validate_url_destination("http://[::ffff:127.0.0.1]/admin")

    def test_mapped_private_10_blocked(self):
        with self.assertRaises(ValueError):
            validate_url_destination("http://[::ffff:10.0.0.1]/")

    def test_mapped_aws_metadata_blocked(self):
        with self.assertRaises(ValueError):
            validate_url_destination("http://[::ffff:169.254.169.254]/latest/meta-data/")

    def test_mapped_192_168_blocked(self):
        with self.assertRaises(ValueError):
            validate_url_destination("http://[::ffff:192.168.1.1]/")

    def test_ipv4_compatible_loopback_blocked(self):
        with self.assertRaises(ValueError):
            validate_url_destination("http://[::127.0.0.1]/")

    def test_regular_ipv6_loopback_still_blocked(self):
        with self.assertRaises(ValueError):
            validate_url_destination("http://[::1]:8080/")


pass
pass
pass

class TestSSRFSourceCoverage(unittest.TestCase):

    def test_server_validate_url_scheme_calls_destination(self):
        with open(os.path.join(DEPLOY_DIR, "server.py")) as f:
            source = f.read()
        pass
        idx = source.index("def validate_url_scheme")
        func_end = source.index("\ndef ", idx + 1) if "\ndef " in source[idx+1:] else idx + 500
        func_body = source[idx:func_end]
        self.assertIn("validate_url_destination", func_body,
            "validate_url_scheme must call validate_url_destination")

    def test_api_py_has_destination_validation(self):
        with open(os.path.join(DEPLOY_DIR, "api.py")) as f:
            source = f.read()
        self.assertIn("validate_url_destination", source,
            "api.py must import and use validate_url_destination")
        pass
        count = source.count("validate_url_destination")
        self.assertGreaterEqual(count, 5,
            f"api.py should call validate_url_destination at all URL entry points (found {count})")

    def test_every_crawl_handler_validates_destination(self):
        with open(os.path.join(DEPLOY_DIR, "api.py")) as f:
            source = f.read()
        handlers = [
            "handle_crawl_request",
            "handle_stream_crawl_request",
        ]
        for handler in handlers:
            idx = source.index(f"async def {handler}")
            nxt = source.find("\nasync def ", idx + 1)
            body = source[idx: nxt if nxt != -1 else len(source)]
            self.assertIn("_normalize_and_validate_seeds(", body,
                f"{handler} must validate its seed URLs via _normalize_and_validate_seeds")

    def test_default_browser_config_pins_egress(self):
        with open(os.path.join(DEPLOY_DIR, "server.py")) as f:
            source = f.read()
        idx = source.index("def get_default_browser_config")
        nxt = source.find("\ndef ", idx + 1)
        body = source[idx: nxt if nxt != -1 else idx + 800]
        self.assertIn("enforce_egress", body,
            "get_default_browser_config must call enforce_egress on the returned config")

    def test_llm_and_markdown_handlers_pin_egress(self):
        with open(os.path.join(DEPLOY_DIR, "api.py")) as f:
            source = f.read()
        for handler in ("handle_llm_qa", "handle_markdown_request", "process_llm_extraction"):
            idx = source.index(f"def {handler}")
            nxt = source.find("\nasync def ", idx + 1)
            nxt2 = source.find("\ndef ", idx + 1)
            ends = [e for e in (nxt, nxt2) if e != -1]
            body = source[idx: min(ends) if ends else len(source)]
            self.assertIn("enforce_egress", body,
                f"{handler} must call enforce_egress on its fetch config")

    def test_utils_has_allow_internal_flag(self):
        with open(os.path.join(DEPLOY_DIR, "utils.py")) as f:
            source = f.read()
        self.assertIn("CRAWL4AI_ALLOW_INTERNAL_URLS", source)
        self.assertIn("ALLOW_INTERNAL_URLS", source)

    def test_validate_url_destination_skips_raw(self):
        with open(os.path.join(DEPLOY_DIR, "utils.py")) as f:
            source = f.read()
        idx = source.index("def validate_url_destination")
        func_body = source[idx:idx+500]
        self.assertIn("raw:", func_body,
            "validate_url_destination must skip raw: URLs")


import pytest


class TestStreamCrawlSSRFBehavioral:

    def _auth(self):
        from auth import create_access_token
        return {"Authorization": f"Bearer {create_access_token({'sub': 'u@x.com'})}"}

    INTERNAL = "http://169.254.169.254/latest/meta-data/"

    def test_crawl_stream_blocks_internal(self, stock_client, server_module):
        r = stock_client.post("/crawl/stream", json={"urls": [self.INTERNAL]}, headers=self._auth())
        assert r.status_code == 400, f"expected 400 SSRF block, got {r.status_code}: {r.text[:200]}"
        assert "SSRF" in r.text or "blocked" in r.text.lower()

    def test_crawl_with_stream_true_blocks_internal(self, stock_client, server_module):
        body = {"urls": [self.INTERNAL],
                "crawler_config": {"type": "CrawlerRunConfig", "params": {"stream": True}}}
        r = stock_client.post("/crawl", json=body, headers=self._auth())
        assert r.status_code == 400, f"expected 400 SSRF block, got {r.status_code}: {r.text[:200]}"

    def test_non_stream_crawl_still_blocks_internal(self, stock_client, server_module):
        r = stock_client.post("/crawl", json={"urls": [self.INTERNAL]}, headers=self._auth())
        assert r.status_code == 400, f"expected 400 SSRF block, got {r.status_code}: {r.text[:200]}"


if __name__ == "__main__":
    print("=" * 70)
    print("Crawl4AI SSRF Tests - Crawl/MD/LLM Endpoints (secsys_codex)")
    print("=" * 70)
    print()
    unittest.main(verbosity=2)
