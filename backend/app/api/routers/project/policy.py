from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ....security.project_mode import DEFAULT_MODE, MODES, clear_mode, get_mode, set_mode
from ...errors import from_error

router = APIRouter()


@router.get("/api/projects/policy")
def read_policy(path: str = ""):
    return {
        "mode": get_mode(path) if path else DEFAULT_MODE,
        "default": DEFAULT_MODE,
        "modes": [
            {"value": "yolo", "label": "全放开",
             "hint": "目录内外都直接执行；只拦 sudo / 删根目录这类硬高危"},
            {"value": "workspace", "label": "目录沙箱",
             "hint": "工作目录内全放开；出目录先 AI 审核，不过再人工"},
            {"value": "review", "label": "全程 AI 审核",
             "hint": "读操作放行，改动一律 AI 审核，不过再人工"},
        ],
        "always": ("三档都会管：安装类命令需人工批准、系统关键路径"
                   "（/etc、~/.ssh 等）与硬高危命令（sudo、mkfs、删根目录、"
                   "下载即执行）直接拒绝"),
    }


class PolicyIn(BaseModel):
    path: str
    mode: str


@router.post("/api/projects/policy")
def write_policy(body: PolicyIn):
    if body.mode not in MODES:
        raise from_error(ValueError(f"mode 必须是 {list(MODES)} 之一，收到: {body.mode}"))
    if not body.path:
        raise from_error(ValueError("path 不能为空"))
    return {"ok": True, "path": body.path, "mode": set_mode(body.path, body.mode)}


@router.delete("/api/projects/policy")
def reset_policy(path: str):
    return {"ok": clear_mode(path), "mode": DEFAULT_MODE}
