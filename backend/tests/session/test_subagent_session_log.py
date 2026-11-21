from __future__ import annotations

import json

from app.agent.subagents import SubAgentRecord
from app.util import status as st


def _rec(tmp_path, rid="sa_page"):
    rec = SubAgentRecord(id=rid, parent_id="p", project=str(tmp_path),
                         task="分页任务", child_session_id="sub_page",
                         rounds_limit=20, rounds_used=2)
    rec.ensure()
    return rec


def _pair(rec, i: int) -> None:
    cid = f"c{i}"
    rec.append_message({"role": "assistant", "content": "",
                        "tool_calls": [{"id": cid, "type": "function",
                                        "function": {"name": "f_read",
                                                     "arguments": '{"path":"a.py"}'}}]})
    rec.append_message({"role": "tool", "tool_call_id": cid,
                        "content": f"第 {i} 个结果"})


def test_pagination_keeps_call_and_result_in_same_window(tmp_path):
    rec = _rec(tmp_path)
    rec.append_message({"role": "user", "content": "任务"})
    for i in range(60):
        _pair(rec, i)
    rec.finish(st.DONE, "结论")

    msgs: list[dict] = []
    offset = 0
    for _ in range(100):
        page = rec.read_messages(offset, 100)
        msgs.extend(page["messages"])
        nxt = page["next_offset"]
        if nxt is None:
            break
        offset = nxt

    assert len(msgs) == 121
    ids = {m["tool_call_id"] for m in msgs if m["role"] == "tool"}
    for m in msgs:
        for tc in m.get("tool_calls") or []:
            assert tc["id"] in ids, f"{tc['id']} 没有配到结果"


def test_first_page_alone_is_what_caused_the_bug(tmp_path):
    rec = _rec(tmp_path, "sa_page2")
    rec.append_message({"role": "user", "content": "任务"})
    for i in range(60):
        _pair(rec, i)
    rec.finish(st.DONE, "结论")

    page = rec.read_messages(0, 100)
    assert page["next_offset"] == 100
    got_ids = {m["tool_call_id"] for m in page["messages"] if m["role"] == "tool"}
    dangling = [tc["id"] for m in page["messages"]
                for tc in (m.get("tool_calls") or []) if tc["id"] not in got_ids]
    assert dangling, "窗口边界切在调用之后，这就是用户看到的一排空壳"


def test_events_skip_tool_plumbing(tmp_path):
    rec = _rec(tmp_path, "sa_ev")
    for t in ("tool_start", "tool_output", "tool_end", "text", "reason"):
        rec.append_event({"type": t, "name": "f_read", "text": "x"})
    rec.append_event({"type": "notice", "text": "限额提示"})
    rec.append_event({"type": "error", "text": "出错了"})
    rec.finish(st.DONE, "结论")

    out = rec.read_messages()
    types = [e["type"] for e in out["events"]]
    assert types == ["notice", "error"]


def test_events_keep_meaningful_ones(tmp_path):
    rec = _rec(tmp_path, "sa_ev2")
    rec.append_event({"type": "notice", "text": "已切换到只读"})
    rec.finish(st.DONE, "结论")
    assert [e["text"] for e in rec.read_messages()["events"]] == ["已切换到只读"]


def test_event_filter_survives_disk_reload(tmp_path):
    rec = _rec(tmp_path, "sa_disk")
    rec.append_event({"type": "tool_end", "name": "grep", "text": "命中 3 处"})
    rec.append_event({"type": "notice", "text": "提示"})
    rec.finish(st.DONE, "结论")

    from app.agent.subagent_access import SubAgentAccess
    fresh = SubAgentAccess(None, None, str(tmp_path))
    got = fresh.get("sa_disk", "p")
    assert got is not None
    assert [e["type"] for e in got.read_messages()["events"]] == ["notice"]


def test_meta_json_still_records_status(tmp_path):
    rec = _rec(tmp_path, "sa_meta")
    rec.finish(st.DONE, "结论")
    meta = json.loads((rec.dir / "meta.json").read_text("utf-8"))
    assert meta["status"] == st.DONE and meta["id"] == "sa_meta"
