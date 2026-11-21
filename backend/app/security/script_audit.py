from __future__ import annotations

import logging
import re
from pathlib import Path
from .core import Risk, grade_paths
from .path_scan import inline_script_bodies
from .core import Risk, grade_paths

logger = logging.getLogger("harness.policy")

pass
_SCRIPT_CMD = re.compile(
    r"^\s*(?:\S*/)?(python[\d.]*|node|bash|sh|zsh)\s+"
    r"(?:-[A-Za-z]+\s+)*([^\s;|&]+\.(?:py|js|mjs|cjs|sh|bash))")


def script_target(command: str) -> tuple[str, str] | None:
    m = _SCRIPT_CMD.match(command or "")
    if not m:
        return None
    return m.group(1), m.group(2)


def audit_script(path: str, root: str, max_bytes: int = 400_000) -> list[Risk]:
    from .audit.base import Auditor

    if not path:
        return []
    try:
        p = Path(path).expanduser()
        if not p.is_absolute():
            p = Path(root).expanduser() / p
        if not p.is_file() or p.stat().st_size > max_bytes:
            return []
        auditor = Auditor.for_language(p.suffix.lstrip("."))
        if auditor is None:
            return []
        result = auditor.audit(p.read_text("utf-8", errors="replace"), str(p))
    except Exception:
        logger.debug("脚本静态审查失败: %s", path, exc_info=True)
        return []

    return _risks_of(result, str(path))


def _risks_of(result, label: str) -> list[Risk]:
    risks: list[Risk] = []
    for c in result.forbidden_calls:
        risks.append(Risk(target=label, severity="high",
                          description=f"脚本里有禁止的嵌套执行: {c.method}"))
    for c in result.callsites:
        targets = [pi.value for pi in c.paths] or [label]
        risks.append(Risk(target=targets[0], severity="medium",
                          description=f"脚本会调用 {c.method}"
                                      f"（第 {c.line_no} 行）"))
    return risks


def _audit_source(source: str, lang: str) -> list[Risk]:
    from .audit.base import Auditor

    if not source or not lang:
        return []
    try:
        auditor = Auditor.for_language(lang)
        if auditor is None:
            return []
        result = auditor.audit(source)
    except Exception:
        logger.debug("内联脚本静态审查失败", exc_info=True)
        return []
    return _risks_of(result, "")


def script_escapes_scope(command: str, root: str,
                          extra_safe: list[str] | None = None) -> list[str]:
    out: list[str] = []
    for r in script_risks(command, root):
        g = grade_paths([r.target], root, extra_safe)
        if g.critical:
            out.extend(g.critical)
        elif g.outside:
            out.extend(g.outside)
    return out


def script_risks(command: str, root: str) -> list[Risk]:
    risks: list[Risk] = []
    hit = script_target(command)
    if hit is not None:
        risks.extend(audit_script(hit[1], root))
    for lang, src in inline_script_bodies(command):
        risks.extend(_audit_source(src, lang))
    return risks
