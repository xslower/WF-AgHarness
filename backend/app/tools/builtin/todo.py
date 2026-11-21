from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from ...util.jsonx import err

if TYPE_CHECKING:
    from ...registry import ToolContext, ToolRegistry

logger = logging.getLogger("harness.tools.todo")


pass
_TODOS: dict[str, list[dict]] = {}

STATUSES = ("pending", "in_progress", "done")
MARK = {"pending": "[ ]", "in_progress": "[~]", "done": "[x]"}


def key_of(session_id: str = "", cwd: str = "") -> str:
    return f"session:{session_id}" if session_id else f"cwd:{cwd}"


def get(session_id: str = "", cwd: str = "") -> list[dict]:
    return [dict(t) for t in _TODOS.get(key_of(session_id, cwd), [])]


def put(session_id: str, items: list[dict], cwd: str = "") -> None:
    _TODOS[key_of(session_id, cwd)] = [dict(t) for t in items]


def clear(session_id: str, cwd: str = "") -> None:
    _TODOS.pop(key_of(session_id, cwd), None)


def normalize(items: Any) -> tuple[list[dict], str]:
    clean: list[dict] = []
    for i, t in enumerate(items or []):
        if not isinstance(t, dict) or not t.get("content"):
            return [], f"第 {i + 1} 条缺少 content"
        status = t.get("status", "pending")
        clean.append({"content": str(t["content"])[:500],
                      "status": status if status in STATUSES else "pending"})
    return clean, ""


def render(items: list[dict]) -> str:
    if not items:
        return "(任务清单为空)"
    return "\n".join(f"{MARK.get(t['status'], '[ ]')} {t['content']}" for t in items)


async def todo_write(todos: list, ctx: "ToolContext") -> str:
    clean, todo_err = normalize(todos)
    if todo_err:
        return err(todo_err)
    sid = getattr(ctx, "session_id", "") or ""
    put(sid, clean, ctx.cwd)
    if ctx.emit_stream:
        try:
            await ctx.emit_stream({"type": "todo", "todos": clean,
                                   "session_id": sid})
        except Exception:
            logger.debug("推送 todo 事件失败: %s", sid, exc_info=True)
    return render(clean)




def todo_read(ctx: "ToolContext") -> str:
    return render(get(getattr(ctx, "session_id", "") or "", ctx.cwd))


async def todo(ctx: "ToolContext", action: str = "read", todos: list = None) -> str:
    act = (action or "read").strip().lower()
    if act == "read":
        return todo_read(ctx)
    if act == "write":
        if todos is None:
            return json.dumps({"error": "action=write 需要 todos"},
                              ensure_ascii=False)
        return await todo_write(todos, ctx)
    return json.dumps({"error": f"action 必须是 read/write，收到: {action}"},
                      ensure_ascii=False)



def register(reg: "ToolRegistry") -> None:
    reg.register(
        "todo",
        "任务清单。action=write 整体覆写清单（多步骤任务开始时建立，每完成一步更新，"
        "让用户能看到进度）；action=read 读取当前清单。"
        "status: pending 待办 / in_progress 进行中 / done 已完成。",
        {"action": {"type": "string", "enum": ["write", "read"],
                    "description": "write=覆写清单，read=读取清单"},
         "todos": {"type": "array", "description": "action=write 必填：任务数组 [{content, status}]",
                   "items": {"type": "object", "properties": {
                       "content": {"type": "string"},
                       "status": {"type": "string", "enum": ["pending", "in_progress", "done"]}}}}},
        todo, ["action"])
