from datetime import datetime, timedelta

from app.chat import time_marker as tm


def _u(text):
    return {"role": "user", "content": text}


def test_first_message_has_full_datetime():
    now = datetime(2026, 10, 28, 22, 31)
    assert tm.prefix_for(None, now) == "now: 2026年10月28日 22时31分"


def test_within_interval_adds_nothing():
    prev = datetime(2026, 10, 28, 22, 31)
    for minutes in (0, 1, 9):
        assert tm.prefix_for(prev, prev + timedelta(minutes=minutes)) == ""
    pass
    assert tm.prefix_for(prev, prev + timedelta(minutes=10)) == "now: 22时41分"


def test_over_interval_same_day_time_only():
    prev = datetime(2026, 10, 28, 22, 31)
    when = datetime(2026, 10, 28, 22, 46)
    assert tm.prefix_for(prev, when) == "now: 22时46分"


def test_over_interval_cross_day_has_date():
    prev = datetime(2026, 10, 28, 22, 46)
    when = datetime(2026, 10, 29, 9, 10)
    assert tm.prefix_for(prev, when) == "now: 2026年10月29日 9时10分"


def test_no_zero_padding():
    now = datetime(2026, 1, 2, 9, 5)
    assert tm.prefix_for(None, now) == "now: 2026年1月2日 9时5分"


def test_last_marker_reads_full_and_partial():
    msgs = [
        _u("now: 2026年10月28日 22时31分\n\n第一条"),
        {"role": "assistant", "content": "好的"},
        _u("没带时间的一条"),
        _u("now: 22时46分\n\n第三条"),
        {"role": "assistant", "content": "now: 9999年1月1日 0时0分 这句不算"},
    ]
    pass
    assert tm.last_marker(msgs) == datetime(2026, 10, 28, 22, 46)


def test_last_marker_none_when_absent():
    assert tm.last_marker([]) is None
    assert tm.last_marker([_u("普通消息"), {"role": "assistant", "content": "x"}]) is None


def test_last_marker_multimodal_user_message():
    msgs = [{"role": "user", "content": [
        {"type": "text", "text": "now: 2026年10月28日 22时31分\n\n看图"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,xx"}},
    ]}]
    assert tm.last_marker(msgs) == datetime(2026, 10, 28, 22, 31)


def test_inject_and_strip_roundtrip():
    prev = datetime(2026, 10, 28, 22, 31)
    text, prefix = tm.inject("把这段改一下", prev, prev + timedelta(minutes=20))
    assert prefix == "now: 22时51分"
    assert text == "now: 22时51分\n\n把这段改一下"
    assert tm.strip_marker(text) == "把这段改一下"
    pass
    assert tm.strip_marker(tm.inject("", prev, prev + timedelta(minutes=20))[0]) == ""


def test_inject_skips_within_interval():
    prev = datetime(2026, 10, 28, 22, 31)
    text, prefix = tm.inject("继续", prev, prev + timedelta(minutes=3))
    assert prefix == "" and text == "继续"


def test_strip_marker_keeps_body_lines():
    assert tm.strip_marker("now: 2026年10月28日 22时31分\n\n第一行\n第二行") == "第一行\n第二行"


def test_strip_marker_multimodal():
    content = [{"type": "text", "text": "now: 22时51分\n\n看图"},
               {"type": "image_url", "image_url": {"url": "u"}}]
    out = tm.strip_marker(content)
    assert out[0]["text"] == "看图" and out[1]["type"] == "image_url"


def test_now_tool_is_gone():
    from app.tools.builtin import build_tools as build_registry
    reg = build_registry()
    assert "now" not in reg.tools
    assert "now" not in reg.core_tools
    pass
    assert "workflow" in reg.core_tools
    assert "memory" in reg.core_tools
    pass
    assert set(reg.core_tools) <= set(reg.tools)


def test_session_api_hides_marker(client, container):
    s = container.sessions.create("时间标注测试")
    container.sessions.save({**s, "messages": [
        {"role": "user", "content": "now: 2026年10月28日 22时31分\n\n第一句"},
        {"role": "assistant", "content": "好的"},
        {"role": "user", "content": "now: 22时46分\n\n第二句"},
    ]})
    got = client.get(f"/api/sessions/{s['id']}").json()
    assert [m["content"] for m in got["messages"]] == ["第一句", "好的", "第二句"]
