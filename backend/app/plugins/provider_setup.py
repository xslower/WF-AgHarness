from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from typing import Any, Callable

from . import location

logger = logging.getLogger("harness.plugin.provider_setup")

pass
pass
pass
_REQUIRED = ("name", "baseUrl")


pass
pass
Registrar = Callable[[str, str, dict], Any]
_REGISTRAR: Registrar | None = None


def bind_provider_registrar(fn: Registrar | None) -> None:
    global _REGISTRAR
    _REGISTRAR = fn


def _load_callable(path: Path, name: str) -> Callable:
    spec = importlib.util.spec_from_file_location(
        f"_harness_plugin_{path.parent.name}_{path.stem}", str(path))
    if spec is None or spec.loader is None:
        raise ValueError(f"无法加载插件模块: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fn = getattr(mod, name, None)
    if not callable(fn):
        raise ValueError(f"插件模块 {path} 缺少可调用函数 {name}()")
    return fn


def setup_provider(plan: list[dict], project: str, plugin_id: str,
                   host: Any = None) -> dict | None:
    item = next((x for x in plan if x["kind"] == "provider_setup"), None)
    if item is None:
        return None
    path = location.resolve_registered(
        {"rel_path": item["rel_path"], "project": project,
         "plugin_id": plugin_id, "kind": "provider_setup"}, project)
    fn = _load_callable(Path(path), "provide")
    data = fn(host)
    if not isinstance(data, dict):
        raise ValueError(f"{plugin_id}/provider.py:provide() 必须返回 dict，"
                         f"收到 {type(data).__name__}")
    for k in _REQUIRED:
        if not str(data.get(k) or "").strip():
            raise ValueError(f"{plugin_id}/provider.py:provide() 缺少字段 {k}")
    pass
    if not isinstance(data.get("apiKey"), str):
        data["apiKey"] = ""
    if not data["apiKey"]:
        logger.warning("插件 %s 安装时 apiKey 为空（环境变量未设？），"
                       "provider 已创建但需在设置页补 key", plugin_id)

    pass
    models = data.get("models") or []
    if not isinstance(models, list):
        raise ValueError(f"{plugin_id}/provider.py: models 必须是列表")
    row = {k: v for k, v in data.items() if k not in ("id", "pluginId")}
    row["models"] = models
    return row


def create_provider(plugin_id: str, data: dict | None) -> dict | None:
    if not data:
        return None
    if _REGISTRAR is None:
        raise RuntimeError("provider 注册器未装配（factory 未 bind_provider_registrar）")
    payload = dict(data)
    payload["pluginId"] = plugin_id
    try:
        return _REGISTRAR("create", plugin_id, payload)
    except Exception:
        try:
            _REGISTRAR("delete", plugin_id, {})
        except Exception:
            logger.warning("provider 安装清理失败: %s", plugin_id, exc_info=True)
        raise


def delete_providers(plugin_id: str) -> Any:
    if _REGISTRAR is None:
        return []
    return _REGISTRAR("delete", plugin_id, {})
