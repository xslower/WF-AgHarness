from __future__ import annotations

from app.regression import make_event
from app.regression.adapters import SimulationBackend
from app.regression.collector import metric_from
from app.regression.model import ProbeSnapshot, Scenario, Step
from app.regression.probes import check_status, evidence_complete, run_checks


def _snap(**kw):
    base = dict(ts="", reported_status="running", pid=42, pid_alive=True,
                heartbeat_seq=3, heartbeat_times=(0.0, 1.0, 2.0),
                output_complete=True, output_schema_ok=True)
    base.update(kw)
    return ProbeSnapshot(**base)


def test_alive_probe_catches_dead_process_with_lie_status():
    s = Scenario("X", "x", steps=(Step("assert", checks=("alive_by_pid",)),))
    snap = _snap(pid_alive=False, reported_status="running")
    checks = run_checks(s, (snap,))
    assert checks[0].name == "alive_by_pid" and not checks[0].ok


def test_status_matches_reality_cross_checks_output():
    assert check_status(_snap(reported_status="done", pid_alive=True)).ok
    assert not check_status(_snap(reported_status="done",
                                  output_complete=False)).ok
    assert check_status(_snap(reported_status="failed", pid_alive=False,
                              error_code="E_X")).ok
    assert not check_status(_snap(reported_status="failed")).ok


def test_heartbeat_must_be_strictly_monotonic():
    s = Scenario("X", "x", steps=(Step("assert", checks=("heartbeat_monotonic",)),))
    assert run_checks(s, (_snap(heartbeat_seq=1), _snap(heartbeat_seq=2)))[0].ok
    assert not run_checks(s, (_snap(heartbeat_seq=2), _snap(heartbeat_seq=2)))[0].ok


def test_evidence_incomplete_blocks_pass():
    s = Scenario("X", "x", required_phases=("start", "running", "resumed"))
    snaps = (_snap(events=({"phase": "start"}, {"phase": "running"})),)
    ok, reason = evidence_complete(s, snaps)
    assert not ok and "resumed" in reason
    pass
    ok, _ = evidence_complete(s, snaps, events=(
        make_event("r", "X", "baseline", 1, "start"),
        make_event("r", "X", "baseline", 2, "running"),
        make_event("r", "X", "baseline", 3, "resumed"),
    ))
    assert ok


def test_event_schema_and_redaction():
    ev = make_event("r1", "TC-01", "baseline", 1, "running",
                    {"code": "OK", "password": "secret", "token": "abc"})
    assert ev.event_id == "ev_r1_0001"
    assert ev.detail["code"] == "OK"
    assert "password" not in ev.detail and "token" not in ev.detail
    assert ev.detail["redacted"] == 2
    assert ev.run_id == "r1" and ev.phase == "running"


def test_metric_from_handles_business_and_resource_metrics():
    snap = _snap(resource={"rss_mb": 42.0}, heartbeat_times=(0.0, 0.5, 1.5),
                 checkpoint=7)
    assert metric_from(snap, "rss_mb") == 42.0
    assert metric_from(snap, "checkpoint") == 7
    assert metric_from(snap, "heartbeat_gap_ms") == 1000.0


def test_simulation_profiles():
    s = Scenario("TC-01", "x", steps=(Step("assert", checks=("output_complete",)),))
    dead = SimulationBackend("dead_process", scenario=s)
    assert not dead.probe().pid_alive
    dup = SimulationBackend("duplicate_side_effect", scenario=s)
    assert dup.probe().idempotency_conflicts == 2
