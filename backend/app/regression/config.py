from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from ..util.jsonx import read_json
from .model import GateResult

pass
DEFAULT_THRESHOLD = 0.10
pass
DEFAULT_SEVERE = 0.25
pass
DEFAULT_ABSOLUTE = 1.0
pass
DEFAULT_LEAK = 1.0

REQUIRED_FIELDS = (
    ("platform", "Q1 后台运行场景类型"),
    ("system.module", "Q2 系统与模块"),
    ("baseline.version", "Q3 基线版本"),
    ("candidate.version", "Q4 候选版本"),
    ("criteria.function", "Q5/Q7 成功标准"),
    ("env.target", "Q10 执行环境"),
)

METRIC_NAMES = ("duration_ms", "cpu_pct", "rss_mb", "fd_count",
                "response_ms", "heartbeat_gap_ms")


@dataclass(frozen=True)
class Thresholds:
    metrics: dict[str, float] = field(default_factory=dict)
    severe: dict[str, float] = field(default_factory=dict)
    absolute: dict[str, float] = field(default_factory=dict)
    leak: float = DEFAULT_LEAK
    k_sigma: float = 3.0
    min_threshold: float = 0.05

    def theta(self, metric: str) -> tuple[float, float, bool]:
        if metric in self.metrics:
            theta = self.metrics[metric]
            temporary = False
        else:
            theta = DEFAULT_THRESHOLD
            temporary = True
        severe = self.severe.get(metric, max(theta * 2.5, DEFAULT_SEVERE))
        return theta, severe, temporary


@dataclass(frozen=True)
class RegressionConfig:
    platform: str = ""
    system: str = ""
    module: str = ""
    baseline_version: str = ""
    candidate_version: str = ""
    baseline_commit: str = ""
    candidate_commit: str = ""
    change_list: tuple[str, ...] = ()
    function_criteria: tuple[str, ...] = ()
    os_matrix: tuple[str, ...] = ()
    runtime_matrix: tuple[str, ...] = ()
    client_matrix: tuple[str, ...] = ()
    thresholds: Thresholds = field(default_factory=Thresholds)
    known_defects: tuple[str, ...] = ()
    env_target: str = ""
    env_image: str = ""
    repeats: int = 1
    wait_timeout: float = 30.0
    entry: str = ""
    data_snapshot: str = "snap_bg_001"
    whitelist: tuple[str, ...] = ()
    rss_sigma: dict[str, float] = field(default_factory=dict)
    output_rules: dict[str, Any] = field(default_factory=dict)

    def _field(self, path: str) -> str:
        parts = path.split(".")
        if parts == ["platform"]:
            return self.platform
        if parts == ["system", "module"]:
            return ".".join(x for x in (self.system, self.module) if x)
        if parts == ["baseline", "version"]:
            return self.baseline_version
        if parts == ["candidate", "version"]:
            return self.candidate_version
        if parts == ["criteria", "function"]:
            return "".join(self.function_criteria)
        if parts == ["env", "target"]:
            return self.env_target
        return ""

    def validate(self) -> GateResult:
        blockers = tuple(f"{path} 缺失（{why}）" for path, why in REQUIRED_FIELDS
                         if not self._field(path))
        warnings: list[str] = []
        if not self.change_list:
            warnings.append("change.list 未提供：定位效率受影响，按未知变更记录")
        if not self.os_matrix and not self.runtime_matrix and not self.client_matrix:
            warnings.append("matrix 未提供：仅覆盖主平台，报告注明覆盖缺口")
        if not self.known_defects:
            warnings.append("known.defects 未提供：历史缺陷复查项缺失")
        for name in METRIC_NAMES:
            if name not in self.thresholds.metrics:
                warnings.append(f"thresholds.{name} 未提供：回退 ±10%（临时阈值）")
        if not self.thresholds.metrics:
            warnings.append("整套阈值为临时值，报告须显式标注")
        return GateResult(not blockers, blockers, tuple(warnings))

    def theta(self, metric: str) -> tuple[float, float, bool]:
        theta, severe, temporary = self.thresholds.theta(metric)
        sigma = self.rss_sigma.get(metric, 0.0)
        if sigma > 0 and metric not in self.thresholds.metrics:
            base = 100.0
            theta = max(self.thresholds.min_threshold, self.thresholds.k_sigma * sigma / base)
        return theta, severe, temporary


def _lookup(data: dict[str, Any], path: str) -> Any:
    if path in data:
        return data[path]
    node: Any = data
    for part in path.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node


def from_mapping(data: dict[str, Any]) -> RegressionConfig:
    def s(path: str, default: str = "") -> str:
        node = _lookup(data, path)
        return str(node) if node not in (None, "") else default

    def lst(path: str) -> tuple[str, ...]:
        node = _lookup(data, path)
        if isinstance(node, (list, tuple)):
            return tuple(str(x) for x in node)
        return (str(node),) if node else ()


    th = data.get("thresholds") or {}
    if not isinstance(th, dict):
        th = {}
    numeric = lambda key, default: float(th[key]) if key in th else default
    t = Thresholds(
        metrics={k: float(v) for k, v in (th.get("metrics") or {}).items()},
        severe={k: float(v) for k, v in (th.get("severe") or {}).items()},
        absolute={k: float(v) for k, v in (th.get("absolute") or {}).items()},
        leak=numeric("leak", DEFAULT_LEAK),
        k_sigma=numeric("k_sigma", 3.0),
        min_threshold=numeric("min_threshold", 0.05),
    )
    criteria = s("criteria.function")
    return RegressionConfig(
        platform=s("platform"), system=s("system.module").split(".")[0],
        module=".".join(s("system.module").split(".")[1:]),
        baseline_version=s("baseline.version"), candidate_version=s("candidate.version"),
        baseline_commit=s("baseline.commit"), candidate_commit=s("candidate.commit"),
        change_list=lst("change.list"),
        function_criteria=tuple(x.strip() for x in criteria.split(";") if x.strip()),
        os_matrix=lst("matrix.os"), runtime_matrix=lst("matrix.runtime"),
        client_matrix=lst("matrix.client"), thresholds=t,
        known_defects=lst("known.defects"), env_target=s("env.target"),
        env_image=s("env.image"), repeats=int(s("repeats", "1") or 1),
        wait_timeout=float(s("wait_timeout", "30") or 30), entry=s("cfg.entry"),
        data_snapshot=s("data.snapshot") or "snap_bg_001", whitelist=lst("whitelist"),
        rss_sigma={k: float(v) for k, v in (th.get("sigma") or {}).items()},
        output_rules=_lookup(data, "criteria.output") or {},
    )


def from_file(path: str | Path) -> RegressionConfig:
    data = read_json(path, None)
    if not isinstance(data, dict):
        return RegressionConfig()
    return from_mapping(data)


def with_repeats(config: RegressionConfig, repeats: int) -> RegressionConfig:
    return replace(config, repeats=max(1, int(repeats)))
