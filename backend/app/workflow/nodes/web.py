from __future__ import annotations

from ...util.jsonx import is_err
from ..errors import WorkflowError
from .registry import NodeContext, NodeField, NodeSpec, NodeRegistry


async def _call_web(node: dict, ctx: NodeContext, vars: dict,
                    label: str, **extra) -> tuple[str, str | None]:
    args = {"query": ctx.sub(node["query"], vars), **extra}
    result = await ctx.tools.execute("web", args, ctx.tool_ctx())
    if is_err(result):
        raise WorkflowError(f"{label} 节点失败: {result[:300]}")
    return result, node.get("next")


async def run_web_search(node: dict, ctx: NodeContext, vars: dict) -> tuple[str, str | None]:
    return await _call_web(node, ctx, vars, "web_search",
                           limit=node.get("limit", 5))


async def run_web_fetch(node: dict, ctx: NodeContext, vars: dict) -> tuple[str, str | None]:
    return await _call_web(node, ctx, vars, "web_fetch")


def register(reg: NodeRegistry) -> None:
    reg.register(NodeSpec(
        type="web_search", label="网络搜索", run=run_web_search,
        fields=(NodeField("query", "搜索词（支持 ${}）", required=True),
                NodeField("limit", "结果数", "number", placeholder="5")),
        required=("query",), group="网络", desc="搜索引擎查询"))
    reg.register(NodeSpec(
        type="web_fetch", label="抓取网页", run=run_web_fetch,
        fields=(NodeField("query", "URL 或搜索词（支持 ${}）", required=True,
                          placeholder="https://..."),),
        required=("query",), group="网络", desc="URL 转文本"))
