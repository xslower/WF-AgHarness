from __future__ import annotations

import json
import logging

from ...provider.gateway import ToolCallAcc
from ..errors import WorkflowError
from ...util.llm_out import fence_prompt, retry_hint
from .registry import (NodeContext, NodeField, NodeSpec, NodeRegistry,
                       node_model, wf_model_field)
from ...util.jsonx import err, parse_tool_args_report, scene_for_tool
from .llm_parse import finalize_list, parse_output
from .llm_prompt import REF_MARK, build_prompt

logger = logging.getLogger("harness.nodes.llm")

MAX_JSON_RETRY = 3
MAX_TOOL_ROUNDS = 50
"""工具调用轮数的**默认值**。节点可用 `maxToolRounds` 覆盖。

为什么从 12 提到 50（2026-11-04 用户要求）：12 轮只够「读一个文件就回答」，
真实的调研/重构节点是「扫目录 → 读十几个文件 → grep → 跑命令 → 改」，
几轮就撞线、节点直接失败，整张图白跑。用户原话：「我就从来没见过几次
调研就能搞定问题的」。50 只是**起步值**，重活节点自己配更大。
"""
pass
pass
MAX_TOOL_ROUNDS_CAP = 800

pass
pass
pass
ROUND_EXTEND_FACTOR = 2


def _tool_rounds(node: dict) -> int:
    raw = node.get("maxToolRounds")
    if raw is None or raw == "":
        return MAX_TOOL_ROUNDS
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return MAX_TOOL_ROUNDS
    return max(1, min(n, MAX_TOOL_ROUNDS_CAP))


async def _chat(ctx: NodeContext, messages: list[dict], node: dict) -> str:
    spec = node_model(node)
    text = ""
    async for chunk in ctx.gateway.chat_stream(
            messages,
            spec=spec, session_id=f"wf:{ctx.run_id}"):
        if chunk.type == "text":
            text += chunk.text
    return text

def _persist(ctx: NodeContext, node: dict, messages: list[dict]) -> None:
    lsess = (ctx.extras or {}).get("llm_session")
    if lsess is None:
        return
    try:
        lsess.save(str(node.get("id") or ""), messages)
    except Exception:
        logger.debug("保存 LLM 节点会话失败: %s", node.get("id"), exc_info=True)


async def _chat_with_tools(ctx: NodeContext, messages: list[dict], node: dict) -> str:
    spec = node_model(node)
    cfg = str(node.get("tools", "auto") or "auto").strip()
    if cfg in ("", "off", "none"):
        return await _chat(ctx, messages, node)
    if ctx.tools is None:
        raise WorkflowError(f"llm 节点 {node['id']}: 工具注册表不可用，无法启用 tools")
    pass
    pass
    pass
    allowed: set[str] | None = None
    if cfg == "auto":
        pass
        schemas = list(ctx.tools.schemas)
        if not schemas:
            return await _chat(ctx, messages, node)
    else:
        allowed = {t.strip() for t in cfg.split(",") if t.strip()}
        schemas = [s for s in ctx.tools.schemas if s["function"]["name"] in allowed]
        if not schemas:
            raise WorkflowError(f"llm 节点 {node['id']}: 指定的工具均不可用: {cfg}")
    tctx = ctx.tool_ctx()
    pass
    pass
    pass
    rounds = _tool_rounds(node)
    used = 0
    while used < rounds:
        used += 1
        text = ""
        acc = ToolCallAcc()
        async for chunk in ctx.gateway.chat_stream(
                messages, tools=schemas, spec=spec,
                session_id=f"wf:{ctx.run_id}"):
            if acc.feed(chunk):
                continue
            if chunk.type == "text":
                text += chunk.text
        tool_calls = acc.calls()
        if not tool_calls:
            return text
        messages.append({"role": "assistant", "content": text or None,
                         "tool_calls": tool_calls})
        for tc in tool_calls:
            name = tc["function"]["name"]
            pass
            pass
            if allowed is not None and name not in allowed:
                messages.append({"role": "tool", "tool_call_id": tc["id"],
                                "content": err(
                                    f"工具 {name} 不在本节点白名单内"
                                    f"（允许: {', '.join(sorted(allowed))}），已拒绝执行")})
                continue
            pass
            pass
            args, arg_err, fix_note = parse_tool_args_report(
                tc["function"].get("arguments") or "",
                scene=scene_for_tool(name))
            result = (err("工具参数 JSON 解析失败", reason=arg_err)
                      if arg_err else
                      await ctx.tools.execute(name, args, tctx))
            if fix_note and not arg_err:
                result = f"[参数 JSON 已自动修复：{fix_note}]\n{result}"
            messages.append({"role": "tool", "tool_call_id": tc["id"],
                            "content": result})
        _persist(ctx, node, messages)
        if used >= rounds and rounds < MAX_TOOL_ROUNDS_CAP:
            nxt = min(MAX_TOOL_ROUNDS_CAP, rounds * ROUND_EXTEND_FACTOR)
            ctx.warn(f"工具轮数用尽（{rounds}），已自动续到 {nxt} 轮继续执行",
                     code="tool-rounds-extended", node=str(node["id"]))
            rounds = nxt
    raise WorkflowError(
        f"llm 节点 {node['id']}: 工具调用超过最大轮数 {rounds}"
        f"（已到硬上限 {MAX_TOOL_ROUNDS_CAP}；可在节点字段 maxToolRounds 里调，但不会超过它）")

async def run_llm(node: dict, ctx: NodeContext, vars: dict) -> tuple[str, str | None]:
    fmt = node.get("format", "text")
    prompt, ref_warning = build_prompt(node, ctx, vars, fence_prompt=fence_prompt)

    lsess = (ctx.extras or {}).get("llm_session")
    history = []
    if lsess is not None:
        try:
            history = lsess.history(str(node.get("id") or ""))
        except Exception:
            history = []

    messages = _base_messages(node, ctx, vars, prompt, history=history)
    retries = 0
    text = ""
    try:
        for attempt in range(MAX_JSON_RETRY + 1):
            text = await _chat_with_tools(ctx, messages, node)
            if not text.strip():
                raise WorkflowError(f"llm 节点 {node['id']} 空回复")
            if fmt not in ("json", "yaml"):
                break
            pass
            pass
            def _repair_log(note: str, _attempt: int = attempt) -> None:
                _log_parse_failure(ctx, node, _attempt, note, text, False)

            raw, err, used_fallback = parse_output(
                text, fmt, allow_fallback=attempt >= 1, log_repair=_repair_log)
            if not err:
                text = raw
                break
            retries += 1
            _log_parse_failure(ctx, node, attempt, err, text, used_fallback)
            if attempt == MAX_JSON_RETRY:
                label = "JSON" if fmt == "json" else "YAML"
                raise WorkflowError(
                    f"llm 节点 {node['id']} {label} 格式错误（已重写 {retries - 1} 次）: {err}")
            pass
            messages.append({"role": "assistant", "content": text})
            messages.append({"role": "user", "content": retry_hint(fmt, err)})


    finally:
        if lsess is not None:
            pass
            pass
            pass
            _persist(ctx, node, messages + [{"role": "assistant", "content": text}])


    pass
    pass
    pass
    return ref_warning + finalize_list(text, retries, fmt), node.get("next")


def _base_messages(node: dict, ctx: NodeContext, vars: dict,
                   prompt: str, history: list[dict] | None = None) -> list[dict]:
    system = ctx.sub(node.get("system", "") or "", vars).strip()
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    for m in history or []:
        if isinstance(m, dict) and m.get("role") != "system":
            messages.append(m)
    messages.append({"role": "user", "content": prompt})
    return messages



def _log_parse_failure(ctx, node: dict, attempt: int, err: str, text: str,
                       used_fallback: bool) -> None:
    if not ctx.log_json_error:
        return
    ctx.log_json_error(ctx.wf_name, node["id"], attempt + 1, err, text,
                       no_fence="没有代码块" in err,
                       used_fallback=used_fallback)
async def run_ocr(node: dict, ctx: NodeContext, vars: dict) -> tuple[str, str | None]:
    pass
    path = ctx.sub_path(node["path"], vars)
    prompt = ctx.sub(node.get("prompt", "识别图片中的所有文字"), vars)
    r = await ctx.gateway.ocr_image(path, prompt=prompt,
                                    spec=node.get("model") or "")
    if not r.get("ok"):
        raise WorkflowError(f"ocr 节点 {node['id']}: {r.get('error')}")
    return r.get("text", ""), node.get("next")

async def run_image(node: dict, ctx: NodeContext, vars: dict) -> tuple[str, str | None]:
    pass
    prompt = ctx.sub(node.get("prompt", ""), vars)
    r = await ctx.gateway.generate_image(
        prompt, spec=node.get("model") or "",
        size=node.get("size", "1024x1024"), n=int(node.get("n", 1)))
    if not r.get("ok"):
        raise WorkflowError(f"image 节点 {node['id']}: {r.get('error')}")
    return json.dumps(r, ensure_ascii=False), node.get("next")

async def run_asr(node: dict, ctx: NodeContext, vars: dict) -> tuple[str, str | None]:
    pass
    path = ctx.sub_path(node["path"], vars)
    r = await ctx.gateway.transcribe_audio(path, spec=node.get("model") or "")
    if not r.get("ok"):
        raise WorkflowError(f"asr 节点 {node['id']}: {r.get('error')}")
    return r.get("text", ""), node.get("next")

LLM_FIELDS = (
    NodeField("role", "角色名称（仅展示，不进模型 prompt）", placeholder="产品经理"),
    NodeField("system", "系统提示词（角色设定/硬约束；与任务 prompt 分开）", "textarea",
              placeholder="你是资深分镜师。只输出 JSON，不要解释。"),
    NodeField("prompt", "提示词（任务本身，${inputs.x} / ${节点id}）", "textarea", required=True,
              placeholder="翻译成英文：${inputs.input}"),
    NodeField("docs", "加载文档（每行一个：路径 / 目录 / glob，如 prompts/*.md）",
              "textarea",
              placeholder="prompts/*.md\n/path/to/doc.txt"),

    NodeField("format", "输出格式（弱模型建议 list）", "select",
              ("text", "json", "yaml", "list")),
    NodeField("jsonFields", "JSON/YAML 字段（逗号分隔）", placeholder="title, summary"),
    wf_model_field("模型（与会话同一套选择；默认总结队列）"),
    NodeField("tools", "工具（auto=全部工具，逗号分隔白名单，off 关闭）",
              placeholder="auto / f_read,f_write / off"),
    NodeField("maxToolRounds", "工具最多几轮（默认 50，上限 800；重活节点调大）",
              "number", placeholder="50"),
)

def register(reg: NodeRegistry) -> None:
    reg.register(NodeSpec(
        type="llm", label="LLM 对话", run=run_llm, fields=LLM_FIELDS,
        required=("prompt",), group="LLM",
        desc="模型选择与会话同款，默认总结队列（可指定），支持 ${变量}"))
    reg.register(NodeSpec(
        type="ocr", label="OCR 识别", run=run_ocr,
        fields=(NodeField("path", "图片路径（${}）", required=True, placeholder="${inputs.img}"),
                NodeField("prompt", "识别提示词", placeholder="识别图片中的所有文字"),
                NodeField("model", "模型 spec（可选）", "model", placeholder="providerId/modelId")),
        required=("path",), group="扩展", desc="图片 → 文本（kind=ocr 模型）"))
    reg.register(NodeSpec(
        type="image", label="生图", run=run_image,
        fields=(NodeField("prompt", "画面描述（${}）", "textarea", required=True),
                NodeField("size", "尺寸", placeholder="1024x1024"),
                NodeField("model", "模型 spec（可选）", "model", placeholder="providerId/modelId")),
        required=("prompt",), group="扩展", desc="文本 → 图片（kind=image 模型）"))
    reg.register(NodeSpec(
        type="asr", label="语音识别", run=run_asr,
        fields=(NodeField("path", "音频路径（${}）", required=True, placeholder="${inputs.audio}"),
                NodeField("model", "模型 spec（可选）", "model", placeholder="providerId/modelId")),
        required=("path",), group="扩展", desc="音频 → 文本（kind=asr 模型）"))
