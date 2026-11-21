from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ...util.jsonx import err
from .workflow_help import build_help
from ...workflow.constants import HUMAN_MODES
from ...provider.spec import (SUBAGENT_WAIT_TIMEOUT_SEC,
                              SUBAGENT_WAIT_TIMEOUT_MAX_SEC)

if TYPE_CHECKING:
    from .. import ToolContext, ToolRegistry

WORKFLOW_ACTIONS = ("list", "help", "run", "wait", "get", "list_node", "add_node",
                    "edit_node", "del_node", "save")


def _engine(ctx: "ToolContext"):
    wf_edit = getattr(ctx, "wf_edit", None)
    if wf_edit is None:
        return None
    return wf_edit


pass
pass
pass
pass
pass
pass
pass
_DRAFTS: dict[tuple[int, str], dict] = {}


def _load(eng, name: str) -> dict | None:
    key = (id(eng), name)
    wf = eng.get(name)
    if wf is None:
        _DRAFTS.pop(key, None)
        return None
    draft = _DRAFTS.get(key)
    pass
    pass
    if draft is not None and draft.get("_revision", "") == wf.get("_revision", ""):
        return draft
    _DRAFTS[key] = wf
    return wf


def _drop_draft(eng, *names: str) -> None:
    for n in names:
        if n:
            _DRAFTS.pop((id(eng), n), None)


def _save(eng, wf: dict) -> None:
    eng.save(wf)
    _drop_draft(eng, wf.get("name", ""))


def _nodes_registry(ctx: "ToolContext"):
    eng = _engine(ctx)
    reg = getattr(eng, "nodes", None) if eng is not None else None
    if reg is None:
        try:
            from ...workflow.nodes import build_default_nodes
            reg = build_default_nodes()
        except Exception:
            return None
    return reg


async def help_workflow(ctx: "ToolContext", topic: str = "") -> str:
    reg = _nodes_registry(ctx)
    if reg is None:
        return "工作流功能不可用"
    return build_help(reg, topic)


async def list_workflow(name: str, ctx: "ToolContext") -> str:
    eng = _engine(ctx)
    if eng is None:
        return err("工作流功能不可用")
    return json.dumps(eng.list(), ensure_ascii=False)


async def get_workflow(name: str, ctx: "ToolContext") -> str:
    eng = _engine(ctx)
    if eng is None:
        return err("工作流功能不可用")
    wf = _load(eng, name)
    if not wf:
        return err(f"工作流不存在: {name}")
    return json.dumps(wf, ensure_ascii=False)


async def list_node(name: str, ctx: "ToolContext") -> str:
    eng = _engine(ctx)
    if eng is None:
        return err("工作流功能不可用")
    wf = _load(eng, name)
    if not wf:
        return err(f"工作流不存在: {name}")
    nodes = [{"id": n.get("id"), "type": n.get("type"),
              "next": n.get("next"),
              "fields": {k: v for k, v in n.items()
                         if k not in ("id", "type", "next", "true", "false", "body")}}
             for n in wf.get("nodes", [])]
    return json.dumps(nodes, ensure_ascii=False)


async def add_node(name: str, ctx: "ToolContext", node: dict) -> str:
    eng = _engine(ctx)
    if eng is None:
        return err("工作流功能不可用")
    wf = _load(eng, name)
    if not wf:
        return err(f"工作流不存在: {name}")
    if not isinstance(node, dict) or not node.get("id") or not node.get("type"):
        return err("node 需要 id 和 type")
    nodes = wf.setdefault("nodes", [])
    if any(n.get("id") == node["id"] for n in nodes):
        return err(f"节点 id 已存在: {node['id']}")
    nodes.append(node)
    nxt = node.get("next") or ("（末端）" if len(nodes) > 1 else "（入口，nodes[0]）")
    return json.dumps({"ok": True, "nodes": len(nodes), "id": node["id"], "next": nxt,
                       "note": "已添加（仅内存）。接到流程里：edit_node 把上游 next 指向 "
                               f"{node['id']}；确认后 save 落盘"},
                      ensure_ascii=False)


async def edit_node(name: str, ctx: "ToolContext", node_id: str, fields: dict) -> str:
    eng = _engine(ctx)
    if eng is None:
        return err("工作流功能不可用")
    wf = _load(eng, name)
    if not wf:
        return err(f"工作流不存在: {name}")
    n = next((x for x in wf.get("nodes", []) if x.get("id") == node_id), None)
    if n is None:
        return err(f"节点不存在: {node_id}")
    for k, v in (fields or {}).items():
        if v is None:
            n.pop(k, None)
        else:
            n[k] = v
    return json.dumps({"ok": True, "node": n, "note": "已改（仅内存），save 落盘"},
                      ensure_ascii=False)


async def del_node(name: str, ctx: "ToolContext", node_id: str) -> str:
    eng = _engine(ctx)
    if eng is None:
        return err("工作流功能不可用")
    wf = _load(eng, name)
    if not wf:
        return err(f"工作流不存在: {name}")
    nodes = wf.get("nodes", [])
    before = len(nodes)
    wf["nodes"] = [n for n in nodes if n.get("id") != node_id]
    if len(wf["nodes"]) == before:
        return err(f"节点不存在: {node_id}")
    for n in wf["nodes"]:
        for k in ("next", "true", "false", "body"):
            if n.get(k) == node_id:
                n.pop(k, None)
    return json.dumps({"ok": True, "nodes": len(wf["nodes"])}, ensure_ascii=False)


async def save_workflow(name: str, ctx: "ToolContext", workflow: dict = None) -> str:
    eng = _engine(ctx)
    if eng is None:
        return err("工作流功能不可用")
    try:
        if workflow:
            wf = dict(workflow)
        else:
            wf = _load(eng, name)
            if not wf:
                return err(f"工作流不存在: {name}")
        _save(eng, wf)
        _drop_draft(eng, name)
        return json.dumps({"ok": True, "name": wf.get("name"),
                           "nodes": len(wf.get("nodes", []))}, ensure_ascii=False)
    except Exception as e:
        return err(str(e))


async def _run_action(ctx: "ToolContext", name: str, input: str, human: str,
                      start_node: str, parallel: str) -> str:
    if not name:
        return err("action=run 需要 name")
    fn = getattr(ctx, "workflow_start", None)
    if fn is None:
        return err("工作流执行不可用")
    mode = (human or "deny").strip().lower()
    if mode not in HUMAN_MODES:
        return err(f"human 只能是 {list(HUMAN_MODES)} 之一，收到: {human}")
    par = (parallel or "").strip().lower()
    if par not in ("", "agent", "sequential"):
        return err(f"parallel 只能是 agent / sequential（留空=用工作流设置），收到: {parallel}")
    try:
        return await fn(name, input, mode, start_node, par)
    except Exception as e:
        return err(f"工作流执行失败: {e}")


async def _wait_action(ctx: "ToolContext", run_id: str, timeout: float,
                       detail: bool) -> str:
    if not run_id:
        return err("action=wait 需要 id（run 返回的 run_id）")
    fn = getattr(ctx, "workflow_wait", None)
    if fn is None:
        return err("等待运行不可用：当前上下文没有注入 workflow_wait")
    try:
        t = float(timeout)
    except (TypeError, ValueError):
        t = 0
    t = t if t > 0 else SUBAGENT_WAIT_TIMEOUT_SEC
    t = min(t, SUBAGENT_WAIT_TIMEOUT_MAX_SEC)
    return await fn(run_id, t, detail=bool(detail))


pass
_NEEDS_NODE_ID = {
    "edit_node": "action=edit_node 需要 node_id 与 fields",
    "del_node": "action=del_node 需要 node_id",
}


async def workflow_cmd(ctx: "ToolContext", action: str = "list", name: str = "",
                       node_id: str = "", node: dict = None, fields: dict = None,
                       workflow: dict = None, input: str = "",
                       human: str = "deny", topic: str = "",
                       start_node: str = "", parallel: str = "",
                       detail: bool = False, id: str = "", timeout: float = 0) -> str:
    act = (action or "list").strip().lower()
    if act not in WORKFLOW_ACTIONS:
        return err(f"action 必须是 {list(WORKFLOW_ACTIONS)} 之一，收到: {action}")
    if act == "help":
        pass
        return await help_workflow(ctx, topic or input)
    if act == "run":
        return await _run_action(ctx, name, input, human, start_node, parallel)
    if act == "wait":
        return await _wait_action(ctx, id, timeout, detail)

    pass
    if act != "list" and not name:
        return err(f"action={act} 需要 name")

    if act == "list":
        return await list_workflow("", ctx)
    if act == "get":
        return await get_workflow(name, ctx)
    if act == "list_node":
        return await list_node(name, ctx)
    if act == "save":
        return await save_workflow(name, ctx, workflow)
    if act == "add_node":
        if not node:
            return err("action=add_node 需要 node")
        return await add_node(name, ctx, node)

    pass
    if act in _NEEDS_NODE_ID and (not node_id or (act == "edit_node" and fields is None)):
        return err(_NEEDS_NODE_ID[act])
    if act == "edit_node":
        return await edit_node(name, ctx, node_id, fields)
    if act == "del_node":
        return await del_node(name, ctx, node_id)
    return await list_workflow("", ctx)


def register(reg: "ToolRegistry") -> None:
    reg.register(
        "workflow",
        "工作流（多步骤任务编排）—— 所有操作都由 action 分派，参数含义见各字段说明。"
        "【不确定就先 action=help】它输出：动作签名、每类节点的字段表、6 个可直接照抄的完整案例；"
        "topic 可指定动作名（add_node）、节点类型（llm）或 recipe（全部案例），留空=速查总表。"
        "动作：list=列出工作流；run=运行（后台启动，立即返回 run_id）；wait=等运行结果；"
        "get=读完整定义；"
        "list_node=只列节点摘要（省 token）；add_node=加节点；edit_node=改节点字段；"
        "del_node=删节点并清连线；save=落盘。"
        "【必须记住】add_node/edit_node/del_node 只改内存草稿，不 save 等于没做；"
        "nodes 是有序列表、nodes[0] 就是入口；连线只有 next/true/false/body（值都是节点 id）；"
        "变量写 ${inputs.名} / ${节点id} / ${prev}。"
        "推荐路径：help → list_node 看现状 → 改 → save → run。",
        {"action": {"type": "string", "enum": list(WORKFLOW_ACTIONS),
                    "description": "要做的事。list=列出 / help=看帮助 / run=运行 / wait=等运行结果 / "
                                   "get=完整定义 / "
                                   "list_node=节点摘要 / add_node=加节点 / edit_node=改字段 / "
                                   "del_node=删节点 / save=落盘"},
         "id": {"type": "string",
                "description": "wait 必填：run 返回的 run_id"},
         "timeout": {"type": "number",
                     "description": "wait 可选：最多等多少秒（默认 300，上限 1800）；"
                                    "超时只结束本次等待、不中止运行，返回 timed_out=true，"
                                    "可再 wait"},
         "topic": {"type": "string",
                   "description": "仅 action=help：要看的内容。动作名（run/add_node/save…）、"
                                  "节点类型（llm/write/condition/map…）或 recipe（6 个完整案例）。"
                                  "留空返回速查总表。不确定字段名时用它"},
         "name": {"type": "string",
                  "description": "工作流名，不带路径和 .json 后缀。除 list/help 外都必填"},
         "node": {"type": "object",
                  "description": "add_node 必填：节点对象，至少要有 id 与 type，"
                                 "如 {\"id\":\"w1\",\"type\":\"write\",\"path\":\"out/a.md\","
                                 "\"content\":\"${s1}\"}。其余字段名按节点类型给"
                                 "（先 help topic=<类型> 查字段表），连线加 next/true/false/body"},
         "node_id": {"type": "string",
                     "description": "edit_node / del_node 必填：目标节点 id（不是类型名）"},
         "fields": {"type": "object",
                    "description": "edit_node 必填：{字段名: 新值}，只写要改的键，其余保持原值；"
                                   "值设为 null 表示删除该键。不能改 id"},
         "workflow": {"type": "object",
                      "description": "save 可选：完整定义 {\"name\",\"desc\",\"inputs\":[...],"
                                     "\"nodes\":[非空] ,\"edges\"?}。传了就创建或整体覆盖；"
                                     "不传则保存前面 add/edit/del 的内存改动"},
         "input": {"type": "string",
                   "description": "run：传给工作流的输入（工作流内用 ${inputs.input} 读取）。"
                                  "传 JSON 对象会自动展开顶层键，所以"
                                  "{\"codes\":\"sz300750\"} 也能用 ${inputs.codes}；"
                                  "help：可当 topic 的简写"},
         "human": {"type": "string", "enum": list(HUMAN_MODES),
                   "description": "run：遇到 human 人工闸门怎么办。默认 deny（无人在场，直接报错）；"
                                  "要跑含闸门的工作流必须显式传 auto-approve 或 auto-reject"},
         "start_node": {"type": "string",
                        "description": "run 可选：从哪个节点 id 开始跑（默认入口 nodes[0]）。"
                                       "用于「单镜返工」「打回后从第 3 级继续」：从指定节点起跑，"
                                       "不必为每种续跑另建工作流。上游节点不会执行，"
                                       "因此只适合“这段之前的结果可以重算/可缺”的场景"},
         "parallel": {"type": "string", "enum": ["", "agent", "sequential"],
                      "description": "run 可选：agent=真并行 / sequential=串行 / 留空=用"
                                     "工作流里保存的并行设置。图设计允许并行，实际跑不跑看这个参数"},
         "detail": {"type": "boolean",
                    "description": "wait 可选：true 时返回 JSON（final + 每节点耗时/字符数/"
                                   "是否被截断/输出文件/告警），不用自己去 runs 目录翻；"
                                   "false（默认）直接返回最终输出文本"}},
        workflow_cmd, ["action"])
