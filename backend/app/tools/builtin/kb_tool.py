from __future__ import annotations

from typing import TYPE_CHECKING

from ...util.jsonx import dumps

if TYPE_CHECKING:
    from ...registry import ToolContext, ToolRegistry


_ACTIONS = ("search", "add", "build", "collections")

def _open_kb(ctx: "ToolContext", gateway):
    from ...plugins.plugin_sdk import PluginHost

    host = PluginHost.for_request(
        getattr(ctx, "project_dir", lambda: "")() or None,
        project=getattr(ctx, "project", "") or "")
    kb = host.kb
    if gateway is not None:
        async def _embed(texts, model: str = ""):
            return await gateway.embed(list(texts), spec=model)
        kb.embed = _embed
    return kb
    kb = host.kb
    if gateway is not None and kb.embed is None:
        async def _embed(texts, model: str = ""):
            return await gateway.embed(list(texts), spec=model)
        kb.embed = _embed
    return kb


def _parse_docs(docs) -> list[dict]:
    from ...util.jsonfix import loads_lenient

    if isinstance(docs, str):
        obj, why, _note = loads_lenient(docs)
        if why:
            raise ValueError(f"docs 不是合法 JSON: {why}")
        docs = obj
    if isinstance(docs, dict):
        docs = [docs]
    rows = [d for d in (docs or []) if isinstance(d, dict)]
    if not rows:
        raise ValueError("docs 至少一条 {key,title,body}")
    return rows


async def _do_search(kb, coll: str, query: str, limit: int) -> dict:
    meta = kb.info(coll)
    vec, err = None, ""
    if meta["model"] and kb.embed is not None:
        got = await kb.embed([query], meta["model"])
        if got.get("ok"):
            vec = got["vectors"][0]
            pass
            if got.get("model") and got["model"] != meta["model"]:
                vec, err = None, (f"当前向量模型 {got['model']} 与集合建库模型 "
                                  f"{meta['model']} 不一致，改用纯词法检索")
        else:
            err = f"向量化失败（{got.get('error', '未知')}），已降级为纯词法检索"
    return kb.search(coll, query, limit=limit, vector=vec, vector_error=err)


async def _do_add(kb, coll: str, docs) -> dict:
    out = kb.add(coll, _parse_docs(docs))
    if not out.get("model") or kb.embed is None:
        return out
    try:
        built = await kb.build(coll, engine="vector")
    except Exception as e:
        out["build_error"] = f"{type(e).__name__}: {e}"
        return out
    return {**out, **{k: built[k] for k in
                      ("engine", "embedded", "model", "dim", "missing")}}


async def _dispatch(action: str, kb, collection: str, query: str,
                    docs, engine: str, limit: int) -> dict:
    act = (action or "search").strip().lower()
    if act not in _ACTIONS:
        return {"error": f"action 必须是 {'/'.join(_ACTIONS)}，收到: {action}"}
    if act == "collections":
        return {"collections": kb.collections()}
    coll = (collection or "").strip()
    if not coll:
        return {"error": f"action={act} 需要 collection（集合名）"}
    if act == "search":
        return await _do_search(kb, coll, query, limit)
    if act == "add":
        return await _do_add(kb, coll, docs)
    return await kb.build(coll, engine=engine)


def make_kb(gateway):
    async def kb(ctx: "ToolContext", action: str = "search",
                 collection: str = "", query: str = "", docs=None,
                 engine: str = "bm25", limit: int = 8) -> str:
        got = None
        try:
            got = _open_kb(ctx, gateway)
            out = await _dispatch(action, got, collection, query,
                                  docs, engine, limit)
        except Exception as e:
            out = {"error": f"{type(e).__name__}: {e}"}
        finally:
            if got is not None:
                got.close()
        return dumps(out)
    return kb


def register(reg: "ToolRegistry", gateway=None) -> None:
    reg.register(
        "kb",
        "知识库（插件自己的 store.db / 普通项目的 <项目>/.agent/store.db）："
        "action=search 检索、add 写入、build 建索引、collections 列集合。"
        "build 的 engine 只有它用：bm25（默认，纯词法 jieba+FTS5，不需模型）/ "
        "vector（需 embedding 模型，只补缺向量的文档）/ hybrid（需模型，全量重算）。"
        "add 与 search 不传 engine：集合锁过模型就自动带向量，没模型就是纯词法，"
        "降级原因在返回体 degraded/reason 里。docs 为 [{key,title,body,meta?}]"
        "（key 集合内唯一，同 key 覆盖）。",
        {"action": {"type": "string", "enum": list(_ACTIONS),
                    "description": "search 检索 / add 写入 / build 建索引 / collections 列集合"},
         "collection": {"type": "string",
                        "description": "集合名（action=collections 时不用）"},
         "query": {"type": "string", "description": "action=search 的查询词"},
         "docs": {"type": "array", "items": {"type": "object"},
                  "description": "action=add 的文档数组 [{key,title,body,meta?}]"},
         "engine": {"type": "string", "enum": ["bm25", "vector", "hybrid"],
                    "description": "action=build 的引擎，默认 bm25（不需模型）"},
         "limit": {"type": "integer", "description": "action=search 返回条数，默认 8"}},
        make_kb(gateway), ["action"])
