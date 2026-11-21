from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field

from .base import CallSiteRisk
from .ast import call_name
from .call_policy import BLACKLIST_NAMES, FORBIDDEN_NAMES

logger = logging.getLogger("harness.audit.func")

# 名单与风险等级统一在 audit/call_policy.py（原先是从 python_auditor 抄来的副本）
_BLACKLIST_NAMES = BLACKLIST_NAMES
_FORBIDDEN_NAMES = FORBIDDEN_NAMES


@dataclass
class FuncInfo:
    name: str
    params: list[str] = field(default_factory=list)
    risk: CallSiteRisk = CallSiteRisk.safe
    body_node: ast.AST | None = None
    blacklist_calls: list[str] = field(default_factory=list)
    forbidden_calls: list[str] = field(default_factory=list)
    line_no: int = 0

    @property
    def is_dangerous(self) -> bool:
        return self.risk == CallSiteRisk.dangerous


class FuncAnalyzer:

    def analyze(self, source: str) -> dict[str, FuncInfo]:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return {}

        funcs: dict[str, FuncInfo] = {}

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                info = self._analyze_func(node)
                funcs[node.name] = info

        return funcs

    def _analyze_func(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> FuncInfo:
        info = FuncInfo(
            name=node.name,
            params=[arg.arg for arg in node.args.args],
            body_node=node,
            line_no=node.lineno,
        )

        blacklist: set[str] = set()
        forbidden: set[str] = set()

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                name = self._resolve_call_name(child)
                if name:
                    # 递归调用自身 → 跳过（避免循环判定）
                    if name == node.name or name.endswith(f".{node.name}"):
                        continue
                    # 检查是否禁止操作
                    if name in _FORBIDDEN_NAMES:
                        forbidden.add(name)
                    # 检查是否黑名单
                    elif name in _BLACKLIST_NAMES:
                        blacklist.add(name)

        # 分级
        if forbidden:
            info.risk = CallSiteRisk.dangerous
            info.forbidden_calls = sorted(forbidden)
        elif blacklist:
            info.risk = CallSiteRisk.monitored
            info.blacklist_calls = sorted(blacklist)
        else:
            info.risk = CallSiteRisk.safe

        return info

    def _resolve_call_name(self, node: ast.Call) -> str | None:
        return call_name(node)


    def inline_body(self, func: FuncInfo,
                    args: list[str]) -> str | None:
        if func.is_dangerous:
            return None
        if not func.body_node:
            return None

        # 提取 return 语句
        return_stmt = None
        for child in ast.walk(func.body_node):
            if isinstance(child, ast.Return) and child.value:
                return_stmt = child
                break

        if not return_stmt:
            return None

        # 构建赋值：param = arg
        lines: list[str] = []
        for param, arg in zip(func.params, args):
            lines.append(f"{param} = {repr(arg)}")

        # 添加 return 表达式作为赋值
        try:
            expr = ast.unparse(return_stmt.value)
            lines.append(f"_result = ({expr})")
        except Exception:
            return None

        return "\n".join(lines)
