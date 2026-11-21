from __future__ import annotations

import logging
from typing import Awaitable, Callable

logger = logging.getLogger("harness.chat_turns")
from ..util.jsonfix import loads_lenient
from ..util.llm_out import extract_fenced, last_json_value
from ..chat.msgs import last_assistant_text, last_user_text

Emit = Callable[[dict], Awaitable[None]]

pass
MAX_QUEUE = 3


def fill_inputs(decl: list | None, content: str) -> dict:
    names = [str(i.get("name")) for i in (decl or [])
             if isinstance(i, dict) and i.get("name")]
    if not names:
        names = ["task"]
    vals = {n: "" for n in names}
    vals[names[0]] = content
    return vals


pass
pass
pass

def queue_payload(items: list[dict]) -> list[dict]:
    return [{"id": it["id"],
             "content": str(it["req"].get("content") or ""),
             "images": len(it["req"].get("images") or []),
             "attachments": [str(a.get("name", ""))[:80]
                             for a in (it["req"].get("attachments") or [])],
             "workflow": str(it["req"].get("workflow") or ""),
             "interjecting": bool(it.get("interjecting"))}
            for it in items]


def apply_queue_action(items: list[dict], action: str, qid: str,
                       running: bool = False) -> tuple[list[dict], str | None]:
    idx = next((i for i, it in enumerate(items) if it["id"] == qid), -1)

    if action == "remove":
        if idx < 0:
            return items, "该消息已不在队列中"
        if items[idx].get("interjecting"):
            return items, "插队中的消息不能删除，请先取消插队"
        new = list(items)
        new.pop(idx)
        return new, None

    if action == "interject":
        if idx < 0:
            return items, "该消息已不在队列中"
        if items[idx].get("interjecting"):
            return items, None
        new = list(items)
        it = {**new.pop(idx), "interjecting": True}
        new.insert(0, it)
        notice = None
        if running:
            notice = "⏳ 已插队：本轮工具调用结束时发送（不会截断当前输出）"
        return new, notice

    if action == "cancel_interject":
        if idx < 0:
            return items, None
        new = list(items)
        new[idx] = {**new[idx], "interjecting": False}
        return new, None

    return items, f"未知的队列操作: {action}"


async def quick_suggest(c, sid: str, messages: list) -> list[str]:
    last_user = last_user_text(messages)
    last_reply = last_assistant_text(messages)
    if not last_user or not last_reply:
        return []
    prompt = (
        "根据下面的对话，推测用户接下来最可能发送的 2-3 条指令/回复。"
        "每条不超过 12 字。最后用一个 ```json 代码块给出 JSON 数组，"
        '如 ```json\n["继续", "先跑测试", "回滚改动"]\n```，代码块之外不要其它内容。\n\n'
        f"[用户] {last_user[:800]}\n[助手] {last_reply[:1500]}")
    try:
        text = await c.gateway.call_utility(
            "suggest", [{"role": "user", "content": prompt}],
            session_id=f"suggest:{sid}")
    except Exception:
        return []
    body, _err = extract_fenced(text, "json")
    arr = None
    if body:
        obj, detail, _note = loads_lenient(body, scene="raw")
        arr = obj if not detail and isinstance(obj, list) else None
    if not isinstance(arr, list):
        cand = last_json_value(text)
        if cand is None:
            pass
            fixed, detail, _note = loads_lenient(text, scene="raw")
            cand = fixed if not detail else None
        arr = cand if isinstance(cand, list) else None
    if not isinstance(arr, list):
        return []
    return [str(x)[:30] for x in arr if isinstance(x, str) and x.strip()][:3]


def declaration_of(eng, name: str) -> dict | None:
    if eng is None:
        return None
    resolver = getattr(eng, "resolve_workflow", None)
    if callable(resolver):
        return resolver(name) or None
    getter = getattr(eng, "get", None)
    return (getter(name) if callable(getter) else None) or None


async def run_workflow(c, session: dict, name: str, content: str,
                       spec: str, emit: Emit) -> None:
    try:
        eng = c.wf_engine(session.get("project", ""))
        await emit({"type": "notice", "text": f"▶ 启动工作流: {name}"})
        decl = (declaration_of(eng, name) or {}).get("inputs")
        rec = await eng.execute_sync(name, fill_inputs(decl, content))
        if rec.status == "failed":
            raise RuntimeError(rec.error or "工作流执行失败")
        result = rec.final
        await emit({"type": "text", "text": result})
        session["messages"].append({"role": "assistant", "content": result,
                                    "turn_complete": True})
        await c.sessions.save_async(session)
        await emit({"type": "done", "model": spec})
    except Exception as e:
        await emit({"type": "error",
                    "text": f"工作流执行失败: {type(e).__name__}: {e}"})
        await c.sessions.save_async(session)
