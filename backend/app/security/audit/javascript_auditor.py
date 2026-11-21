from __future__ import annotations

import re
import logging

from .base import Auditor, AuditResult, CallSite, CallSiteRisk, PathInfo, PathConfidence

logger = logging.getLogger("harness.audit.js")

pass
pass
_DANGEROUS_APIS: list[tuple[str, str, CallSiteRisk, str]] = [
    # 写文件
    (
        r"(?:fs|require\(['\"](?:fs|node:fs)['\"]\))\.writeFile(?:Sync)?\s*\(\s*(['\"`])(.*?)\1",
        "fs.writeFile", CallSiteRisk.monitored, "$2",
    ),
    (
        r"(?:fs|require\(['\"](?:fs|node:fs)['\"]\))\.appendFile(?:Sync)?\s*\(\s*(['\"`])(.*?)\1",
        "fs.appendFile", CallSiteRisk.monitored, "$2",
    ),
    # 删除
    (
        r"(?:fs|require\(['\"](?:fs|node:fs)['\"]\))\.unlink(?:Sync)?\s*\(\s*(['\"`])(.*?)\1",
        "fs.unlink", CallSiteRisk.monitored, "$2",
    ),
    (
        r"(?:fs|require\(['\"](?:fs|node:fs)['\"]\))\.rmdir(?:Sync)?\s*\(\s*(['\"`])(.*?)\1",
        "fs.rmdir", CallSiteRisk.monitored, "$2",
    ),
    (
        r"(?:fs|require\(['\"](?:fs|node:fs)['\"]\))\.rm\s*\(\s*(['\"`])(.*?)\1",
        "fs.rm", CallSiteRisk.monitored, "$2",
    ),
    (
        r"(?:fs|require\(['\"](?:fs|node:fs)['\"]\))\.rmSync\s*\(\s*(['\"`])(.*?)\1",
        "fs.rmSync", CallSiteRisk.monitored, "$2",
    ),
    # 权限
    (
        r"(?:fs|require\(['\"](?:fs|node:fs)['\"]\))\.chmod(?:Sync)?\s*\(\s*(['\"`])(.*?)\1",
        "fs.chmod", CallSiteRisk.monitored, "$2",
    ),
    (
        r"(?:fs|require\(['\"](?:fs|node:fs)['\"]\))\.chown(?:Sync)?\s*\(\s*(['\"`])(.*?)\1",
        "fs.chown", CallSiteRisk.monitored, "$2",
    ),
    # 创建写入流
    (
        r"(?:fs|require\(['\"](?:fs|node:fs)['\"]\))\.createWriteStream\s*\(\s*(['\"`])(.*?)\1",
        "fs.createWriteStream", CallSiteRisk.monitored, "$2",
    ),
    # 移动/重命名
    (
        r"(?:fs|require\(['\"](?:fs|node:fs)['\"]\))\.rename(?:Sync)?\s*\(\s*(['\"`])(.*?)\1",
        "fs.rename", CallSiteRisk.monitored, "$2",
    ),
]

pass
_FORBIDDEN_APIS: list[tuple[str, str]] = [
    (r"child_process\.exec\s*\(", "child_process.exec"),
    (r"child_process\.execSync\s*\(", "child_process.execSync"),
    (r"child_process\.spawn\s*\(", "child_process.spawn"),
    (r"child_process\.spawnSync\s*\(", "child_process.spawnSync"),
    (r"child_process\.fork\s*\(", "child_process.fork"),
    (r"require\(['\"]child_process['\"]\)", "require child_process"),
    (r"eval\s*\(", "eval"),
    (r"new\s+Function\s*\(", "new Function"),
]

pass
_PATH_EXTRACT = re.compile(r"(['\"`])((?:(?!\1).)*?/.*?)\1")


def _extract_paths_from_line(line: str, line_no: int) -> list[PathInfo]:
    paths: list[PathInfo] = []
    for m in _PATH_EXTRACT.finditer(line):
        val = m.group(2)
        if "/" in val:
            paths.append(PathInfo(
                value=val, confidence=PathConfidence.known,
                expression=val, line_no=line_no,
            ))
    return paths


class JavaScriptAuditor(Auditor):

    def audit(self, source: str, script_path: str = "") -> AuditResult:
        callsites: list[CallSite] = []
        forbidden: list[CallSite] = []

        if not source or not source.strip():
            return AuditResult(language="javascript", safe=True)

        lines = source.split("\n")

        for line_no, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("//") or stripped.startswith("#"):
                continue

            pass
            for pattern, method in _FORBIDDEN_APIS:
                if re.search(pattern, line):
                    forbidden.append(CallSite(
                        method=method, line_no=line_no,
                        risk=CallSiteRisk.dangerous,
                        expression=stripped[:200],
                    ))

            pass
            for pattern, method, risk, _ in _DANGEROUS_APIS:
                if re.search(pattern, line):
                    paths = _extract_paths_from_line(line, line_no)
                    callsites.append(CallSite(
                        method=method, line_no=line_no,
                        paths=paths, risk=risk,
                        expression=stripped[:200],
                    ))
                    break

        return AuditResult(
            language="javascript",
            safe=len(callsites) == 0 and len(forbidden) == 0,
            callsites=callsites,
            forbidden_calls=forbidden,
        )
