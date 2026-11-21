from __future__ import annotations

import json

from ...util.jsonfix import loads_lenient
from ..errors import WorkflowError
from .registry import NodeContext, NodeField, NodeSpec, NodeRegistry


async def run_workflow(node: dict, ctx: NodeContext, vars: dict) -> tuple[str, str | None]:
    runner = (ctx.extras or {}).get("run_subflow")
    if runner is None:
        raise WorkflowError(f"workflow 节点 {node['id']}: 当前运行不支持子工作流")

    name = ctx.sub(node.get("name", ""), vars).strip()
    if not name:
        raise WorkflowError(f"workflow 节点 {node['id']}: name 为空")

    raw_inputs = node.get("inputsJson") or ""
    if raw_inputs.strip():
        text = ctx.sub(raw_inputs, vars)
        try:
            inputs = json.loads(text)
        except (ValueError, RecursionError):
            pass
            pass
            obj, detail, _note = loads_lenient(text, scene="raw")
            if detail or not isinstance(obj, dict):
                raise WorkflowError(
                    f"workflow 节点 {node['id']}: inputsJson 不是合法 JSON；"
                    "要传文本就用 {\"input\": \"${prev}\"} 这种对象写法")
            inputs = obj
        if not isinstance(inputs, dict):
            raise WorkflowError(
                f"workflow 节点 {node['id']}: inputsJson 必须是对象（键=子工作流的输入名）")
    else:
        pass
        pass
        parent_inputs = dict(vars.get("inputs") or {})
        if parent_inputs:
            inputs = parent_inputs
        else:
            text = ctx.sub(node.get("input", "${prev}") or "${prev}", vars)
            pass
            inputs = {"input": "" if "${" in text else text}

    output = str(node.get("output") or "final")
    try:
        text = await runner(name, inputs, output, str(node["id"]))
    except WorkflowError:
        raise
    except Exception as e:
        raise WorkflowError(
            f"workflow 节点 {node['id']}: 调用「{name}」失败: {type(e).__name__}: {e}")
    if not str(text).strip():
        pass
        text = f"[子工作流 {name} 无输出]"
    return text, node.get("next")


def register(reg: NodeRegistry) -> None:
    reg.register(NodeSpec(
        type="workflow", label="子工作流", run=run_workflow,
        fields=(NodeField("name", "子工作流名称（支持 ${}）", required=True,
                          placeholder="单镜制作"),
                NodeField("inputsJson", "输入（JSON 对象，值支持 ${}；留空则传 input=${prev}）",
                          "textarea",
                          placeholder='{"shot": ${__item__!raw}["shot"], "style": "国风"}'),
                NodeField("input", "留空 inputsJson 时传的内容（默认 ${prev}）",
                          placeholder="${prev}"),
                NodeField("output", "取子工作流的哪段输出（final / node:<节点id>）",
                          placeholder="final")),
        required=("name",), group="逻辑",
        desc="调用另一个工作流并取它的输出；限深 3 层、禁止循环调用"))
