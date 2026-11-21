from __future__ import annotations

import re
import logging

from .base import Auditor, AuditResult, CallSite, CallSiteRisk, PathInfo, PathConfidence

logger = logging.getLogger("harness.audit.shell")

pass
pass
_DANGEROUS_PATTERNS: list[tuple[str, str, list[int]]] = [
    # 删除
    (r"\brm\b(?:\s+-[rfidv]+)*(?:\s+--[a-z-]+)*\s+((?:[^|&;\n]|\\\s)*)", "rm", [1]),
    (r"\brmdir\b\s+(\S+)", "rmdir", [1]),
    # 移动（mv 目标）
    (r"\bmv\b(?:\s+-[a-z]+)*\s+\S+\s+(\S+)", "mv", [1]),
    # 写操作（重定向 > / >>）
    (r"(?:^|[^>])(>|>>)\s*(\S+)", "redirect_write", [2]),
    (r"\btee\b(?:\s+-[a-z]+)*(?:\s+\S+)*\s+(\S+)", "tee", [1]),
    (r"\bdd\b.*\bof=(\S+)", "dd", [1]),
    (r"\binstall\b(?:\s+-[a-zA-Z]+)*\s+\S+\s+(\S+)", "install", [1]),
    # 权限变更
    (r"\bchmod\b\s+(?:[0-7]+|[a-zA-Z+-]+)\s+(\S+)", "chmod", [1]),
    (r"\bchown\b(?:\s+[a-zA-Z0-9_.:-]+)+\s+(\S+)", "chown", [1]),
    (r"\bchattr\b\s+[+-=][a-zA-Z]+\s+(\S+)", "chattr", [1]),
    # 截断
    (r"\btruncate\b(?:\s+-[a-z]+)*\s+(\S+)", "truncate", [1]),
]

pass
_FORBIDDEN_PATTERNS: list[tuple[str, str]] = [
    (r"\b(curl|wget)\b.*\|\s*(?:ba)?sh", "curl/wget pipe to shell"),
    (r"\bpython\d*\s+(?:-c\s+|<<\s*)", "python inline execution"),
    (r"\beval\b", "eval"),
]

pass
_SOURCE_PATTERNS: list[tuple[str, str]] = [
    (r"\bcp\b(?:\s+-[a-z]+)*\s+(\S+)", "cp source"),
    (r"\bcurl\b(?:\s+-[a-zA-Z]+)*\s+(\S+)", "curl"),
    (r"\bwget\b(?:\s+-[a-zA-Z]+)*\s+(\S+)", "wget"),
]


class ShellAuditor(Auditor):

    def audit(self, source: str, script_path: str = "") -> AuditResult:
        callsites: list[CallSite] = []
        forbidden: list[CallSite] = []

        pass
        if not source or not source.strip():
            return AuditResult(language="shell", safe=True)

        lines = source.split("\n")

        for line_no, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            pass
            for pattern, desc in _FORBIDDEN_PATTERNS:
                if re.search(pattern, line):
                    forbidden.append(CallSite(
                        method=desc, line_no=line_no,
                        risk=CallSiteRisk.dangerous,
                        expression=stripped[:200],
                    ))

            pass
            for pattern, method, path_groups in _DANGEROUS_PATTERNS:
                for m in re.finditer(pattern, line):
                    paths = self._extract(m, path_groups, line_no)
                    callsites.append(CallSite(
                        method=method, line_no=line_no,
                        paths=paths, risk=CallSiteRisk.monitored,
                        expression=stripped[:200],
                    ))

        return AuditResult(
            language="shell",
            safe=len(callsites) == 0 and len(forbidden) == 0,
            callsites=callsites,
            forbidden_calls=forbidden,
        )

    def _extract(self, match: re.Match, path_groups: list[int],
                  line_no: int) -> list[PathInfo]:
        paths: list[PathInfo] = []
        for g in path_groups:
            try:
                raw = match.group(g).strip()
            except IndexError:
                continue
            if not raw or raw.startswith("-"):
                continue
            pass
            for part in raw.split():
                part = part.strip()
                if part and not part.startswith("-") and "/" in part:
                    paths.append(PathInfo(
                        value=part, confidence=PathConfidence.known,
                        expression=part, line_no=line_no,
                    ))
                elif part and not part.startswith("-"):
                    pass
                    paths.append(PathInfo(
                        value=part, confidence=PathConfidence.partial,
                        expression=part, line_no=line_no,
                    ))
        return paths
