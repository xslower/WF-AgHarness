from __future__ import annotations

import json
import time

from ..errors import WorkflowError
from .registry import NodeContext, NodeField, NodeSpec, NodeRegistry

pass
pass
DEFAULT_OPTIONS = ["批准", "驳回"]


def parse_options(raw: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for line in str(raw or "").splitlines():
        text = line.strip()
        if not text:
            continue
        label, _, target = text.partition("=")
        label = label.strip()
        if not label:
            continue
        out.append((label, target.strip()))
    return out or [(x, "") for x in DEFAULT_OPTIONS]


async def run_human(node: dict, ctx: NodeContext, vars: dict) -> tuple[str, str | None]:
    node_id = str(node["id"])
    title = ctx.sub(node.get("title", ""), vars)
    ask = ctx.sub(node.get("ask", ""), vars)
    pass
    pass
    show = ctx.sub(node.get("show", ""), vars, long_ref=True)
    opts = parse_options(node.get("options", ""))
    labels = [label for label, _ in opts]

    mode = str(ctx.extras.get("human_mode", "ask") or "ask")
    pass
    pass
    pass
    if str(node.get("auto") or "").strip().lower() in ("1", "true", "yes"):
        return _auto_decide(node, ctx, vars, opts, labels)
    if mode == "deny":
        pass
        raise WorkflowError(
            f"human 节点 {node_id}: 该工作流含人工闸门「{title}」，当前是无人在场的运行方式"
            "（agent 工具触发 / 定时）。请从画布运行，或在运行参数里传 human=auto-approve"
            "（自动批准）/ human=auto-reject（自动驳回）")
    if mode != "ask":
        pass
        pick = 0 if mode == "auto-approve" else (1 if len(labels) > 1 else 0)
        return _finish(node, opts, pick, "（自动）", "")

    gate_open = ctx.extras.get("human_open")
    if gate_open is None:
        raise WorkflowError(
            f"human 节点 {node_id}: 当前运行不支持人工闸门（缺少闸门通道），"
            "请从画布运行，或给运行参数传 human=auto-approve")

    gate = gate_open(node_id=node_id, title=title, ask=ask, show=show,
                     options=labels)
    try:
        timeout = float(node.get("timeout") or 0)
    except (TypeError, ValueError):
        timeout = 0.0
    if timeout > 0:
        pass
        gate = await ctx.extras["human_wait"](gate, timeout)
    else:
        gate = await ctx.extras["human_wait"](gate, 0)
    ctx.extras["human_close"](node_id)

    if not gate.decided:
        on_timeout = str(node.get("onTimeout", "fail") or "fail")
        if on_timeout == "approve":
            return _finish(node, opts, 0, "（超时自动批准）", "")
        if on_timeout == "reject":
            pick = 1 if len(labels) > 1 else 0
            return _finish(node, opts, pick, "（超时自动驳回）", "")
        raise WorkflowError(
            f"human 节点 {node_id}: 等待人工确认超时（{timeout:.0f} 秒）"
            f"，标题「{title}」。可在节点上设 onTimeout=approve/reject 或调大 timeout")

    choice = gate.choice
    idx = labels.index(choice) if choice in labels else 0
    return _finish(node, opts, idx, gate.comment or "", choice)


def _auto_decide(node: dict, ctx: NodeContext, vars: dict,
                 opts: list[tuple[str, str]], labels: list[str]) -> tuple[str, str | None]:
    node_id = str(node["id"])
    rounds_key = "__gate_rounds__"
    rounds = dict((vars.get("outputs") or {}).get(rounds_key) or {})
    prev = int(rounds.get(node_id, 0))
    rounds[node_id] = prev + 1

    raw = (vars.get("inputs") or {}).get(node_id)
    raw = dict(raw) if isinstance(raw, dict) else {}
    decision = str(raw.get("decision") or "").strip().lower()
    consumed = False
    if prev >= 1 and decision in ("revise", "abort"):
        decision = "approve"
        consumed = True

    pass
    if decision in ("revise", "abort", "reject") and len(labels) > 1:
        pick = 1
    else:
        pick = 0
    payload = json.dumps({"choice": labels[pick], "index": pick,
                          "comment": str(raw.get("note") or ""),
                          "by": "auto", "auto": True,
                          "preset": bool(raw), "preset_consumed": consumed,
                          "round": rounds[node_id]},
                         ensure_ascii=False)
    vars.setdefault("outputs", {})[rounds_key] = rounds
    pass
    ctx.warn(f"auto 闸门 {node_id} 自动放行（第 {rounds[node_id]} 轮，"
             f"decision={label_of(opts, pick)}"
             + ("，已消费预置意见" if consumed else "")
             + ("" if raw else "，无预置意见") + "）",
             code="auto-gate", node=node_id)
    branch = node.get("true") if pick == 0 else node.get("false")
    target = opts[pick][1] if pick < len(opts) else ""
    return payload, (target or branch or node.get("next") or None)


def label_of(opts: list[tuple[str, str]], idx: int) -> str:
    return opts[idx][0] if 0 <= idx < len(opts) else ""


def _finish(node: dict, opts: list[tuple[str, str]], idx: int,
            comment: str, choice: str = "") -> tuple[str, str | None]:
    label, target = opts[idx] if idx < len(opts) else (choice, "")
    out = json.dumps({"choice": label or choice, "index": idx,
                      "comment": comment, "by": "user",
                      "ts": int(time.time())}, ensure_ascii=False)
    branch = node.get("true") if idx == 0 else node.get("false")
    nxt = target or branch or node.get("next")
    return out, (nxt or None)


def register(reg: NodeRegistry) -> None:
    reg.register(NodeSpec(
        type="human", label="人工闸门", run=run_human,
        fields=(NodeField("title", "标题", required=True,
                          placeholder="确认分镜，开始生成 30 张图"),
                NodeField("ask", "说明（支持 ${}）", "textarea",
                          placeholder="下面是要展示的内容说明"),
                NodeField("show", "展示内容（每行一个变量，支持 ${}）", "textarea",
                          placeholder="${s2}\n${s2.scenes}"),
                NodeField("options", "按钮（每行一个；可写 按钮=目标节点id）",
                          "textarea", required=True,
                          placeholder="批准\n驳回\n只重做第3镜=s3b"),
                NodeField("true", "选第1项后去哪（不写则走 next）", "text",
                          placeholder="w8"),
                NodeField("false", "选其它项后去哪（不写则走 next）", "text",
                          placeholder="w2"),
                NodeField("next", "统一出口（true/false 都没写时生效）", "text",
                          placeholder="w8"),
                NodeField("timeout", "等待超时（秒，0=一直等）", "number",
                          placeholder="0"),
                NodeField("onTimeout", "超时处理", "select",
                          ("fail", "approve", "reject")),
                NodeField("auto", "自动闸门（不留人，直接放行）", "boolean",
                          placeholder="置 true 时不停下：留档 + 放行，意见由运行 inputs 预置")),
        required=("title", "options"), group="逻辑",
        branch_keys=("true", "false", "next"),
        desc="流程挂起等人拍板；首项走 true、其余走 false，都没写就走 next。不是 handoff。"
             "auto=true 时不停下（留档 + 直接放行，意见由运行 inputs 预置）"))
