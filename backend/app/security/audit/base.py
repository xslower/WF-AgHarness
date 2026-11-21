from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class CallSiteRisk(Enum):
    safe = "safe"
    monitored = "monitored"
    dangerous = "dangerous"


class PathConfidence(Enum):
    known = "known"
    partial = "partial"
    unknown = "unknown"


@dataclass
class PathInfo:
    value: str
    confidence: PathConfidence = PathConfidence.known
    line_no: int = 0
    expression: str = ""



@dataclass
class CallSite:
    method: str
    line_no: int
    paths: list[PathInfo] = field(default_factory=list)
    risk: CallSiteRisk = CallSiteRisk.monitored
    expression: str = ""



@dataclass
class AuditResult:
    language: str
    safe: bool
    callsites: list[CallSite] = field(default_factory=list)
    forbidden_calls: list[CallSite] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class Auditor(ABC):

    @abstractmethod
    def audit(self, source: str, script_path: str = "") -> AuditResult:
        ...

    @staticmethod
    def for_language(lang: str) -> "Auditor | None":
        lang = lang.lower()
        if lang in ("py", "python", "python3"):
            from .python_auditor import PythonAuditor
            return PythonAuditor()
        if lang in ("sh", "bash", "shell", "zsh"):
            from .shell_auditor import ShellAuditor
            return ShellAuditor()
        if lang in ("js", "javascript", "node", "ts", "typescript"):
            from .javascript_auditor import JavaScriptAuditor
            return JavaScriptAuditor()
        return None
