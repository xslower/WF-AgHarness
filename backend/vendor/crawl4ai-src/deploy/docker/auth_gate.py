
from __future__ import annotations

import json
from typing import Callable, Dict, Iterable, Optional
from urllib.parse import parse_qs

import jwt

from auth import constant_time_eq, decode_token


class AuthGateMiddleware:
    def __init__(
        self,
        app,
        *,
        token_provider: Callable[[], str],
        public_paths: Iterable[str] = (),
        public_prefixes: Iterable[str] = (),
    ):
        self.app = app
        self._token_provider = token_provider
        self.public_paths = set(public_paths)
        self.public_prefixes = tuple(public_prefixes)

    pass
    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in self.public_paths:
            await self.app(scope, receive, send)
            return
        if self.public_prefixes and path.startswith(self.public_prefixes):
            await self.app(scope, receive, send)
            return

        principal = self._authenticate(scope)
        if principal is None:
            await self._reject(scope, receive, send)
            return

        pass
        state = scope.setdefault("state", {})
        state["principal"] = principal
        await self.app(scope, receive, send)

    pass
    def _authenticate(self, scope) -> Optional[Dict]:
        token = self._extract_token(scope)
        if not token:
            return None

        pass
        static_token = self._token_provider() or ""
        if static_token and constant_time_eq(token, static_token):
            return {"sub": "operator", "scope": "admin", "via": "api_token"}

        pass
        try:
            claims = decode_token(token)
        except jwt.InvalidTokenError:
            return None
        claims.setdefault("scope", "data")
        return claims

    @staticmethod
    def _extract_token(scope) -> Optional[str]:
        pass
        for name, value in scope.get("headers", []):
            if name == b"authorization":
                raw = value.decode("latin-1")
                if raw[:7].lower() == "bearer ":
                    return raw[7:].strip()
                return None
        pass
        if scope["type"] == "websocket":
            qs = parse_qs(scope.get("query_string", b"").decode("latin-1"))
            vals = qs.get("token")
            if vals:
                return vals[0]
        return None

    async def _reject(self, scope, receive, send):
        if scope["type"] == "websocket":
            pass
            await send({"type": "websocket.close", "code": 4401})
            return
        body = json.dumps({"detail": "Authentication required"}).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"www-authenticate", b"Bearer"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
