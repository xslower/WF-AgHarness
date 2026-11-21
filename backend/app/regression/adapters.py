from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .model import BASELINE, CANDIDATE, Event, ProbeSnapshot, Scenario, CheckResult
from .model import PHASES

pass
PLATFORM_LABELS = {
    "server": "服务端守护进程：systemd/supervisor/setsid + 输出重定向",
    "cli": "CLI 长任务：nohup/disown/tmux，关注 SIGHUP 与 fd 继承",
    "desktop": "桌面应用：关窗/最小化/锁屏，关注 OS 后台抑制策略",
    "mobile": "移动端：切后台/锁屏，关注 Doze 与后台限制",
    "web": "Web 前端：Service Worker/Worker/visibilitychange，关注节流冻结",
    "queue": "任务队列：worker 租约/心跳，关注重启后租约回收与幂等",
}


class UnsupportedPlatform(ValueError):
    pass


@dataclass
class BackendResult:
    events: list[dict[str, Any]] = field(default_factory=list)
    snapshot: ProbeSnapshot | None = None


class Backend:

    def background(self, action: str, params: dict[str, Any]) -> BackendResult:
        return BackendResult()

    def restore(self, action: str, params: dict[str, Any]) -> BackendResult:
        return BackendResult()

    def fault(self, action: str, params: dict[str, Any]) -> BackendResult:
        return BackendResult()

    def probe(self) -> ProbeSnapshot:
        return ProbeSnapshot(ts="")


class SimulationBackend(Backend):

    def __init__(self, profile: str = "normal", role: str = BASELINE,
                 scenario: Scenario | None = None, seed: str = "") -> None:
        if profile not in ("normal", "dead_process", "incomplete_output",
                           "missing_events", "crash", "duplicate_side_effect",
                           "status_lie", "leak"):
            raise ValueError(f"未知模拟轨迹: {profile}")
        self.profile = profile
        self.role = role
        self.scenario = scenario
        self.seed = seed
        self.checkpoints: list[int] = []
        self.phase_trail: list[str] = []
        self.killed = False
        self.restored = False
        self.fault_kind = ""
        self.probe_count = 0

    pass
    def _advance(self, n: int = 1) -> None:
        start = self.checkpoints[-1] if self.checkpoints else 0
        self.checkpoints.extend(range(start + 1, start + 1 + n))

    def _phase(self, phase: str) -> dict[str, Any]:
        self.phase_trail.append(phase)
        return {"phase": phase, "detail": {"source": "simulation", "seed": self.seed}}

    def background(self, action: str, params: dict[str, Any]) -> BackendResult:
        return BackendResult(events=[self._phase("running")])

    def restore(self, action: str, params: dict[str, Any]) -> BackendResult:
        self.restored = True
        self.killed = False
        return BackendResult(events=[self._phase("resumed")])

    def fault(self, action: str, params: dict[str, Any]) -> BackendResult:
        self.fault_kind = action
        if action in ("kill_process", "user_stop", "service_restart"):
            self.killed = True
        phase = "stopped" if action == "user_stop" else "failed"
        return BackendResult(events=[self._phase(phase)])

    def _phases(self) -> tuple[str, ...]:
        phases = tuple(self.phase_trail)
        if self.profile == "missing_events":
            phases = tuple(p for p in phases if p != "resumed")
        if self.probe_count == 1:
            phases = ("start",) + phases
        live = ("stopped" if self.killed and self.fault_kind == "user_stop" else
                "failed" if self.killed else "running")
        if live not in phases:
            phases += (live,)
        return phases

    def _status(self, dead: bool, complete: bool) -> str:
        if dead and self.profile == "status_lie":
            return "running"
        if dead and not self.restored:
            return "failed"
        if dead:
            return "stopped"
        return "done" if self.restored else "running"

    def _resource(self, slope: float, seq: int) -> dict[str, float]:
        return {
            "rss_mb": 100.0 + slope * seq, "fd_count": 20.0 + slope * seq,
            "rss_slope": slope, "fd_slope": slope, "cpu_pct": 3.0,
            "duration_ms": 1000.0 if self.role == BASELINE else 1050.0,
            "response_ms": 50.0 if self.role == BASELINE else 52.0,
        }

    def probe(self) -> ProbeSnapshot:
        self.probe_count += 1
        self._advance(2 if not self.killed else 0)
        seq = self.checkpoints[-1] if self.checkpoints else 0
        dead = self.killed or self.profile == "dead_process"
        complete = self.profile not in ("incomplete_output", "crash")
        if self.killed and not self.restored:
            complete = False
        pass
        leaking = self.profile == "leak" and self.role == CANDIDATE
        slope = 4.0 if leaking else 0.2
        error = ("E_IO" if self.profile == "crash" else
                 "E_PERM" if dead and self.fault_kind == "revoke_permission" else
                 "E_ABORT" if dead else "")
        return ProbeSnapshot(
            ts="", reported_status=self._status(dead, complete),
            pid=4242, pid_alive=not dead,
            heartbeat_seq=seq, heartbeat_times=tuple(float(i) for i in range(seq)),
            checkpoint=seq, records=seq * 10,
            idempotency_conflicts=2 if self.profile == "duplicate_side_effect" else 0,
            retries=1 if self.fault_kind else 0,
            output_complete=complete,
            output_schema_ok=self.profile not in ("incomplete_output", "crash"),
            output_signature={"schema": "v1", "records": seq * 10,
                              "status": "done"},
            resource=self._resource(slope, seq), error_code=error,
            exit_code=(-9 if dead and self.fault_kind == "kill_process" else
                       1 if self.profile == "crash" else 0),
            events=tuple({"phase": p} for p in self._phases()),
        )


@dataclass(frozen=True)
class Adapter:

    platform: str
    backend: Backend

    def __post_init__(self) -> None:
        if self.platform not in PLATFORM_LABELS:
            raise UnsupportedPlatform(
                f"平台 {self.platform!r} 未在 G0 确认；可选: {','.join(PLATFORM_LABELS)}")

    def background(self, action: str, params: dict[str, Any]) -> BackendResult:
        return self.backend.background(action, params)

    def restore(self, action: str, params: dict[str, Any]) -> BackendResult:
        return self.backend.restore(action, params)

    def fault(self, action: str, params: dict[str, Any]) -> BackendResult:
        return self.backend.fault(action, params)

    def probe(self) -> ProbeSnapshot:
        return self.backend.probe()


BackendFactory = Callable[[str, str, Scenario | None, str], Backend]


def build_adapter(platform: str, role: str, scenario: Scenario, seed: str,
                  factory: BackendFactory | None = None) -> Adapter:
    backend = (factory(role, platform, scenario, seed) if factory else
               SimulationBackend(profile="normal", role=role, scenario=scenario, seed=seed))
    return Adapter(platform, backend)
