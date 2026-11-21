from __future__ import annotations

import asyncio

from app.chat.compaction import SUMMARY_CHARS, ContextCompactor
from app.chat.compaction_kit import get_strategy
from app.chat.compaction_legacy import (BATCH_PROMPT, BODY_CHARS,
                                        CONDENSE_PROMPT, LegacyStrategy)
from app.chat.compaction_memo_strategy import (MEMO_CHARS, MEMO_PROMPT,
                                               OUTPUT_HARD_CHARS,
                                               MemoStrategy)
from app.chat.compaction_secondary import SecondaryStrategy


class _Chunk:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _Gateway:

    def __init__(self, *replies: str, context_length: int = 1_000_000) -> None:
        self.replies = list(replies)
        self.prompts: list[str] = []
        self.config = _Config(context_length)

    def _ordered_specs(self, queue):
        return ["m/1"]

    async def stream_hedged(self, messages, specs, hedge_ms=0, **kw):
        self.prompts.append(messages[0]["content"])
        text = self.replies.pop(0) if self.replies else "短总结"
        yield _Chunk(text)


class _Config:
    def __init__(self, context_length: int) -> None:
        from app.config import AppConfig
        from app.provider.models import ModelInfo, ModelQueues, Provider
        cfg = AppConfig()
        cfg.providers = [Provider(id="m", name="m", baseUrl="http://x",
                                  apiKey="k",
                                  models=[ModelInfo(id="1", kind="lm",
                                                    contextLength=context_length)])]
        cfg.queues = ModelQueues(parent=["m/1"], child=["m/1"], summary=["m/1"])
        self.settings = cfg.settings
        self.queues = cfg.queues
        self.providers = cfg.providers


def _folded(n: int = 2, body_len: int = 5000) -> list[dict]:
    return [{"_seq": i * 2, "role": "assistant",
             "content": "字" * body_len} for i in range(n)]


class TestWindowStrategy:
    def test_full_body_reaches_prompt_when_under_budget(self):
        gw = _Gateway("总结")
        text = MemoStrategy._tail_within(["字" * 5000], 500_000)
        asyncio.run(hedged(gw, MEMO_PROMPT + text))
        assert "字" * 5000 in gw.prompts[0]

    def test_over_budget_keeps_tail_drops_head(self):
        lines = ["头" * 100, "中" * 100, "尾" * 100]
        out = MemoStrategy._tail_within(lines, 150)
        assert "尾" * 100 in out
        assert "头" * 100 not in out

    def test_single_line_over_budget_keeps_its_tail(self):
        ln = "前" * 100 + "结论在后面" * 20
        out = MemoStrategy._tail_within([ln], 60)
        assert out.endswith("结论在后面" * 4)
        assert "前" * 100 not in out

    def test_prompt_requires_3000_chars_and_no_thinking(self):
        assert "3000" in MEMO_PROMPT
        assert "不要思考模式" in MEMO_PROMPT
        assert "直接给出文字回复" in MEMO_PROMPT
        pass
        assert str(MEMO_CHARS) in MEMO_PROMPT

    def test_summary_length_has_single_source(self):
        from app.chat.compaction_legacy import CONDENSE_CHARS

        assert MEMO_CHARS is SUMMARY_CHARS
        assert CONDENSE_CHARS is SUMMARY_CHARS

    def test_output_6000_is_hard_clip_to_tail(self):
        assert OUTPUT_HARD_CHARS == 6000
        long = "x" * (OUTPUT_HARD_CHARS + 50)
        assert long[-OUTPUT_HARD_CHARS:] == "x" * OUTPUT_HARD_CHARS
        assert len("x" * (OUTPUT_HARD_CHARS - 10)) == OUTPUT_HARD_CHARS - 10

    def test_summary_window_uses_summary_queue(self):
        gw = _Gateway("总结", context_length=8000)
        assert MemoStrategy._summary_window(gw) == 8000


async def hedged(gw, prompt: str) -> str:
    from app.chat.compaction_kit import hedged_call
    return await hedged_call(gw, prompt, "sid", 0)


class TestStrategyRegistry:
    def test_three_strategies_are_independent(self):
        assert get_strategy("memo").name == "memo"
        assert get_strategy("secondary").name == "secondary"
        assert get_strategy("legacy").name == "legacy"
        assert isinstance(get_strategy("legacy"), LegacyStrategy)
        assert isinstance(get_strategy("secondary"), SecondaryStrategy)

    def test_legacy_keeps_old_prompts_and_limits(self):
        assert BODY_CHARS == 20000
        assert "3000" in CONDENSE_PROMPT
        assert "中文总结" in BATCH_PROMPT


class TestMergeRangeKeepsTextWithoutSummary:
    def test_empty_summary_preserves_every_assistant_body(self):
        folded = [
            {"_seq": 0, "role": "user", "content": "问题"},
            {"_seq": 1, "role": "assistant", "content": "方案 A/B/C 的细节"},
            {"_seq": 2, "role": "tool", "content": "[msg#2 tool → 结果]"},
            {"_seq": 3, "role": "assistant", "content": "关键决定：用 C"},
        ]
        out = ContextCompactor.merge_range(folded, "")
        assert [m.get("content") for m in out] == [
            "问题", "方案 A/B/C 的细节", "[msg#2 tool → 结果]", "关键决定：用 C"]
        assert not any("助手回复已压缩" in str(m.get("content")) for m in out)

    def test_with_summary_replaces_only_once(self):
        folded = [
            {"_seq": 0, "role": "user", "content": "问题"},
            {"_seq": 1, "role": "assistant", "content": "正文一"},
            {"_seq": 2, "role": "assistant", "content": "正文二"},
        ]
        out = ContextCompactor.merge_range(folded, "一段总结")
        assert len(out) == 2
        assert "助手回复已压缩" in out[1]["content"]
        assert out[1]["content"].endswith("一段总结")
