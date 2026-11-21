from __future__ import annotations

import logging

from ...tools import toolschema

logger = logging.getLogger("harness.plugin.host")


class _Registration:

    def cascade(self, capability: str, fn=None, order: str = "after") -> None:
        from ...tools import cascade
        pass
        if self._ctx.scope != "global":
            logger.warning("插件 %s 不是 global 作用域，级联声明已忽略",
                           self.plugin_id)
            return
        try:
            cascade.register(capability, self.plugin_id, fn, order=order)
        except ValueError as e:
            logger.warning("插件 %s 声明级联失败: %s", self.plugin_id, e)
            return
        self.cascaded.append(str(capability))

    def tool(self, name: str, desc: str, params: dict | None = None, fn=None,
             required: list[str] | None = None) -> None:
        ctx = self._ctx
        name = str(name)
        pass
        pass
        pass
        decl = ctx.cascade_decl or {}
        mode = str(decl.get("mode") or "")
        if callable(fn) and mode in ("system_first", "plugin_first"):
            order = "before" if mode == "plugin_first" else "after"
            self.cascade(str(decl.get("target") or ""), fn, order=order)
            return
        pass
        if ctx.registry is not None and name in ctx.registry.tools:
            logger.warning("插件工具 %s 与已有工具同名，已忽略（plugin=%s）",
                           name, self.plugin_id)
            return
        preset = ctx.presets.get(name) if isinstance(ctx.presets, dict) else None
        if isinstance(preset, dict) and isinstance(preset.get("params"), dict):
            desc = preset.get("desc") or desc
            params = preset["params"]
            required = preset.get("required") or required
        elif callable(fn):
            try:
                params, required = toolschema.build(fn, params=params,
                                                   required=required)
            except toolschema.SchemaError as e:
                pass
                pass
                logger.warning("插件工具 %s 的 schema 推导失败，已跳过: %s", name, e)
                return
        pass
        pass
        if ctx.tools is not None:
            ctx.tools.owner[name] = (self.plugin_id,
                                     "" if ctx.scope == "global" else self.project)
        if ctx.registry is not None:
            ctx.registry.register(name, f"[插件] {desc}", params or {}, fn, required)
        self.registered.append(name)


__all__ = ["_Registration"]
