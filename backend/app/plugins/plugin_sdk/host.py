from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .data import (ACTIVE_PLUGIN_ID, PluginData, namespace_for_cwd,
                   namespace_for_plugin, namespace_for_request,
                   request_plugin_id)
from .registration import _Registration
from ...store import layout

logger = logging.getLogger("harness.plugin.host")


@dataclass
class HostContext:

    plugin_id: str
    project: str = ""
    pass
    data_project: str = ""
    namespace: str = ""
    pass
    container: Any = None
    pass
    registry: Any = None
    tools: Any = None
    presets: dict = field(default_factory=dict)
    scope: str = "system"
    cascade_decl: dict = field(default_factory=dict)
    pass
    specs: tuple = ()


class PluginHost(_Registration):

    def __init__(self, ctx: HostContext) -> None:
        self._ctx = ctx
        self.plugin_id = ctx.plugin_id
        self.project = ctx.project
        self.namespace = ctx.namespace
        self._data: PluginData | None = None
        self._kb = None
        self._log = logging.getLogger(f"harness.plugin.{ctx.plugin_id}")
        pass
        self.registered: list[str] = []
        self.cascaded: list[str] = []

    pass
    @classmethod
    def for_handler(cls, plugin_id: str, project: str, container) -> "PluginHost":
        top, ns = namespace_for_plugin(plugin_id, project)
        return cls(HostContext(plugin_id, project, top, ns, container=container))

    @classmethod
    def for_plugin(cls, plugin_id: str, project: str) -> "PluginHost":
        top, ns = namespace_for_plugin(plugin_id, project)
        return cls(HostContext(plugin_id, project, top, ns))

    @classmethod
    def for_tool(cls, plugin_id: str, project: str, *, tools, registry,
                 presets: dict | None = None, scope: str = "system",
                 cascade_decl: dict | None = None,
                 specs: tuple = ()) -> "PluginHost":
        top, ns = namespace_for_plugin(plugin_id, project)
        return cls(HostContext(plugin_id, project, top, ns,
                               registry=registry, tools=tools,
                               presets=presets or {}, scope=scope,
                               cascade_decl=cascade_decl or {},
                               specs=tuple(specs or ())))

    @classmethod
    def for_request(cls, path: str | Path | None = None, *,
                    project: str = "") -> "PluginHost":
        top, ns = namespace_for_request(path)
        pid = request_plugin_id()
        proj = str(top or project or "")
        return cls(HostContext(pid, proj, proj, ns))

    @classmethod
    def for_cwd(cls, path: str | Path | None = None) -> "PluginHost":
        top, ns = namespace_for_cwd(path)
        return cls(HostContext("", str(top or ""), str(top or ""), ns))

    @classmethod
    def for_setup(cls, pkg, project: str) -> "PluginHost":
        specs = tuple(getattr(pkg, "config", None) or ())
        top, ns = namespace_for_plugin(pkg.id, project)
        return cls(HostContext(pkg.id, project, top, ns, specs=specs))

    pass
    def config(self, key: str | None = None):
        from .. import config as pc
        try:
            values = pc.load(self.plugin_id, self.project, self._ctx.specs)
        except Exception:
            values = {s["key"]: s.get("default") for s in self._ctx.specs
                      if s.get("key")}
        return values if key is None else values.get(key)

    pass
    def provider_key(self, name: str) -> list[str]:
        from ...provider.store import ProviderStore
        from ...store import vault
        from ...store.plugin_config import PluginConfigStore
        if not name or name not in PluginConfigStore().grants(
                self.plugin_id, self.project):
            raise PermissionError(
                f"插件 {self.plugin_id} 未声明或未获许可读取 provider 前缀 "
                f"{name} 的 key（见清单 requested_provider_keys）")
        matched = [p for p in ProviderStore().list_all()
                   if str(p.get("name") or "").startswith(name)]
        matched.sort(key=lambda p: (str(p.get("name") or ""),
                                    str(p.get("id") or "")))
        pass
        return [vault.remember(p.get("apiKey") or "") for p in matched]

    pass
    @property
    def data(self) -> PluginData:
        if self._data is None:
            self._data = PluginData(self._ctx.data_project, self._ctx.namespace,
                                    path=self._data_path())
        return self._data

    def _data_path(self):
        pid = (self.plugin_id or request_plugin_id() or "").strip()
        if pid:
            try:
                from ..homes import data_json
                p = data_json(pid, self.project)
            except Exception:
                p = None
            if p is not None:
                return p
        return PluginData._default_path(self._ctx.data_project, self._ctx.namespace)

    pass
    @property
    def kb(self):
        if self._kb is None:
            from .kb import KnowledgeBase
            self._kb = KnowledgeBase(self._kb_path(), self.project,
                                     embed=self._embed_for_kb)
        return self._kb

    async def _embed_for_kb(self, texts, model: str = ""):
        return await self.embed(texts, model)

    def _kb_path(self):
        pid = (self.plugin_id or request_plugin_id() or "").strip()
        if pid:
            try:
                from ..homes import stores_dir
                p = stores_dir(pid, self.project)
            except Exception:
                p = None
            if p is not None:
                return p
        base = (self._ctx.data_project or self.project)
        root = (Path(base) / ".agent" if base else layout.data_dir())
        return root / "store.db"

    pass
    async def embed(self, texts, model: str = "") -> dict:
        gw = getattr(self._container(), "gateway", None) \
            if self._ctx.container is not None else None
        if gw is None:
            return {"ok": False, "error": "该宿主未绑定模型网关，不能向量化"}
        return await gw.embed(list(texts or []), spec=model)

    async def llm(self, messages: list[dict], *, model: str = "",
                  temperature: float | None = None,
                  max_tokens: int | None = None) -> dict:
        gw = getattr(self._container(), "gateway", None) \
            if self._ctx.container is not None else None
        if gw is None:
            return {"ok": False, "error": "该宿主未绑定模型网关，不能调模型"}
        from ...provider.stream import collect_reply
        try:
            got = await collect_reply(gw.chat_stream(
                list(messages or []), spec=model or None,
                session_id=f"plugin:{self.plugin_id}",
                temperature=temperature, max_tokens=max_tokens))
        except Exception as e:
            return {"ok": False, "error": f"模型调用失败: {type(e).__name__}",
                    "model": model}
        return {"ok": True, "text": got["text"],
                # 网关没发 model 事件时（极早期的失败分支）回退到请求值
                "model": got["spec"] or model,
                "usage": got["usage"]}

    pass
    @staticmethod
    def json(req: dict) -> dict:
        out: dict = {}
        raw = req.get("json")
        if isinstance(raw, dict):
            out.update(raw)
        elif isinstance(raw, list):
            out["items"] = raw
        elif req.get("body"):
            out["body"] = req["body"].decode("utf-8", "replace") \
                if isinstance(req["body"], (bytes, bytearray)) else str(req["body"])
        out.update(req.get("query") or {})
        return out

    pass
    async def run_workflow(self, name: str, inputs: dict | None = None,
                           *, human: str = "deny", start_node: str = "") -> dict:
        router = self._container().wf_router
        if router is None:
            raise RuntimeError("工作流引擎不可用")
        token = ACTIVE_PLUGIN_ID.set(self.plugin_id)
        try:
            rec = await router.run_for(name, inputs or {}, self.project,
                                       human_mode=human, start_node=start_node,
                                       session=f"plugin:{self.plugin_id}")
        finally:
            ACTIVE_PLUGIN_ID.reset(token)
        return rec.to_dict() if hasattr(rec, "to_dict") else dict(rec or {})

    async def call_tool(self, name: str, args: dict | None = None) -> str:
        c = self._container()
        pass
        pass
        try:
            pm = getattr(c, "pluginman", None)
            if pm is not None and self.project and name not in c.registry.tools:
                pm.ensure_project_registered(c.registry, self.project)
        except Exception:
            self._log.debug("插件 call_tool 预加载失败", exc_info=True)
        ctx = self._tool_ctx()
        return await c.registry.execute(name, dict(args or {}), ctx)

    async def mcp(self, server: str, tool: str, args: dict | None = None) -> str:
        return await self.call_tool(f"mcp__{server}__{tool}", args)

    def emit(self, event: dict) -> None:
        try:
            from ...event.bus import HUB
            HUB.publish("plugin.event",
                        {"plugin": self.plugin_id, "project": self.project,
                         "event": event})
        except Exception:
            self._log.debug("emit 失败", exc_info=True)

    def log(self, msg: str, *args) -> None:
        self._log.info(msg, *args)

    pass
    def bot_prompt(self, name: str | None = None) -> dict:
        from .. import bot_prompt as bp
        from ..install import InstallStore

        pid = self.plugin_id
        if not pid:
            return {}
        installs = InstallStore()
        project = self.project
        if name:
            return bp.pick(installs, pid, project, name)
        got = bp.current(installs, pid, project)
        return got or {"name": bp.DEFAULT_PROFILE_NAME, "mode": "append",
                      "text": ""}

    pass
    def _container(self):
        if self._ctx.container is None:
            raise RuntimeError("该宿主未绑定运行时，不能调用请求期能力")
        return self._ctx.container

    def _tool_ctx(self):
        from ...security.wiring import wire_policy
        from ...tools import ToolContext
        c = self._container()
        ctx = ToolContext(self.project)
        ctx.session_id = f"plugin:{self.plugin_id}"
        ctx.mcp = c.mcp
        ctx.registry = c.registry

        async def _emit(ev: dict) -> None:
            self.emit(ev)

        wire_policy(ctx, self.project, _emit, [], c.policy,
                    c.approvals, c.gateway)
        return ctx


def parse_result(result: Any) -> tuple[int, Any, bool]:
    if result is None:
        return 200, {}, False
    if isinstance(result, tuple) and len(result) == 2 and isinstance(result[0], int):
        return result[0], result[1], False
    if hasattr(result, "__aiter__"):
        return 200, result, True
    return 200, result, False


def jsonable(payload: Any, _depth: int = 0) -> Any:
    if payload is None or isinstance(payload, (str, int, float, bool)):
        return payload
    if _depth > 12:
        return str(payload)
    if isinstance(payload, dict):
        return {str(k): jsonable(v, _depth + 1) for k, v in payload.items()}
    if isinstance(payload, (list, tuple, set)):
        return [jsonable(v, _depth + 1) for v in payload]
    if hasattr(payload, "to_dict"):
        return jsonable(payload.to_dict(), _depth + 1)
    return str(payload)


__all__ = ["HostContext", "PluginHost", "parse_result", "jsonable",
           "ACTIVE_PLUGIN_ID"]
