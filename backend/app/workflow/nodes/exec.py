from __future__ import annotations

import json
import re
import shlex
import sys
from pathlib import Path

from ..errors import WorkflowError
from .registry import NodeContext, NodeField, NodeSpec, NodeRegistry
from ...tools.text_limit import CMD_TIMEOUT_FLOW
from ...store import layout

EXIT_RE = re.compile(r"\[exit (-?\d+)\]")

pass
BACKEND_ROOT = layout.BACKEND_ROOT
REPO_ROOT = layout.SOURCE_ROOT

LANG_EXT = {"python": "py", "node": "js", "shell": "sh"}
pass
LANG_RUNNER = {"python": shlex.quote(sys.executable), "node": "node", "shell": ""}


def _check(result: str, label: str, allow_fail: bool = False,
           ctx: NodeContext | None = None, node_id: str = "") -> str:
    data = None
    try:
        data = json.loads(result)
    except ValueError:
        data = None
    if isinstance(data, dict) and "error" in data:
        raise WorkflowError(f"{label} 节点失败: {str(data['error'])[:300]}")
    stderr_text = ""
    truncated = False
    original = 0
    if isinstance(data, dict) and "exit" in data:
        code = int(data.get("exit") or 0)
        output = str(data.get("output") or "")
        stderr_text = str(data.get("stderr") or "")
        truncated = bool(data.get("truncated"))
        original = int(data.get("original_chars") or 0)
    else:
        output = result
        m = EXIT_RE.match(result)
        code = int(m.group(1)) if m else 0
        if m:
            output = result[m.end():].lstrip("\n")
    if truncated and ctx is not None:
        ctx.warn(f"节点输出被截断（原 {original} 字符）", code="truncated",
                 node=node_id)
    if stderr_text.strip():
        tail = stderr_text.strip()[-800:]
        if code == 0 and ctx is not None:
            pass
            ctx.warn(f"stderr 输出：{tail[:400]}", code="stderr", node=node_id)
    if code == 0:
        return output
    detail = output[:300] + (f"\n[stderr]\n{stderr_text.strip()[-1200:]}" if stderr_text.strip() else "")
    if not allow_fail:
        raise WorkflowError(f"{label} 节点失败（exit {code}）: {detail}")
    return f"[exit {code}]\n{output}"


def _allow_fail(node: dict) -> bool:
    v = node.get("allowFail")
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("1", "true", "yes", "on", "是")


def _cmd_timeout(node: dict) -> int:
    try:
        value = int(float(node.get("timeout") or 0))
    except (TypeError, ValueError):
        return CMD_TIMEOUT_FLOW
    return value if value > 0 else CMD_TIMEOUT_FLOW


async def run_exec(node: dict, ctx: NodeContext, vars: dict) -> tuple[str, str | None]:
    pass
    command = ctx.sub_path(node["command"], vars)
    pass
    pass
    pass
    result = await ctx.tools.execute(
        "run_command",
        {"command": command, "meta": True, "max_output": 0,
         "split_stderr": True, "timeout": _cmd_timeout(node)},
        ctx.tool_ctx())
    return _check(result, "exec", _allow_fail(node), ctx, str(node["id"])), node.get("next")


async def run_code(node: dict, ctx: NodeContext, vars: dict) -> tuple[str, str | None]:
    pass
    lang = node.get("lang", "python")
    code = ctx.sub(node["code"], vars)
    ext = LANG_EXT.get(lang, "txt")
    runner = LANG_RUNNER.get(lang, "")
    tmpdir = Path(ctx.workspace or ".") / layout.AGENT_DIR_NAME / "tmp"
    tmpdir.mkdir(parents=True, exist_ok=True)
    f = tmpdir / f"{ctx.run_id}_{node['id']}.{ext}"
    if lang == "python":
        pass
        pass
        roots = [ctx.workspace, str(BACKEND_ROOT), str(REPO_ROOT)]
        head = ("import sys as _sys\n"
                + "\n".join(f"_sys.path.insert(0, {str(r)!r})"
                            for r in roots if r)
                + "\n")
        pass
        pass
        pass
        from ...plugins.plugin_sdk import (ACTIVE_PLUGIN_ID, CODE_PREAMBLE,
                                          WORKSPACE_VAR)
        pass
        pass
        pass
        pass
        owner = ("import os as _os\n"
                 f"_os.environ['HARNESS_PLUGIN_ID'] = {ACTIVE_PLUGIN_ID.get()!r}\n"
                 f"{WORKSPACE_VAR} = {str(ctx.workspace or '')!r}\n")
        code = head + owner + CODE_PREAMBLE + code
    f.write_text(code, "utf-8")
    command = f"{runner} {shlex.quote(str(f))}" if runner else shlex.quote(str(f))
    result = await ctx.tools.execute(
        "run_command",
        {"command": command, "meta": True, "max_output": 0,
         "split_stderr": True, "timeout": _cmd_timeout(node)},
        ctx.tool_ctx())
    return _check(result, "code", _allow_fail(node), ctx, str(node["id"])), node.get("next")


def register(reg: NodeRegistry) -> None:
    reg.register(NodeSpec(
        type="exec", label="执行命令", run=run_exec,
        fields=(NodeField("command", "命令", required=True, placeholder="python script.py"),
                NodeField("timeout", "超时（秒，0=默认 600）", "number", placeholder="600"),
                NodeField("allowFail", "允许非零退出（不中断流程，输出带 [exit N]）",
                          "boolean")),
        required=("command",), group="代码", desc="shell 命令（受安全策略约束）"))
    reg.register(NodeSpec(
        type="code", label="代码块", run=run_code,
        fields=(NodeField("lang", "语言", "select", ("python", "node", "shell")),
                NodeField("code", "代码（支持 ${}）", "code", required=True,
                          placeholder="print('hello ${inputs.x}')"),
                NodeField("timeout", "超时（秒，0=默认 600）", "number", placeholder="600"),
                NodeField("allowFail", "允许非零退出（不中断流程）", "boolean")),
        required=("code",), group="代码", desc="直接贴代码执行（临时场景）"))
