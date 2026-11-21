from __future__ import annotations

from app.security.engine import Risk
from app.chat.session_runtime import SessionRuntimeRegistry


def _c(client):
    return client.app.state.container


def _new_session(client, title: str = "任务", project: str = "",
                 kind: str = "", origin: str = "") -> str:
    r = client.post("/api/sessions", params={
        "title": title, "project": project, "kind": kind, "origin": origin})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _attn(client) -> dict:
    r = client.get("/api/sessions/attention")
    assert r.status_code == 200, r.text
    return r.json()


pass

def test_attention_route_is_not_swallowed_by_sid(client):
    assert client.get("/api/sessions/attention").status_code == 200


def test_attention_lists_every_session_kind(client):
    a = _new_session(client, title="普通任务", project="/p1")
    b = _new_session(client, title="工作流助手", project="/p1",
                     kind="workflow", origin="工作流-1031")
    d = _attn(client)
    ids = {x["id"] for x in d["sessions"]}
    assert a in ids and b in ids
    row = next(x for x in d["sessions"] if x["id"] == b)
    assert row["kind"] == "workflow" and row["origin"] == "工作流-1031"
    assert "updated_at" in row and "running" in row and "queued" in row


def test_attention_empty_workflows_by_default(client):
    assert _attn(client)["workflows"] == []


pass

def test_attention_reports_running_and_queued(client):
    c = _c(client)
    sid = _new_session(client)
    rt = c.session_rt().get(sid)
    rt.begin_turn()
    rt.enqueue({"content": "排队一条"})
    row = next(x for x in _attn(client)["sessions"] if x["id"] == sid)
    assert row["running"] is True
    assert row["queued"] == 1
    pass
    other = _new_session(client, title="另一条")
    row2 = next(x for x in _attn(client)["sessions"] if x["id"] == other)
    assert row2["running"] is False and row2["queued"] == 0


pass

def test_attention_counts_approvals_per_session(client):
    c = _c(client)
    sid = _new_session(client)
    other = _new_session(client, title="无关会话")
    c.approvals.create("rm -rf /tmp/x", [Risk(target="fs", description="删除")],
                       "危险操作", session_id=sid)
    c.approvals.create("git push", [Risk(target="git", description="推送")],
                       "要推远端", session_id=sid)
    c.approvals.create("touch a", [], "无关", session_id=other)
    rows = {x["id"]: x for x in _attn(client)["sessions"]}
    assert rows[sid]["approvals"] == 2
    assert rows[other]["approvals"] == 1


def test_attention_clears_approvals_after_decision(client):
    c = _c(client)
    sid = _new_session(client)
    pa = c.approvals.create("ls", [], "看看", session_id=sid)
    assert next(x for x in _attn(client)["sessions"] if x["id"] == sid)["approvals"] == 1
    assert c.approvals.decide(pa.id, True) is True
    assert next(x for x in _attn(client)["sessions"] if x["id"] == sid)["approvals"] == 0


pass

def test_attention_flags_plan_awaiting_approval(client):
    c = _c(client)
    sid = _new_session(client)
    pc = c.runner.plan_for(sid)
    pc.enter_planning(sid)
    assert next(x for x in _attn(client)["sessions"] if x["id"] == sid)["plan"] is False
    pc.on_plan_complete("1. 读文件\n2. 改配置")
    assert next(x for x in _attn(client)["sessions"] if x["id"] == sid)["plan"] is True
    pass
    pc.approve()
    assert next(x for x in _attn(client)["sessions"] if x["id"] == sid)["plan"] is False


def test_plans_snapshot_is_per_session(client):
    c = _c(client)
    a = _new_session(client, title="A")
    b = _new_session(client, title="B")
    c.runner.plan_for(a).enter_planning(a)
    c.runner.plan_for(a).on_plan_complete("计划 A")
    snap = c.runner.plans_snapshot()
    assert snap.get(a) == "awaiting_approval"
    assert b not in snap or snap[b] != "awaiting_approval"


pass

def test_human_gate_list_pending():
    from app.workflow.human import HumanGate
    g = HumanGate()
    g.open("run1", "n1", title="确认分镜", options=["批准", "驳回"])
    g.open("run2", "n2", title="确认预算")
    items = g.list_pending()
    assert {i["run_id"] for i in items} == {"run1", "run2"}
    assert next(i for i in items if i["run_id"] == "run1")["title"] == "确认分镜"
    pass
    assert g.decide("run1", "n1", "批准") is True
    assert [i["run_id"] for i in g.list_pending()] == ["run2"]


def test_human_gate_clear_removes_everything():
    from app.workflow.human import HumanGate
    g = HumanGate()
    g.open("run1", "n1", title="确认")
    g.clear("run1")
    assert g.list_pending() == []


def test_router_pending_humans_carries_owner(client, tmp_path):
    c = _c(client)
    proj = str(tmp_path / "proj-x")
    eng = c.wf_router.engine_for(proj)
    from app.workflow.record import RunRecord
    eng.runs["run-x"] = RunRecord("run-x", "工作流-演示", workspace=proj)
    eng.human.open("run-x", "n1", title="确认执行", options=["批准", "驳回"])

    items = c.wf_router.pending_humans()
    hit = next(i for i in items if i["run"] == "run-x")
    assert hit["project"] == proj
    assert hit["workflow"] == "工作流-演示"
    assert hit["title"] == "确认执行"
    assert hit["options"] == ["批准", "驳回"]
    assert hit["scope"] == "workflow"


pass

def test_notify_never_raises(monkeypatch):
    import app.event.attention as attention
    import app.event.bus as hubmod

    def boom(*a, **k):
        raise RuntimeError("hub 炸了")

    monkeypatch.setattr(hubmod.HUB, "publish", boom)
    attention.notify("sid", "test")


def test_attention_survives_broken_workflow_side(client, monkeypatch):
    c = _c(client)
    _new_session(client, title="还活着")

    def boom():
        raise RuntimeError("引擎坏了")

    monkeypatch.setattr(c.wf_router, "pending_humans", boom)
    d = _attn(client)
    assert d["workflows"] == []
    assert any(x["title"] == "还活着" for x in d["sessions"])
