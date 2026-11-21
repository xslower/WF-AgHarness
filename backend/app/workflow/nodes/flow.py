from __future__ import annotations

import asyncio
import json
import re

from ..errors import WorkflowError
from .registry import (NodeContext, NodeField, NodeSpec, NodeRegistry,
                       node_model, wf_model_field)

MAX_ITER = 100


def _cond_out(ok: bool, note: str = "", error: str = "") -> str:
    detail = f"condition={'true' if ok else 'false'}{note}"
    out = {"pass": ok, "detail": detail}
    if error:
        pass
        out["error"] = error
    return json.dumps(out, ensure_ascii=False)


async def run_condition(node: dict, ctx: NodeContext, vars: dict) -> tuple[str, str | None]:
    mode = str(node.get("mode", "expr") or "expr").strip()
    inp = ctx.sub(str(node.get("input", "${prev}") or "${prev}"), vars)
    if mode == "llm":
        pass
        q = ctx.sub(node.get("expr", ""), vars)
        prompt = ("判断下面的内容是否满足给定条件。只回答 true 或 false，不要任何其它内容。\n"
                  f"条件：{q}\n"
                  f"内容：\n{inp}")
        text = ""
        async for chunk in ctx.gateway.chat_stream(
                [{"role": "user", "content": prompt}],
                spec=node_model(node), session_id=f"wf:{ctx.run_id}"):
            if chunk.type == "text":
                text += chunk.text
        head = text.strip().lower()[:20]
        ok = head.startswith("true") or "true" in head.split()
        note = f"（llm 判断：{text.strip()[:100]}）"
        return _cond_out(ok, note), (node.get("true") if ok else node.get("false")) or None
    ok = ctx.eval_condition(node["expr"], vars)
    err_box = ctx.extras.get("expr_error") or {}
    return (_cond_out(ok, "", err_box.get("error", "")),
            (node.get("true") if ok else node.get("false")) or None)

async def run_loop(node: dict, ctx: NodeContext, vars: dict) -> tuple[str, str | None]:
    times_s = ctx.sub(str(node.get("times", 1)), vars)
    try:
        times = int(float(times_s))
    except ValueError:
        times = 1
    times = max(0, min(times, MAX_ITER))
    for i in range(times):
        vars["outputs"]["__i__"] = str(i)
        await ctx.traverse(node["body"], {node["id"]})
    return f"循环完成 ×{times}", node.get("next")


def _items_from_raw(raw: str, ctx: NodeContext, vars: dict) -> list[str]:
    evaluator = (ctx.extras or {}).get("eval_value")
    if evaluator is not None and "${" in raw:
        try:
            value = evaluator(raw, vars)
        except Exception:
            value = None
        pass
        if isinstance(value, list):
            return [json.dumps(x, ensure_ascii=False) if isinstance(x, (dict, list))
                    else str(x) for x in value]
        if isinstance(value, dict):
            raise WorkflowError(
                f"map 节点 {node_label(ctx)}: items 求值得到的是对象（键：{list(value)[:5]}），"
                "不是列表。请写明要哪一段，例如 items: ${x!raw}['scenes']；"
                "若本来就想遍历这个对象的键，用 items: list(${x!raw}) 或 get(...)")
        if isinstance(value, str):
            raw = value
        elif value is not None:
            return [str(value)]
    pass
    if "${" in raw:
        raw = ctx.sub(raw, vars)

    t = raw.strip()
    if t.startswith("[") or t.startswith("- "):
        try:
            arr = json.loads(t)
        except ValueError:
            from ..expr import yaml_value
            arr = yaml_value(t, None)
        if isinstance(arr, list):
            return [json.dumps(x, ensure_ascii=False) if isinstance(x, (dict, list))
                    else str(x) for x in arr]
        if isinstance(arr, dict):
            raise WorkflowError(
                f"map 节点: items 解析得到对象（键：{list(arr)[:5]}），需要一个列表")
    return [x.strip() for x in re.split(r"[\n,]", raw) if x.strip()]


def node_label(ctx: NodeContext) -> str:
    return str((ctx.extras or {}).get("node_id") or "")


pass

def _item_digest(item: str) -> str:
    import hashlib
    return hashlib.sha1(str(item).encode("utf-8")).hexdigest()[:16]


def _load_progress(ctx: NodeContext, node_id: str) -> dict[str, str]:
    fn = (ctx.extras or {}).get("progress_read")
    if not fn or not node_id:
        return {}
    try:
        return fn(node_id) or {}
    except Exception:
        return {}


def _save_progress(ctx: NodeContext, node_id: str, i: int, digest: str,
                   result: str) -> None:
    fn = (ctx.extras or {}).get("progress_append")
    if not fn or not node_id:
        return
    try:
        fn(node_id, {"i": i, "item_digest": digest, "result": result})
    except Exception:
        pass



async def run_map(node: dict, ctx: NodeContext, vars: dict) -> tuple[str, str | None]:
    pass
    pass
    pass
    items = _items_from_raw(str(node.get("items", "")), ctx, vars)[:MAX_ITER]
    collect = str(node.get("collect") or "__item__").strip() or "__item__"
    pass
    pass
    pass
    fmt = str(node.get("output") or "text").strip().lower()

    pass
    slots = 1
    if ctx.extras:
        try:
            slots = max(1, int(ctx.extras.get("parallel_slots") or 1))
        except (TypeError, ValueError):
            slots = 1
    slots = min(slots, len(items) or 1)

    pass
    pass
    pass
    node_id = str(node.get("id") or "")
    done = _load_progress(ctx, node_id)
    hits = sum(1 for it in items if _item_digest(it) in done)
    if hits and hits < len(items):
        ctx.warn(f"map {node_id} 续跑：{hits}/{len(items)} 项命中已完成进度，将跳过",
                 code="map-resume", node=node_id)
    elif hits and hits == len(items):
        ctx.warn(f"map {node_id} 全部 {hits} 项均已在上轮完成，本轮直接复用结果",
                 code="map-resume", node=node_id)

    warned = {"missing": False}

    def _pick(box: dict, i: int, item: str) -> str:
        if collect in box:
            return box[collect]
        if collect != "__item__" and not warned["missing"]:
            warned["missing"] = True
            ctx.warn(f"map 的 collect=\"{collect}\" 在循环体里没有任何节点产出，"
                     "已回落到当前项；要收集结果请写 body 里那个节点的 id",
                     code="map-collect", node=str(node.get("id") or ""))
        return item

    if slots <= 1:
        results: list[str] = []
        for i, item in enumerate(items):
            digest = _item_digest(item)
            if digest in done:
                results.append(done[digest])
                continue
            vars["outputs"]["__item__"] = item
            vars["outputs"]["__i__"] = str(i)
            await ctx.traverse(node["body"], {node["id"]})
            result = _pick(vars["outputs"], i, item)
            results.append(result)
            _save_progress(ctx, node_id, i, digest, result)
    else:
        pass
        pass
        sem = asyncio.Semaphore(slots)
        results = [""] * len(items)

        async def _one(i: int, item: str) -> None:
            digest = _item_digest(item)
            if digest in done:
                results[i] = done[digest]
                return
            local = {"inputs": vars.get("inputs", {}),
                     "outputs": dict(vars.get("outputs", {})),
                     "output_paths": dict(vars.get("output_paths") or {}),
                     "_known": vars.get("_known") or set()}
            local["outputs"]["__item__"] = item
            local["outputs"]["__i__"] = str(i)
            async with sem:
                await ctx.traverse(node["body"], {node["id"]},
                                   local_vars=local, suffix=f"@{i}")
            results[i] = _pick(local["outputs"], i, item)
            pass
            _save_progress(ctx, node_id, i, digest, results[i])

        await asyncio.gather(*[_one(i, it) for i, it in enumerate(items)])

    if fmt == "json":
        pass
        pass
        pass
        from ..expr import parse_any
        parsed = [parse_any(r, r) for r in results]
        return json.dumps({"n": len(parsed), "items": items,
                           "results": parsed}, ensure_ascii=False), node.get("next")
    return "\n\n".join(results), node.get("next")


async def run_join(node: dict, ctx: NodeContext, vars: dict) -> tuple[str, str | None]:
    prev = str(vars.get("outputs", {}).get("prev") or "")
    return prev, node.get("next")


def register(reg: NodeRegistry) -> None:
    reg.register(NodeSpec(
        type="join", label="汇合", run=run_join,
        fields=(NodeField("next", "汇合后去哪", placeholder="下游节点 id"),),
        group="逻辑", branch_keys=("next",),
        desc="多分支汇合点：幂等（同一趟只跑一次），把上游输出拼起来继续"))
    reg.register(NodeSpec(
        type="condition", label="条件分支", run=run_condition,
        fields=(NodeField("expr", "表达式（expr 模式）或条件描述（llm 模式）",
                          required=True,
                          placeholder="len(${prev}) > 100 或：输出包含敏感词"),
                NodeField("mode", "判断方式", "select", ("expr", "llm")),
                wf_model_field("模型（llm 判断用；默认总结队列）"),
                NodeField("input", "判断输入（默认上一节点输出 ${prev}）",
                          placeholder="${prev} / ${s1} / ${inputs.x}"),
                NodeField("maxVisits", "最多进入次数（0=不限；回边循环用它收敛）",
                          "number", placeholder="3")),
        required=("expr", "true"), group="逻辑",
        branch_keys=("true", "false"),
        desc="expr / llm 判断走 true/false；true 指回上游即 while/do-while（false 可空=结束）；llm 判断默认总结队列，可指定模型"))
    reg.register(NodeSpec(
        type="loop", label="循环", run=run_loop,
        fields=(NodeField("times", "次数（支持 ${}）", placeholder="3"),
                NodeField("body", "循环体起始节点 id", required=True, placeholder="b1")),
        required=("body",), group="逻辑", branch_keys=("body",),
        desc="body 子链重复 N 次，${__i__} 为轮次"))
    reg.register(NodeSpec(
        type="map", label="Map 遍历", run=run_map,
        fields=(NodeField("items", "列表（JSON 数组 / 逗号 / 换行分隔，支持 ${}）", "textarea",
                          required=True, placeholder="[\"a\", \"b\"] 或 ${s1}"),
                NodeField("body", "循环体起始节点 id", required=True, placeholder="b1"),
                NodeField("collect", "收集哪个变量（默认 __item__=当前项）",
                          placeholder="body 里最后那个节点的 id"),
                NodeField("concurrency", "并发数（0=跟随全局；受运行参数 parallel 约束）",
                          "number", placeholder="3"),
                NodeField("output", "输出形态（json 时 ${m1.results} 是数组，${m1.results.0.字段} 可下钻）",
                          "select", ("text", "json"))),
        required=("body",), group="逻辑", branch_keys=("body",),
        desc="items 逐项跑 body，${__item__}/${__i__} 注入；可配并发"))
    pass
    pass
