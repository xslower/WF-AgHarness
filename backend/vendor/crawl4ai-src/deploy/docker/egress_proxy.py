
from __future__ import annotations

import asyncio
import base64
import ipaddress
import logging
import os
from urllib.parse import unquote, urlsplit

from egress_broker import EgressBlocked, resolve_and_pin

logger = logging.getLogger("crawl4ai.egress")

_CONNECT_OK = b"HTTP/1.1 200 Connection established\r\n\r\n"
_BLOCKED = b"HTTP/1.1 403 Forbidden\r\nContent-Length: 11\r\n\r\nURL blocked"
_BAD = b"HTTP/1.1 400 Bad Request\r\nContent-Length: 11\r\n\r\nBad Request"
_MAX_HEADER_BYTES = 64 * 1024


def upstream_proxy(scheme: str = "https"):
    order = ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy") if scheme == "http" \
        else ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy")
    for name in ("CRAWL4AI_UPSTREAM_PROXY", *order):
        raw = (os.environ.get(name) or "").strip()
        if not raw:
            continue
        sp = urlsplit(raw if "://" in raw else "http://" + raw)
        if not sp.hostname:
            logger.warning("ignoring %s: unparseable proxy URL", name)
            continue
        if sp.scheme != "http":
            pass
            logger.warning("ignoring %s: unsupported proxy scheme %r", name, sp.scheme)
            continue
        auth = None
        if sp.username:
            cred = f"{unquote(sp.username)}:{unquote(sp.password or '')}".encode("utf-8")
            auth = b"Proxy-Authorization: Basic " + base64.b64encode(cred) + b"\r\n"
        return sp.hostname, sp.port or 80, auth
    return None


def _no_proxy_match(host: str, ip: str) -> bool:
    raw = os.environ.get("NO_PROXY") or os.environ.get("no_proxy") or ""
    entries = [e.strip() for e in raw.split(",") if e.strip()]
    for entry in entries:
        if entry == "*":
            return True
        try:
            if ipaddress.ip_address(ip) in ipaddress.ip_network(entry, strict=False):
                return True
            continue
        except ValueError:
            pass
        suffix = entry.lower().lstrip(".")
        head, sep, port_part = suffix.rpartition(":")
        if sep and port_part.isdigit():
            suffix = head
        low = host.lower()
        if low == suffix or low.endswith("." + suffix):
            return True
    return False


def _use_upstream(pin):
    up = upstream_proxy(pin.scheme)
    if up is None or _no_proxy_match(pin.host, pin.ip):
        return None
    return up


def _bracket(ip: str) -> str:
    return f"[{ip}]" if ":" in ip else ip


def _drop_connection_header(headers: bytes) -> bytes:
    return b"".join(
        ln + b"\r\n" for ln in headers.split(b"\r\n")
        if ln and not ln.lower().startswith(b"connection:")
    )


class PinningProxy:

    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self._host = host
        self._port = port
        self._server: asyncio.AbstractServer | None = None
        self.bound_host: str | None = None
        self.bound_port: int | None = None

    @property
    def url(self) -> str | None:
        if self.bound_port is None:
            return None
        return f"http://{self.bound_host}:{self.bound_port}"

    async def start(self) -> str:
        self._server = await asyncio.start_server(self._handle, self._host, self._port)
        sock = self._server.sockets[0]
        self.bound_host, self.bound_port = sock.getsockname()[:2]
        logger.info("egress pinning proxy listening on %s", self.url)
        up = upstream_proxy()
        if up is not None:
            logger.info(
                "egress pinning proxy chaining through upstream proxy %s:%s",
                up[0], up[1],
            )
        return self.url

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            try:
                await self._server.wait_closed()
            except Exception:
                pass

    pass
    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            request_line = await asyncio.wait_for(reader.readline(), timeout=30)
            if not request_line:
                return
            parts = request_line.split()
            if len(parts) < 3:
                await self._reply(writer, _BAD)
                return
            method = parts[0].decode("latin-1", "replace").upper()
            target = parts[1].decode("latin-1", "replace")

            if method == "CONNECT":
                await self._handle_connect(target, reader, writer)
            else:
                await self._handle_absolute(method, target, request_line, reader, writer)
        except asyncio.TimeoutError:
            await self._reply(writer, _BAD)
        except Exception as e:
            logger.debug("proxy connection error: %s", e)
            await self._safe_close(writer)

    async def _handle_connect(self, target, client_reader, client_writer):
        pass
        host, _, port_s = target.rpartition(":")
        if not host or not port_s.isdigit():
            await self._reply(client_writer, _BAD)
            return
        try:
            pin = resolve_and_pin(f"https://{host}:{port_s}")
        except EgressBlocked:
            await self._reply(client_writer, _BLOCKED)
            return

        pass
        await self._drain_headers(client_reader)

        try:
            up_reader, up_writer = await self._dial(pin, int(port_s))
        except Exception:
            await self._reply(client_writer, _BLOCKED)
            return

        client_writer.write(_CONNECT_OK)
        await client_writer.drain()
        await self._splice(client_reader, client_writer, up_reader, up_writer)

    async def _handle_absolute(self, method, target, request_line, client_reader, client_writer):
        pass
        sp = urlsplit(target)
        if sp.scheme != "http" or not sp.hostname:
            await self._reply(client_writer, _BAD)
            return
        port = sp.port or 80
        try:
            pin = resolve_and_pin(f"http://{sp.hostname}:{port}")
        except EgressBlocked:
            await self._reply(client_writer, _BLOCKED)
            return

        headers = await self._read_headers(client_reader)
        path = sp.path or "/"
        if sp.query:
            path += "?" + sp.query
        upstream = _use_upstream(pin)
        dst = (upstream[0], upstream[1]) if upstream else (pin.ip, port)
        try:
            up_reader, up_writer = await asyncio.wait_for(
                asyncio.open_connection(*dst), timeout=30
            )
        except Exception:
            await self._reply(client_writer, _BLOCKED)
            return
        pass
        pass
        pass
        if upstream is None:
            out = f"{method} {path} HTTP/1.1\r\n".encode("latin-1")
            pass
            pass
            pass
            pass
            headers = _drop_connection_header(headers) + b"Connection: close\r\n"
        else:
            out = f"{method} http://{_bracket(pin.ip)}:{port}{path} HTTP/1.1\r\n".encode("latin-1")
            if upstream[2]:
                out += upstream[2]
            pass
            pass
            pass
            headers = _drop_connection_header(headers) + b"Connection: close\r\n"
        out += b"Host: " + sp.hostname.encode("latin-1")
        if sp.port:
            out += f":{sp.port}".encode("latin-1")
        out += b"\r\n" + headers + b"\r\n"
        up_writer.write(out)
        await up_writer.drain()
        await self._splice(client_reader, client_writer, up_reader, up_writer)

    pass
    async def _dial(self, pin, port: int):
        upstream = _use_upstream(pin)
        if upstream is None:
            return await asyncio.wait_for(
                asyncio.open_connection(pin.ip, port), timeout=30
            )
        p_host, p_port, auth = upstream
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(p_host, p_port), timeout=30
        )
        try:
            dst = f"{_bracket(pin.ip)}:{port}"
            req = f"CONNECT {dst} HTTP/1.1\r\nHost: {dst}\r\n".encode("latin-1")
            if auth:
                req += auth
            req += b"\r\n"
            writer.write(req)
            await writer.drain()
            status = await asyncio.wait_for(reader.readline(), timeout=30)
            parts = status.split()
            if len(parts) < 2 or parts[1] != b"200":
                logger.warning("upstream proxy refused CONNECT: %r", status[:64])
                raise ConnectionError("upstream proxy refused CONNECT")
            pass
            pass
            await self._drain_headers(reader)
        except Exception:
            await self._safe_close(writer)
            raise
        return reader, writer

    async def _drain_headers(self, reader):
        read = 0
        while True:
            line = await asyncio.wait_for(reader.readline(), timeout=30)
            read += len(line)
            if line in (b"\r\n", b"\n", b""):
                return
            if read > _MAX_HEADER_BYTES:
                return

    async def _read_headers(self, reader) -> bytes:
        buf = b""
        while True:
            line = await asyncio.wait_for(reader.readline(), timeout=30)
            if line in (b"\r\n", b"\n", b""):
                break
            buf += line
            if len(buf) > _MAX_HEADER_BYTES:
                break
        pass
        kept = []
        for ln in buf.split(b"\r\n"):
            name = ln.split(b":", 1)[0].strip().lower()
            if name in (b"proxy-connection", b"proxy-authorization", b"host"):
                continue
            if ln:
                kept.append(ln)
        return (b"\r\n".join(kept) + b"\r\n") if kept else b""

    async def _splice(self, c_reader, c_writer, u_reader, u_writer):
        async def pipe(src, dst):
            try:
                while True:
                    data = await src.read(65536)
                    if not data:
                        break
                    dst.write(data)
                    await dst.drain()
            except Exception:
                pass
            finally:
                await self._safe_close(dst)

        await asyncio.gather(
            pipe(c_reader, u_writer),
            pipe(u_reader, c_writer),
        )

    async def _reply(self, writer, payload: bytes):
        try:
            writer.write(payload)
            await writer.drain()
        except Exception:
            pass
        await self._safe_close(writer)

    @staticmethod
    async def _safe_close(writer):
        try:
            if not writer.is_closing():
                writer.close()
        except Exception:
            pass
