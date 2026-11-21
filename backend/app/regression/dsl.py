from __future__ import annotations

from dataclasses import replace
from typing import Any, Iterable

from .model import PHASES, STEP_TYPES, Scenario, Step, RunSpec
from .model import BASELINE, CANDIDATE

pass
pass
_DEF: dict[str, dict[str, Any]] = {
    "TC-01": {
        "title": "后台启动成功且只启动一个实例", "priority": "P0", "core": True,
        "fr": ("FR-01",), "phases": ("start",),
        "steps": [
            {"type": "setup", "action": "restore_snapshot", "ref": "${cfg.snapshot}"},
            {"type": "trigger", "action": "start_background_job", "entry": "${cfg.entry}",
             "capture": ("pid", "status_api")},
            {"type": "assert", "checks": ("status_matches_reality", "no_duplicate_instance")},
            {"type": "teardown", "action": "stop_and_archive"},
        ],
    },
    "TC-02": {
        "title": "前台关闭后任务持续运行", "priority": "P0", "core": True,
        "fr": ("FR-02",), "phases": ("start", "running", "stopped"),
        "steps": [
            {"type": "trigger", "action": "start_background_job", "entry": "${cfg.entry}",
             "capture": ("pid", "status_api")},
            {"type": "background", "action": "close_foreground"},
            {"type": "wait", "action": "wait_checkpoint", "min_seq": 3,
             "timeout": "${cfg.wait_timeout}"},
            {"type": "assert", "checks": ("alive_by_pid", "heartbeat_monotonic")},
            {"type": "teardown", "action": "stop_and_archive"},
        ],
    },
    "TC-03": {
        "title": "状态显示与实际运行状态一致", "priority": "P0", "core": True,
        "fr": ("FR-03",), "phases": ("start", "running", "stopped"),
        "steps": [
            {"type": "trigger", "action": "start_background_job", "entry": "${cfg.entry}",
             "capture": ("pid", "status_api")},
            {"type": "wait", "action": "wait_checkpoint", "min_seq": 2},
            {"type": "assert", "checks": ("status_matches_reality",)},
            {"type": "teardown", "action": "stop_and_archive"},
        ],
    },
    "TC-04": {
        "title": "切到后台后进度 checkpoint 连续", "priority": "P0", "core": True,
        "fr": ("FR-04",), "phases": ("start", "running", "resumed"),
        "steps": [
            {"type": "trigger", "action": "start_background_job", "entry": "${cfg.entry}",
             "capture": ("pid", "status_api")},
            {"type": "background", "action": "send_to_background"},
            {"type": "wait", "action": "wait_checkpoint", "min_seq": 3},
            {"type": "restore", "action": "restore_foreground"},
            {"type": "assert", "checks": ("heartbeat_monotonic", "status_matches_reality")},
            {"type": "teardown", "action": "stop_and_archive"},
        ],
    },
    "TC-05": {
        "title": "断开 SSH/终端/登录会话后进程存活", "priority": "P0", "core": True,
        "fr": ("FR-02", "FR-04"), "phases": ("start", "running", "resumed", "stopped"),
        "steps": [
            {"type": "setup", "action": "restore_snapshot", "ref": "${cfg.snapshot}"},
            {"type": "trigger", "action": "start_background_job", "entry": "${cfg.entry}",
             "capture": ("pid", "status_api")},
            {"type": "background", "action": "disconnect_session", "mode": "ssh_drop"},
            {"type": "wait", "action": "wait_checkpoint", "min_seq": 3,
             "timeout": "${cfg.wait_timeout}"},
            {"type": "assert", "checks": ("alive_by_pid", "heartbeat_monotonic",
                                          "status_matches_reality")},
            {"type": "restore", "action": "reconnect_session"},
            {"type": "assert", "checks": ("output_complete", "no_duplicate_side_effect")},
            {"type": "teardown", "action": "stop_and_archive",
             "artifacts": ("logs", "metrics", "output")},
        ],
    },
    "TC-06": {
        "title": "用户主动停止后台任务", "priority": "P0", "core": True,
        "fr": ("FR-05",), "phases": ("start", "stopped"),
        "steps": [
            {"type": "trigger", "action": "start_background_job", "entry": "${cfg.entry}",
             "capture": ("pid", "status_api")},
            {"type": "fault", "action": "user_stop"},
            {"type": "assert", "checks": ("status_matches_reality", "alive_by_pid")},
            {"type": "teardown", "action": "archive"},
        ],
    },
    "TC-07": {
        "title": "进程被 kill -9 后被检测并可恢复", "priority": "P0", "core": True,
        "fr": ("FR-05", "FR-08"), "phases": ("start", "running", "failed", "stopped"),
        "steps": [
            {"type": "trigger", "action": "start_background_job", "entry": "${cfg.entry}",
             "capture": ("pid", "status_api")},
            {"type": "fault", "action": "kill_process", "signal": 9},
            {"type": "assert", "checks": ("status_matches_reality",)},
            {"type": "restore", "action": "retry_job", "idempotency": True},
            {"type": "assert", "checks": ("output_complete", "no_duplicate_side_effect")},
            {"type": "teardown", "action": "stop_and_archive"},
        ],
    },
    "TC-08": {
        "title": "重启后按幂等键对账无重复副作用", "priority": "P0", "core": True,
        "fr": ("FR-05", "FR-06"), "phases": ("start", "failed", "resumed", "stopped"),
        "steps": [
            {"type": "trigger", "action": "start_background_job", "entry": "${cfg.entry}",
             "capture": ("pid", "status_api")},
            {"type": "fault", "action": "service_restart"},
            {"type": "restore", "action": "retry_job", "idempotency": True},
            {"type": "assert", "checks": ("output_complete", "no_duplicate_side_effect")},
            {"type": "teardown", "action": "stop_and_archive"},
        ],
    },
    "TC-09": {
        "title": "产出物完整且 schema/业务规则校验通过", "priority": "P0", "core": True,
        "fr": ("FR-06",), "phases": ("start", "stopped"),
        "steps": [
            {"type": "trigger", "action": "start_background_job", "entry": "${cfg.entry}",
             "capture": ("pid", "status_api")},
            {"type": "wait", "action": "wait_terminal", "timeout": "${cfg.wait_timeout}"},
            {"type": "assert", "checks": ("output_complete",)},
            {"type": "teardown", "action": "archive"},
        ],
    },
    "TC-10": {
        "title": "网络中断不崩溃、失败可记录、恢复可重试", "priority": "P1", "core": False,
        "fr": ("FR-08",), "phases": ("start", "running", "failed", "resumed"),
        "steps": [
            {"type": "trigger", "action": "start_background_job", "entry": "${cfg.entry}",
             "capture": ("pid", "status_api")},
            {"type": "fault", "action": "network_drop"},
            {"type": "assert", "checks": ("no_crash", "status_matches_reality")},
            {"type": "restore", "action": "network_restore"},
            {"type": "assert", "checks": ("output_complete",)},
            {"type": "teardown", "action": "stop_and_archive"},
        ],
    },
    "TC-11": {
        "title": "权限不足时明确失败且无越权行为", "priority": "P1", "core": False,
        "fr": ("FR-08",), "phases": ("start", "failed"),
        "steps": [
            {"type": "trigger", "action": "start_background_job", "entry": "${cfg.entry}",
             "capture": ("pid", "status_api")},
            {"type": "fault", "action": "revoke_permission"},
            {"type": "assert", "checks": ("status_matches_reality", "no_crash")},
            {"type": "teardown", "action": "stop_and_archive"},
        ],
    },
    "TC-12": {
        "title": "资源受限下不崩溃且错误可追踪", "priority": "P1", "core": False,
        "fr": ("FR-08",), "phases": ("start", "running", "failed"),
        "steps": [
            {"type": "trigger", "action": "start_background_job", "entry": "${cfg.entry}",
             "capture": ("pid", "status_api")},
            {"type": "fault", "action": "limit_resources", "cpu": 0.1, "memory_mb": 128},
            {"type": "assert", "checks": ("no_crash", "status_matches_reality")},
            {"type": "teardown", "action": "stop_and_archive"},
        ],
    },
    "TC-13": {
        "title": "长时间运行无内存/FD 泄漏且心跳连续", "priority": "P1", "core": False,
        "kind": "stability", "phases": ("start", "running", "stopped"),
        "fr": ("FR-07", "FR-09"), "steps": [
            {"type": "trigger", "action": "start_background_job", "entry": "${cfg.entry}",
             "capture": ("pid", "status_api")},
            {"type": "wait", "action": "long_run", "duration_min": "${cfg.duration_min}"},
            {"type": "assert", "checks": ("heartbeat_monotonic", "no_resource_leak")},
            {"type": "teardown", "action": "stop_and_archive"},
        ],
    },
    "TC-14": {
        "title": "候选与基线产出物/状态码行为指纹一致", "priority": "P0", "core": False,
        "kind": "function", "phases": ("start", "running", "stopped"),
        "fr": ("FR-09",), "steps": [
            {"type": "trigger", "action": "start_background_job", "entry": "${cfg.entry}",
             "capture": ("pid", "status_api")},
            {"type": "wait", "action": "wait_terminal", "timeout": "${cfg.wait_timeout}"},
            {"type": "assert", "checks": ("output_complete", "fingerprint_matches")},
            {"type": "teardown", "action": "stop_and_archive"},
        ],
    },
    "TC-15": {
        "title": "候选与基线关键指标偏差在阈值内", "priority": "P1", "core": False,
        "kind": "performance", "phases": ("start", "running", "stopped"),
        "fr": ("FR-09",), "steps": [
            {"type": "trigger", "action": "start_background_job", "entry": "${cfg.entry}",
             "capture": ("pid", "status_api")},
            {"type": "wait", "action": "wait_terminal", "timeout": "${cfg.wait_timeout}"},
            {"type": "assert", "checks": ("metrics_within_threshold",)},
            {"type": "teardown", "action": "stop_and_archive"},
        ],
    },
}

ALL_PLATFORMS = ("server", "cli", "desktop", "mobile", "web", "queue")


def _step(raw: dict[str, Any]) -> Step:
    known = {"type", "action", "checks"}
    params = {k: v for k, v in raw.items() if k not in known}
    checks = raw.get("checks", ())
    if isinstance(checks, str):
        checks = (checks,)
    return Step(str(raw["type"]), str(raw.get("action", "")),
                tuple(str(c) for c in checks), params)


def validate_scenario(s: Scenario) -> tuple[str, ...]:
    errors: list[str] = []
    if not s.id or not s.title:
        errors.append(f"{s.id}: id/title 不得为空")
    if not s.steps:
        errors.append(f"{s.id}: 无步骤")
    if not any(st.type == "trigger" for st in s.steps):
        errors.append(f"{s.id}: 缺少 trigger 步骤")
    for st in s.steps:
        if st.type not in STEP_TYPES:
            errors.append(f"{s.id}: 未知步骤类型 {st.type!r}")
    for phase in s.required_phases:
        if phase not in PHASES:
            errors.append(f"{s.id}: 未知 phase {phase!r}")
    return tuple(errors)


def all_scenarios() -> tuple[Scenario, ...]:
    out: list[Scenario] = []
    for sid, raw in _DEF.items():
        kind = raw.get("kind", "function")
        tags = raw.get("platforms", ALL_PLATFORMS)
        s = Scenario(
            id=sid, title=raw["title"], priority=raw["priority"], kind=kind,
            core=bool(raw.get("core", False)), fr=tuple(raw.get("fr", ())),
            tc=sid, platform_tags=tuple(tags),
            required_phases=tuple(raw.get("phases", ())),
            steps=tuple(_step(x) for x in raw["steps"]),
        )
        errors = validate_scenario(s)
        if errors:
            raise ValueError("; ".join(errors))
        out.append(s)
    return tuple(out)


def by_id(case_id: str) -> Scenario | None:
    return next((s for s in all_scenarios() if s.id == case_id), None)


def core_scenarios() -> tuple[Scenario, ...]:
    return tuple(s for s in all_scenarios() if s.core)


def matrix(scenarios: Iterable[Scenario], platform: str, repeats: int,
           env_id: str, seed_prefix: str) -> list[RunSpec]:
    specs: list[RunSpec] = []
    order = 0
    platforms = (platform,)
    for scenario in scenarios:
        for round_no in range(1, max(1, repeats) + 1):
            for role in (BASELINE, CANDIDATE):
                for plat in platforms:
                    run_id = f"{seed_prefix}-{scenario.id.lower()}-{role}-{round_no}"
                    specs.append(RunSpec(run_id, scenario.id, role, plat, round_no,
                                         env_id, f"{seed_prefix}-{scenario.id}-{round_no}",
                                         order))
                    order += 1
    return specs


def substitute(step: Step, values: dict[str, str]) -> Step:
    def conv(v: Any) -> Any:
        if isinstance(v, str) and v.startswith("${cfg.") and v.endswith("}"):
            key = v[6:-1]
            return values.get(key, v)
        if isinstance(v, (list, tuple)):
            return tuple(conv(x) for x in v)
        return v

    return replace(step, params={k: conv(v) for k, v in step.params.items()})
