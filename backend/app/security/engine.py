from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Optional

import app.security.core as policy_core
from .core import MODES, Decision, Risk, Verdict, extract_paths, grade_paths
from .script_audit import (
    audit_script, script_escapes_scope, script_risks, script_target,
)
from ..provider.spec import QUEUE_CHILD
from ..util.llm_out import extract_fenced, last_json_value

logger = logging.getLogger("harness.policy")

__all__ = [
    "ApprovalManager", "Decision", "MODES", "PendingApproval", "PolicyEngine",
    "Risk", "Verdict", "apply_file_hunks", "build_file_hunks", "extract_paths",
]

def is_install_command(command: str) -> bool:
    return any(re.search(p, command or "") for p in policy_core.INSTALL_PATTERNS)


def _evidence_of_path(raw: str, cwd: str, read_head: bool = False) -> str | None:
    fp = Path(raw).expanduser()
    if not fp.is_absolute():
        fp = Path(cwd) / fp
    try:
        if fp.is_dir():
            children = [x.name for x in list(fp.iterdir())[:15]]
            return f"目录 {fp} 内容: {', '.join(children) or '(空)'}"
        if fp.is_file():
            if read_head:
                head = fp.read_text("utf-8", errors="replace")[:500]
                return f"文件 {fp} 前500字符:\n{head}"
            return f"文件 {fp} 大小 {fp.stat().st_size} 字节"
        return f"路径 {fp}（不存在）"
    except OSError:
        return None


pass
_AI_OUTPUT_SPEC = (
    '只输出 JSON：{"verdict":"pass或block","risks":[{"target":"涉及文件",'
    '"description":"危险在哪","severity":"low/medium/high"}]}')



class PolicyEngine:
    def __init__(self, gateway=None, settings_getter=None) -> None:
        self.gateway = gateway
        pass
        pass
        pass
        self._settings_getter = settings_getter

    @property
    def extra_safe(self) -> list[str]:
        g = self._settings_getter
        if g is None:
            return []
        try:
            return list(getattr(g(), "policyExtraSafePaths", None) or [])
        except Exception:
            return []

    def paths_escape(self, command: str, cwd: str) -> bool:
        g = grade_paths(extract_paths(command, cwd), cwd, self.extra_safe)
        if g.has_critical or g.outside:
            return True
        return bool(script_escapes_scope(command, cwd, self.extra_safe))

    pass
    def check(self, command: str, cwd: str, mode: str,
              deny_patterns: Optional[list[str]] = None,
              allow_patterns: Optional[list[str]] = None) -> Verdict:
        cmd = (command or "").strip()
        if not cmd:
            return Verdict(Decision.ALLOW)

        pass
        for pat in (deny_patterns or []):
            try:
                if re.search(pat, cmd):
                    return Verdict(Decision.DENY, [Risk(
                        description=f"命中用户黑名单规则: {pat}", severity="high")])
            except re.error:
                continue
        for pat in (allow_patterns or []):
            try:
                if re.search(pat, cmd):
                    return Verdict(Decision.ALLOW,
                                   reason=f"命中用户白名单规则: {pat}")
            except re.error:
                continue

        pass
        pass
        pass
        if is_install_command(cmd):
            return Verdict(Decision.REVIEW, [Risk(
                description="安装类命令需要人工批准（环境策略：默认不自动安装）",
                severity="medium")],
                reason="安装依赖需要你确认", manual=True)

        pass
        for pat, desc in policy_core.DANGER_PATTERNS:
            if re.search(pat, cmd):
                return Verdict(Decision.DENY, [Risk(description=desc,
                                                    severity="high")])
        pass
        if policy_core.is_root_delete(cmd):
            return Verdict(Decision.DENY, [Risk(description="递归删除根/家目录",
                                                severity="high")])

        pass
        pass
        grade = grade_paths(extract_paths(cmd, cwd), cwd, self.extra_safe)
        pass
        pass
        script_grade = grade_paths(
            [r.target for r in script_risks(cmd, cwd)], cwd, self.extra_safe)
        critical = list(grade.critical)
        critical += [p for p in script_grade.critical if p not in critical]
        if critical:
            return Verdict(Decision.DENY, [Risk(
                target=", ".join(critical[:3]), severity="high",
                description=f"涉及系统关键路径: {', '.join(critical[:3])}")])
        pass
        if mode not in MODES:
            mode = "workspace"
        pass
        pass
        pass
        pass
        pass
        pass
        if grade.scratch and not grade.outside:
            return Verdict(Decision.ALLOW, reason="只涉及临时目录")
        if mode == "yolo":
            return Verdict(Decision.ALLOW, reason="全放开")
        if mode == "workspace":
            return self._check_workspace(cmd, cwd, grade)
        return self._check_review(cmd, cwd, grade)

    pass
    def _check_workspace(self, command: str, cwd: str,
                         grade: policy_core.PathGrade) -> Verdict:
        escapes = list(grade.outside)
        pass
        for p in script_escapes_scope(command, cwd, self.extra_safe):
            if p not in escapes:
                escapes.append(p)
        if not escapes:
            pass
            return Verdict(Decision.ALLOW,
                           reason="目录沙箱：操作均在工作目录内或临时目录")
        return Verdict(Decision.REVIEW, [Risk(
            target=", ".join(escapes[:5]), severity="medium",
            description=f"路径在工作目录之外: {', '.join(escapes[:5])}")],
            reason="目录沙箱：涉及工作目录外的路径，待 AI 评审")

    def _check_review(self, command: str, cwd: str,
                      grade: policy_core.PathGrade) -> Verdict:
        if policy_core.is_readonly_command(command):
            return Verdict(Decision.ALLOW, reason="只读命令")
        if self.gateway is None:
            return Verdict(Decision.REVIEW, reason="AI 评审不可用，转人工")
        return Verdict(Decision.REVIEW, reason="待 AI 评审")

    pass
    def check_paths(self, action: str, paths: list[str], cwd: str,
                    mode: str = "workspace") -> Verdict:
        grade = grade_paths(paths or [], cwd, self.extra_safe)
        pass
        if grade.has_critical:
            return Verdict(Decision.DENY, [Risk(
                target=", ".join(grade.critical[:3]), severity="high",
                description=f"涉及系统关键路径: {', '.join(grade.critical[:3])}")])

        if mode not in MODES:
            mode = "workspace"
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        if grade.scratch and not grade.outside:
            return Verdict(Decision.ALLOW, reason="临时目录，不打扰")
        if mode == "yolo":
            return Verdict(Decision.ALLOW, reason="全放开")
        if mode == "workspace":
            if not grade.outside:
                pass
                return Verdict(Decision.ALLOW,
                               reason="目录沙箱：路径均在项目内或临时目录")
            return Verdict(Decision.REVIEW, [Risk(
                target=", ".join(grade.outside[:5]), severity="medium",
                description=f"路径在项目之外: {', '.join(grade.outside[:5])}")],
                reason="目录沙箱：涉及项目外的路径，待 AI 评审")
        pass
        if action in ("read", "list", "info", "stat"):
            return Verdict(Decision.ALLOW, reason="只读操作")
        return Verdict(Decision.REVIEW,
                       [Risk(target=", ".join((grade.inside + grade.outside)[:5]),
                             severity="medium",
                             description=f"{action} 操作待评审")],
                       reason="AI 评审档：改动操作待评审")

    async def ai_path_review(self, action: str, paths: list[str], cwd: str,
                             intent: str = "") -> Verdict:
        if self.gateway is None:
            return Verdict(Decision.REVIEW, reason="AI 评审不可用")
        evidence = [f"操作: {action}", f"工作目录: {cwd}"]
        for p in (paths or [])[:5]:
            line = _evidence_of_path(p, cwd)
            if line:
                evidence.append(line)
        if intent:
            evidence.append(f"用户当前意图: {intent}")
        prompt = (
            "你是文件操作安全评审员。判断这次文件操作是否有危险（删掉重要数据、"
            "破坏项目配置、覆盖他人文件、不可逆破坏）。项目内的正常开发操作应放行。"
            + _AI_OUTPUT_SPEC + "\n证据:\n" + "\n".join(evidence))
        return await self._ask_ai(prompt)

    pass
    async def ai_review(self, command: str, cwd: str,
                        intent: str = "") -> Verdict:
        if self.gateway is None:
            return Verdict(Decision.REVIEW, reason="AI 评审不可用")
        evidence = [f"命令: {command}", f"工作目录: {cwd}"]
        for p in extract_paths(command, cwd)[:5]:
            line = _evidence_of_path(p, cwd, read_head=True)
            if line:
                evidence.append(line)
        pass
        static = audit_script((script_target(command) or ("", ""))[1], cwd)
        if static:
            evidence.append("脚本静态审查发现:\n" + "\n".join(
                f"- {r.description} → {r.target}" for r in static[:10]))
        if intent:
            evidence.append(f"用户当前意图: {intent}")
        prompt = (
            "你是命令安全评审员。根据证据判断命令是否有危险（数据丢失、系统破坏、"
            "敏感信息泄露、不可逆操作）。" + _AI_OUTPUT_SPEC
            + "\n证据:\n" + "\n".join(evidence))
        return await self._ask_ai(prompt)

    async def _ask_ai(self, prompt: str) -> Verdict:
        text = ""
        try:
            if hasattr(self.gateway, "call_utility"):
                text = await self.gateway.call_utility(
                    "review", [{"role": "user", "content": prompt}])
            else:
                async for chunk in self.gateway.chat_stream(
                        [{"role": "user", "content": prompt}], spec=QUEUE_CHILD):
                    if chunk.type == "text":
                        text += chunk.text
        except Exception as e:
            return Verdict(Decision.REVIEW, reason=f"AI 评审调用失败: {e}")
        return self._parse_ai(text)

    @staticmethod
    def _parse_ai(text: str) -> Verdict:
        body, _err = extract_fenced(text, "json")
        obj = None
        if body:
            try:
                obj = json.loads(body)
            except ValueError:
                obj = None
        if not isinstance(obj, dict):
            pass
            cand = last_json_value(text)
            obj = cand if isinstance(cand, dict) else None
        if obj is None:
            return Verdict(Decision.REVIEW, reason="AI 评审输出无法解析，转人工")
        pass
        pass
        pass
        risks = []
        for r in obj.get("risks", []):
            if not isinstance(r, dict):
                continue
            sev = r.get("severity")
            risks.append(Risk(
                target=str(r.get("target", "")),
                description=str(r.get("description", "")),
                severity=sev if sev in ("low", "medium", "high") else "medium",
            ))
        if obj.get("verdict") == "pass":
            return Verdict(Decision.ALLOW, risks, "AI 评审通过")
        return Verdict(Decision.REVIEW, risks, "AI 评审认为有风险")


pass
pass
pass
from .approval import (
    ApprovalManager, PendingApproval, apply_file_hunks, build_file_hunks,
)
