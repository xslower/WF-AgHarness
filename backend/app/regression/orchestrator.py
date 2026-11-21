from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from ..store import layout
from ..util.fsx import ensure_dir
from ..util.timeutil import clock, fmt_compact
from .adapters import Backend, BackendFactory, build_adapter
from .collector import make_event, metric_from, persist_events, snapshot_events
from .config import RegressionConfig
from .dsl import all_scenarios, core_scenarios, matrix, substitute, validate_scenario
from .model import (
    BASELINE, CANDIDATE, CheckResult, Defect, Environment, Event, GateResult,
    ProbeSnapshot, RegressionResult, RunOutcome, RunSpec, Scenario,
)
from .probes import evidence_complete, run_checks
from .reports import render_all
from .verdict import decide

StageHook = Callable[[str], None]


def _noop(_stage: str) -> None:
    pass


class Orchestrator:

    def __init__(self, config: RegressionConfig, *,
                 backend_factory: BackendFactory | None = None,
                 hook: StageHook = _noop,
                 workspace: str = "",
                 env: Environment | None = None,
                 defects: tuple[Defect, ...] = (),
                 env_ok: bool = True, baseline_ok: bool = True,
                 data_ok: bool = True, out_dir: str | Path | None = None) -> None:
        self.config = config
        self.backend_factory = backend_factory
        self.hook = hook
        self.workspace = workspace
        self.env = env or Environment(id=config.env_target or "env_default",
                                      image_tag=config.env_image)
        self.defects = defects
        self.env_ok = env_ok
        self.baseline_ok = baseline_ok
        self.data_ok = data_ok
        self.out_dir = out_dir

    pass
    def gate(self) -> GateResult:
        g0 = self.config.validate()
        errors = [e for s in all_scenarios() for e in validate_scenario(s)]
        blockers = list(g0.blockers) + errors
        return GateResult(not blockers, tuple(blockers), g0.warnings)

    def run_dir(self, stamp: str = "") -> Path:
        name = f"regression-{stamp or fmt_compact(clock())}"
        root = (Path(self.out_dir) if self.out_dir is not None else
                layout.project_runs_dir(self.workspace or layout.global_workspace()))
        return ensure_dir(root / name)

    pass
    def run(self, *, write_reports: bool = True, stamp: str = "") -> RegressionResult:
        gate = self.gate()
        self.hook(f"G0/G2: {'PASS' if gate.passed else 'BLOCK'}")
        scenarios = all_scenarios()
        if not gate.passed:
            return self._blocked(gate.blockers, gate.warnings, scenarios,
                                 write_reports, stamp)

        env_report = self._env_fingerprint()
        self.hook("G1: ENV_CHECK")
        self.hook("G3/G4: EXECUTE")
        specs = matrix(core_scenarios() + tuple(s for s in scenarios if not s.core),
                       self.config.platform, self.config.repeats,
                       self.env.id, fmt_compact(clock()))
        outcomes = tuple(self._run_one(spec, scenarios) for spec in specs)
        self.hook("G5: VERDICT")

        result = decide(self.config, outcomes, scenarios, self.defects,
                        env_ok=self.env_ok, baseline_ok=self.baseline_ok,
                        data_ok=self.data_ok, run_dir=str(self.run_dir(stamp)))
        warnings = list(result.warnings) + list(gate.warnings)
        result = RegressionResult(
            result.verdict, result.rows, result.outcomes, result.deltas,
            result.differences, result.defects, result.blockers,
            tuple(warnings), result.reports, result.run_dir,
        )
        if write_reports:
            out = self.run_dir(stamp)
            from .reports import FILE_NAMES
            from ..util.jsonx import write_json
            render_all(result, self.config, self.env.id, out)
            result = RegressionResult(
                result.verdict, result.rows, result.outcomes, result.deltas,
                result.differences, result.defects, result.blockers,
                result.warnings, {k: str(out / v) for k, v in FILE_NAMES.items()},
                result.run_dir,
            )
            self.persist_events(result, out)
            write_json(out / "environment.json", env_report)
            (out / "environment.json").write_text(
                __import__("json").dumps(env_report, ensure_ascii=False, indent=2),
                "utf-8")
        return result

    def _blocked(self, blockers: tuple[str, ...], warnings: tuple[str, ...],
                 scenarios: tuple[Scenario, ...], write_reports: bool,
                 stamp: str) -> RegressionResult:
        from .model import UNDECIDABLE
        result = RegressionResult(
            UNDECIDABLE, (), (), (), (), (), blockers, warnings, {},
            str(self.run_dir(stamp)) if write_reports else "",
        )
        if write_reports:
            out = self.run_dir(stamp)
            docs = render_all(result, self.config, self.env.id, out)
            pass
            from ..util.fsx import write_text
            write_text(out / "00_无法判定说明.md",
                       "# 无法判定说明\n\nG0 澄清门禁未通过，禁止执行用例。\n\n"
                       + "\n".join(f"- {b}" for b in blockers) + "\n")
            from .reports import FILE_NAMES
            result = RegressionResult(
                result.verdict, result.rows, result.outcomes, result.deltas,
                result.differences, result.defects, result.blockers,
                result.warnings, {k: str(out / v) for k, v in FILE_NAMES.items()},
                result.run_dir,
            )
        return result

    def _env_fingerprint(self) -> dict[str, Any]:
        import platform as py_platform
        import sys
        return {
            "id": self.env.id, "image_tag": self.env.image_tag,
            "os": py_platform.platform(), "python": sys.version.split()[0],
            "runtime": self.env.runtime, "deps": dict(self.env.deps),
            "network_policy": self.env.network_policy,
            "config_snapshot": {
                "platform": self.config.platform,
                "baseline": self.config.baseline_version,
                "candidate": self.config.candidate_version,
                "repeats": self.config.repeats,
                "thresholds": self.config.thresholds.metrics,
            },
        }

    @staticmethod
    def _config_values(config: RegressionConfig) -> dict[str, str]:
        return {
            "entry": config.entry, "wait_timeout": str(config.wait_timeout),
            "snapshot": config.data_snapshot,
            "duration_min": str(config.wait_timeout),
        }

    @staticmethod
    def _step_result(adapter: Any, step: Any) -> tuple[object, str]:
        action = str(step.params.get("action", ""))
        if step.type == "background":
            return adapter.background(action, step.params), ""
        if step.type == "restore":
            return adapter.restore(action, step.params), ""
        if step.type == "fault":
            return adapter.fault(action, step.params), action
        return None, ""

    def _run_one(self, spec: RunSpec, scenarios: tuple[Scenario, ...]) -> RunOutcome:
        scenario = next(s for s in scenarios if s.id == spec.scenario_id)
        adapter = build_adapter(spec.platform, spec.version_role, scenario,
                                spec.data_seed, self.backend_factory)
        values = self._config_values(self.config)
        events: list[Event] = [make_event(spec.run_id, spec.scenario_id,
                                          spec.version_role, 0, "start",
                                          {"code": "RUN_START", "seed": spec.data_seed})]
        snaps: list[ProbeSnapshot] = []
        fault_kind = ""
        failure = ""
        seq = 1
        for raw_step in scenario.steps:
            step = substitute(raw_step, values)
            try:
                result, fault = self._step_result(adapter, step)
                fault_kind = fault or fault_kind
                if result is not None:
                    events.extend(snapshot_events(spec.run_id, spec.scenario_id,
                                                  spec.version_role, result.events, seq))
                    seq += len(result.events)
                snap = adapter.probe()
                snaps.append(snap)
                events.extend(snapshot_events(spec.run_id, spec.scenario_id,
                                              spec.version_role, snap.events, seq))
                seq += len(snap.events)
            except Exception as exc:
                failure = f"{step.type}:{exc}"
                break

        events.append(make_event(spec.run_id, spec.scenario_id, spec.version_role,
                                 seq, "stopped", {"code": "RUN_END"}))
        snap_tuple = tuple(snaps)
        checks = (run_checks(scenario, snap_tuple, self.config.output_rules,
                             self.config.thresholds.leak, fault_kind)
                  if not failure else (CheckResult("execution", False, failure),))
        sufficient, reason = evidence_complete(scenario, snap_tuple, tuple(events))
        if not sufficient:
            checks += (CheckResult("evidence", False, reason),)
        return RunOutcome(
            spec.run_id, spec.scenario_id, spec.version_role, spec.platform,
            spec.round, "done" if not failure else "failed",
            checks, snap_tuple, tuple(events), self._collect_metrics(snap_tuple),
            (f"run:{spec.run_id}", f"case:{spec.scenario_id}"),
            sufficient, failure,
        )

    def _collect_metrics(self, snaps: tuple[ProbeSnapshot, ...]) -> dict[str, float]:
        if not snaps:
            return {}
        last = snaps[-1]
        out: dict[str, float] = {}
        for key, value in (last.resource or {}).items():
            out[key] = float(value)
        for key in ("checkpoint", "records", "idempotency_conflicts", "retries"):
            value = metric_from(last, key)
            if value is not None:
                out[key] = value
        return out

    def persist_events(self, result: RegressionResult, out_dir: str | Path) -> bool:
        path = Path(out_dir) / "events.jsonl"
        return persist_events(str(path), tuple(e for o in result.outcomes for e in o.events))
