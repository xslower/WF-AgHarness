import json
import time

from app.store.runs import RunStore, STALE_RUN_ERROR


def _meta(store: RunStore, rid: str, **kw) -> None:
    store.prepare(rid, kw.pop("workflow", "wf"))
    data = json.loads((store.paths.run_dir(rid) / "meta.json").read_text("utf-8"))
    data.update(kw)
    store.write_meta(rid, data)


def test_purge_legacy_runs_keeps_session_runs(tmp_path):
    store = RunStore(str(tmp_path))
    _meta(store, "old1", status="done")
    _meta(store, "old2", status="failed")
    _meta(store, "new1", status="done", session="20261105-000000-abc")

    assert store.purge_legacy_runs() == 2
    left = {i["id"] for i in store.list_runs()}
    assert left == {"new1"}


def test_purge_drops_runs_whose_session_is_gone(tmp_path):
    store = RunStore(str(tmp_path))
    _meta(store, "alive", status="done", session="s-alive")
    _meta(store, "orphan", status="done", session="s-dead")

    assert store.purge_legacy_runs(live_sessions={"s-alive"}) == 1
    assert {i["id"] for i in store.list_runs()} == {"alive"}



def test_sweep_stale_marks_running_as_cancelled(tmp_path):
    store = RunStore(str(tmp_path))
    _meta(store, "stale", status="running",
          nodes={"s1": {"status": "running"}, "s2": {"status": "done"}})
    _meta(store, "live", status="running", session="s")
    _meta(store, "finished", status="done")

    changed = store.sweep_stale(live_ids={"live"})
    assert changed == 1

    stale = store.load_run("stale")
    assert stale["status"] == "cancelled"
    assert stale["error"] == STALE_RUN_ERROR
    assert stale["finished"]
    assert stale["nodes"]["s1"]["status"] == "cancelled"
    assert stale["nodes"]["s2"]["status"] == "done"

    pass
    assert store.load_run("live")["status"] == "running"
    assert store.load_run("finished")["status"] == "done"


def test_sweep_stale_then_cancel_succeeds(tmp_path):
    from app.workflow.engine import WorkflowEngine

    store = RunStore(str(tmp_path))
    _meta(store, "stale", status="running")
    store.sweep_stale()

    eng = WorkflowEngine(workspace=str(tmp_path))
    eng.store = store
    res = eng.cancel("stale")
    assert res["ok"] is False
    assert "已结束" in res["reason"]
    assert not res["status"] or res["status"] == "cancelled"
