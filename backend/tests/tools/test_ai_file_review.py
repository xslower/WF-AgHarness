from __future__ import annotations

from app.security.engine import Decision, PolicyEngine, Risk
from app.security.wiring import file_diff_payload, risks_payload


class _Gw:
    def __init__(self, reply="", raises=None):
        self.reply = reply
        self.raises = raises
        self.calls: list = []

    async def call_utility(self, kind, messages):
        self.calls.append((kind, messages))
        if self.raises:
            raise self.raises
        return self.reply


HUNKS = [{"old": "a", "new": "b"}]


async def test_pass_verdict_allows():
    eng = PolicyEngine(gateway=_Gw('{"verdict":"pass","risks":[]}'))
    v = await eng.ai_path_review("write", ["/p/a.py"], "/p")
    assert v.decision == Decision.ALLOW


async def test_block_verdict_reviews():
    eng = PolicyEngine(gateway=_Gw('{"verdict":"block","risks":[]}'))
    v = await eng.ai_path_review("write", ["/p/a.py"], "/p")
    assert v.decision == Decision.REVIEW


async def test_no_gateway_reviews():
    v = await PolicyEngine().ai_path_review("write", ["/p/a.py"], "/p")
    assert v.decision == Decision.REVIEW


async def test_gateway_exception_reviews():
    eng = PolicyEngine(gateway=_Gw(raises=RuntimeError("timeout")))
    v = await eng.ai_path_review("write", ["/p/a.py"], "/p")
    assert v.decision == Decision.REVIEW
    assert "timeout" in v.reason


async def test_unparseable_reply_reviews():
    eng = PolicyEngine(gateway=_Gw("我觉得这个修改没问题"))
    v = await eng.ai_path_review("write", ["/p/a.py"], "/p")
    assert v.decision == Decision.REVIEW


async def test_verdict_with_extra_text_still_parsed():
    eng = PolicyEngine(gateway=_Gw('好的，我的判断是：\n{"verdict":"pass"}\n以上。'))
    v = await eng.ai_path_review("write", ["/p/a.py"], "/p")
    assert v.decision == Decision.ALLOW


async def test_unknown_verdict_value_reviews():
    eng = PolicyEngine(gateway=_Gw('{"verdict":"maybe"}'))
    v = await eng.ai_path_review("write", ["/p/a.py"], "/p")
    assert v.decision == Decision.REVIEW


async def test_prompt_includes_action_paths_and_intent():
    gw = _Gw('{"verdict":"pass"}')
    await PolicyEngine(gateway=gw).ai_path_review(
        "write", ["/p/conf.py"], "/p", intent="改默认值")
    kind, messages = gw.calls[0]
    assert kind == "review"
    body = messages[0]["content"]
    assert "write" in body and "/p/conf.py" in body and "改默认值" in body


pass
def test_risks_payload_shape():
    risks = [Risk(target="/p/a", description="覆盖", severity="high")]
    assert risks_payload(risks) == [
        {"target": "/p/a", "description": "覆盖", "severity": "high"}]


def test_risks_payload_empty():
    assert risks_payload([]) == []


def test_file_diff_payload_shape():
    from pathlib import Path
    payload = file_diff_payload(Path("/p/a.py"), HUNKS)
    assert payload == {"path": "/p/a.py", "hunks": HUNKS}


pass
import json


def test_llm_severity_normalized_to_three_tiers():

    from app.security.engine import PolicyEngine

    def sevs(raw_list):
        text = "```json\n" + json.dumps({
            "verdict": "block", "risks": raw_list}) + "\n```"
        return [r.severity for r in PolicyEngine._parse_ai(text).risks]

    dirty = [{"target": "x", "severity": v}
             for v in ("critical", "HIGH", "", None, 123)]
    assert sevs(dirty) == ["medium"] * 5
    good = [{"target": "x", "severity": v}
            for v in ("low", "medium", "high")]
    assert sevs(good) == ["low", "medium", "high"]
    pass
    assert sevs(["junk", 1, {"severity": "high"}]) == ["high"]
