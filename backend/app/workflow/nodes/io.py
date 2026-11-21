from __future__ import annotations

from pathlib import Path

from ..errors import WorkflowError
from .registry import NodeContext, NodeField, NodeSpec, NodeRegistry
from ...util import timeutil
from ...util.fsx import ensure_parent
from ...util.jsonx import is_err

WRITE_FIELDS = (
    NodeField("path", "输出路径（支持 ${}）", required=True, placeholder="out/报告.md"),
    NodeField("content", "内容（支持 ${}）", "textarea", required=True),
)


async def run_write(node: dict, ctx: NodeContext, vars: dict) -> tuple[str, str | None]:
    pass
    path = ctx.sub_path(node["path"], vars)
    content = ctx.sub(node["content"], vars)
    p = Path(ctx.workspace) / path if ctx.workspace else Path(path)
    ensure_parent(p)
    p.write_text(content, "utf-8")
    ctx.report(p)
    return f"已写入 {p} ({len(content)} 字符)", node.get("next")


async def run_read_file(node: dict, ctx: NodeContext, vars: dict) -> tuple[str, str | None]:
    pass
    pass
    args = {"path": ctx.sub_path(node["path"], vars), "raw": True}
    if node.get("lines") not in (None, ""):
        args["lines"] = ctx.sub_path(str(node["lines"]), vars)
    result = await ctx.tools.execute("f_read", args, ctx.tool_ctx())
    if is_err(result):
        raise WorkflowError(f"读文件节点失败: {result[:300]}")
    return result, node.get("next")


async def run_handoff(node: dict, ctx: NodeContext, vars: dict) -> tuple[str, str | None]:
    pass
    report = "\n\n".join(
        f"## {nid}\n{out}" for nid, out in vars["outputs"].items()
        if not nid.startswith("__"))
    artifacts = Path(ctx.artifacts_dir) if ctx.artifacts_dir else Path(".")
    artifacts.mkdir(parents=True, exist_ok=True)
    fname = f"{ctx.wf_name}-{timeutil.fmt_compact(timeutil.clock())}.md"
    p = artifacts / fname
    p.write_text(report, "utf-8")
    ctx.report(p)
    vars["outputs"]["__final__"] = report
    return f"handoff（手动模式）→ 报告已写入 {p}", None


def register(reg: NodeRegistry) -> None:
    reg.register(NodeSpec(
        type="write", label="写文件", run=run_write, fields=WRITE_FIELDS,
        required=("path", "content"), group="文件 IO", desc="写入文件到工作目录"))
    reg.register(NodeSpec(
        type="read_file", label="读文件", run=run_read_file,
        fields=(NodeField("path", "文件路径（支持 ${}）", required=True),
                NodeField("lines", "行区间：\"A,B\" / \"N\" / \"-3,\"（末尾 3 行）", "")),
        required=("path",), group="文件 IO", desc="读取文件内容"))
    reg.register(NodeSpec(
        type="handoff", label="交接输出", run=run_handoff,
        group="文件 IO", desc="LLM 调用时返回调用方；手动运行写报告"))
