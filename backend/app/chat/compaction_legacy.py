from __future__ import annotations

import asyncio
import logging

from .compaction import (SUMMARY_CHARS, ContextCompactor, is_text_reply,
                         keep_from, plan_batch, text_of)
from .compaction_kit import (Emit, MIN_MESSAGES, call_twice, fold_batch,
                             notice, report_after, session_data)

logger = logging.getLogger("harness.compact.legacy")

BATCH_PROMPT = """下面是一个 agent 会话里若干条助手回复（按时间顺序，带 msg# 编号）。
请把它们合并成**一段**中文总结，供后续对话回忆使用。

要求：
- 保住任务目标、已完成的改动（文件路径:行号）、关键决定、重要命令结论、未完成事项；
- 丢掉寒暄、重复尝试、中间过程、被推翻的方案；
- 长度建议 1000 字左右：以保住任务信息为先（超过 3000 字系统会再压一次）；
- 只输出总结正文：不要标题、不要 JSON、不要逐条编号、不要分隔线。

助手回复：
"""

CHUNK_CHARS = 20000
BODY_CHARS = CHUNK_CHARS

pass
pass
CONDENSE_CHARS = SUMMARY_CHARS

CONDENSE_PROMPT = f"""下面是一段会话总结，超过了 {SUMMARY_CHARS} 字。请把它再压缩到 {SUMMARY_CHARS} 字以内。

要求：保住任务目标、已完成的改动（文件路径:行号）、关键决定、重要命令结论、
未完成事项；丢掉重复表述与过程细节。只输出压缩后的正文，不要标题、不要解释。

总结：
"""


def _chunk_lines(lines: list[str], limit: int) -> list[str]:
    chunks: list[str] = []
    cur: list[str] = []
    size = 0
    for ln in lines:
        if cur and size + len(ln) > limit:
            chunks.append("\n".join(cur))
            cur, size = [], 0
        cur.append(ln)
        size += len(ln) + 1
    if cur:
        chunks.append("\n".join(cur))
    return chunks or [""]


class LegacyStrategy:
    name = "legacy"

    pass
    async def _batch(self, c, folded: list[dict], sid: str,
                     hedge_ms: int) -> str:
        lines = [f"[msg#{m.get('_seq')}] {text_of(m).strip()[:BODY_CHARS]}"
                 for m in folded if is_text_reply(m)]
        if not lines:
            return ""
        chunks = _chunk_lines(lines, CHUNK_CHARS)
        if len(chunks) == 1:
            text = await c.compactor.hedged_call(
                BATCH_PROMPT + chunks[0], sid, hedge_ms)
        else:
            parts = await asyncio.gather(*[
                c.compactor.hedged_call(
                    BATCH_PROMPT + part +
                    "\n\n（这是整段对话的一部分，请只总结这一部分，控制在 300 字内）",
                    sid, hedge_ms)
                for part in chunks], return_exceptions=True)
            out = [p.strip() for p in parts if isinstance(p, str) and p.strip()]
            if not out:
                raise RuntimeError("分块总结全部失败")
            text = "\n".join(out)
        if len(text) <= CONDENSE_CHARS:
            return text
        try:
            shorter = await c.compactor.hedged_call(
                CONDENSE_PROMPT + text, sid, hedge_ms)
            return shorter or text
        except Exception:
            return text

    pass
    async def compact(self, c, sid: str, emit: Emit, *,
                      session: dict | None = None, model: str = "") -> None:
        ctx = session_data(c, sid, session=session, model=model)
        if ctx is None or len(ctx.msgs) <= MIN_MESSAGES:
            return
        compacted_upto = ctx.segments[-1]["upto_seq"] if ctx.segments else 0
        start, end = plan_batch(len(ctx.msgs), compacted_upto,
                                end=keep_from(ctx.msgs))
        if start < 0:
            return
        folded = fold_batch(ctx.msgs, start, end)
        if not folded:
            return
        st = c.store.config.settings
        mode = getattr(st, "compactSummaryMode", "batch") or "batch"
        await notice(emit, f"正在整理上下文（msg#{start}..{end - 1}），请稍候…")
        items = None
        if mode == "per_message":
            need = any(is_text_reply(m) for m in folded)
            summaries = await call_twice(
                lambda: c.compactor.summarize_batch(folded, sid), "per_message") \
                if need else {}
            if summaries is None:
                items = None
            else:
                items = ContextCompactor.merge(folded, summaries)
        else:
            need = bool(folded)
            summary = await call_twice(
                lambda: self._batch(c, folded, sid,
                                    getattr(st, "summaryHedgeMs", 2500)),
                "batch") if need else ""
            if summary is None:
                await notice(emit, "整理上下文失败，本批保留原文，下次再压。")
                return
            items = ContextCompactor.merge_range(
                folded, summary,
                user_msg_limit=getattr(st, "compactUserMsgLimit", 1000))
        if items is None:
            await notice(emit, "整理上下文失败，本批保留原文，下次再压。")
            return
        c.sessions.add_compaction(ctx.project, sid, end, items)
        await report_after(c, ctx, emit)
