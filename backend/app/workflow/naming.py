from __future__ import annotations

import re

pass
NAME_RE = re.compile(r"[\w\u4e00-\u9fff.-]+")


def valid_name(name: str) -> bool:
    n = (name or "").strip()
    if not n or n in (".", "..") or not NAME_RE.fullmatch(n):
        return False
    return True


def check_name(name: str) -> str:
    from .errors import WorkflowError

    n = (name or "").strip()
    if not valid_name(n):
        raise WorkflowError(f"非法工作流名称: {n}")
    return n
