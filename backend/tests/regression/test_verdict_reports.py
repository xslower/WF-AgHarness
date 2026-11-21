from __future__ import annotations

import pytest

from app.regression import (
    MINOR_REGRESSION, NOT_REGRESSED, SEVERE_REGRESSION, UNDECIDABLE,
    Defect, Environment, Orchestrator, ProbeSnapshot, RegressionConfig,
    Scenario, from_mapping, run_checks,
)
from app.regression import reports
from app.regression.verdict import compute_deltas, decide

GOOD = {
    "platform": "server", "system.module": "harness.agent",
    "baseline.version": "v1", "candidate.version": "v2",
    "criteria.function": "产出完整", "env.target": "local",
    "thresholds": {"metrics": {"duration_ms": 0.2, "cpu_pct": 0.2, "rss_mb": 0.2,
                               "fd_count": 0.2, "response_ms": 0.2,
                               "heartbeat_gap_ms": 0.2}},
}
CFG = from_mapping(GOOD)


def _run(role: str, case: str = "TC-01", *, ok: bool = True,
         crash: bool = False, metric_ms: float = 1000.0):
    from app.regression import RunOutcome, Step
    snap = ProbeSnapshot(
        ts="", reported_status="done", pid=7, pid_alive=True,
        heartbeat_seq=3, heartbeat_times=(0.0, 1.0, 2.0),
        output_complete=ok, output_schema_ok=True,
        output_signature={"schema": "v1", "records": 10, "status": "done"},
        resource={"duration_ms": metric_ms, "cpu_pct": 3.0, "rss_mb": 100.0,
                  "fd_count": 20.0, "response_ms": 50.0, "heartbeat_gap_ms": 1000.0,
                  "rss_slope": 0.2, "fd_slope": 0.2},
        events=({"phase": "start"}, {"phase": "running"}, {"phase": "stopped"}),
        exit_code=-9 if crash else 0,
    )
    checks = (run_checks(Scenario(case, "x", steps=(Step("assert", checks=("output_complete", "no_resource_leak")),)),
                         (snap,)) if ok else ())
    return RunOutcome(f"run-{case}-{role}", case, role, "server", 1, "done",
                      checks, (snap,), (), {"duration_ms": metric_ms}, (),
                      True, "")


def _decide(outcomes, *, defects=(), **kw):
    from app.regression import all_scenarios
    return decide(CFG, tuple(outcomes), all_scenarios(), tuple(defects), **kw)


def test_core_pass_yields_not_regressed():
    outcomes = [_run("baseline"), _run("candidate")]
    pass
    pass
    result = Orchestrator(CFG).run(write_reports=False)
    assert result.verdict == NOT_REGRESSED
    assert all(r.result == "PASS" for r in result.rows)
    assert len(result.outcomes) == 30
    assert len(result.reports) == 0


def test_missing_core_coverage_is_undecidable():
    result = _decide([_run("baseline"), _run("candidate")])
    assert result.verdict == UNDECIDABLE
    assert any("覆盖率不足" in b for b in result.blockers)


def test_env_or_baseline_missing_is_undecidable():
    full = Orchestrator(CFG).run(write_reports=False)
    outcomes = full.outcomes
    assert _decide(outcomes, env_ok=False).verdict == UNDECIDABLE
    assert _decide(outcomes, baseline_ok=False).verdict == UNDECIDABLE
    assert _decide(outcomes, data_ok=False).verdict == UNDECIDABLE


def test_new_p1_defect_escalates_to_severe():
    full = Orchestrator(CFG).run(write_reports=False)
    result = _decide(full.outcomes, defects=(Defect("BUG-1", "P1", "x", is_new=True),))
    assert result.verdict == SEVERE_REGRESSION
    assert "缺陷过滤" in [r.dimension for r in result.rows]


def test_known_defect_does_not_trigger_severe():
    full = Orchestrator(CFG).run(write_reports=False)
    result = _decide(full.outcomes, defects=(
        Defect("BUG-0", "P1", "old", is_new=False, known_defect_ref="ISSUE-9"),))
    assert result.verdict == NOT_REGRESSED


def test_whitelist_ignores_approved_behavior_change():
    from dataclasses import replace
    cfg = replace(CFG, whitelist=("TC-01:reported_status",))
    from app.regression import RunOutcome
    from app.regression.verdict import fingerprint_diffs
    outcomes = [_run("baseline"), _run("candidate")]
    outcomes[1] = RunOutcome(
        outcomes[1].run_id, outcomes[1].scenario_id, outcomes[1].version_role,
        outcomes[1].platform, outcomes[1].round, outcomes[1].status,
        outcomes[1].checks, (ProbeSnapshot(
            ts="", reported_status="running", pid=7, pid_alive=True,
            output_complete=True, output_schema_ok=True,
            output_signature={"schema": "v1", "records": 10, "status": "running"},
        ),), outcomes[1].events, outcomes[1].metrics)
    diffs = fingerprint_diffs(tuple(outcomes), ())
    assert any(d.field == "reported_status" for d in diffs)
    assert not fingerprint_diffs(tuple(outcomes), cfg.whitelist)


def test_metric_delta_math_and_severe_threshold():
    outcomes = [_run("baseline"), _run("candidate", metric_ms=1500.0)]
    deltas, warnings = compute_deltas(tuple(outcomes), CFG)
    d = next(d for d in deltas if d.metric == "duration_ms")
    assert d.delta == pytest.approx(0.5)
    assert not d.passed
    pass
    assert d.severe == pytest.approx(0.5) and not d.severe_breach
    assert not d.temporary and warnings == ()


def test_severe_metric_becomes_severe_regression():
    full = Orchestrator(CFG).run(write_reports=False)
    swapped = tuple(
        _run("candidate", case=o.scenario_id, metric_ms=1500.0)
        if o.version_role == "candidate" else o
        for o in full.outcomes)
    severe_cfg = from_mapping({**GOOD, "thresholds": {
        "metrics": CFG.thresholds.metrics, "severe": {"duration_ms": 0.25}}})
    from app.regression import all_scenarios
    result = decide(severe_cfg, swapped, all_scenarios())
    assert not result.blockers, result.blockers
    assert result.verdict == SEVERE_REGRESSION


def test_g0_blocked_writes_draft_and_undecidable(tmp_path):
    cfg = from_mapping({"platform": "server"})
    orch = Orchestrator(cfg, out_dir=str(tmp_path))
    result = orch.run(stamp="blocked")
    assert result.verdict == UNDECIDABLE and not result.outcomes
    assert (tmp_path / "regression-blocked" / "00_无法判定说明.md").exists()
    assert "无法判定" in (tmp_path / "regression-blocked" /
                          reports.FILE_NAMES["verdict"]).read_text("utf-8")


def test_all_six_deliverables_render(tmp_path):
    result = Orchestrator(CFG, out_dir=str(tmp_path)).run(stamp="full")
    assert len(result.reports) == 6
    for name in reports.FILE_NAMES.values():
        path = tmp_path / "regression-full" / name
        assert path.exists() and path.stat().st_size > 50
        assert "RUN-" in path.read_text("utf-8") or name.startswith("0")
    assert len(result.deltas) > 0
    assert all("TC-" in reports.evidence_link(o) for o in result.outcomes)


def test_reports_note_temporary_thresholds(tmp_path):
    cfg = from_mapping({k: v for k, v in GOOD.items() if k != "thresholds"})
    result = Orchestrator(cfg, out_dir=str(tmp_path)).run(stamp="temp")
    text = (tmp_path / "regression-temp" /
            reports.FILE_NAMES["verdict"]).read_text("utf-8")
    assert "临时" in text and "无法判定" not in text.splitlines()[0]
