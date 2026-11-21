from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

pass
STEP_TYPES = ("setup", "trigger", "background", "wait", "fault",
              "restore", "assert", "teardown")

BASELINE = "baseline"
CANDIDATE = "candidate"
ROLES = (BASELINE, CANDIDATE)

pass
NOT_REGRESSED = "未回归"
MINOR_REGRESSION = "存在轻微回归"
SEVERE_REGRESSION = "存在严重回归"
UNDECIDABLE = "无法判定"
VERDICTS = (NOT_REGRESSED, MINOR_REGRESSION, SEVERE_REGRESSION, UNDECIDABLE)

pass
PHASES = ("start", "running", "paused", "resumed", "failed", "stopped")


def plain(obj: Any) -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    if isinstance(obj, dict):
        return {k: plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [plain(v) for v in obj]
    return obj


@dataclass(frozen=True)
class Version:
    id: str
    role: str = BASELINE
    commit: str = ""
    tag: str = ""
    config_snapshot: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Environment:
    id: str
    image_tag: str = ""
    os: str = ""
    runtime: str = ""
    deps: dict[str, str] = field(default_factory=dict)
    network_policy: str = ""


@dataclass(frozen=True)
class Step:
    type: str
    action: str = ""
    checks: tuple[str, ...] = ()
    params: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"type": self.type}
        if self.action:
            out["action"] = self.action
        if self.checks:
            out["checks"] = list(self.checks)
        out.update(self.params)
        return out


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    priority: str = "P0"
    kind: str = "function"
    core: bool = False
    fr: tuple[str, ...] = ()
    tc: str = ""
    platform_tags: tuple[str, ...] = ()
    required_phases: tuple[str, ...] = ()
    steps: tuple[Step, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {"id": self.id, "title": self.title, "priority": self.priority,
                "kind": self.kind, "core": self.core, "fr": list(self.fr),
                "tc": self.tc, "platform_tags": list(self.platform_tags),
                "required_phases": list(self.required_phases),
                "steps": [s.as_dict() for s in self.steps]}


@dataclass(frozen=True)
class RunSpec:
    run_id: str
    scenario_id: str
    version_role: str
    platform: str
    round: int
    env_id: str
    data_seed: str
    order: int = 0


@dataclass(frozen=True)
class Event:
    event_id: str
    run_id: str
    case_id: str
    version_role: str
    ts: str
    phase: str
    subject: dict[str, Any] = field(default_factory=dict)
    detail: dict[str, Any] = field(default_factory=dict)
    trace: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProbeSnapshot:
    ts: str
    reported_status: str = ""
    pid: int = 0
    pid_alive: bool = False
    heartbeat_seq: int = 0
    heartbeat_times: tuple[float, ...] = ()
    checkpoint: int = 0
    records: int = 0
    idempotency_conflicts: int = 0
    retries: int = 0
    output_complete: bool = False
    output_schema_ok: bool = False
    output_signature: dict[str, Any] = field(default_factory=dict)
    resource: dict[str, float] = field(default_factory=dict)
    error_code: str = ""
    exit_code: int | None = None
    events: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    reason: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunOutcome:
    run_id: str
    scenario_id: str
    version_role: str
    platform: str
    round: int
    status: str
    checks: tuple[CheckResult, ...] = ()
    snapshots: tuple[ProbeSnapshot, ...] = ()
    events: tuple[Event, ...] = ()
    metrics: dict[str, float] = field(default_factory=dict)
    evidence_refs: tuple[str, ...] = ()
    evidence_sufficient: bool = True
    error: str = ""

    @property
    def passed(self) -> bool:
        return (self.status == "done" and self.evidence_sufficient
                and all(c.ok for c in self.checks) and not self.error)


@dataclass(frozen=True)
class MetricDelta:
    metric: str
    baseline: float
    candidate: float
    delta: float
    threshold: float
    severe: float
    relative: bool
    temporary: bool
    passed: bool = True

    @property
    def severe_breach(self) -> bool:
        return abs(self.delta) > self.severe if self.relative else self.delta > self.severe


@dataclass(frozen=True)
class Difference:
    kind: str
    scenario_id: str
    field: str
    baseline: Any
    candidate: Any
    reason: str = ""


@dataclass(frozen=True)
class Defect:
    id: str
    severity: str
    title: str = ""
    run_id: str = ""
    repro_steps: str = ""
    is_new: bool = True
    known_defect_ref: str = ""


@dataclass(frozen=True)
class VerdictRow:
    dimension: str
    result: str
    reason: str = ""
    delta: str = ""
    threshold: str = ""
    evidence: str = ""


@dataclass(frozen=True)
class RegressionResult:
    verdict: str
    rows: tuple[VerdictRow, ...] = ()
    outcomes: tuple[RunOutcome, ...] = ()
    deltas: tuple[MetricDelta, ...] = ()
    differences: tuple[Difference, ...] = ()
    defects: tuple[Defect, ...] = ()
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    reports: dict[str, str] = field(default_factory=dict)
    run_dir: str = ""


@dataclass(frozen=True)
class GateResult:
    passed: bool
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
