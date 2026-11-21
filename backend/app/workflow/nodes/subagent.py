from __future__ import annotations

from ..errors import WorkflowError
from .registry import (NodeContext, NodeField, NodeSpec, NodeRegistry,
                       node_model, wf_model_field)


async def run_subagent(node: dict, ctx: NodeContext, vars: dict) -> tuple[str, str | None]:
    if ctx.agent_runner is None:
        raise WorkflowError(f"subagent 节点 {node['id']}: 子 Agent 不可用")
    task = ctx.sub(node["task"], vars)

    async def _swallow(ev: dict) -> None:
        return None

    text = ""
    async for msg in ctx.agent_runner.run(
            [{"role": "user", "content": task}],
            ctx.workspace or ".", _swallow,
            spec=node_model(node), session_id=f"wf-sub:{ctx.run_id}"):
        if msg.get("role") == "assistant" and msg.get("content"):
            text = msg["content"]
    return text, node.get("next")


def register(reg: NodeRegistry) -> None:
    reg.register(NodeSpec(
        type="subagent", label="子 Agent", run=run_subagent,
        fields=(NodeField("task", "任务描述", "textarea", required=True),
                wf_model_field("模型（与会话同一套选择；默认总结队列）"),),
        required=("task",), group="LLM",
        desc="独立上下文，默认走总结队列，可指定模型"))
