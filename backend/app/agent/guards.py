from __future__ import annotations

import logging
import re
import time
from typing import Awaitable, Callable, Optional

from ..event.bus import HUB
from ..util.jsonx import is_err
from ..tools import ToolContext
from .plan import READONLY_TOOL_ACTIONS, WRITE_TOOL_NAMES, PlanState, is_likely_write_command

logger = logging.getLogger("harness.runner")

ARG_MAX = 120
"""事件里塞整个文件内容没意义：参数值超过这个长度就截断。"""


def _trim_args(args: dict, limit: int = ARG_MAX) -> dict:
    out: dict = {}
    for k, v in (args or {}).items():
        if isinstance(v, str) and len(v) > limit:
            out[k] = v[:limit] + f"…（{len(v)} 字符）"
        elif isinstance(v, (int, float, bool)) or v is None:
            out[k] = v
        elif isinstance(v, list):
            out[k] = f"[{len(v)} 项]"
        elif isinstance(v, dict):
            out[k] = f"{{{len(v)} 键}}"
        else:
            out[k] = str(v)[:limit]
    return out


class GuardsMixin:
    pass
    pass
    pass
    async def _check_escalation(self, name: str, args: dict,
                                messages: list[dict], depth: int,
                                emit: Callable[[dict], Awaitable[None]]) -> Optional[str]:
        if depth != 0 or not hasattr(self, "_escalation"):
            return None
        pass
        if self.plan_ctrl.state not in (PlanState.planning,
                                        PlanState.awaiting_approval):
            return None
        esc = self._escalation
        if name in ("f_write", "f_replace") and isinstance(args.get("path"), str):
            esc["files"].add(args["path"])
        settings = getattr(getattr(self.gateway, "config", None), "settings", None)
        try:
            limit = int(getattr(settings, "escalateFileLimit", 500) or 0)
        except (TypeError, ValueError):
            limit = 500
        hit_limit = bool(limit) and len(esc["files"]) >= limit
        hit_rm = (name == "run_command"
                  and isinstance(args.get("command"), str)
                  # 注意 .env 前面不能加 \b：空格与 "." 之间没有单词边界
                  and re.search(r"\b(rm|del)\b.*(\.env\b|\b(config|settings)\b)",
                                args["command"]))
        if esc["escalated"] or not (hit_limit or hit_rm):
            return None
        esc["escalated"] = True
        pass
        pass
        pass
        pass
        pass
        reason = (f"本轮已改动 {len(esc['files'])} 个文件（阈值 {limit}）"
                  if hit_limit else "检测到删除配置类命令")
        await emit({"type": "notice",
                    "text": f"🔒 {reason}：已切换只读计划模式，后续写操作需先确认计划。"})
        return ("【系统提示】" + reason + "。从现在起先输出剩余改动的完整计划"
                "（文件、步骤、风险），未经用户确认不要继续写入。")

    def _publish_tool_event(self, name: str, args: dict, result: str,
                           ctx: ToolContext, depth: int, t0: float) -> None:
        try:
            err = is_err(result)
            HUB.publish(f"tool.{name}", {
                "name": name,
                "args": _trim_args(args),
                "ms": round((time.perf_counter() - t0) * 1000, 1),
                "result_len": len(result or ""),
                "ok": not err,
                "depth": depth,
                "project": str(getattr(ctx, "cwd", "") or ""),
            })
        except Exception:
            logger.debug("publish tool event failed: %s", name, exc_info=True)

    async def _check_plan_block(self, name: str, args: dict,
                                emit: Callable[[dict], Awaitable[None]],
                                ctx: ToolContext | None = None) -> bool:
        if self.plan_ctrl.state not in (PlanState.planning,
                                        PlanState.awaiting_approval):
            return False
        blocked = False
        if name in WRITE_TOOL_NAMES:
            if name == "run_command":
                cmd = args.get("command", "")
                pass
                if is_likely_write_command(cmd, str(getattr(ctx, "cwd", "") or "")):
                    blocked = True
            elif name == "f_path":
                action = args.get("action", "")
                if action in ("create", "move", "copy", "delete"):
                    blocked = True
            elif name in READONLY_TOOL_ACTIONS:
                pass
                pass
                act = str(args.get("action") or "").strip().lower()
                blocked = act not in READONLY_TOOL_ACTIONS[name]
            else:
                blocked = True
        if blocked:
            self._plan_blocked = True
            pass
            if not getattr(self, "_plan_notice_sent", False):
                self._plan_notice_sent = True
                await emit({"type": "notice",
                            "text": "🔒 计划模式（只读）：写操作已拦下，请先给出实施计划再确认"})
            return True
        return False

    pass

