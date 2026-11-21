from __future__ import annotations

import asyncio
import inspect
import json
import logging
import subprocess

from pathlib import Path
from typing import Callable, Optional

from ..util.jsonx import err
from .schema_fmt import popular_row

logger = logging.getLogger("harness.tools")

__all__ = ["ToolContext", "ToolRegistry"]


class ToolRegistry:
    pass
    pass
    pass
    CORE_TOOLS = {
        "f_read", "f_write", "f_replace", "f_path", "search_files", "grep",
        "config_write",
        "run_command", "web", "subagent", "todo", "tool",
        # 文件族入口：模型必须自己想起来「这是表格/幻灯片」，放扩展工具里就得先
        # tool(action=search) 才发现，太绕。
        "table", "ppt",
        # 工作流/编排会话需要直接跑工作流，放扩展工具里要先 search 一轮才知道，
        # 与「会话与工作流同构」的目标冲突，因此直接进核心集。
        "workflow",
        # memory = 项目记忆（save/search/replace/delete）+ 历史原文取回（history_get）：
        # 上下文压缩后，模型必须**随时**能按 [msg#N] 取回原文，
        # 这个能力不能藏在 tool(action=search) 后面。
        "memory",
        # 插件工具不写在这里：由插件 manifest 的 `coreTools` 字段声明，
        # 扫描时经 PluginManager.core_tools() → ToolRegistry.add_core_tools() 注入。
        # 硬编码插件工具名 = 每加一个插件就改一次系统代码，那是错的。
    }

    def __init__(self) -> None:
        self.tools: dict[str, Callable] = {}
        self.schemas: list[dict] = []
        pass
        self.pluginman = None
        self.hooks: dict[str, list[str]] = {"before": [], "after": []}
        self._call_counts: dict[str, int] = {}
        pass
        self._extra_core: set[str] = set()
        pass
        pass
        pass
        self.describe_hook: Callable[..., None] | None = None

    def refresh_descriptions(self, mcp=None, project: str = "") -> None:
        hook = self.describe_hook
        if hook is None:
            return
        hook(self, mcp, project)

    def add_core_tools(self, names) -> None:
        self._extra_core.update(str(n) for n in (names or []) if n)

    @property
    def core_tools(self) -> list[str]:
        return [n for n in (*self.CORE_TOOLS, *sorted(self._extra_core))
                if n in self.tools]

    def popular_builtin_tools(self, limit: int = 10) -> list[dict]:
        if not self._call_counts:
            return []
        core_set = self.CORE_TOOLS
        sorted_names = sorted(
            ((n, c) for n, c in self._call_counts.items() if n not in core_set),
            key=lambda x: x[1], reverse=True)[:limit]
        out = []
        for name, count in sorted_names:
            schema = next((s for s in self.schemas
                          if s["function"]["name"] == name), None)
            if not schema:
                continue
            out.append(popular_row(name, count, schema))
        return out

    def builtin_summary(self, project: str = "") -> list[dict]:
        core_set = set(self.core_tools)
        pm = self.pluginman
        out = []
        for s in self.schemas:
            f = s["function"]
            name = f["name"]
            if name in core_set:
                continue
            if pm is not None:
                try:
                    if not pm.tool_visible(name, project or ""):
                        continue
                except Exception:
                    logger.debug("tool_visible 判定失败: %s", name, exc_info=True)
            params = f["parameters"].get("properties", {})
            pstr = ", ".join(f"{k}:{v.get('type', '?')}" for k, v in params.items())
            out.append({
                "name": name,
                "params": pstr,
                "description": f.get("description", "")[:80],
            })
        return out

    def add_hook(self, when: str, script: str) -> None:
        if when in self.hooks:
            self.hooks[when].append(script)

    async def _run_hooks(self, when: str, name: str, args: dict,
                         ctx: "ToolContext") -> tuple[bool, str]:
        import os as _os
        for script in self.hooks.get(when, []):
            env = {**_os.environ,
                   "HOOK_TOOL": name,
                   "HOOK_ARGS": json.dumps(args, ensure_ascii=False),
                   "HOOK_CWD": ctx.cwd}
            try:
                pass
                pass
                pass
                r = await asyncio.to_thread(
                    lambda s=script: subprocess.run(
                        [s], env=env, capture_output=True, timeout=30,
                        cwd=ctx.cwd))
            except Exception:
                continue
            if when == "before" and r.returncode != 0:
                msg = r.stdout.decode("utf-8", errors="replace").strip()[:500]
                return False, msg or f"被 before 钩子拦截: {script}"
        return True, ""

    def register(self, name: str, desc: str, params: dict, fn: Callable,
                 required: Optional[list] = None) -> None:
        self.tools[name] = fn
        self.schemas.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": desc,
                    "parameters": {
                        "type": "object",
                        "properties": params,
                        # 显式 required=[] 表示"无必填"；不传（None）才是"全部必填"
                        "required": (list(params.keys()) if required is None
                                     else list(required)),
                    },
                },
            }
        )

    def unregister(self, name: str) -> None:
        self.tools.pop(name, None)
        self.schemas = [s for s in self.schemas
                        if s.get("function", {}).get("name") != name]
        self._call_counts.pop(name, None)

    async def execute(self, name: str, args: dict, ctx: "ToolContext") -> str:
        fn = self.tools.get(name)
        if not fn:
            return err(f"未知工具: {name}")
        pass
        pm = self.pluginman
        if pm is not None and name in self.tools:
            try:
                if not pm.tool_visible(name, getattr(ctx, "project_dir", lambda: "")() or "",
                                       allow_internal=bool(
                                           getattr(ctx, "allow_internal", False))):
                    return err(f"工具 {name} 在当前上下文不可用")
            except Exception:
                logger.debug("execute 前 tool_visible 判定失败: %s", name, exc_info=True)
        pass
        if self.hooks.get("before"):
            ok, msg = await self._run_hooks("before", name, args, ctx)
            if not ok:
                return err(msg)
        try:
            result = await self._call_tool(fn, name, args, ctx)
            pass
            self._call_counts[name] = self._call_counts.get(name, 0) + 1
        except TypeError as e:
            return err(f"参数错误: {e}")
        except Exception as e:
            return err(f"{type(e).__name__}: {e}")
        pass
        if self.hooks.get("after"):
            await self._run_hooks("after", name, args, ctx)
        return result

    @staticmethod
    async def _call_tool(fn: Callable, name: str, args: dict,
                         ctx: "ToolContext") -> str:
        if inspect.iscoroutinefunction(fn):
            res = await fn(**args, ctx=ctx)
        else:
            pass
            pass
            res = await asyncio.to_thread(fn, **args, ctx=ctx)
            if inspect.isawaitable(res):
                res = await res
        return res if isinstance(res, str) else json.dumps(res, ensure_ascii=False)


class ToolContext:
    def __init__(self, cwd: str, project: str = "") -> None:
        self.cwd = cwd
        pass
        pass
        pass
        self.project = project or cwd
        pass
        pass
        self.session_id = ""
        self.mcp = None
        pass
        pass
        pass
        self.suggested_tools: list[dict] | None = None
        pass
        pass
        pass
        pass
        self.pending_images: list[str] = []
        pass
        pass
        pass
        self.images_channel = False
        self.registry = None
        pass
        pass
        self.allow_internal = False
        self.spawn = None
        self.extend = None
        self.snapshot = None
        self.policy_check = None
        self.request_approval = None
        pass
        pass
        pass
        pass
        pass
        self.path_check = None
        self.env_rewrite = None
        pass
        pass
        pass
        pass
        self.emit_stream = None
        self.workflow_start = None

        self.workflow_wait = None
        self.save_memory = None
        self.memory_search = None
        self.memory_replace = None
        self.memory_delete = None
        self.history_get = None
        self.request_file_approval = None
        self.wf_edit = None
        pass
        pass
        self.report_file = None
        pass
        self.subagents = None
        self.subagent_parent = ""
        self.subagent_project = ""
        self._snapshotted = False

    def project_dir(self) -> str:
        return self.project or self.cwd or ""

    def suggest_tools(self, schemas: list[dict]) -> None:
        if not schemas:
            return
        pass
        seen: set = set()
        uniq: list[dict] = []
        for s in schemas:
            name = s.get("function", {}).get("name", "")
            if name and name not in seen:
                seen.add(name)
                uniq.append(s)
        self.suggested_tools = uniq

    async def auto_snapshot(self, message: str,
                            paths: "Sequence[str | Path] | None" = None) -> None:
        if not self.snapshot:
            return
        if paths is None:
            if self._snapshotted:
                return
            self._snapshotted = True
        try:
            if paths is None:
                await asyncio.to_thread(self.snapshot, message)
            else:
                await asyncio.to_thread(self.snapshot, message, list(paths))
        except Exception:
            logger.debug("自动快照失败: %s", message[:60], exc_info=True)
