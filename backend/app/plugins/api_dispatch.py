from __future__ import annotations

import asyncio
import importlib.util
import inspect
import logging
import sys

import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any


from .plugin_sdk import PluginHost, jsonable, parse_result
from .tool_loader import parse_extra
from .tool_unit import drop_bytecode

logger = logging.getLogger("harness.plugin.api")

pass
_MODULE_CACHE: dict[tuple, Any] = {}

pass
pass
pass
_PLUGIN_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="plugin-api")



class PluginApiRouter:

    def __init__(self, installs) -> None:
        self._installs = installs
        self._handlers: dict[tuple[str, str], dict] = {}

    def reload(self) -> int:
        self._handlers.clear()
        seen: set[tuple[str, str]] = set()
        for row in self._installs.files_by_kind("api", None):
            extra = parse_extra(row.get("extra") or "")
            if extra.get("kind") != "code":
                continue
            key = (row["plugin_id"], row["project"])
            if key in seen:
                continue
            seen.add(key)
            self._handlers[key] = {
                "project": row["project"],
                "rel_path": row["rel_path"],
                "handler": extra.get("handler") or "handle",
            }
        logger.info("插件 api 注册表已重建：%d 个 handler", len(self._handlers))
        return len(self._handlers)

    def lookup(self, plugin_id: str, project: str = "") -> dict | None:
        from . import resolve as resolver

        try:
            rec = resolver.resolve(self._installs, plugin_id, project)
        except resolver.PluginScopeError:
            return None
        return self._handlers.get((plugin_id, rec["project"]))

    async def invoke(self, plugin_id: str, project: str, req: dict,
                     container) -> tuple[int, Any, bool]:
        entry = self.lookup(plugin_id, project)
        if entry is None:
            return 404, {"error": {"plugin": plugin_id,
                                   "detail": "插件未注册 api（未安装或未声明 api kind）"}}, False

        pass
        host = PluginHost.for_handler(plugin_id, entry["project"], container)
        started = time.time()
        try:
            handler = _load_handler(entry, plugin_id)
            result = await _call_handler(handler, req, host)
            status, payload, is_stream = parse_result(result)
            pass
            pass
            return status, (_redact(payload) if not is_stream else payload), is_stream
        except Exception as e:
            from ..store import vault
            logger.warning("插件 %s handler 抛错: %s", plugin_id,
                           vault.redact(e), exc_info=True)
            return 500, {"error": {
                "plugin": plugin_id,
                "detail": vault.redact(f"{type(e).__name__}: {e}")}}, False
        finally:
            logger.info("插件 api %s %s %dms", plugin_id, req.get("path"),
                        int((time.time() - started) * 1000))


async def _call_handler(handler, req: dict, host: PluginHost):
    if inspect.iscoroutinefunction(handler):
        return await handler(req, host)
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(_PLUGIN_POOL, handler, req, host)
    if inspect.isawaitable(result):
        result = await result
    return result




def _load_handler(entry: dict, plugin_id: str):
    from . import location

    file_path = location.resolve_registered(entry, entry.get("project") or "")
    if not file_path.is_file():
        raise FileNotFoundError(f"插件模块不存在: {file_path}")
    st = file_path.stat()
    key = (str(file_path), st.st_mtime, st.st_size)
    mod = _MODULE_CACHE.get(key)
    if mod is None:
        drop_bytecode(file_path)
        modname = f"_plugin_api_{plugin_id.replace('-', '_')}"
        spec = importlib.util.spec_from_file_location(modname, file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"无法加载插件模块: {file_path}")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[modname] = mod
        spec.loader.exec_module(mod)
        _MODULE_CACHE[key] = mod
    handler = getattr(mod, entry.get("handler") or "handle", None)
    if not callable(handler):
        raise AttributeError(
            f"插件模块 {file_path} 缺少可调用的 handler: {entry.get('handler') or 'handle'}")
    return handler


def reset_cache() -> None:
    _MODULE_CACHE.clear()


__all__ = ["PluginApiRouter", "reset_cache"]


def _redact(payload: Any) -> Any:
    from ..store import vault
    if isinstance(payload, (dict, list)) or payload is None:
        return vault.redact_obj(jsonable(payload))
    return vault.redact(payload)
