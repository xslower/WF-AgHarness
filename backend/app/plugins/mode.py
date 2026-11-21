
import re
from pathlib import Path
from typing import Any

import yaml

from . import location
from . import package as pkgmod

_MODES = frozenset({pkgmod.MODE_DEV, pkgmod.MODE_RELEASE})


def resolve_project_package(pid: str, project: str, installs: Any) -> Path:
    from . import resolve as resolver

    if installs is None:
        raise ValueError(f"插件 {pid} 未登记（安装库不可用）")
    rec = resolver.resolve(installs, pid, project)
    return location.resolve_package(rec, str(rec["project"] or ""))



def set_mode(root: str | Path, mode: str) -> str:
    if mode not in _MODES:
        raise ValueError(f"mode 只能是 dev / release: {mode!r}")
    f = Path(root) / pkgmod.PLUGIN_YAML
    raw = f.read_text("utf-8")
    lines = raw.splitlines(keepends=True)
    hit = next((i for i, line in enumerate(lines)
                if re.match(r"^mode\s*:", line)), -1)
    if hit < 0:
        raise ValueError(f"plugin.yaml 缺少 mode 字段（不做兼容缺省）: {f}")
    nl = "\n" if lines[hit].endswith("\n") else ""
    lines[hit] = f"mode: {mode}{nl}"
    text = "".join(lines)
    try:
        data = yaml.safe_load(text) or {}
    except Exception as e:
        raise ValueError(f"plugin.yaml 解析失败: {f}: {e}") from e
    if not isinstance(data, dict) or str(data.get("mode") or "") != mode:
        raise ValueError(f"写回后 mode 校验失败: {f}")
    tmp = f.with_name(f.name + ".tmp")
    try:
        tmp.write_text(text, "utf-8")
        tmp.replace(f)
    finally:
        tmp.unlink(missing_ok=True)
    return text
