from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Optional

from . import spec
from .conn import (HEARTBEAT_INTERVAL, MAX_RETRIES, QUEUE_MAXSIZE,
                   RETRY_BACKOFF, ConnWorkerMixin, _Conn, human_error,
                   os_path_basename, preload_sdk, tool_fullname, transport)
from .query import MCPQueryMixin
from ..config import McpServerCfg
from ..util import pathx

logger = logging.getLogger("harness.mcp")

pass
ServersSource = Callable[[], dict[str, McpServerCfg]]


class MCPManager(ConnWorkerMixin, MCPQueryMixin):

    def __init__(self, servers: Optional[ServersSource] = None) -> None:
        pass
        pass
        self._source: ServersSource = servers or spec.global_servers
        self._conns: dict[str, _Conn] = {}
        self._tool_call_counts: dict[str, int] = {}
        self._sdk_ready: Optional[asyncio.Future] = None

    pass
    def servers(self) -> dict[str, McpServerCfg]:
        try:
            return dict(self._source() or {})
        except Exception:
            logger.warning("读取 MCP 服务器定义失败", exc_info=True)
            return {}

    def cfg_of(self, name: str) -> Optional[McpServerCfg]:
        raw = self.servers().get(name)
        return spec.effective(name, raw) if raw is not None else None

    pass
    async def ensure_sdk(self) -> None:
        if self._sdk_ready is not None and self._sdk_ready.done() \
                and not self._sdk_ready.cancelled() \
                and self._sdk_ready.exception() is not None:
            self._sdk_ready = None
        if self._sdk_ready is None:
            fut = asyncio.get_running_loop().create_future()
            self._sdk_ready = fut
            try:
                await asyncio.to_thread(preload_sdk)
            except BaseException as e:
                self._sdk_ready = None
                if not fut.done():
                    fut.set_exception(e)
                raise
            if not fut.done():
                fut.set_result(None)
        await self._sdk_ready

    pass
    def status(self) -> list[dict]:
        out = []
        for name, raw in self.servers().items():
            eff = spec.effective(name, raw)
            c = self._conns.get(name)
            out.append({
                "name": name,
                "desc": eff.desc,
                "transport": eff.transport,
                "connected": bool(c and c.ready),
                "tools": sorted(c.tools.keys()) if c else [],
                "error": (c.error if c else "") or "",
                "error_detail": (c.error_detail if c else "") or "",
                "lazy": c.lazy if c else eff.lazy,
                "disabled": bool(eff.disabled),
                "disabled_reason": eff.disabled_reason or "",
                "connect_time": c.connect_time if c else 0.0,
                "last_call_time": c.last_call_time if c else 0.0,
                "call_count": c.call_count if c else 0,
            })
        return out

    pass
    async def reload(self) -> list[dict]:
        await self.close()
        for name, raw in self.servers().items():
            eff = spec.effective(name, raw)
            if eff.disabled:
                logger.info("MCP 服务器 %s 已禁用（%s），跳过连接",
                            name, eff.disabled_reason or "手动停用")
                continue
            conn = _Conn(name, eff)
            self._conns[name] = conn
            if conn.lazy:
                logger.info("MCP 服务器 %s 配置为懒连接，跳过启动", name)
                continue
            conn.started = True
            conn.task = asyncio.create_task(self._worker(conn))
        pass
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            pending = [c for c in self._conns.values()
                       if c.started and not c.ready and not c.error
                       and c.task and not c.task.done()]
            if not pending:
                break
            await asyncio.sleep(0.2)
        return self.status()

    async def _stop_conn(self, conn: "_Conn | None") -> None:
        if not conn or not conn.task or conn.task.done():
            return
        try:
            await asyncio.wait_for(self._request(conn, "stop", {}), timeout=5)
        except Exception:
            logger.debug("MCP stop 请求失败，取消任务: %s", conn.name, exc_info=True)
            conn.task.cancel()
        try:
            await conn.task
        except Exception:
            logger.debug("MCP 任务收尾异常: %s", conn.name, exc_info=True)

    async def replace_server(self, name: str, cfg: McpServerCfg,
                             wait_ready: float = 0.0) -> "_Conn":
        eff = spec.effective(name, cfg)
        await self._stop_conn(self._conns.pop(name, None))
        conn = _Conn(name, eff)
        if eff.disabled:
            self._conns[name] = conn
            return conn
        self._conns[name] = conn
        if conn.lazy:
            logger.info("MCP 服务器 %s 配置为懒连接，跳过启动", name)
            return conn
        conn.started = True
        conn.task = asyncio.create_task(self._worker(conn))
        if wait_ready:
            deadline = time.monotonic() + wait_ready
            while time.monotonic() < deadline:
                if conn.ready or conn.error or (conn.task and conn.task.done()):
                    break
                await asyncio.sleep(0.2)
        return conn

    async def remove_server(self, name: str) -> bool:
        conn = self._conns.pop(name, None)
        await self._stop_conn(conn)
        return conn is not None

    async def _ensure_connected(self, conn: _Conn) -> None:
        if conn.ready:
            return
        if conn.lazy and not conn.started:
            logger.info("MCP 服务器 %s 懒连接启动", conn.name)
            conn.started = True
            conn.task = asyncio.create_task(self._worker(conn))
            pass
            for _ in range(75):
                if conn.ready or conn.error or (conn.task and conn.task.done()):
                    break
                await asyncio.sleep(0.2)

    async def close(self) -> None:
        for conn in list(self._conns.values()):
            if conn.task and not conn.task.done():
                try:
                    await asyncio.wait_for(self._request(conn, "stop", {}),
                                           timeout=5)
                except Exception:
                    logger.debug("MCP stop 失败，取消任务: %s", conn.name,
                                 exc_info=True)
                    conn.task.cancel()
                try:
                    await conn.task
                except Exception:
                    logger.debug("MCP 任务收尾异常: %s", conn.name, exc_info=True)
            conn.tools = {}
        self._conns = {}

    pass
    async def ensure_project_servers(self, servers: dict[str, dict],
                                     owner: str) -> list[str]:
        if not owner or not servers:
            return []
        base_name = os_path_basename(owner)
        started: list[str] = []
        global_names = self.servers()
        for sname, scfg in servers.items():
            if sname in global_names:
                continue
            conn_name = f"{sname}@{base_name}"
            existing = self._conns.get(conn_name)
            if existing is not None and (existing.ready or existing.started):
                continue
            try:
                raw = McpServerCfg(**(scfg if isinstance(scfg, McpServerCfg)
                                      else dict(scfg)))
            except Exception as e:
                logger.warning("项目 MCP 定义无效 %s: %s", conn_name, e)
                continue
            eff = spec.effective(conn_name, raw)
            conn = _Conn(conn_name, eff)
            conn.owner = owner
            self._conns[conn_name] = conn
            if eff.disabled:
                logger.info("项目 MCP %s 已禁用（%s）", conn_name,
                            eff.disabled_reason or "手动停用")
                continue
            if conn.lazy:
                logger.info("项目 MCP %s 配置为懒连接，跳过启动", conn_name)
                continue
            conn.started = True
            conn.task = asyncio.create_task(self._worker(conn))
            started.append(conn_name)
        pass
        loop = asyncio.get_running_loop()
        deadline = loop.time() + 2.0
        while loop.time() < deadline:
            pending = [n for n in started
                       if (c := self._conns.get(n)) and not c.ready and not c.error]
            if not pending:
                break
            await asyncio.sleep(0.1)
        return started

    def _visible_conns(self, project: str = "") -> list["_Conn"]:
        p = str(pathx.project_dir(project)) if project else ""
        out = []
        for c in self._conns.values():
            owner = getattr(c, "owner", "") or ""
            if not owner or (p and owner == p):
                out.append(c)
        return out
