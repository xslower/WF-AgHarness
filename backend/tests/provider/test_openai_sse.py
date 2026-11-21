from __future__ import annotations

import asyncio

import pytest

from app.provider.errors import RateLimitedError
from app.provider.adapters.openai_sse import chunk_events, delta_events, error_from_status, parse_sse


def _run(agen) -> list[dict]:
    out: list[dict] = []

    async def go():
        async for ev in agen:
            out.append(ev)

    asyncio.run(go())
    return out


async def _lines(*items: str):
    for it in items:
        yield it


def _collect_sse(*items: str) -> list[dict]:
    return _run(parse_sse(_lines(*items)))


pass
def test_reason_field_names_all_recognized():
    for field in ("reasoning_content", "reasoning", "thinking"):
        evs = delta_events({field: "想"})
        assert evs == [{"type": "reason", "text": "想"}], field


def test_text_and_reason_together_keep_order():
    evs = delta_events({"reasoning_content": "想", "content": "答"})
    assert [e["type"] for e in evs] == ["reason", "text"]


def test_tool_name_arrives_before_arguments():
    evs = delta_events({"tool_calls": [
        {"index": 0, "id": "c1",
         "function": {"name": "read_file", "arguments": '{"pa'}}]})
    assert evs[0]["type"] == "tool_meta" and evs[1]["type"] == "tool_args"
    assert evs[0]["tool_index"] == evs[1]["tool_index"] == 0
    assert evs[1]["text"] == '{"pa'


def test_tool_args_without_name_is_kept():
    fragment = "th}}"
    evs = delta_events({"tool_calls": [{"index": 2, "function": {"arguments": fragment}}]})
    assert evs == [{"type": "tool_args", "text": fragment, "tool_index": 2}]


def test_empty_delta_yields_nothing():
    assert delta_events({}) == []


def test_usage_missing_fields_default_to_zero():
    evs = chunk_events({"usage": {"prompt_tokens": None}, "choices": []})
    assert evs == [{"type": "usage",
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0}}]


pass
def test_parse_sse_skips_comments_and_blank_lines():
    body = 'data: {"choices":[{"delta":{"content":"a"}}]}'
    evs = _collect_sse(": keep-alive", "", body, "data: [DONE]")
    assert evs == [{"type": "text", "text": "a"}]


def test_parse_sse_broken_frame_is_skipped():
    evs = _collect_sse('data: {"choices":[{"delta":{"content":"a"}}]}',
                       "data: {broken",
                       'data: {"choices":[{"delta":{"content":"b"}}]}',
                       "data: [DONE]")
    assert [e["text"] for e in evs if e["type"] == "text"] == ["a", "b"]


def test_done_alone_does_not_stop_the_stream():
    evs = _collect_sse('data: {"choices":[{"delta":{"content":"a"}}]}',
                       "data: [DONE]",
                       'data: {"choices":[{"delta":{"content":"never"}}]}')
    assert [e["text"] for e in evs if e["type"] == "text"] == ["a", "never"]


def test_done_after_finish_reason_is_terminal():
    evs = _collect_sse(
        'data: {"choices":[{"delta":{"content":"a"},"finish_reason":"stop"}]}',
        "data: [DONE]",
        'data: {"choices":[{"delta":{"content":"之后的数据不读"}}]}')
    assert [e["text"] for e in evs if e["type"] == "text"] == ["a"]


def test_parse_sse_multiple_choices():
    evs = _collect_sse('data: {"choices":[{"delta":{"content":"a"}},'
                       '{"delta":{"content":"b"}}]}', "data: [DONE]")
    assert [e["text"] for e in evs if e["type"] == "text"] == ["a", "b"]


pass
def test_finish_reason_counts_as_complete():
    evs = chunk_events({"choices": [{"delta": {"content": "a"},
                                     "finish_reason": "stop"}]})
    assert evs[-1] == {"type": "end", "text": "stop"}


def test_sse_error_frame_raises():
    with pytest.raises(RuntimeError):
        _collect_sse('data: {"error":{"message":"upstream exploded"}}')


pass
@pytest.mark.parametrize("status", [429, 502, 503, 529])
def test_overload_codes_are_rate_limited(status):
    assert isinstance(error_from_status(status, "", "p/m"), RateLimitedError)


@pytest.mark.parametrize("status", [200, 201, 204])
def test_success_codes_return_none(status):
    assert error_from_status(status, "", "p/m") is None


def test_other_4xx_is_plain_error_with_detail():
    err = error_from_status(400, "bad request body", "p/m")
    assert err is not None and not isinstance(err, RateLimitedError)
    assert "400" in str(err) and "bad request body" in str(err)


def test_detail_is_capped_at_2000():
    from app.provider.adapters.openai_sse import ERROR_DETAIL_LIMIT
    assert ERROR_DETAIL_LIMIT == 2000
    err = error_from_status(500, "x" * 5000, "p/m")
    assert str(err).count("x") == 2000


def test_short_detail_kept_intact():
    body = ('{"error":{"message":"Provider returned error","code":400,'
            '"metadata":{"raw":"Validation: messages[95].tool_calls[0]'
            '.function.arguments must be a valid JSON object string",'
            '"provider_name":"Nvidia"}}}' + "y" * 400)
    err = error_from_status(400, body, "p/m")
    text = str(err)
    assert "provider_name" in text and body in text
