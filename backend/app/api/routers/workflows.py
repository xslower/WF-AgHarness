from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from ..errors import bad_request, from_error, http_error, not_found
from ...util.jsonfix import loads_lenient
from ...util.llm_out import extract_fenced, last_json_value, retry_hint
from ...provider.spec import QUEUE_PARENT
from ...workflow import WorkflowError
from ...workflow.errors import KIND_NOT_FOUND
from ..deps import Container, get_container

router = APIRouter()


@router.get("/api/workflows")
def wf_list(project: str = "", status: str = "", c: Container = Depends(get_container)):
    items = [it for it in c.wf_engine(project).list() if not it.get("internal")]
    if status:
        items = [it for it in items if it.get("status") == status]
    return items


@router.get("/api/workflows/nodes")
def wf_nodes(c: Container = Depends(get_container)):
    return c.nodes.catalog() if c.nodes else c.wf_engine("").nodes.catalog()


@router.get("/api/workflows/available")
def wf_available(project: str = "", c: Container = Depends(get_container)):
    return c.wf_engine(project).list_available()


pass
pass
@router.get("/api/workflows/runs")
def wf_run_list(project: str = "", workflow: str = "", limit: int = 50,
                c: Container = Depends(get_container)):
    return {"items": c.wf_engine(project).list_runs(workflow=workflow, limit=limit)}


@router.get("/api/workflows/{name}")
def wf_get(name: str, project: str = "", c: Container = Depends(get_container)):
    wf = c.wf_engine(project).get(name)
    if wf is None and project:
        pass
        pass
        wf = c.wf_engine("").get(name)
        if wf is not None:
            wf["_scope"] = "global"
    if not wf:
        raise not_found("工作流不存在")
    return wf


@router.post("/api/workflows")
async def wf_save(wf: dict, project: str = "", c: Container = Depends(get_container)):
    return _call(c, project, "save", wf)


@router.delete("/api/workflows/{name}")
def wf_delete(name: str, project: str = "", c: Container = Depends(get_container)):
    return {"ok": c.wf_engine(project).delete(name)}


class WfRenameIn(BaseModel):
    new_name: str


@router.post("/api/workflows/{name}/rename")
def wf_rename(name: str, r: WfRenameIn, project: str = "",
              c: Container = Depends(get_container)):
    return _call(c, project, "rename", name, r.new_name.strip())


class WfParentIn(BaseModel):
    parent: str = ""


class WfStatusIn(BaseModel):
    status: str = "draft"


@router.post("/api/workflows/{name}/status")
def wf_set_status(name: str, r: WfStatusIn, project: str = "",
                  c: Container = Depends(get_container)):
    return _call(c, project, "set_status", name, r.status.strip())



@router.post("/api/workflows/{name}/parent")
def wf_set_parent(name: str, r: WfParentIn, project: str = "",
                  c: Container = Depends(get_container)):
    return _call(c, project, "set_parent", name, r.parent.strip())


class WfAssistIn(BaseModel):
    instruction: str
    project: str = ""


@router.post("/api/workflows/import")
async def wf_import(wf: dict, project: str = "", adapt: bool = True,
                    c: Container = Depends(get_container)):
    if adapt:
        pass
        pass
        pass
        free_map: dict[str, bool] = {}
        by_kind: dict[str, list[str]] = {}
        for p in c.store.config.providers:
            for m in p.models:
                spec = f"{p.id}/{m.id}"
                free_map[spec] = bool(getattr(m, "free", False))
                by_kind.setdefault(m.kind or "lm", []).append(spec)
        for k in by_kind:
            by_kind[k].sort(key=lambda s: not free_map.get(s, False))
        resolved = set(free_map)
        for n in wf.get("nodes", []):
            spec = n.get("model")
            if not spec:
                continue
            if spec in resolved:
                continue
            pass
            kind = {"ocr": "ocr", "image": "image", "asr": "asr"}.get(n.get("type"), "lm")
            cands = by_kind.get(kind) or by_kind.get("lm", [])
            if cands:
                n["model"] = cands[0]
    return _call(c, project, "save", wf)


@router.get("/api/workflows/{name}/export")
def wf_export(name: str, project: str = "", c: Container = Depends(get_container)):
    wf = c.wf_engine(project).get(name)
    if not wf:
        raise not_found("工作流不存在")
    return Response(
        content=json.dumps(wf, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{name}.workflow.json"'})


@router.post("/api/workflows/{name}/assist")
async def wf_assist(name: str, r: WfAssistIn, c: Container = Depends(get_container)):
    eng = c.wf_engine(r.project)
    wf = eng.get(name)
    if not wf:
        raise not_found("工作流不存在")
    prompt = (
        "你是工作流编辑器。根据指令修改下面的工作流 JSON（React Flow 画布同源数据）\n"
        # 节点类型从注册表取：硬编码清单会和实际能力漂移（新加的类型模型不知道，
        # 下线/改名的类型模型还在用），这里出错的代价是整张图校验不过。
        f"节点类型：{'/'.join(eng.nodes.types())}\n"
        "规则：最后用一个 ```json 代码块输出修改后的完整工作流 JSON，代码块之外不要解释；"
        "保持未涉及部分不变；节点 id 稳定（已存在的不改名）；"
        "next/true/false 指向的 id 必须存在；变量引用 ${inputs.x} 与 ${节点id}。\n"
        f"指令：{r.instruction}\n"
        f"当前工作流：\n{json.dumps(wf, ensure_ascii=False)}")
    last_err = ""
    messages: list[dict] = [{"role": "user", "content": prompt}]
    for attempt in range(4):
        text = ""
        async for chunk in c.gateway.chat_stream(
                messages, spec=QUEUE_PARENT, session_id=f"wfassist:{name}"):
            if chunk.type == "text":
                text += chunk.text
        body, err = extract_fenced(text, "json")
        new_wf = None
        last_err = err
        if body:
            obj, detail, _note = loads_lenient(body, scene="raw")
            if detail or not isinstance(obj, dict):
                last_err = detail or "结果必须是 JSON 对象"
            else:
                new_wf, last_err = obj, ""
        elif attempt >= 1:
            pass
            pass
            cand = last_json_value(text)
            if cand is None:
                fixed, detail, _note = loads_lenient(text, scene="raw")
                cand = fixed if not detail and isinstance(fixed, dict) else None
            if isinstance(cand, dict):
                new_wf, last_err = cand, ""
        if new_wf is not None:
            try:
                eng.validate(new_wf, eng.nodes)
                return {"ok": True, "workflow": new_wf}
            except (ValueError, WorkflowError) as e:
                last_err = str(e)
        messages.append({"role": "assistant", "content": text})
        messages.append({"role": "user", "content": retry_hint("json", last_err)})
    raise bad_request(f"LLM 修改工作流失败（已重试 3 次）: {last_err}")


def _call(c: Container, project: str, op: str, *args, **kw):
    try:
        return getattr(c.wf_engine(project), op)(*args, **kw)
    except WorkflowError as e:
        raise from_error(e)


def _engine_with_run(c: Container, rid: str, project: str = ""):
    eng = c.wf_engine(project)
    if rid in eng.runs:
        return eng
    return (c.wf_router.find_run(rid) if c.wf_router else None) or eng




class RunCtlIn(BaseModel):
    project: str = ""
    start_node: str = ""
    note: str = ""


@router.post("/api/workflows/runs/{rid}/cancel")
def wf_run_cancel(rid: str, r: RunCtlIn, c: Container = Depends(get_container)):
    res = _engine_with_run(c, rid, r.project).cancel(rid)
    if not res["ok"]:
        pass
        pass
        raise http_error(404 if res["reason"] == "运行不存在" else 409, res["reason"])
    return res


@router.post("/api/workflows/runs/{rid}/resume")
async def wf_run_resume(rid: str, r: RunCtlIn, c: Container = Depends(get_container)):
    eng = _engine_with_run(c, rid, r.project)
    try:
        rec = await eng.resume(rid, start_node=r.start_node)
    except WorkflowError as e:
        raise from_error(e)
    return rec.to_dict()


@router.post("/api/workflows/runs/{rid}/redo")
async def wf_run_redo(rid: str, r: RunCtlIn, c: Container = Depends(get_container)):
    owner = _engine_with_run(c, rid, r.project)
    try:
        rec = await owner.redo(rid, from_node=r.start_node, note=r.note)
    except WorkflowError as e:
        raise from_error(e)
    return {"run_id": rec.id}


class WfRunIn(BaseModel):
    inputs: dict = {}
    project: str = ""
    start_node: str = ""
    preset_outputs: dict = {}
    parallel_mode: str = ""
    pass
    human: str = "ask"
    pass
    pass
    session: str = ""


@router.post("/api/workflows/{name}/run")
async def wf_run(name: str, r: WfRunIn, c: Container = Depends(get_container)):
    eng = c.wf_engine(r.project)
    try:
        rec = eng.start(
            name, r.inputs, start_node=r.start_node,
            preset_outputs=r.preset_outputs or None,
            parallel_mode=r.parallel_mode, human_mode=r.human,
            session=r.session)
    except WorkflowError as e:
        if e.kind == KIND_NOT_FOUND and r.project:
            pass
            try:
                rec = c.wf_engine("").start(
                    name, r.inputs, start_node=r.start_node,
                    preset_outputs=r.preset_outputs or None,
                    parallel_mode=r.parallel_mode, human_mode=r.human,
                    session=r.session)
                return {"run_id": rec.id, "scope": "global"}
            except WorkflowError:
                pass
            raise not_found(f"{e}（当前项目与全局目录都没找到）")
        raise from_error(e)
    return {"run_id": rec.id}


class WfSingleIn(BaseModel):
    node_id: str
    inputs: dict = {}
    project: str = ""
    preset_outputs: dict = {}


@router.post("/api/workflows/{name}/run_single")
async def wf_run_single(name: str, r: WfSingleIn,
                        c: Container = Depends(get_container)):
    eng = c.wf_engine(r.project)
    try:
        rec = await eng.run_single(name, r.node_id, r.inputs,
                                   r.preset_outputs or None)
    except WorkflowError as e:
        raise from_error(e)
    return rec.to_dict()


class HumanDecideIn(BaseModel):
    project: str = ""
    node_id: str
    choice: str
    comment: str = ""


@router.post("/api/workflows/runs/{rid}/human")
def wf_run_human(rid: str, r: HumanDecideIn, c: Container = Depends(get_container)):
    eng = _engine_with_run(c, rid, r.project)
    if not eng.human.decide(rid, r.node_id, r.choice, r.comment):
        pass
        pass
        pending = eng.human.pending(rid) or {}
        if pending and pending.get("node_id") == r.node_id:
            raise bad_request(
                f"选项 {r.choice!r} 不在这个闸门的按钮里（可选："
                f"{', '.join(pending.get('options') or [])}）")
        raise not_found("该运行没有等待中的闸门（可能已处理或运行已结束）")
    return {"ok": True, "node_id": r.node_id, "choice": r.choice}


@router.get("/api/workflows/runs/{rid}/why")
def wf_run_why(rid: str, node: str = "", key: str = "", grep: str = "",
               project: str = "", c: Container = Depends(get_container)):
    owner = _engine_with_run(c, rid, project)
    pass
    pass
    try:
        return owner.why(rid, node=node, key=key, grep=grep)
    except WorkflowError as e:
        raise from_error(e)


@router.get("/api/workflows/runs/{rid}")
def wf_run_status(rid: str, project: str = "", c: Container = Depends(get_container)):
    owner = _engine_with_run(c, rid, project)
    rec = owner.runs.get(rid)
    if not rec:
        pass
        pass
        restored = c.wf_engine(project).load_run(rid)
        if restored:
            return restored
        raise not_found("运行不存在")
    data = rec.to_dict()
    pass
    data["pending_human"] = ((owner.human.pending(rid) or rec.pending_human)
                             if rec.status == "running" else None)
    return data
