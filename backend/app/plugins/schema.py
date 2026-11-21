from __future__ import annotations

from . import location, tool_unit


def validate_tool_files(files: list[dict], project: str,
                        gateway=None) -> tuple[list[str], list[str]]:
    from . import schema_llm as llm_mod
    from ..tools import toolschema

    errors: list[str] = []
    warnings: list[str] = []
    for f in files:
        if f["kind"] != "tool":
            continue
        try:
            path = location.resolve_registered(f, project)
        except ValueError as e:
            errors.append(f"{f['rel_path']}: {e}")
            continue
        try:
            unit = tool_unit.from_row(path, f["extra"])
            mod = tool_unit.import_module(unit, prefix="_probe", cached=False)
        except Exception as e:
            errors.append(f"{f['rel_path']}: 无法 import（{type(e).__name__}: {e}）")
            continue
        register = getattr(mod, "register", None)
        if not callable(register):
            errors.append(f"{f['rel_path']}: 缺少 register(reg)")
            continue
        probe = _SchemaProbe()
        try:
            register(probe)
        except Exception as e:
            errors.append(f"{f['rel_path']}: register() 执行失败（{type(e).__name__}: {e}）")
            continue
        if not probe.seen and not probe.cascaded:
            errors.append(f"{f['rel_path']}: register() 没有注册任何工具")
            continue
        resolved: dict[str, dict] = {}
        descs = f["extra"].get("descs") or {}
        for name, desc, params, fn in probe.seen:
            pass
            desc = desc or (descs.get(name) if isinstance(descs, dict) else "") or ""
            schema, warning, fatal = _one_tool_schema(
                name, desc, params, fn, gateway=gateway, llm=llm_mod,
                toolschema=toolschema, rel=f["rel_path"])
            if fatal:
                errors.append(fatal)
            if warning:
                warnings.append(warning)
            if schema:
                resolved[name] = schema
        if resolved:
            f["extra"]["schemas"] = resolved
    return errors, warnings


def _one_tool_schema(name: str, desc: str, params, fn, *,
                     gateway, llm, toolschema, rel: str
                     ) -> tuple[dict | None, str, str]:
    if fn is None:
        return None, (f"工具 {name} 没有描述（模型不知道什么时候该用它）"
                      if desc == "" else ""), ""
    if not llm.needs_llm(params, desc, fn):
        return ({"desc": desc, "params": params,
                 "required": _required_from(fn, params, toolschema)}, "", "")
    generated = llm.run_sync(llm.infer_tool_schema(
        gateway, name=name, desc=desc, fn=fn))
    if generated and generated.get("params"):
        final_desc = generated.get("desc") or desc or name
        return ({"desc": final_desc, "params": generated["params"],
                 "required": generated["required"] or []}, "", "")
    try:
        rules, required = toolschema.build(fn, params=params)
    except toolschema.SchemaError as e:
        return None, "", f"{rel}: 工具 {name} 的签名推不出参数（{e}）——" \
                         f"请补类型注解或显式 params"
    return ({"desc": desc or name, "params": rules, "required": required},
            "" if desc else f"工具 {name} 没有描述（模型不知道什么时候该用它）", "")


def _required_from(fn, params, toolschema) -> list[str]:
    try:
        _, required = toolschema.build(fn, params=params)
        return required
    except toolschema.SchemaError:
        return []


class _SchemaProbe:

    def __init__(self) -> None:
        self.seen: list[tuple[str, str, dict | None, object]] = []
        self.cascaded = False

    def tool(self, name, desc="", params=None, fn=None, required=None) -> None:
        self.seen.append((str(name), str(desc or ""), params, fn))

    def cascade(self, capability, fn=None, order="after") -> None:
        self.cascaded = True

    def __getattr__(self, _name):
        return lambda *a, **k: None


