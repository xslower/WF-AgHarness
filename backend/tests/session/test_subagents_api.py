import json

from app.agent.subagents import SubAgentRecord
from app.util import status as st


def _seed(client, cwd, sa_id="sa_api_hist", parent="p_api"):
    pass
    from app.chat.sessions import SessionStore
    runner = client.app.state.container.runner
    if runner.sessions is None:
        runner.sessions = SessionStore()
    sessions = runner.sessions
    pass
    pass
    sessions.create(title="父会话", project=str(cwd))
    sid = max(sessions.list(project=str(cwd)), key=lambda s: int(s["id"]))["id"]
    rec = SubAgentRecord(
        id=sa_id, parent_id=sid, project=str(cwd),
        task="上个进程的任务", child_session_id="sub_api_hist",
        rounds_limit=20, rounds_used=2)
    rec.ensure()
    rec.append_message({"role": "assistant", "content": "历史结论"})
    rec.finish(st.DONE, "历史结论")
    return sid, rec


def test_api_get_history_without_project(client, tmp_path):
    parent, rec = _seed(client, tmp_path)
    r = client.get(f"/api/subagents/{rec.id}?parent={parent}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == rec.id
    assert body["status"] == st.DONE
    assert body["messages"][0]["content"] == "历史结论"


def test_api_result_history_without_project(client, tmp_path):
    parent, rec = _seed(client, tmp_path)
    r = client.get(f"/api/subagents/{rec.id}/result?parent={parent}")
    assert r.status_code == 200, r.text
    assert r.json()["content"] == "历史结论"


def test_api_list_history_with_project(client, tmp_path):
    parent, rec = _seed(client, tmp_path)
    r = client.get(f"/api/subagents?parent={parent}&project={tmp_path}")
    assert r.status_code == 200, r.text
    assert rec.id in [x["id"] for x in r.json()]


def test_api_message_history_queues_instruction(client, tmp_path):
    parent, rec = _seed(client, tmp_path)
    r = client.post(f"/api/subagents/{rec.id}/message",
                    json={"text": "继续", "parent": parent})
    assert r.status_code == 200, r.text
    assert r.json()["queued"] == "继续"
    assert "extend" in r.json()["hint"]


def test_api_stale_result_path_still_readable(client, tmp_path):
    parent, rec = _seed(client, tmp_path)
    meta = json.loads((rec.dir / "meta.json").read_text("utf-8"))
    meta["result_path"] = "/失效/旧挂载/result.md"
    (rec.dir / "meta.json").write_text(json.dumps(meta), "utf-8")
    r = client.get(f"/api/subagents/{rec.id}/result?parent={parent}")
    assert r.status_code == 200 and r.json()["content"] == "历史结论"
