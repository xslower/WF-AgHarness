from __future__ import annotations

from typing import TYPE_CHECKING

from ...util.jsonx import dumps

if TYPE_CHECKING:
    from ...registry import ToolContext, ToolRegistry


_ACTIONS = ("get", "set", "delete", "keys")


def plugin_data(ctx: "ToolContext", action: str = "get", key: str = "",
                value=None) -> str:
    from ...plugins.plugin_sdk import PluginHost

    act = (action or "get").strip().lower()
    data = PluginHost.for_request(
        getattr(ctx, "project_dir", lambda: "")() or None).data
    if act == "get":
        if not key:
            return dumps({"error": "action=get 需要 key"})
        return dumps({"key": key, "value": data.get(key)})
    if act == "set":
        if not key:
            return dumps({"error": "action=set 需要 key"})
        data.set(key, value)
        return dumps({"key": key, "value": value})
    if act == "delete":
        if not key:
            return dumps({"error": "action=delete 需要 key"})
        return dumps({"key": key, "deleted": data.delete(key)})
    if act == "keys":
        return dumps({"keys": data.keys()})
    return dumps({"error": f"action 必须是 {'/'.join(_ACTIONS)}，收到: {action}"})


def register(reg: "ToolRegistry") -> None:
    reg.register(
        "plugin_data",
        "插件/工作流共用的键值数据（如小游戏进度）。action=get/set/delete/keys；"
        "有插件归属时存在该插件自己的目录（<插件家>/data.json），普通项目工作流存"
        "<项目>/.agent/kv.json，与插件 api 的 host.data、工作流 code 节点的 "
        "plugin.data 是同一份。set 的 value 可为任意 JSON 值。",
        {"action": {"type": "string", "enum": list(_ACTIONS),
                    "description": "get 读 / set 写 / delete 删 / keys 列全部键"},
         "key": {"type": "string", "description": "键名；action=keys 时不用"},
         "value": {"description": "action=set 时写入的值（任意 JSON）"}},
        plugin_data, ["action"])
