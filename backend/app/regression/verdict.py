from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Iterable

from .config import METRIC_NAMES, RegressionConfig
from .model import (
    BASELINE, CANDIDATE, Difference, MetricDelta, NOT_REGRESSED, MINOR_REGRESSION,
    SEVERE_REGRESSION, UNDECIDABLE, CheckResult, Defect, RegressionResult,
    RunOutcome, Scenario, VerdictRow,
)
from .model import plain
from .collector import metric_from


def _by_case(outcomes: Iterable[RunOutcome]) -> dict[str, dict[str, list[RunOutcome]]]:
    grouped: dict[str, dict[str, list[RunOutcome]]] = defaultdict(
        lambda: defaultdict(list))
    for o in outcomes:
        grouped[o.scenario_id][o.version_role].append(o)
    return grouped


def _avg(values: Iterable[float]) -> float:
    rows = list(values)
    return statistics.fmean(rows) if rows else 0.0


def compute_deltas(outcomes: tuple[RunOutcome, ...], config: RegressionConfig
                   ) -> tuple[tuple[MetricDelta, ...], tuple[str, ...]]:
    grouped = _by_case(outcomes)
    deltas: list[MetricDelta] = []
    warnings: list[str] = []
    for case_id, roles in sorted(grouped.items()):
        bases, cands = roles.get(BASELINE, []), roles.get(CANDIDATE, [])
        if not bases or not cands:
            warnings.append(f"{case_id}: 缺少双版本之一，跳过偏差计算")
            continue
        for metric in METRIC_NAMES:
            bvals = [v for o in bases if (v := metric_from(_first(o), metric)) is not None]
            cvals = [v for o in cands if (v := metric_from(_first(o), metric)) is not None]
            if not bvals or not cvals:
                continue
            b, c = _avg(bvals), _avg(cvals)
            theta, severe, temporary = config.theta(metric)
            relative = abs(b) > 1e-9
            delta = (c - b) / b if relative else c - b
            if temporary:
                abs_theta = config.thresholds.absolute.get(metric, 1.0)
                warnings.append(f"{metric}: 使用临时阈值 ±{theta:.0%}"
                                f"（基线≈0 时绝对阈值 {abs_theta}）")
            passed = abs(delta) <= theta if relative else delta <= abs_theta
            deltas.append(MetricDelta(metric, b, c, delta, theta, severe,
                                      relative, temporary, passed))
    return tuple(deltas), tuple(dict.fromkeys(warnings))


def _first(run: RunOutcome) -> object:
    return run.snapshots[-1] if run.snapshots else _EMPTY_SNAP


class _EmptySnap:

    heartbeat_times: tuple[float, ...] = ()
    resource: dict[str, float] = {}

    def __getattr__(self, name: str) -> object:
        return None


_EMPTY_SNAP = _EmptySnap()


def fingerprint_diffs(outcomes: tuple[RunOutcome, ...], whitelist: tuple[str, ...],
                      ) -> tuple[Difference, ...]:
    grouped = _by_case(outcomes)
    diffs: list[Difference] = []
    for case_id, roles in grouped.items():
        bases, cands = roles.get(BASELINE, []), roles.get(CANDIDATE, [])
        if not bases or not cands:
            continue
        b, c = _first(bases[0]), _first(cands[0])
        pairs: list[tuple[str, str, object, object]] = [
            ("status", "reported_status", b.reported_status, c.reported_status),
            ("output", "schema", b.output_signature.get("schema"),
             c.output_signature.get("schema")),
            ("output", "records", b.output_signature.get("records"),
             c.output_signature.get("records")),
        ]
        pass
        pass
        bphases = tuple(dict.fromkeys(e.phase for e in bases[0].events))
        cphases = tuple(dict.fromkeys(e.phase for e in cands[0].events))
        pairs.append(("event", "phases", bphases, cphases))
        for kind, field, bv, cv in pairs:
            if bv == cv:
                continue
            key = f"{case_id}:{field}"
            if key in whitelist or field in whitelist:
                continue
            diffs.append(Difference(kind, case_id, field, bv, cv,
                                    "命中未批准的行为差异"))
    return tuple(diffs)


def data_differences(outcomes: tuple[RunOutcome, ...]) -> tuple[Difference, ...]:
    diffs: list[Difference] = []
    for o in outcomes:
        for check in o.checks:
            if check.name in ("output_complete", "no_duplicate_side_effect",
                              "no_duplicate_instance") and not check.ok:
                diffs.append(Difference("data", o.scenario_id, check.name,
                                        "expected_ok", "failed", check.reason))
    return tuple(diffs)


def stability_differences(outcomes: tuple[RunOutcome, ...]) -> tuple[Difference, ...]:
    diffs: list[Difference] = []
    for o in outcomes:
        snap = _first(o)
        if snap.exit_code not in (None, 0) and o.version_role == CANDIDATE:
            diffs.append(Difference("stability", o.scenario_id, "crash",
                                    0, snap.exit_code, "候选版本异常退出"))
        for check in o.checks:
            if check.name == "no_resource_leak" and not check.ok:
                diffs.append(Difference("stability", o.scenario_id, "leak",
                                        "<= threshold", check.reason,
                                        "内存/FD 斜率超阈"))
    return tuple(diffs)


def coverage_blocker(outcomes: tuple[RunOutcome, ...],
                     scenarios: tuple[Scenario, ...]) -> tuple[str, ...]:
    missing: list[str] = []
    grouped = _by_case(outcomes)
    for s in scenarios:
        if not s.core:
            continue
        roles = grouped.get(s.id, {})
        for role in (BASELINE, CANDIDATE):
            runs = roles.get(role, [])
            if not any(r.passed for r in runs):
                missing.append(f"{s.id}/{role}")
    return tuple(missing)


def _blockers(outcomes: tuple[RunOutcome, ...],
              scenarios: tuple[Scenario, ...], env_ok: bool,
              baseline_ok: bool, data_ok: bool) -> tuple[str, ...]:
    out: list[str] = []
    if not env_ok:
        out.append("环境指纹/镜像不可用")
    if not baseline_ok:
        out.append("基线数据缺失或不稳定")
    if not data_ok:
        out.append("数据快照不可用")
    gaps = [o.run_id for o in outcomes if not o.evidence_sufficient]
    if gaps:
        out.append("证据不足: " + ",".join(gaps))
    missing = coverage_blocker(outcomes, scenarios)
    if missing:
        out.append("核心用例覆盖率不足: " + ",".join(missing))
    return tuple(out)


def _rows(outcomes: tuple[RunOutcome, ...], diffs: tuple[Difference, ...],
          d_data: tuple[Difference, ...], d_stable: tuple[Difference, ...],
          deltas: tuple[MetricDelta, ...], new_high: list[Defect],
          core_failed: list[str], core_ids: set[str]) -> list[VerdictRow]:
    crashes = [d for d in d_stable if d.field == "crash"]
    minor = [d for d in deltas if not d.passed and not d.severe_breach]
    severe = [d for d in deltas if d.severe_breach]
    return [
        VerdictRow("功能门槛", "PASS" if not core_failed else "FAIL",
                   "核心用例全部通过" if not core_failed
                   else "核心用例失败: " + ",".join(core_failed),
                   evidence="core=" + ",".join(sorted(core_ids))),
        VerdictRow("行为指纹", "PASS" if not diffs else "DIFF",
                   f"{len(diffs)} 项未批准差异", evidence="fingerprint"),
        VerdictRow("数据一致性", "PASS" if not d_data else "FAIL",
                   f"{len(d_data)} 项数据异常", evidence="idempotency"),
        VerdictRow("性能偏差", "PASS" if not minor and not severe else "DEVIATE",
                   f"超阈 {len(minor)} 项，严重超阈 {len(severe)} 项",
                   evidence="metrics"),
        VerdictRow("稳定性", "PASS" if not d_stable else "FAIL",
                   f"崩溃 {len(crashes)} 次，泄漏 {len(d_stable) - len(crashes)} 项",
                   evidence="events"),
        VerdictRow("缺陷过滤", "PASS" if not new_high else "FAIL",
                   f"新增 P0/P1 共 {len(new_high)} 项", evidence="defects"),
    ]


def _reason(core_failed: list[str], d_data: tuple[Difference, ...],
            crashes: list[Difference], severe: list[MetricDelta],
            new_high: list[Defect], diffs: tuple[Difference, ...],
            minor: list[MetricDelta], noncore_failed: list[str]
            ) -> tuple[str, str]:
    if core_failed or d_data or crashes or severe or new_high:
        return (SEVERE_REGRESSION,
                "核心用例失败/数据异常/崩溃/严重指标偏差/新增 P0P1："
                f"core={len(core_failed)}, data={len(d_data)}, "
                f"crash={len(crashes)}, severe={len(severe)}, newhigh={len(new_high)}")
    if diffs or minor or noncore_failed:
        return (MINOR_REGRESSION,
                f"非核心用例失败 {len(noncore_failed)}，未批准行为差异 {len(diffs)}，"
                f"轻微指标偏差 {len(minor)}")
    return (NOT_REGRESSED,
            "核心流程通过、行为指纹一致、数据完整、指标在阈值内、无新增 P0P1")


def decide(config: RegressionConfig, outcomes: tuple[RunOutcome, ...],
           scenarios: tuple[Scenario, ...], defects: tuple[Defect, ...] = (),
           env_ok: bool = True, baseline_ok: bool = True,
           data_ok: bool = True, run_dir: str = "") -> RegressionResult:
    warnings: list[str] = []
    blockers = _blockers(outcomes, scenarios, env_ok, baseline_ok, data_ok)
    if blockers:
        return _result(UNDECIDABLE, blockers, warnings, outcomes, (), (),
                       defects, run_dir)

    deltas, metric_warnings = compute_deltas(outcomes, config)
    warnings.extend(metric_warnings)
    diffs = fingerprint_diffs(outcomes, config.whitelist)
    d_data = data_differences(outcomes)
    d_stable = stability_differences(outcomes)
    core_ids = {s.id for s in scenarios if s.core}
    core_failed = [o.run_id for o in outcomes
                   if o.scenario_id in core_ids and not o.passed]
    noncore_failed = [o.run_id for o in outcomes
                      if o.scenario_id not in core_ids and not o.passed]
    new_high = [d for d in defects if d.is_new and d.severity in ("P0", "P1")]
    severe = [d for d in deltas if d.severe_breach]
    minor = [d for d in deltas if not d.passed and not d.severe_breach]
    crashes = [d for d in d_stable if d.field == "crash"]

    rows = _rows(outcomes, diffs, d_data, d_stable, deltas, new_high,
                 core_failed, core_ids)
    verdict, reason = _reason(core_failed, d_data, crashes, severe,
                              new_high, diffs, minor, noncore_failed)
    all_diffs = tuple(diffs) + d_data + d_stable
    return _result(verdict, blockers, warnings, outcomes, deltas, all_diffs,
                   defects, run_dir, tuple(rows), reason)


def _result(verdict: str, blockers: tuple[str, ...], warnings: tuple[str, ...],
            outcomes: tuple[RunOutcome, ...], deltas: tuple[MetricDelta, ...],
            diffs: tuple[Difference, ...], defects: tuple[Defect, ...],
            run_dir: str, rows: tuple[VerdictRow, ...] = (),
            reason: str = "") -> RegressionResult:
    if not rows:
        rows = (VerdictRow("判定", verdict, reason or "; ".join(blockers)
                           or "执行被阻断"),)
    return RegressionResult(verdict, rows, outcomes, deltas, diffs, defects,
                            tuple(blockers), tuple(warnings), {}, run_dir)


def evidence_link(run: RunOutcome, kind: str = "") -> str:
    base = f"{run.run_id} → {run.scenario_id}"
    if kind:
        base += f" → {kind}"
    checks = ",".join(c.name for c in run.checks) or "none"
    return base + f" → events[{len(run.events)}] → metrics[{len(run.metrics)}] → checks[{checks}]"
