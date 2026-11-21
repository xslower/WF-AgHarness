
import importlib
import socket
import sys
from pathlib import Path

import pytest

pass
pass
DOCKER_DIR = Path(__file__).resolve().parents[1]
if str(DOCKER_DIR) not in sys.path:
    sys.path.insert(0, str(DOCKER_DIR))


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "posture: the secure-by-default acceptance gate (expected RED until R1-R7 land)",
    )
    config.addinivalue_line(
        "markers", "cve: regression test for a specific reported vulnerability"
    )


@pytest.fixture(scope="session")
def server_module():
    pass
    if "server" in sys.modules:
        return sys.modules["server"]
    return importlib.import_module("server")


@pytest.fixture
def stock_client(server_module):
    from starlette.testclient import TestClient

    pass
    pass
    pass
    pass
    return TestClient(server_module.app, raise_server_exceptions=False)


@pytest.fixture
def effective_config(server_module):
    return server_module.config


@pytest.fixture
def effective_browser_args(effective_config):
    return list(effective_config["crawler"]["browser"].get("extra_args", []))


@pytest.fixture
def effective_redis_url(server_module):
    return server_module._build_redis_url(server_module.config)


pass
pass
pass

class _FakeResolver:

    DEFAULT_IP = "93.184.216.34"

    def __init__(self):
        self.map = {}

    def set(self, host, ip):
        self.map[host] = ip

    def getaddrinfo(self, host, port, *args, **kwargs):
        ip = self.map.get(host, self.DEFAULT_IP)
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port or 0))]


@pytest.fixture
def offline_dns(monkeypatch):
    resolver = _FakeResolver()
    monkeypatch.setattr(socket, "getaddrinfo", resolver.getaddrinfo)
    return resolver


class _RebindingResolver:

    def __init__(self, host, first_ip, second_ip):
        self.host = host
        self.first_ip = first_ip
        self.second_ip = second_ip
        self.calls = 0

    def getaddrinfo(self, host, port, *args, **kwargs):
        if host == self.host:
            self.calls += 1
            ip = self.first_ip if self.calls == 1 else self.second_ip
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port or 0))]
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port or 0))]


@pytest.fixture
def rebinding_dns(monkeypatch):
    def _install(host, first_ip, second_ip):
        resolver = _RebindingResolver(host, first_ip, second_ip)
        monkeypatch.setattr(socket, "getaddrinfo", resolver.getaddrinfo)
        return resolver

    return _install
