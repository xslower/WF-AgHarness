from __future__ import annotations

from ...util.jsonx import is_err
from ..errors import WorkflowError
from .jsonargs import load_args
from .registry import NodeContext, NodeField, NodeRegistry, NodeSpec


async def run_tool(node: dict, ctx: NodeContext, vars: dict) -> tuple[str, str | None]:
    pass
    pass
    pass
    pass
    args = load_args(f"tool 节点 {node['id']}", node, ctx, vars)
    result = await ctx.tools.execute(ctx.sub(node["tool"], vars), args, ctx.tool_ctx())
    if is_err(result):
        raise WorkflowError(f"tool 节点失败: {result[:300]}")
    return result, node.get("next")


def register(reg: NodeRegistry) -> None:
    reg.register(NodeSpec(
        type="tool", label="内置函数", run=run_tool,
        fields=(NodeField("tool", "工具名", required=True,
                          placeholder="f_read / grep / skill / ..."),
                NodeField("argsJson", "参数 JSON（值支持 ${}）", "textarea",
                          placeholder='{"path": "${s1}"}')),
        required=("tool",), group="扩展",
        desc="任意内置工具：文件/搜索/命令/skill 全部可用"))
