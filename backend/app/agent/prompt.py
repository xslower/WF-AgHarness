from __future__ import annotations

import logging
from typing import Awaitable, Callable, Optional

from ..agent.profile import AgentProfile
from ..store import layout
from ..util import pathx
from .plan import PLAN_MODE_SYSTEM_PROMPT
from .subagent_result import RESULT_PROTOCOL

pass
pass
pass
SUBAGENT_CLOSING_RULE = (
    "\n\n【子 Agent 收尾规则】\n"
    "1. 任务边界：只做 task 明确要求的事。不顺手重构、不扩大范围、不追加"
    "「顺带发现」的优化；遇到范围外的东西最多一句话提及，不要动手。\n"
    "2. 同批给全：互不依赖的多个 tool_call 必须在同一轮一次性给到（f_read 的\n"
    "   path 可传数组、grep 的 key 可传数组、f_write/f_replace 用 edits 数组）；\n"
    "   **只有后一步依赖前一步结果时才分批**。一轮一个 call 会把轮次耗在等待上，\n"
    "   也是「任务没做完就撞额度」的主要原因。\n"
    "3. 达标即停：目标达成后立即停止调用工具，用一条不带工具调用的纯文本回复"
    "给出最终结论并结束。不要为「再确认一遍」重复检索、复验或重写，工具轮额度"
    "有限，结论一次给全。确实没做完就如实说明已完成/未完成，不要用工具反复试探。\n"
    "4. 额度耗尽：系统会禁止工具并再给你一次回复机会。这时**不要只说没做完**，"
    "要按「已查明（含 路径:行号）/ 已完成与未完成 / 下一步读哪里最可能出结果 /"
    "父级重新委派的 task 该怎么写」给阶段总结，让主 LLM 能接着干或自己接力。\n"
    "5. 输出协议：" + RESULT_PROTOCOL + "\n"
)

logger = logging.getLogger("harness.agent_prompt")


async def build_system(self, profile: AgentProfile,
                       messages: list[dict], depth: int,
                       emit: Callable[[dict], Awaitable[None]],
                       session_id: str, plan_mode: str = "") -> str:
    system = profile.system_prompt
    if depth != 0:
        return system + SUBAGENT_CLOSING_RULE
    system += PLAN_MODE_SYSTEM_PROMPT
    mode = plan_mode or profile.plan_mode
    if mode in ("off", "disabled"):
        self.plan_ctrl.reset()
    elif mode != "executing":
        self.plan_ctrl.enter_planning(session_id)
        await emit({"type": "plan_start", "text": "只读计划模式"})
    return system


def _tool_visible(pm, name: str, cwd: str) -> bool:
    try:
        return pm.tool_visible(name, cwd or "")
    except Exception:
        return True


def build_schemas(self, profile: AgentProfile,
                  allowed_tools: Optional[list[str]],
                  cwd: str = "") -> list[dict]:
    pass
    pm = getattr(self.registry, "pluginman", None)
    if pm is not None:
        pass
        try:
            pm.ensure_project_registered(self.registry, cwd)
            pass
            servers = pm.project_mcp_servers(cwd)
            if servers and self.mcp is not None:
                import asyncio as _asyncio
                _asyncio.ensure_future(self.mcp.ensure_project_servers(
                    servers, str(pathx.project_dir(cwd))))
        except Exception:
            logger.debug("项目插件 MCP 懒连接失败: %s", cwd, exc_info=True)
    core_names = set(self.registry.core_tools) | {"tool"}
    pass
    try:
        self.registry.refresh_descriptions(self.mcp, project=cwd)
    except Exception:
        logger.debug("刷新工具描述失败", exc_info=True)
    pass
    pass
    schemas = [s for s in self.registry.schemas
               if s["function"]["name"] in core_names]
    if pm is not None:
        schemas = [s for s in schemas
                   if _tool_visible(pm, s["function"]["name"], cwd)]
    active_allowed = (profile.allowed_tools
                      if allowed_tools is None else allowed_tools)
    if active_allowed is not None:
        pass
        allowed = set(active_allowed)
        mcp_servers = {a.split("__")[1] for a in allowed
                       if a.startswith("mcp__") and a.endswith("__*")}
        schemas = [s for s in schemas if (
            s["function"]["name"] in allowed
            or any(s["function"]["name"].startswith(f"mcp__{srv}__")
                   for srv in mcp_servers))]
    return schemas


def apply_prompt_template(self, messages: list) -> list:
    cfg = getattr(self.gateway, "config", None)
    settings = getattr(cfg, "settings", None) if cfg else None
    s = getattr(settings, "promptTemplateMode", "off") if settings else "off"
    prefix = getattr(settings, "promptPrefix", "") if settings else ""
    suffix = getattr(settings, "promptSuffix", "") if settings else ""
    if s == "off" or not (prefix or suffix):
        return messages
    out = list(messages)
    user_idx = [i for i, m in enumerate(out) if m.get("role") == "user"]
    if not user_idx:
        return out
    wrap = user_idx if s == "every" else user_idx[:1]
    for i in wrap:
        m = out[i]
        content = m.get("content")
        if not isinstance(content, str) or "{指令}" in content:
            continue
        out[i] = {**m, "content": f"{prefix}{{指令}}{suffix}".replace(
            "{指令}", content)}
    return out
