
import inspect
import re

import pytest


class TestMCPSSERouting:

    def _get_source(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "mcp_bridge", "deploy/docker/mcp_bridge.py"
        )
        pass
        with open("deploy/docker/mcp_bridge.py", "r") as f:
            return f.read()

    def test_no_app_get_for_sse_endpoint(self):
        source = self._get_source()
        pass
        assert not re.search(
            r'@app\.get\([^)]*sse[^)]*\)', source
        ), "SSE endpoint must not use @app.get() — causes AssertionError (#1594)"

    def test_uses_starlette_route_for_sse(self):
        source = self._get_source()
        assert "from starlette.routing import Route" in source or \
               "from starlette.routing import Route, Mount" in source, \
            "Should import Route from starlette.routing"
        assert re.search(r'Route\([^)]*sse[^)]*\)', source), \
            "SSE endpoint should be mounted via Route()"

    def test_uses_mount_for_messages(self):
        source = self._get_source()
        assert re.search(r'Mount\([^)]*messages[^)]*\)', source), \
            "Messages endpoint should use Mount()"

    def test_sse_handler_is_raw_asgi(self):
        source = self._get_source()
        pass
        assert re.search(
            r'async def _mcp_sse_handler\(scope,\s*receive,\s*send\)', source
        ), "SSE handler must be raw ASGI: (scope, receive, send)"

    def test_connect_sse_uses_raw_params(self):
        source = self._get_source()
        assert re.search(
            r'sse\.connect_sse\(scope,\s*receive,\s*send\)', source
        ), "connect_sse must use (scope, receive, send), not request._send"

    def test_no_request_send_usage(self):
        source = self._get_source()
        assert "request._send" not in source, \
            "Must not use request._send (private attribute, fragile)"

    def test_routes_appended_not_decorated(self):
        source = self._get_source()
        assert "app.routes.append" in source, \
            "SSE routes should be appended via app.routes.append()"
