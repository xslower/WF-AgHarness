from __future__ import annotations

import json
from typing import TYPE_CHECKING
from ...util.jsonx import err
from ...provider.spec import (SUBAGENT_WAIT_TIMEOUT_SEC,
                              SUBAGENT_WAIT_TIMEOUT_MAX_SEC)

if TYPE_CHECKING:
    from .. import ToolContext, ToolRegistry


SUBAGENT_ACTIONS = ("spawn", "list", "get", "message", "wait", "stop",
                    "extend")

pass
PROFILE_PROMPT_LIMIT = 20000




async def subagent(ctx: "ToolContext", action: str = "spawn", id: str = "",
                   task: str = "", message: str = "", tools: list[str] = None,
                   background: bool = True, force: bool = True,
                   offset: int = 0, limit: int = 100,
                   profile_prompt: str = "", rounds: int = 0,
                   timeout: float = 0, hints: list[str] = None) -> str:
    act = (action or "spawn").strip().lower()
    if act not in SUBAGENT_ACTIONS:
        return err(f"action 必须是 {list(SUBAGENT_ACTIONS)} 之一，收到: {action}")

    if act == "spawn":
        if ctx.spawn is None:
            return err(
                "子 Agent 不可用：当前会话/深度不允许再派生（已到 max_spawn_depth，"
                "或计划模式下未注入 spawn）。别重试 spawn —— 这批只读操作请在主会话"
                "用同批 f_read/grep 一次给全。")
        if not task.strip():
            return err("action=spawn 需要 task")
        prompt = (profile_prompt or "").strip()
        if len(prompt) > PROFILE_PROMPT_LIMIT:
            return err(f"profile_prompt 超过 {PROFILE_PROMPT_LIMIT} 字符"
                       f"（{len(prompt)}）；长提示词请写进项目文件让子 Agent 读")
        return await ctx.spawn(task, ctx.project_dir(), tools, bg=bool(background),
                               profile_prompt=prompt, rounds=rounds,
                               hints=list(hints or []))

    manager = getattr(ctx, "subagents", None)
    if manager is None:
        return err(
            "子 Agent 管理器不可用：当前上下文没有注入 subagents 访问器。"
            "别重试 get/wait —— 需要的结论请直接在主会话用只读工具查，"
            "或先确认后端服务已重启加载新代码。")
    parent = getattr(ctx, "subagent_parent", "")
    project = getattr(ctx, "subagent_project", "")

    if act == "list":
        return json.dumps(manager.list(parent, project), ensure_ascii=False)
    if not id:
        return err(f"action={act} 需要 id（spawn 返回的 subagent_id）")
    if act == "extend":
        if getattr(ctx, "extend", None) is None:
            return err("续跑不可用")
        return await ctx.extend(id, parent, rounds=rounds, task=task,
                                background=bool(background))
    if act == "get":
        data = manager.read(id, parent, offset, limit)
        return json.dumps(data or {"error": f"子 Agent 不存在: {id}"},
                          ensure_ascii=False)
    if act == "message":
        if not message.strip():
            return err("action=message 需要 message")
        return json.dumps(manager.message(id, message, parent),
                          ensure_ascii=False)
    if act == "wait":
        pass
        pass
        try:
            t = float(timeout)
        except (TypeError, ValueError):
            t = 0
        t = t if t > 0 else SUBAGENT_WAIT_TIMEOUT_SEC
        t = min(t, SUBAGENT_WAIT_TIMEOUT_MAX_SEC)
        return json.dumps(await manager.wait(id, parent, timeout=t),
                          ensure_ascii=False)
    return json.dumps(manager.stop(id, parent, force), ensure_ascii=False)


def register(reg: "ToolRegistry") -> None:
    reg.register(
        "subagent",
        "子 Agent：独立上下文的子任务执行者，过程与结果不占主对话上下文。"
        "把「一批不依赖主上下文的调用」和「跑到通过为止的闭环任务」整块委派，"
        "例如 task='确保 tests/ 全绿，不通过自行 debug 修复并再跑，最后只回结论与改动文件'。"
        "子 Agent 最终结论用 ```json/```text/```md 围栏包住，只有围栏内的总结会回给你；"
        "结论过长时只回文件回执（全文在 result.md，用 f_read 取，不要重开子任务）。"
        "action：spawn=启动（task 必填，默认后台立即返回 id）；"
        "hints=[疑似相关文件/关键词] 可让系统把项目代码地图摘要与命中文件的方法大纲"
        "自动塞进子 Agent 首条消息，省掉它自己多轮列目录/猜文件/读大纲；"
        "list=列出；get=查看会话（含剩余工具轮数）；message=追加指令；"
        "wait=等结果（timeout 秒，超时不中止子 Agent，返回 timed_out=true）；"
        "stop=中止；extend=给已收尾（done）的子 Agent 追加额度继续跑，"
        "**复用已落盘的完整历史**，不用重开、不用重做；服务重启后凭 id 同样可用。"
        "带 task=可追加新目标（否则接着做原任务），rounds=追加轮数；"
        "background 默认 true（后台立即返回 id，用 wait 取回）；显式传 false 才前台同步等。"
        "额度耗尽返回的是「阶段总结」不是最终结论，需要它做完就 extend。"
        "除 spawn / list 外都必须带 id。子任务描述要完整自包含。",
        {"action": {"type": "string", "enum": list(SUBAGENT_ACTIONS),
                    "description": "spawn / list / get / message / wait / stop / extend"},
                 "hints": {"type": "array", "items": {"type": "string"},
                            "description": "spawn 可选：疑似相关文件路径片段或功能关键词；"
                                  "系统据此把代码地图摘要与命中文件大纲塞进子 Agent 首条消息"},
         "profile_prompt": {"type": "string",
                     "description": "spawn 可选：一个字符串两用。写 default（能写）/"
                                    "researcher（只读调研）/ reviewer（只读审阅）等已注册"
                                    "profile 名 → 用该 profile 的全部设定；写别的任意文本 →"
                                    "整段当作子 Agent 的 system 提示词（替换默认提示词，"
                                    "工具/轮数沿用 default）；不传 → 走系统默认 profile"},
         "rounds": {"type": "integer",
                    "description": "spawn/extend 可选：追加或指定的工具轮数（默认 20）"},
         "task": {"type": "string",
                  "description": "spawn 必填 / extend 可选：extend 时作为追加的新目标，"
                                 "会接在已落盘历史之后，实现「基于历史追加任务」"},
         "id": {"type": "string",
                "description": "spawn 返回的 subagent_id；get/message/wait/stop 必填"},
         "message": {"type": "string",
                     "description": "message 必填：追加给子 Agent 的指令"},
         "tools": {"type": "array", "items": {"type": "string"},
                   "description": "spawn 可选：子 Agent 可用工具白名单，"
                                  "支持 mcp__<server>__* 通配，不传=全部"},
         "background": {"type": "boolean",
                       "description": "spawn/extend 可选：默认 true（后台立即返回 id，"
                                      "用 wait 取回）；显式传 false 才前台同步等结果"},
         "force": {"type": "boolean",
                   "description": "stop 可选：true 立即取消，false 下一空档优雅退出"},
         "offset": {"type": "integer", "description": "get 可选：消息游标，默认 0"},
         "limit": {"type": "integer", "description": "get 可选：返回消息数，默认 100"},
         "timeout": {"type": "number",
                     "description": "wait 可选：最多等多少秒（默认 300，上限 1800）；"
                                    "超时只结束本次等待、不中止子 Agent，返回 timed_out=true，"
                                    "可再 wait / get / extend / stop"}},
        subagent, ["action"])

