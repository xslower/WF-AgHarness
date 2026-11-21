from __future__ import annotations

import asyncio
import inspect
import json
import logging
from typing import Any

from ..provider.spec import QUEUE_CHILD
from ..tools import toolschema

logger = logging.getLogger("harness.toolschema.llm")

_PROMPT = """你在给一个工具的 Python 实现生成 JSON Schema（供 LLM 调用）。

函数名：{name}
现有描述：{desc}
源码：
```python
{source}
```
{docstring}

只输出一个 JSON 对象，不要 markdown 代码块、不要解释：
{{
  "desc": "工具描述：说清它做什么、什么时候该用、有什么坑（中文）",
  "params": {{"参数名": {{"type": "string|integer|number|boolean|array|object", "description": "这个参数是什么、取值范围/格式、默认值意味着什么"}}}},
  "required": ["必填参数名"]
}}

规则：
- **只写源码里真实存在的参数**，不要发明；`ctx`/`self`/`*args`/`**kwargs` 不要写进去。
- `type` 必须能从注解或用法判断出来；判断不出就按最合理的给它自己定，但要在 description 里说清格式。
- 枚举型参数（取值有限）在 description 里把全部取值列出来，例如 "1=执行（默认），2=撤销上一次写入，3=回滚后重写"。
- `required` 只包含**没有默认值**的参数。
- 工具描述要写给"不知道这个项目"的模型看，不要只重复函数名。"""


async def infer_tool_schema(gateway, *, name: str, desc: str,
                            fn) -> dict[str, Any] | None:
    if gateway is None or fn is None:
        return None
    try:
        source = inspect.getsource(fn)
    except (OSError, TypeError):
        return None
    doc = inspect.getdoc(fn) or ""
    prompt = _PROMPT.format(
        name=name, desc=desc or "(无)", source=source,
        docstring=f"\n函数 docstring：\n{doc}" if doc else "")
    text = ""
    try:
        async for chunk in gateway.chat_stream(
                [{"role": "user", "content": prompt}], spec=QUEUE_CHILD):
            if chunk.type == "text":
                text += chunk.text
    except Exception as e:
        logger.warning("schema 生成调用失败（%s）：%s", name, e)
        return None
    return parse_schema_text(text, fn=fn, name=name)


def parse_schema_text(text: str, *, fn=None, name: str = "") -> dict | None:
    from ..util.llm_out import extract_fenced, last_json_value

    got = last_json_value(text)
    if not isinstance(got, dict):
        fenced, _rest = extract_fenced(text, "json")
        try:
            got = json.loads(fenced) if fenced else None
        except ValueError:
            got = None
    if not isinstance(got, dict):
        logger.warning("schema 生成返回的不是 JSON（%s）：%s", name, text[:200])
        return None
    params = got.get("params")
    if not isinstance(params, dict):
        return None
    clean: dict[str, dict] = {}
    for key, rule in params.items():
        if not isinstance(rule, dict):
            continue
        t = str(rule.get("type") or "string")
        if t not in ("string", "integer", "number", "boolean", "array", "object"):
            t = "string"
        row: dict[str, Any] = {"type": t}
        if rule.get("description"):
            row["description"] = str(rule["description"])
        if isinstance(rule.get("enum"), list):
            row["enum"] = [str(x) for x in rule["enum"]]
        if isinstance(rule.get("items"), dict):
            row["items"] = rule["items"]
        clean[key] = row
    if fn is not None:
        clean = _drop_unknown(fn, clean)
    required = [str(x) for x in (got.get("required") or []) if str(x) in clean]
    return {"desc": str(got.get("desc") or ""), "params": clean,
            "required": required}


def _drop_unknown(fn, params: dict[str, dict]) -> dict[str, dict]:
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return params
    real = {n for n in sig.parameters if n not in ("ctx", "self", "cls")}
    dropped = sorted(set(params) - real)
    if dropped:
        logger.warning("模型生成了不存在的参数 %s，已丢弃", dropped)
    return {k: v for k, v in params.items() if k in real}


def needs_llm(params: dict | None, desc: str, fn) -> bool:
    if fn is None:
        return False
    if not desc:
        return True
    if params is None:
        return True
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return False
    real = {n for n, p in sig.parameters.items()
            if n not in ("ctx", "self", "cls")
            and p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)}
    if real - set(params):
        return True
    return any(not (rule or {}).get("description") for rule in params.values())


def run_sync(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()
