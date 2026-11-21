from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Optional

from ..config import McpServerCfg
from . import result as mcp_result

logger = logging.getLogger("harness.mcp")

pass
HEARTBEAT_INTERVAL = 30
pass
MAX_RETRIES = 3
pass
RETRY_BACKOFF = 1.0
pass
QUEUE_MAXSIZE = 100
pass
ERROR_TAIL = 2000
pass
HUMAN_ERROR_LIMIT = 200


def tool_fullname(server: str, tool: str) -> str:
    return f"mcp__{server}__{tool}"


def os_path_basename(path: str) -> str:
    import os as _os
    return _os.path.basename(str(path).rstrip("/\\")) or "project"


def preload_sdk() -> None:
    import mcp
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.sse import sse_client
    from mcp.client.stdio import stdio_client
    from mcp.client.streamable_http import streamable_http_client


def human_error(e: BaseException) -> str:
    seen: list[str] = []
    cur: Optional[BaseException] = e
    depth = 0
    while cur is not None and depth < 8:
        text = str(cur).strip()
        if text and text not in seen:
            seen.append(text)
        subs = getattr(cur, "exceptions", None)
        cur = cur.__cause__ or (subs[0] if subs else None)
        depth += 1
    text = seen[-1] if seen else type(e).__name__
    if len(text) > HUMAN_ERROR_LIMIT:
        text = text[:HUMAN_ERROR_LIMIT] + "…"
    return text


def traceback_tail(e: BaseException) -> str:
    import traceback
    tb = traceback.format_exception(type(e), e, e.__traceback__)
    for sub in getattr(e, "exceptions", ()) or ():
        tb += traceback.format_exception(type(sub), sub, sub.__traceback__)
    return "".join(tb)[-ERROR_TAIL:]


class _Conn:

    def __init__(self, name: str, cfg: McpServerCfg) -> None:
        self.name = name
        self.cfg = cfg
        self.task: Optional[asyncio.Task] = None
        pass
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_MAXSIZE)
        self.tools: dict[str, dict] = {}
        pass
        self.error: str = ""
        self.error_detail: str = ""
        self.connect_time: float = 0.0
        self.last_call_time: float = 0.0
        self.call_count: int = 0
        self.lazy: bool = cfg.lazy
        self.started: bool = False
        pass
        pass
        self.owner: str = ""

    @property
    def ready(self) -> bool:
        return bool(self.tools) and self.task and not self.task.done()

    def fail(self, e: BaseException) -> None:
        self.error = human_error(e)
        self.error_detail = traceback_tail(e)
        self.tools = {}


@asynccontextmanager
async def transport(conn: _Conn):
    if conn.cfg.transport == "sse":
        from mcp.client.sse import sse_client
        async with sse_client(conn.cfg.url,
                              headers=conn.cfg.headers or None) as streams:
            yield streams
    elif conn.cfg.transport == "http":
        from mcp.client.streamable_http import streamable_http_client
        async with streamable_http_client(
                conn.cfg.url,
                headers=conn.cfg.headers or None) as streams:
            yield streams
    else:
        from mcp import StdioServerParameters
        from mcp.client.stdio import stdio_client
        async with stdio_client(StdioServerParameters(
                command=conn.cfg.command, args=conn.cfg.args,
                env=conn.cfg.env or None)) as streams:
            yield streams


class ConnWorkerMixin:

    async def _worker(self, conn: _Conn) -> None:
        for attempt in range(MAX_RETRIES + 1):
            try:
                await self.ensure_sdk()
                async with transport(conn) as (reader, writer):
                    clean = await self._session_loop(conn, reader, writer)
                if clean:
                    return
                raise ConnectionError("会话被对端关闭")
            except asyncio.CancelledError:
                raise
            except Exception as e:
                conn.fail(e)
                if attempt < MAX_RETRIES:
                    delay = RETRY_BACKOFF * (2 ** attempt)
                    logger.warning("MCP 服务器 %s 连接失败（第 %d 次），%.1fs 后重试: %s",
                                   conn.name, attempt + 1, delay, conn.error)
                    await asyncio.sleep(delay)
                    conn.error = ""
                    conn.error_detail = ""
                else:
                    logger.error("MCP 服务器 %s 连接失败，已达最大重试次数: %s\n%s",
                                 conn.name, conn.error, conn.error_detail)

    async def _session_loop(self, conn: _Conn, reader, writer) -> bool:
        from mcp import ClientSession
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            conn.connect_time = time.time()
            conn.error = ""
            conn.error_detail = ""
            logger.info("MCP 服务器 %s 连接成功", conn.name)

            await self._discover_tools(conn, session)

            hb_task = asyncio.create_task(self._heartbeat(conn, session))
            try:
                while True:
                    op, payload, fut = await conn.queue.get()
                    if op == "stop":
                        if not fut.done():
                            fut.set_result(None)
                        return True
                    if op == "refresh":
                        await self._refresh_tools(conn, session, fut)
                        continue
                    if op == "call":
                        await self._do_call(conn, session, payload, fut)
            finally:
                hb_task.cancel()
                try:
                    await hb_task
                except (Exception, asyncio.CancelledError):
                    pass
                logger.info("MCP 服务器 %s 会话结束", conn.name)

    async def _heartbeat(self, conn: _Conn, session) -> None:
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            try:
                await session.list_tools()
            except Exception as e:
                raise ConnectionError(f"心跳失败: {e}") from e

    async def _refresh_tools(self, conn: _Conn, session, fut) -> None:
        try:
            await self._discover_tools(conn, session)
            if not fut.done():
                fut.set_result(None)
        except Exception as e:
            if not fut.done():
                fut.set_exception(e)

    async def _do_call(self, conn: _Conn, session, payload: dict, fut) -> None:
        try:
            short = payload["name"].split("__", 2)[2]
            result = await session.call_tool(short, payload["args"])
            conn.last_call_time = time.time()
            conn.call_count += 1
            if not fut.done():
                fut.set_result(mcp_result.finalize(result))
            logger.debug("MCP 工具 %s 调用成功", payload["name"])
        except Exception as e:
            logger.warning("MCP 工具 %s 调用失败: %s", payload.get("name", "?"), e)
            if not fut.done():
                fut.set_exception(e)

    async def _discover_tools(self, conn: _Conn, session) -> None:
        res = await session.list_tools()
        conn.tools = {}
        for t in res.tools:
            schema = (getattr(t, "input_schema", None)
                      or getattr(t, "inputSchema", None) or {})
            pass
            params = {
                "type": schema.get("type", "object"),
                "properties": schema.get("properties", {}),
                "required": schema.get("required", []),
            }
            pass
            if "additionalProperties" in schema:
                params["additionalProperties"] = schema["additionalProperties"]
            full = tool_fullname(conn.name, t.name)
            conn.tools[full] = {
                "type": "function",
                "function": {"name": full,
                             "description": t.description or "",
                             "parameters": params},
            }
        logger.info("MCP 服务器 %s 发现 %d 个工具", conn.name, len(conn.tools))

    async def _request(self, conn: _Conn, op: str, payload: Any) -> Any:
        if not conn.ready:
            raise RuntimeError(f"MCP 服务器 {conn.name} 未连接: "
                               f"{conn.error or '已停止'}")
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        await conn.queue.put((op, payload, fut))
        return await fut
