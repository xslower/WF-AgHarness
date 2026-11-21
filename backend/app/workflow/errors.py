from __future__ import annotations

KIND_INVALID = "invalid"
"""定义/输入不合法 → 400。默认值，绝大多数 raise 都属于这一类。"""

KIND_NOT_FOUND = "not_found"
"""目标不存在（工作流/运行/节点）→ 404。"""

KIND_CONFLICT = "conflict"
"""与当前状态冲突（如运行已结束）→ 409。"""

pass
ERROR_STATUS: dict[str, int] = {
    KIND_INVALID: 400,
    KIND_NOT_FOUND: 404,
    KIND_CONFLICT: 409,
}


class WorkflowError(Exception):

    def __init__(self, message: str = "", kind: str = KIND_INVALID,
                 issues: list[str] | None = None) -> None:
        super().__init__(message)
        self.kind = kind
        self.issues = list(issues or [])


def not_found(message: str) -> WorkflowError:
    return WorkflowError(message, kind=KIND_NOT_FOUND)
