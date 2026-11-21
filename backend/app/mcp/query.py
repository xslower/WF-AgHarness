from __future__ import annotations

import json
import logging

from ..util.jsonx import err
from ..tools.schema_fmt import popular_row

logger = logging.getLogger("harness.mcp")


class MCPQueryMixin:

    pass
    def visible_conns(self, project: str = "") -> list:
        return self._visible_conns(project)

    def visible_status(self, project: str = "") -> list[dict]:
        names = {c.name for c in self._visible_conns(project)}
        return [s for s in self.status() if s["name"] in names]

    def schemas(self) -> list[dict]:
        return []

    pass
    def knows(self, name: str, project: str = "") -> bool:
        return any(name in c.tools for c in self._visible_conns(project))

    def search_tools(self, query: str, project: str = "") -> list[dict]:
        query_lower = query.lower()
        results = []
        for c in self._visible_conns(project):
            if not c.ready:
                continue
            for full_name, schema in c.tools.items():
                desc = schema["function"].get("description", "")
                if (not query_lower or query_lower in full_name.lower()
                        or query_lower in desc.lower()):
                    results.append({"name": full_name, "description": desc,
                                    "source": "mcp"})
        return results

    def get_tool_schema(self, name: str, project: str = "") -> dict | None:
        for c in self._visible_conns(project):
            if name in c.tools:
                return c.tools[name]
        return None

    def popular_mcp_tools(self, limit: int = 10, project: str = "") -> list[dict]:
        if not self._tool_call_counts:
            return []
        visible = {n for c in self._visible_conns(project) for n in c.tools}
        sorted_names = sorted(
            ((n, c) for n, c in self._tool_call_counts.items() if n in visible),
            key=lambda x: x[1], reverse=True)[:limit]
        out = []
        for name, count in sorted_names:
            schema = self.get_tool_schema(name, project)
            if not schema:
                continue
            out.append(popular_row(name, count, schema))
        return out

    def mcp_summary(self, project: str = "") -> list[dict]:
        out = []
        for c in self._visible_conns(project):
            if not c.tools:
                continue
            tool_names = list(c.tools.keys())
            pass
            short_names = [n.split("__", 2)[2] if "__" in n else n
                           for n in tool_names]
            out.append({
                "server": c.name,
                "tool_count": len(c.tools),
                "tools": short_names,
                "connected": c.ready,
                "owner": getattr(c, "owner", "") or "",
            })
        return out

    pass
    async def call(self, name: str, args: dict, project: str = "") -> str:
        for c in self._visible_conns(project):
            if name in c.tools:
                try:
                    pass
                    await self._ensure_connected(c)
                    result = await self._request(c, "call",
                                                 {"name": name, "args": args})
                    pass
                    pass
                    self._tool_call_counts[name] = \
                        self._tool_call_counts.get(name, 0) + 1
                    return result
                except Exception as e:
                    logger.error("MCP 调用失败 %s: %s", name, e)
                    return json.dumps({"error": f"MCP 调用失败: {e}"},
                                      ensure_ascii=False)
        return err(f"MCP 工具不存在: {name}")

    async def refresh_tools(self, server_name: str) -> dict:
        c = self._conns.get(server_name)
        if not c or not c.ready:
            return {"error": f"MCP 服务器 {server_name} 未连接"}
        try:
            await self._request(c, "refresh", {})
            return {"ok": True, "tools": sorted(c.tools.keys())}
        except Exception as e:
            return {"error": f"刷新失败: {e}"}
