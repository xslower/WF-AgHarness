# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from ....store import layout

_WORKER = layout.BACKEND_ROOT / "vendor" / "doc_worker.py"

# 解释器优先级：显式环境变量 > 本机主用的 conda 313 > 当前解释器
_DEFAULT_PY = "/usr/bin/python3"

# 各 op 的超时（秒）。大表 inspect 只读前几行，但 xls 要整份加载。
_TIMEOUT = {"table_inspect": 60, "table_rows": 60, "table_query": 60,
            "ppt_edit": 120, "ppt_probe": 60}


def worker_python() -> str:
    env = (os.environ.get("HARNESS_DOC_PYTHON") or "").strip()
    if env:
        return env
    if Path(_DEFAULT_PY).is_file():
        return _DEFAULT_PY
    return sys.executable


def install_hint(py: str, pkgs: list[str] | None = None) -> str:
    pkgs = pkgs or ["openpyxl", "xlrd", "PyYAML"]
    return f"{py} -m pip install {' '.join(pkgs)}"


def run_worker(payload: dict) -> dict:
    py = worker_python()
    if not Path(py).is_file():
        return {"ok": False, "code": "env_unavailable",
                "error": f"插件解释器不存在: {py}",
                "hint": "改 manifest.env.python 或设置 settings.envPython / HARNESS_DOC_PYTHON"}
    if not _WORKER.is_file():
        return {"ok": False, "code": "worker_missing",
                "error": f"解析器不存在: {_WORKER}"}

    op = str(payload.get("op") or "")
    timeout = _TIMEOUT.get(op, 60)
    try:
        proc = subprocess.run(
            [py, str(_WORKER)],
            input=json.dumps(payload, ensure_ascii=False),
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "code": "timeout",
                "error": f"{op} 超过 {timeout}s 未返回（文件可能过大）"}
    except OSError as e:
        return {"ok": False, "code": "env_unavailable", "error": f"起子进程失败: {e}"}

    lines = [ln for ln in (proc.stdout or "").splitlines() if ln.strip()]
    if not lines:
        stderr_lines = (proc.stderr or "").strip().splitlines()
        return {"ok": False, "code": "no_output",
                "error": "worker 没有输出"
                         + (("：" + stderr_lines[-1]) if stderr_lines else "")}
    try:
        out = json.loads(lines[-1])
    except json.JSONDecodeError:
        return {"ok": False, "code": "bad_output",
                "error": f"worker 输出不是 JSON: {lines[-1][:300]}"}

    if not out.get("ok") and out.get("code") == "missing_deps":
        # 缺哪个包就从错误里认出来，给一条精确命令
        msg = str(out.get("error") or "")
        pkgs = [p for p in ("openpyxl", "xlrd", "PyYAML", "python-pptx",
                            "python-docx") if p.lower().replace("-", "_") in msg.lower()
                or p.lower() in msg.lower()]
        out["hint"] = install_hint(py, pkgs or None)
    return out
