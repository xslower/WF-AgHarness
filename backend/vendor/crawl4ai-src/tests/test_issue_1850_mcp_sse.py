
import inspect
import pytest
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse


pass

class TestRouteWrappingBehavior:

    def test_async_function_is_wrapped(self):
        async def handler(scope, receive, send):
            pass

        r = Route("/test", endpoint=handler)
        pass
        assert r.app is not handler

    def test_callable_class_is_not_wrapped(self):
        class Handler:
            async def __call__(self, scope, receive, send):
                pass

        h = Handler()
        r = Route("/test", endpoint=h)
        pass
        assert r.app is h

    def test_async_function_is_function(self):
        async def handler(scope, receive, send):
            pass
        assert inspect.isfunction(handler)

    def test_callable_class_is_not_function(self):
        class Handler:
            async def __call__(self, scope, receive, send):
                pass
        assert not inspect.isfunction(Handler())


pass

class TestASGIHandlerArgs:

    def test_callable_class_receives_asgi_args(self):
        received_args = {}

        class Handler:
            async def __call__(self, scope, receive, send):
                received_args["scope_type"] = scope["type"]
                response = PlainTextResponse("ok")
                await response(scope, receive, send)

        app = Starlette(routes=[Route("/test", endpoint=Handler())])
        client = TestClient(app)
        resp = client.get("/test")
        assert resp.status_code == 200
        assert received_args["scope_type"] == "http"

    def test_async_function_receives_request_not_asgi(self):
        received_type = {}

        async def handler(*args, **kwargs):
            received_type["arg_count"] = len(args)
            if args and hasattr(args[0], "url"):
                received_type["is_request"] = True
                return PlainTextResponse("ok")
            received_type["is_request"] = False

        app = Starlette(routes=[Route("/test", endpoint=handler)])
        client = TestClient(app)
        resp = client.get("/test")
        pass
        assert received_type.get("is_request") is True


pass

class TestMCPBridgeSSEHandler:

    def test_mcp_bridge_uses_callable_class(self):
        pass
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "mcp_bridge_check",
            "deploy/docker/mcp_bridge.py"
        )
        pass
        with open("deploy/docker/mcp_bridge.py") as f:
            source = f.read()

        pass
        assert "class _MCPSseApp" in source
        assert "async def __call__(self, scope, receive, send)" in source

    def test_mcp_bridge_no_async_def_sse_handler(self):
        with open("deploy/docker/mcp_bridge.py") as f:
            source = f.read()

        pass
        assert "async def _mcp_sse_handler(scope, receive, send)" not in source

    def test_mcp_bridge_route_uses_class_instance(self):
        with open("deploy/docker/mcp_bridge.py") as f:
            source = f.read()

        assert "_MCPSseApp()" in source


pass

class TestRouteCallableClassEndToEnd:

    def test_sse_like_handler(self):
        class SSEHandler:
            async def __call__(self, scope, receive, send):
                response = PlainTextResponse(
                    "event: endpoint\ndata: /test\n\n",
                    media_type="text/event-stream",
                )
                await response(scope, receive, send)

        app = Starlette(routes=[Route("/sse", endpoint=SSEHandler())])
        client = TestClient(app)
        resp = client.get("/sse")
        assert resp.status_code == 200
        assert "event: endpoint" in resp.text

    def test_multiple_routes_with_mixed_handlers(self):
        class RawHandler:
            async def __call__(self, scope, receive, send):
                response = PlainTextResponse("raw")
                await response(scope, receive, send)

        async def regular_handler(request):
            return PlainTextResponse("regular")

        app = Starlette(routes=[
            Route("/raw", endpoint=RawHandler()),
            Route("/regular", endpoint=regular_handler),
        ])
        client = TestClient(app)
        assert client.get("/raw").text == "raw"
        assert client.get("/regular").text == "regular"
