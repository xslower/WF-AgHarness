from __future__ import annotations

from pathlib import Path
from typing import Any

from ..util.fsx import write_text
from ..util.jsonx import dumps
from .config import RegressionConfig
from .dsl import all_scenarios, matrix
from .model import RegressionResult, plain
from .verdict import evidence_link

FILE_NAMES = {
    "plan": "01_回归测试计划.md",
    "cases": "02_测试用例清单.md",
    "records": "03_测试执行记录.md",
    "compare": "04_基线对比报告.md",
    "defects": "05_缺陷清单.md",
    "verdict": "06_回归结论报告.md",
}


def _md_table(headers: tuple[str, ...], rows: list[tuple[Any, ...]]) -> str:
    head = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(str(x).replace("|", "\\|") for x in row) + " |"
            for row in rows]
    return "\n".join([head, sep, *body]) if body else head + "\n" + sep


def _plan(config: RegressionConfig, env_id: str) -> str:
    gate = config.validate()
    scenarios = all_scenarios()
    specs = matrix(scenarios, config.platform or "未确认", config.repeats, env_id, "R")
    lines = [
        "# 回归测试计划（自动生成）", "",
        "## 范围", f"- 系统/模块：{config.system}.{config.module}（需要 G0 确认）",
        f"- 平台：{config.platform or '未确认'}",
        f"- G0 门禁：{'通过' if gate.passed else '未通过'}", "",
        "## 版本", f"- 基线：{config.baseline_version} ({config.baseline_commit or 'commit 未确认'})",
        f"- 候选：{config.candidate_version} ({config.candidate_commit or 'commit 未确认'})",
        f"- 近期变更：{', '.join(config.change_list) or '未知变更'}", "",
        "## 环境与时间窗", f"- 环境：{config.env_target} / 镜像 {config.env_image or '待确认'}",
        f"- 数据快照：{config.data_snapshot}，随机种子前缀 R",
        f"- 重复轮次 R：{config.repeats}（功能≥1，性能/长稳建议≥3）", "",
        "## 执行矩阵", f"规模 = 2 版本 × {len(scenarios)} 场景 × 1 平台 × {config.repeats} 轮 = {len(specs)} 轮次",
        "- ABAB 交替执行：每个场景内 baseline/candidate 交替，抵消环境漂移", "",
        "## 门禁", "G0 配置 → G1 环境 → G2 用例 → G3 基线 → G4 候选 → G5 判定出报告",
    ]
    if gate.blockers:
        lines.extend(["", "## 待澄清项（阻断执行）",
                      _md_table(("阻断项",), [(b,) for b in gate.blockers])])
    return "\n".join(lines) + "\n"


def _cases(config: RegressionConfig) -> str:
    rows = [(s.id, s.title, s.priority, s.kind, "是" if s.core else "否",
             ",".join(s.fr), ",".join(s.required_phases))
            for s in all_scenarios()]
    return "\n".join([
        "# 测试用例清单", "",
        _md_table(("用例", "标题", "优先级", "类别", "核心", "FR 映射", "关键 phase"), rows),
        "", "步骤类型：setup / trigger / background / wait / fault / restore / assert / teardown",
        "", "DSL 详情见 `backend/app/regression/dsl.py`；配置化占位 ${cfg.*} 由实例化时替换。",
    ]) + "\n"


def _records(result: RegressionResult) -> str:
    rows = [(o.run_id, o.scenario_id, o.version_role, o.round, o.status,
             "是" if o.passed else "否",
             "是" if o.evidence_sufficient else "否",
             ",".join(c.name for c in o.checks if not c.ok) or "-")
            for o in result.outcomes]
    lines = ["# 测试执行记录", "",
             _md_table(("run_id", "用例", "角色", "轮次", "状态", "通过", "证据完备", "失败断言"), rows)]
    for o in result.outcomes:
        lines.extend(["", f"## {o.run_id}", evidence_link(o),
                      f"- 环境/版本指纹：{o.platform} / {o.version_role}",
                      f"- 事件数：{len(o.events)}，快照数：{len(o.snapshots)}"])
        if o.error:
            lines.append(f"- 错误：{o.error}")
    return "\n".join(lines) + "\n"


def _compare(result: RegressionResult) -> str:
    deltas = [(d.metric, f"{d.baseline:.4g}", f"{d.candidate:.4g}",
               f"{d.delta:+.2%}" if d.relative else f"{d.delta:+.4g}",
               f"±{d.threshold:.0%}" if d.relative else f"{d.threshold:.4g}",
               "临时" if d.temporary else "正式",
               "通过" if d.passed else "超阈")
              for d in result.deltas]
    diffs = [(d.kind, d.scenario_id, d.field, str(d.baseline), str(d.candidate), d.reason)
             for d in result.differences]
    return "\n".join([
        "# 基线对比报告", "", "## 行为差异表",
        _md_table(("类别", "用例", "字段", "基线", "候选", "说明"), diffs), "",
        "## 指标偏差表",
        _md_table(("指标", "基线", "候选", "偏差 δ", "阈值 θ", "阈值来源", "判定"), deltas),
        "", "δ = (candidate − baseline) / baseline；基线≈0 时改用绝对阈值。",
        "", "## 证据链接",
        *[evidence_link(o) for o in result.outcomes],
    ]) + "\n"


def _defects(result: RegressionResult) -> str:
    rows = [(d.id, d.severity, d.title, "新增" if d.is_new else "历史",
             d.known_defect_ref or "-", d.run_id, d.repro_steps)
            for d in result.defects]
    return "\n".join([
        "# 缺陷清单", "",
        _md_table(("ID", "严重度", "标题", "来源", "历史缺陷引用", "run_id", "复现步骤"), rows),
        "", "仅**新增 P0/P1** 触发严重回归；历史已知缺陷单列不触发。",
    ]) + "\n"


def _verdict(result: RegressionResult, config: RegressionConfig) -> str:
    rows = [(r.dimension, r.result, r.reason, r.delta, r.threshold)
            for r in result.rows]
    lines = [
        f"# 回归结论报告：{result.verdict}", "",
        f"- 配置：{config.system}.{config.module} / {config.platform}",
        f"- 版本：{config.baseline_version} → {config.candidate_version}",
        f"- 执行记录目录：{result.run_dir or '(内存)'}", "",
        "## 判定维度", _md_table(("维度", "结果", "说明", "偏差", "阈值"), rows),
        "",
    ]
    if result.blockers:
        lines.extend(["## 阻断项", "",
                      _md_table(("阻断原因",), [(b,) for b in result.blockers])])
    if result.warnings:
        lines.extend(["", "## 说明与临时值", "",
                      _md_table(("提示",), [(w,) for w in result.warnings])])
    lines.extend(["", "## 证据链", ""])
    lines.extend(evidence_link(o) for o in result.outcomes)
    lines.extend(["", "## 发布建议", _release_advice(result.verdict)])
    return "\n".join(lines) + "\n"


def _release_advice(verdict: str) -> str:
    if verdict == "未回归":
        return "建议按既定流程发布；保留本次 run_id 与证据供审计。"
    if verdict == "存在轻微回归":
        return "建议带风险说明发布，非核心失败项列出跟进负责人与复现步骤。"
    if verdict == "存在严重回归":
        return "建议阻断发布，定位核心用例失败/数据异常/崩溃项后重新执行受控对比。"
    return "不得据此给出发布结论：先回填 G0 澄清项或补齐基线/环境/日志证据，重跑验证。"


def render_all(result: RegressionResult, config: RegressionConfig,
               env_id: str = "env_default", out_dir: str | Path | None = None
               ) -> dict[str, str]:
    docs = {
        "plan": _plan(config, env_id),
        "cases": _cases(config),
        "records": _records(result),
        "compare": _compare(result),
        "defects": _defects(result),
        "verdict": _verdict(result, config),
    }
    if out_dir is not None:
        root = Path(out_dir)
        for key, text in docs.items():
            write_text(root / FILE_NAMES[key], text)
    return docs
