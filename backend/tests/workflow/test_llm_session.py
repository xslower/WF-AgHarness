from __future__ import annotations

from app.workflow.llm_session import HISTORY_MAX_CHARS, LLMSession, WF_NODE_KIND, trim_history


class _Sess:

    def __init__(self):
        self.rows: dict[str, dict] = {}
        self._n = 0

    def create(self, title="", project="", kind="", origin=""):
        self._n += 1
        sid = f"s{self._n}"
        self.rows[sid] = {"id": sid, "title": title, "project": project,
                          "created_at": 100.0 + self._n, "messages": [],
                          "kind": kind, "origin": origin}
        return dict(self.rows[sid])

    def find_active(self, project, kind, origin):
        hits = [r for r in self.rows.values()
                if r["kind"] == kind and r["origin"] == origin]
        return hits[-1] if hits else None

    def get(self, sid):
        row = self.rows.get(sid)
        return dict(row) if row else None

    def save(self, s):
        row = self.rows.setdefault(s["id"], {})
        row.update({k: v for k, v in s.items() if k != "messages"})
        row["messages"] = list(s.get("messages") or [])


def _user(text):
    return {"role": "user", "content": text}


def _assistant(text, calls=None):
    m = {"role": "assistant", "content": text}
    if calls:
        m["tool_calls"] = calls
    return m


pass
def test_continue_latest_session_by_default():
    store = _Sess()
    a = LLMSession(store, "/p", "bugfix")
    assert a.resolve("") == "s1"
    b = LLMSession(store, "/p", "bugfix")
    assert b.resolve("") == "s1"
    assert store.rows["s1"]["kind"] == "wf-session"
    assert store.rows["s1"]["origin"] == "bugfix"


def test_new_session_forces_fresh_context():
    store = _Sess()
    LLMSession(store, "/p", "bugfix").resolve("")
    assert LLMSession(store, "/p", "bugfix").resolve("new") == "s2"


def test_explicit_session_id_wins():
    store = _Sess()
    store.create(title="x", kind="wf-session", origin="bugfix")
    store.create(title="y", kind="wf-session", origin="bugfix")
    assert LLMSession(store, "/p", "bugfix").resolve("s1") == "s1"


pass
def test_node_history_roundtrip_and_accumulates():
    store = _Sess()
    ls = LLMSession(store, "/p", "bugfix")
    ls.resolve("")
    ls.save("locator", [_user("读 a.py"), _assistant("根因在 X")])

    again = LLMSession(store, "/p", "bugfix")
    again.resolve("")
    hist = again.history("locator")
    assert [m["role"] for m in hist] == ["user", "assistant"]
    assert hist[0]["content"] == "读 a.py"

    pass
    again.save("locator", hist + [_user("再改一处"), _assistant("已改")])
    third = LLMSession(store, "/p", "bugfix")
    third.resolve("")
    hist2 = third.history("locator")
    assert len(hist2) == 4
    assert store.rows[again.node_sid("locator")]["kind"] == WF_NODE_KIND


def test_system_message_is_never_persisted():
    store = _Sess()
    ls = LLMSession(store, "/p", "wf")
    ls.resolve("")
    ls.save("n1", [{"role": "system", "content": "旧规则"},
                   _user("任务"), _assistant("好的")])
    assert all(m["role"] != "system"
               for m in store.rows[ls.node_sid("n1")]["messages"])


pass
def test_trim_never_splits_tool_chain():
    calls = [{"id": "c1", "type": "function",
              "function": {"name": "f_read", "arguments": "{}"}}]
    msgs = [
        _user("第一轮" + "x" * 500),
        _assistant(None, calls),
        {"role": "tool", "tool_call_id": "c1", "content": "y" * 500},
        _assistant("第一轮结论" + "z" * 500),
        _user("第二轮"),
        _assistant("第二轮结论"),
    ]
    kept = trim_history(msgs, budget=1200)
    assert kept[0]["role"] == "user"
    roles = [m["role"] for m in kept]
    pass
    for i, role in enumerate(roles):
        if role == "tool":
            assert any(m.get("tool_calls") for m in kept[:i]), "tool 消息被切丢了调用方"


def test_trim_keeps_everything_under_budget():
    msgs = [_user("a"), _assistant("b")]
    assert trim_history(msgs, budget=HISTORY_MAX_CHARS) == msgs
    assert trim_history([], budget=10) == []
