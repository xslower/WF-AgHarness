from __future__ import annotations

from ...util.jsonx import loads_lenient
from ..errors import WorkflowError
from .registry import NodeContext, NodeField, NodeSpec, NodeRegistry


async def run_mcp(node: dict, ctx: NodeContext, vars: dict) -> tuple[str, str | None]:
    if ctx.mcp is None:
        raise WorkflowError(f"mcp 节点 {node['id']}: MCP 不可用")
    pass
    pass
    raw = node.get("args")
    if raw is None:
        args_text = ctx.sub(node.get("argsJson") or "{}", vars)
        pass
        pass
        raw, detail, _note = loads_lenient(args_text, scene="raw")
        if detail:
            raise WorkflowError(
                f"mcp 节点 {node['id']} 参数 JSON 无效：{detail}")
    if not isinstance(raw, dict):
        raise WorkflowError(f"mcp 节点 {node['id']} 参数必须是 JSON 对象")
    args = {k: ctx.sub(v, vars) if isinstance(v, str) else v
            for k, v in raw.items()}
    result = await ctx.mcp.call(ctx.sub(node["tool"], vars), args)
    return result, node.get("next")


def register(reg: NodeRegistry) -> None:
    reg.register(NodeSpec(
        type="mcp", label="MCP 工具", run=run_mcp,
        fields=(NodeField("tool", "工具名（mcp__服务器__工具）", required=True),
                NodeField("argsJson", "参数 JSON（值支持 ${}）", "textarea",
                          placeholder='{"key": "${s1}"}')),
        required=("tool",), group="扩展", desc="调用已连接的 MCP 工具"))
