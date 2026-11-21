from __future__ import annotations

import json
import logging
from typing import Any


from ..provider.gateway import ModelGateway
from ..provider.spec import QUEUE_SUMMARY

from .tool_window import KEEP_RECENT, keep_from, text_of

pass
MEMO_SECTIONS = ("[任务]", "[线索]", "[已完成]", "[决定]",
                 "[进行中]", "[未完成]", "[建议]")

pass
pass
pass
pass
pass
SUMMARY_CHARS = 3000

pass
pass
pass


def _brief_params(args: Any, limit: int = 120) -> str:
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except ValueError:
            return (args or "")[:limit]
    if isinstance(args, dict):
        parts = []
        for k, v in list(args.items())[:4]:
            s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
            parts.append(f"{k}={s[:40]}")
        return ", ".join(parts)[:limit]
    return str(args)[:limit]


def _first_line(text: str, limit: int = 160) -> str:
    t = " ".join(str(text or "").split())
    return t[:limit]


def _name_args(msg: dict) -> str:
    name = msg.get("name") or msg.get("tool_name") or "tool"
    args = msg.get("arguments") or msg.get("tool_arguments") or ""
    return f"{name}({_brief_params(args, 60)})" if args else name


def is_text_reply(msg: dict) -> bool:
    return (msg.get("role") == "assistant"
            and not msg.get("tool_calls")
            and bool(text_of(msg).strip()))


def l1_fold(msg: dict) -> dict | None:
    role = msg.get("role")
    if role == "tool":
        name = msg.get("name") or msg.get("tool_name") or "tool"
        return {"role": "tool", "name": name,
                "content": f"[msg#{msg.get('_seq', '?')} {_name_args(msg)} → {_first_line(text_of(msg))}]"}

    if role == "assistant" and msg.get("tool_calls"):
        calls = []
        for tc in msg["tool_calls"]:
            fn = tc.get("function", {})
            calls.append(f"[msg#{msg.get('_seq', '?')} 调用 {fn.get('name')}({_brief_params(fn.get('arguments'))})]")
        out: dict = {"role": "assistant", "content": " ".join(calls)}
        text = text_of(msg)
        if text:
            out["content"] = f"{text}\n{' '.join(calls)}"
        return out

    if role in ("user", "assistant"):
        pass
        out = {"role": role, "content": msg.get("content")}
        if role == "assistant" and msg.get("reasoning_content"):
            out.pop("reasoning_content", None)
        return out
    return None


pass
def plan_batch(total: int, compacted_upto: int,
               keep_recent: int = KEEP_RECENT,
               *, end: int | None = None) -> tuple[int, int]:
    start = max(compacted_upto, 0)
    end = total - keep_recent if end is None else end
    if end <= start:
        return (-1, -1)
    return (start, end)


logger = logging.getLogger("harness.compaction")


class ContextCompactor:
    pass
    SUMMARY_CHARS = SUMMARY_CHARS

    pass
    pass
    SUMMARY_PROMPT = """你在压缩一个 agent 会话的旧消息。下面每条消息带编号（msg#N）。
对**每一条**输出一两句话的总结，保住任务推进必需的信息：任务目标、已完成的改动
（文件路径:行号）、关键决定、未完成事项、重要命令结论。丢掉寒暄、重复尝试、中间过程。

只输出 JSON 数组，不要其它文字，格式：
[{"n": <编号数字>, "s": "<一两句总结>"}]
每条消息都必须有一条对应输出，顺序与输入一致。

消息列表：
"""

    def __init__(self, gateway: ModelGateway) -> None:
        self.gateway = gateway

    pass
    async def hedged_call(self, prompt: str, sid: str,
                          hedge_ms: int = 2500) -> str:
        from .compaction_kit import hedged_call
        return await hedged_call(self.gateway, prompt, sid, hedge_ms)

    async def summarize_batch(self, folded: list[dict],
                              session_id: str = "") -> dict[int, str]:
        if not folded:
            return {}
        lines = [f"[msg#{m.get('_seq')} {m.get('role')}] {text_of(m)[:2000]}"
                 for m in folded]
        try:
            text = await self._collect(
                [{"role": "user",
                  "content": self.SUMMARY_PROMPT + "\n".join(lines)}],
                session_id)
        except Exception:
            return {}
        return self._parse_items(text)

    async def _collect(self, messages: list[dict], session_id: str) -> str:
        parts: list[str] = []
        async for chunk in self.gateway.chat_stream(
                messages, spec=QUEUE_SUMMARY, session_id=session_id):
            if chunk.type == "text":
                parts.append(chunk.text)
        return "".join(parts)



    @classmethod
    def merge(cls, folded: list[dict], summaries: dict[int, str]) -> list[dict]:
        out: list[dict] = []
        for m in folded:
            seq = m.get("_seq")
            s = summaries.get(seq)
            if s and m.get("role") in ("user", "assistant"):
                out.append({"role": m.get("role"),
                            "content": f"[msg#{seq}] {s}"})
            else:
                out.append(m)
        return out

    @staticmethod
    def _parse_items(text: str) -> dict[int, str]:
        try:
            text = (text or "").strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            arr = json.loads(text)
            out: dict[int, str] = {}
            if isinstance(arr, list):
                for it in arr:
                    if isinstance(it, dict) and "n" in it and "s" in it:
                        out[int(it["n"])] = str(it["s"])[:400]
            return out
        except (ValueError, TypeError):
            return {}

    pass
    @staticmethod
    def merge_range(folded: list[dict], summary: str,
                    user_msg_limit: int = 1000) -> list[dict]:
        covered = [int(m["_seq"]) for m in folded if is_text_reply(m)]

        out: list[dict] = []
        placed = False
        for m in folded:
            role = m.get("role")
            if is_text_reply(m):
                if not summary:
                    out.append(m)
                    continue
                if not placed:
                    ids = ",".join(str(c) for c in covered)
                    out.append({"role": "user",
                                "content": f"[msg#{ids} 助手回复已压缩] {summary}"})
                    placed = True
                continue
            if role == "user":
                out.append(fold_user(m, user_msg_limit))
                continue
            out.append(m)
        pass
        if summary and not placed:
            ids = ",".join(str(c) for c in covered) or "?"
            out.insert(0, {"role": "user",
                           "content": f"[msg#{ids} 助手回复已压缩] {summary}"})
        return out


pass


def merge_memo(folded: list[dict], summary: str,
               user_msg_limit: int = 1000) -> list[dict]:
    if not summary:
        return ContextCompactor.merge_range(folded, "", user_msg_limit)
    ids = ",".join(str(m.get("_seq")) for m in folded
                    if m.get("_seq") is not None)
    out: list[dict] = []
    if user_msg_limit:
        for m in folded:
            if (m.get("role") == "user"
                    and len(text_of(m)) > user_msg_limit):
                out.append(fold_user(m, user_msg_limit))
    out.append({"role": "user",
                "content": f"[msg#{ids} 任务纪要；原文可 "
                           f"memory(action=history_get, ids=[{ids}]) 取回]\n{summary}"})
    return out


pass
def fold_user(msg: dict, limit: int) -> dict:
    seq = msg.get("_seq")
    text = text_of(msg)
    if not limit or len(text) <= limit:
        return msg
    head, tail = text[:800], text[-400:]
    return {"role": "user",
            "content": f"{head}\n…[省略 {len(text) - 1200} 字，原文 msg#{seq}，"
                       f"可 memory(action=history_get, ids=[{seq}]) 取回]\n{tail}"}




