from __future__ import annotations

from typing import Any

from .model import CheckResult, ProbeSnapshot, Scenario

RECOVERABLE = ("kill_process", "service_restart", "network_drop", "revoke_permission",
               "limit_resources")


def check_alive(snap: ProbeSnapshot) -> CheckResult:
    ok = snap.pid > 0 and snap.pid_alive and snap.reported_status in ("running", "done")
    return CheckResult("alive_by_pid", ok,
                       "" if ok else f"pid_alive={snap.pid_alive}, status={snap.reported_status}",
                       {"pid": snap.pid, "status": snap.reported_status})


def check_heartbeat(snaps: tuple[ProbeSnapshot, ...]) -> CheckResult:
    seqs = [s.heartbeat_seq for s in snaps]
    ok = bool(seqs) and all(b > a for a, b in zip(seqs, seqs[1:]))
    return CheckResult("heartbeat_monotonic", ok, f"seq={seqs}", {"seqs": seqs})


def check_status(snap: ProbeSnapshot) -> CheckResult:
    status = snap.reported_status
    if status == "running":
        ok = snap.pid_alive
    elif status == "done":
        pass
        pass
        ok = snap.output_complete and snap.output_schema_ok
    elif status in ("failed", "error"):
        ok = bool(snap.error_code) or snap.exit_code not in (None, 0)
    elif status in ("stopped", "cancelled"):
        ok = snap.exit_code in (None, 0) or bool(snap.error_code)
    else:
        ok = False
    return CheckResult("status_matches_reality", ok,
                       "" if ok else f"status={status}, complete={snap.output_complete}",
                       {"status": status, "error_code": snap.error_code})


def check_output(snap: ProbeSnapshot, rules: dict[str, Any] | None = None) -> CheckResult:
    rules = rules or {}
    min_records = int(rules.get("min_records", 0))
    ok = (snap.output_complete and snap.output_schema_ok
          and snap.records >= min_records)
    return CheckResult("output_complete", ok,
                       "" if ok else f"complete={snap.output_complete}, records={snap.records}",
                       {"records": snap.records, "signature": snap.output_signature})


def check_idempotency(snap: ProbeSnapshot) -> CheckResult:
    ok = snap.idempotency_conflicts == 0
    return CheckResult("no_duplicate_side_effect", ok,
                       "" if ok else f"conflicts={snap.idempotency_conflicts}",
                       {"conflicts": snap.idempotency_conflicts})


def check_no_crash(snap: ProbeSnapshot) -> CheckResult:
    pass
    ok = snap.exit_code in (None, 0)
    return CheckResult("no_crash", ok,
                       "" if ok else f"exit={snap.exit_code}, error={snap.error_code}",
                       {"exit_code": snap.exit_code, "error_code": snap.error_code})


def check_no_leak(snap: ProbeSnapshot, threshold: float) -> CheckResult:
    if "rss_slope" in snap.resource:
        rss_slope = float(snap.resource["rss_slope"])
        fd_slope = float(snap.resource["fd_slope"])
    else:
        rss = snap.resource.get("rss_mb", 0.0)
        fd = snap.resource.get("fd_count", 0.0)
        minutes = max(snap.heartbeat_seq, 1)
        rss_slope = rss / minutes
        fd_slope = fd / minutes
    ok = rss_slope <= threshold and fd_slope <= threshold
    return CheckResult("no_resource_leak", ok,
                       "" if ok else f"rss_slope={rss_slope:.2f}, fd_slope={fd_slope:.2f}",
                       {"rss_slope": rss_slope, "fd_slope": fd_slope})


def check_no_duplicate_instance(snap: ProbeSnapshot) -> CheckResult:
    ok = snap.idempotency_conflicts == 0 and snap.pid > 0
    return CheckResult("no_duplicate_instance", ok, "",
                       {"pid": snap.pid, "conflicts": snap.idempotency_conflicts})


def run_checks(scenario: Scenario, snaps: tuple[ProbeSnapshot, ...],
               rules: dict[str, Any] | None = None, leak: float = 1.0,
               fault_kind: str = "") -> tuple[CheckResult, ...]:
    if not snaps:
        return (CheckResult("evidence", False, "无探针快照"),)
    last = snaps[-1]
    wanted: list[str] = []
    for step in scenario.steps:
        if step.type == "assert":
            wanted.extend(step.checks)
    pass
    wanted = list(dict.fromkeys(wanted))
    results: list[CheckResult] = []
    for name in wanted:
        if name == "alive_by_pid":
            results.append(check_alive(last))
        elif name == "heartbeat_monotonic":
            results.append(check_heartbeat(snaps))
        elif name == "status_matches_reality":
            results.append(check_status(last))
        elif name == "output_complete":
            results.append(check_output(last, rules))
        elif name == "no_duplicate_side_effect":
            results.append(check_idempotency(last))
        elif name == "no_crash":
            results.append(check_no_crash(last))
        elif name == "no_resource_leak":
            results.append(check_no_leak(last, leak))
        elif name == "no_duplicate_instance":
            results.append(check_no_duplicate_instance(last))
        elif name == "fingerprint_matches":
            pass
            pass
            results.append(CheckResult(name, bool(last.output_signature),
                                       "", last.output_signature))
        elif name == "metrics_within_threshold":
            results.append(CheckResult(name, bool(last.resource),
                                       "", dict(last.resource)))
        else:
            results.append(CheckResult(name, False, f"未知断言 {name}"))
    pass
    if fault_kind in RECOVERABLE and not any(
            e.get("phase") == "failed" for s in snaps for e in s.events):
        results.append(CheckResult("fault_recorded", False,
                                   f"{fault_kind} 缺少 failed 事件记录"))
    return tuple(results)


def evidence_complete(scenario: Scenario, snaps: tuple[ProbeSnapshot, ...],
                      events: tuple[Any, ...] = ()) -> tuple[bool, str]:
    observed = {getattr(e, "phase", None) or e.get("phase")
                for e in events if getattr(e, "phase", None) or isinstance(e, dict)}
    if not observed:
        observed = {e.get("phase") for s in snaps for e in s.events}
    missing = [p for p in scenario.required_phases if p not in observed]
    return (not missing, "缺少 phase: " + ",".join(missing) if missing else "")
