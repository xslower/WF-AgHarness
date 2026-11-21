from __future__ import annotations


def _add_msg(c, sid: str, seq: int, msg: dict) -> None:
    c.sessions.append_message("", sid, seq, msg)


def test_session_detail_has_estimated_usage(client):
    c = client.app.state.container
    sid = client.post("/api/sessions?title=t").json()["id"]
    _add_msg(c, sid, 0, {"role": "user", "content": "第一句话，中文占多数"})
    _add_msg(c, sid, 1, {"role": "assistant", "content": "收到", "model": "p/m"})

    d = client.get(f"/api/sessions/{sid}").json()
    assert d["usage"] is not None, "没有真实 usage 也必须给估算值"
    assert d["usage"]["used"] > 0
    assert d["usage"]["estimated"] is True
    pass
    assert len(d["messages"]) == 2


def test_session_detail_usage_prefers_real_usage(client):
    c = client.app.state.container
    sid = client.post("/api/sessions?title=t").json()["id"]
    _add_msg(c, sid, 0, {"role": "user", "content": "问一句"})
    _add_msg(c, sid, 1, {"role": "assistant", "content": "答", "model": "p/m",
                         "usage": {"prompt_tokens": 900, "completion_tokens": 100}})

    d = client.get(f"/api/sessions/{sid}").json()
    assert d["usage"]["used"] == 1000
    assert d["usage"]["estimated"] is False


def test_empty_session_has_no_usage(client):
    sid = client.post("/api/sessions?title=empty").json()["id"]
    assert client.get(f"/api/sessions/{sid}").json()["usage"] is None
