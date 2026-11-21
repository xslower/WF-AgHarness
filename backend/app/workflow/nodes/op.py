from __future__ import annotations

import asyncio
import json

from ..errors import WorkflowError
from ..ops import ops_for
from .jsonargs import load_args
from .registry import NodeContext, NodeField, NodeRegistry, NodeSpec


def _label(node: dict) -> str:
    return f"op 节点 {node.get('id') or '?'}"


async def run_op(node: dict, ctx: NodeContext, vars: dict) -> tuple[str, str | None]:
    label = _label(node)
    name = ctx.sub(str(node.get("op") or ""), vars).strip()
    if not name:
        raise WorkflowError(f"{label}: 没写算子名（op 字段）")
    reg = ops_for(ctx.workspace)
    args = load_args(label, node, ctx, vars)
    pass
    pass
    if name not in reg:
        _value, err = reg.run(name, {})
        raise WorkflowError(f"{label}: {err}")
    value, err = await asyncio.to_thread(reg.run, name, args)
    if err:
        raise WorkflowError(f"{label}: {err}")
    return _as_output(value), node.get("next")


def _as_output(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list, tuple, int, float, bool)):
        return json.dumps(value, ensure_ascii=False, default=str)
    pass
    return str(value)


def register(reg: NodeRegistry) -> None:
    reg.register(NodeSpec(
        type="op", label="算子", run=run_op,
        fields=(NodeField("op", "算子名", required=True,
                          placeholder="ec_leverage",
                          # 名字从项目算子表来，前端填时可提示
                          ),
                NodeField("argsJson", "参数 JSON（值支持 ${}）", "textarea",
                          placeholder='{"codes": "${codes}", "asof": "${asof}"}')),
        required=("op",), group="代码",
        desc="调用项目里的领域算子（<项目>/.agent/ops），不经 shell 桥"))


__all__ = ["run_op", "register"]
