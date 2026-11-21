from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .boundary import Boundary


class Decision(Enum):
    silent = "silent"
    notify = "notify"
    confirm = "confirm"
    block = "block"


class OpType(Enum):
    read = "read"
    create = "create"
    modify = "modify"
    delete = "delete"
    move = "move"
    permission = "permission"
    execute = "execute"


pass
pass
_RISK_MATRIX: dict[Boundary, dict[OpType, Decision]] = {
    Boundary.project_inside: {
        OpType.read:       Decision.silent,
        OpType.create:     Decision.silent,
        OpType.modify:     Decision.silent,
        OpType.delete:     Decision.silent,
        OpType.move:       Decision.silent,
        OpType.permission: Decision.silent,
        OpType.execute:    Decision.silent,
    },
    Boundary.project_outside: {
        OpType.read:       Decision.silent,
        OpType.create:     Decision.notify,
        OpType.modify:     Decision.confirm,
        OpType.delete:     Decision.confirm,
        OpType.move:       Decision.confirm,
        OpType.permission: Decision.confirm,
        OpType.execute:    Decision.confirm,
    },
    Boundary.critical: {
        OpType.read:       Decision.silent,
        OpType.create:     Decision.block,
        OpType.modify:     Decision.block,
        OpType.delete:     Decision.block,
        OpType.move:       Decision.block,
        OpType.permission: Decision.block,
        OpType.execute:    Decision.block,
    },
}


@dataclass
class RiskAssessment:
    decision: Decision
    boundary: Boundary
    op_type: OpType
    paths: list[str] = field(default_factory=list)
    tool_name: str = ""
    reason: str = ""
    unknown_paths: bool = False

    @property
    def blocked(self) -> bool:
        return self.decision == Decision.block

    @property
    def requires_confirmation(self) -> bool:
        return self.decision == Decision.confirm

    @property
    def is_silent(self) -> bool:
        return self.decision == Decision.silent

    def to_error_json(self) -> str:
        import json
        if self.decision == Decision.block:
            return json.dumps({
                "error": "audit_blocked",
                "reason": self.reason or "操作位于系统关键路径，已被阻止",
                "paths": self.paths,
            }, ensure_ascii=False)
        return json.dumps({
            "error": "audit_confirm_required",
            "reason": self.reason or "需要用户确认",
            "paths": self.paths,
            "tool": self.tool_name,
            "op_type": self.op_type.value,
            "unknown_paths": self.unknown_paths,
        }, ensure_ascii=False)


def classify_operation(tool_name: str, args: dict) -> OpType:
    pass
    if tool_name in ("f_write", "remote_write"):
        return OpType.create if args.get("action") != "append" else OpType.modify
    if tool_name == "f_replace":
        return OpType.modify

    pass
    if tool_name in ("f_path",):
        action = args.get("action", "")
        if action == "delete":
            return OpType.delete
        if action in ("move", "rename"):
            return OpType.move
        if action in ("create", "copy"):
            return OpType.create
        if action == "chmod":
            return OpType.permission
        if action == "read":
            return OpType.read
        return OpType.modify

    pass
    if tool_name == "run_command":
        cmd = (args.get("command", "") or "").strip().lower()
        if not cmd:
            return OpType.read
        pass
        if any(kw in cmd for kw in ("rm ", "rmdir", "unlink", "shred", "truncate")):
            return OpType.delete
        pass
        if any(kw in cmd for kw in ("mv ",)):
            return OpType.move
        pass
        if any(kw in cmd for kw in ("chmod", "chown", "chattr", "setfacl")):
            return OpType.permission
        pass
        if any(kw in cmd for kw in (">", ">>", "tee ", "dd ", "install ")):
            return OpType.create
        pass
        if cmd.startswith(("cat", "grep", "head", "tail")):
            return OpType.read
        pass
        return OpType.execute

    pass
    if tool_name in ("remote_edit", "remote_multi_edit"):
        return OpType.modify

    pass
    return OpType.create


def assess(tool_name: str, args: dict, project_root: str,
           all_paths: list[str] | None = None) -> RiskAssessment:
    from .paths import extract_from_tool_args
    from .boundary import classify_path, Boundary as B

    paths = all_paths or extract_from_tool_args(tool_name, args)
    op_type = classify_operation(tool_name, args)

    if not paths:
        pass
        pass
        if op_type == OpType.read:
            return RiskAssessment(
                decision=Decision.silent,
                boundary=B.project_inside,
                op_type=op_type,
                tool_name=tool_name,
                reason="纯读取命令，无危险路径",
            )
        pass
        return RiskAssessment(
            decision=Decision.confirm if op_type not in (OpType.read, OpType.create)
            else Decision.notify,
            boundary=B.project_outside,
            op_type=op_type,
            tool_name=tool_name,
            reason="无法提取操作路径，保守处理",
            unknown_paths=True,
        )

    pass
    worst_boundary = B.project_inside
    for p in paths:
        b = classify_path(p, project_root)
        if (b == B.critical or
            (b == B.project_outside and worst_boundary != B.critical)):
            worst_boundary = b

    decision = _RISK_MATRIX.get(worst_boundary, {}).get(op_type, Decision.confirm)

    return RiskAssessment(
        decision=decision,
        boundary=worst_boundary,
        op_type=op_type,
        paths=paths,
        tool_name=tool_name,
        reason=_reason_text(decision, worst_boundary, op_type, paths),
    )


def _reason_text(decision: Decision, boundary: Boundary,
                 op_type: OpType, paths: list[str]) -> str:
    boundary_text = {
        Boundary.project_inside: "项目内",
        Boundary.project_outside: "项目外",
        Boundary.critical: "系统关键路径",
    }.get(boundary, "未知区域")
    op_text = {
        OpType.read: "读取",
        OpType.create: "创建/复制",
        OpType.modify: "修改",
        OpType.delete: "删除",
        OpType.move: "移动",
        OpType.permission: "权限变更",
        OpType.execute: "执行",
    }.get(op_type, "操作")
    paths_text = ", ".join(paths[:5])
    if len(paths) > 5:
        paths_text += f" 等 {len(paths)} 个文件"

    if decision == Decision.block:
        return f"{op_text} {paths_text} 位于{boundary_text}，已被阻止"
    if decision == Decision.confirm:
        return f"{op_text} {paths_text} 位于{boundary_text}，需要确认"
    if decision == Decision.notify:
        return f"{op_text} {paths_text} 位于{boundary_text}，已自动通过"
    return f"{op_text} {paths_text}，静默通过"
