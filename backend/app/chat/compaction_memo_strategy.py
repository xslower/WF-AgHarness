from __future__ import annotations

import logging

from ..provider.registry import ModelRegistry
from ..provider.spec import QUEUE_SUMMARY
from ..util.tokens import estimate_text
from .compaction import MEMO_SECTIONS, SUMMARY_CHARS, merge_memo, text_of
from .compaction_kit import (Emit, MIN_MESSAGES, call_twice, fold_batch,
                             notice, plan_batch_scope, report_after,
                             session_data)

logger = logging.getLogger("harness.compact.memo")

pass
INPUT_WINDOW_RATIO = 0.5
pass
pass
MEMO_CHARS = SUMMARY_CHARS
OUTPUT_HARD_CHARS = MEMO_CHARS * 2

MEMO_PROMPT = f"""下面是一个 agent 会话里若干**用户回合**的记录（按时间顺序，每条带 msg# 编号）。
请把它们整理成一份**任务纪要**，供后续对话回忆使用。任务完成后，工具调用的
参数与结果正文已经没用了，但**前后探索路径的关键线索**必须留下。

严格按下面 7 个小节输出，每节一行，没有内容就写「无」：
[任务] 这一阶段要解决什么（含用户明确的目标 / 约束 / 验收标准）
[线索] 探索路径的关键线索：定位到的文件与行号、报错结论、关键命令结果、被排除的方向
[已完成] 完成了哪些内容、改了哪些文件（文件路径:行号）、跑了哪些测试及结论
[决定] 做出的关键决定（含被推翻的方案，注明推翻原因）
[进行中] 尚未完成的方案 / 步骤，只写精简要点
[未完成] 遗留事项、下一步
[建议] 给用户的建议（如开新会话、换方案等）

要求：
- 总长不超过 {MEMO_CHARS} 字，以保住任务信息为先；
- 文件路径与行号、命令结论、报错原文的关键信息不能丢；
- 丢掉寒暄、重复尝试、中间过程、原始工具参数与输出正文；
- 标有「用户补充（上一回合未完成）」的是同一回合里的中断 / 插话 / 重启碎片，
  归入 [线索] 或 [未完成]，不要当成一份已完成任务单独总结；
- **不要思考模式**：不要输出思考过程、分析步骤或推理说明，直接给出文字回复；
- 只输出上面的 7 个小节正文，不要额外标题、不要 JSON、不要解释、不要分隔线。

会话记录：
"""


class MemoStrategy:
    name = "memo"

    pass
    @staticmethod
    def _summary_window(gateway) -> int:
        try:
            specs = gateway._ordered_specs(QUEUE_SUMMARY)
            info = ModelRegistry(gateway.config).model_of(specs[0]) if specs else None
            return int(getattr(info, "contextLength", 0) or 0)
        except Exception:
            return 0

    @staticmethod
    def _lines(folded: list[dict]) -> list[str]:
        out: list[str] = []
        turn = 0
        opened = False
        for m in folded:
            seq = m.get("_seq", "?")
            text = text_of(m).strip()
            if m.get("role") == "user":
                if opened:
                    out.append(f"[msg#{seq} 用户补充（上一回合未完成）] {text}")
                else:
                    turn += 1
                    opened = True
                    out.append(f"[回合 {turn} / msg#{seq} 用户] {text}")
            elif m.get("role") == "assistant" and m.get("_complete"):
                out.append(f"[msg#{seq} 助手] {text}")
                opened = False
            elif m.get("role") == "assistant" and not m.get("tool_calls"):
                out.append(f"[msg#{seq} 助手] {text}")
            else:
                out.append(f"[msg#{seq} 工具] {text}")
        return [ln for ln in out if ln.strip()]

    @staticmethod
    def _tail_within(lines: list[str], budget: int) -> str:
        text = "\n".join(lines)
        if budget <= 0 or estimate_text(text) <= budget:
            return text
        rest = list(lines)
        while rest and estimate_text("\n".join(rest)) > budget:
            if len(rest) == 1:
                ln = rest[0]
                lo, hi = 0, len(ln)
                while lo < hi:
                    mid = (lo + hi + 1) // 2
                    if estimate_text(ln[-mid:]) <= budget:
                        lo = mid
                    else:
                        hi = mid - 1
                return ln[-lo:] if lo else ""
            rest.pop(0)
        return "\n".join(rest)

    pass
    async def compact(self, c, sid: str, emit: Emit, *,
                      session: dict | None = None, model: str = "") -> None:
        ctx = session_data(c, sid, session=session, model=model)
        if ctx is None or len(ctx.msgs) <= MIN_MESSAGES:
            return
        start, end = plan_batch_scope(ctx.msgs, ctx.segments)
        if start < 0:
            return
        folded = fold_batch(ctx.msgs, start, end)
        if not folded:
            return
        await notice(emit, f"正在整理上下文（msg#{start}..{end - 1}），请稍候…")

        budget = int(self._summary_window(c.gateway) * INPUT_WINDOW_RATIO)
        transcript = self._tail_within(self._lines(folded), budget)
        pass
        for m in folded:
            m.pop("_complete", None)
        hedge_ms = getattr(c.store.config.settings, "summaryHedgeMs", 2500)
        summary = await call_twice(
            lambda: c.compactor.hedged_call(MEMO_PROMPT + transcript, sid,
                                            hedge_ms),
            "memo")
        if summary is None:
            pass
            await notice(emit, "整理上下文失败，本批保留原文，下次再压。")
            return
        if len(summary) > OUTPUT_HARD_CHARS:
            summary = summary[-OUTPUT_HARD_CHARS:]
        items = merge_memo(
            folded, summary,
            user_msg_limit=getattr(c.store.config.settings,
                                   "compactUserMsgLimit", 1000))
        c.sessions.add_compaction(ctx.project, sid, end, items)
        await report_after(c, ctx, emit)
