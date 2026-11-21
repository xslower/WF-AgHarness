from __future__ import annotations

import copy
import json
import logging
from typing import TYPE_CHECKING

logger = logging.getLogger("harness.tools.meta")

from ...util.jsonx import err
from ...skills import catalog_text, match_skills, skill_index, skill_roots, use_skill

if TYPE_CHECKING:
    from .. import ToolContext, ToolRegistry

pass
pass
pass
pass
pass
pass
_FULL_LIMIT = 18
_FULL_LIMIT_SMALL = _FULL_LIMIT + 1
_BRIEF_END = 50


def _format_full_signature(name: str, schema: dict) -> str:
    f = schema["function"]
    params = f["parameters"].get("properties", {})
    required = set(f["parameters"].get("required", []))
    parts = []
    for k, v in params.items():
        ptype = v.get("type", "?")
        pdesc = v.get("description", "")
        req = "必填" if k in required else "可选"
        parts.append(f"{k}:{ptype}({req}) — {pdesc}")
    pstr = ", ".join(parts) if parts else "无参数"
    return f"{name}({pstr}) — {f.get('description', '')}"


def _copy_schema_with_desc(reg: "ToolRegistry", name: str, desc: str) -> dict | None:
    for s in reg.schemas:
        if s["function"]["name"] == name:
            c = copy.deepcopy(s)
            c["function"]["description"] = desc
            return c
    return None


async def tool_cmd(ctx: "ToolContext", action: str = "search", query: str = "",
                   name: str = "", args: dict = None) -> str:
    act = (action or "search").strip().lower()
    if act == "search":
        return await _search(query, ctx)
    if act == "use":
        if not name:
            return json.dumps({"error": "action=use 需要 name（skill 名，形如 skill__xxx）"},
                              ensure_ascii=False)
        return use_skill(name, skill_roots())
    if act == "invoke":
        if not name:
            return json.dumps({"error": "action=invoke 需要 name"},
                              ensure_ascii=False)
        return await _invoke(name, args or {}, ctx)
    return json.dumps({"error": f"action 必须是 search/invoke/use，收到: {action}"},
                      ensure_ascii=False)


def _visible(name: str, ctx: "ToolContext") -> bool:
    pm = getattr(getattr(ctx, "registry", None), "pluginman", None)
    if pm is None:
        return True
    try:
        project = getattr(ctx, "project_dir", lambda: "")()
        return bool(pm.tool_visible(
            name, project,
            allow_internal=bool(getattr(ctx, "allow_internal", False))))
    except Exception:
        return True


def _builtin_matches(reg, ctx, terms: list[str]) -> list[tuple[str, dict, str]]:
    out: list[tuple[str, dict, str]] = []
    for s in reg.schemas:
        f = s["function"]
        name = f["name"]
        if name == "tool":
            continue
        pass
        if not _visible(name, ctx):
            continue
        text = f"{name} {f['description']}".lower()
        if not terms or any(t in text for t in terms):
            out.append((name, s, "builtin"))
    return out


def _mcp_matches(ctx, terms: list[str]) -> tuple[list[tuple[str, dict, str]], dict[str, int]]:
    matches: list[tuple[str, dict, str]] = []
    per_server: dict[str, int] = {}
    if not ctx.mcp:
        return matches, per_server
    pass
    for c in ctx.mcp.visible_conns(getattr(ctx, "project_dir", lambda: "")() or ""):
        if not c.ready:
            continue
        for full_name, schema in c.tools.items():
            desc = schema["function"].get("description", "")
            text = f"{full_name} {desc}".lower()
            if not terms or any(t in text for t in terms):
                matches.append((full_name, schema, c.name))
                per_server[c.name] = per_server.get(c.name, 0) + 1
    return matches, per_server


def _stats_text(builtin_hit: int, per_server: dict[str, int]) -> str:
    parts: list[str] = []
    if builtin_hit:
        parts.append(f"[内置]x{builtin_hit}")
    for srv, cnt in per_server.items():
        parts.append(f"[MCP/{srv}]x{cnt}")
    return " ".join(parts) or "无命中"


def _tiered(
    matches: list[tuple[str, dict, str]], stats_text: str,
) -> tuple[list[dict], list[str], str]:
    total = len(matches)
    if total == 0:
        return [], [], (f"共 0 个匹配。命中统计：{stats_text}。"
                        "可换关键词缩小范围重搜。")
    if total < _FULL_LIMIT_SMALL:
        return [s for _, s, _ in matches], [], (
            f"共 {total} 个匹配（{stats_text}），"
            "已全部将完整签名加入本轮可调工具，可直接调用；"
            "不满意可继续 tool(action=search) 缩小范围重搜。")
    def _brief(name: str, schema: dict, src: str) -> str:
        params = schema["function"].get("parameters", {}).get("properties", {})
        keys = ", ".join(list(params)[:6]) or "无参数"
        tag = "[内置]" if src == "builtin" else f"[MCP/{src}]"
        desc = schema["function"].get("description", "")[:60]
        return f"{name}({keys}) — {desc} {tag}"

    briefs = [_brief(name, schema, src)
              for name, schema, src in matches[_FULL_LIMIT:_BRIEF_END]]
    header = (f"共 {total} 个匹配（{stats_text}）。"
              f"前 {_FULL_LIMIT} 个完整签名已加入本轮可调工具，可直接调用；"
              f"以下 {len(briefs)} 个为简述，可用 tool(action=invoke) 调用。")
    if total >= _BRIEF_END:
        header += ("\n命中过多（>=50），建议缩小范围、增加更精确的关键词"
                   "重新 tool(action=search)。")
    return [s for _, s, _ in matches[:_FULL_LIMIT]], briefs, header


async def _search(query: str, ctx: "ToolContext") -> str:
    reg = _REGISTRY.get("reg")
    if reg is None:
        return err("工具目录不可用")
    terms = [t.lower() for t in (query or "").split() if t]

    builtin = _builtin_matches(reg, ctx, terms)
    mcp, per_server = _mcp_matches(ctx, terms)
    matches = builtin + mcp
    stats_text = _stats_text(len(builtin), per_server)

    full_schemas, briefs, header = _tiered(matches, stats_text)

    pass
    pass
    pass
    project = getattr(ctx, "project_dir", lambda: "")() or ""
    tool_schema = _copy_schema_with_desc(
        reg, "tool",
        _build_tool_description(reg, ctx.mcp, stats_text=stats_text,
                                total=len(matches), project=project))
    boost_schemas = full_schemas + [s for s in (tool_schema,) if s]

    ctx.suggest_tools(boost_schemas)
    out = header + ("\n" + "\n".join(briefs) if briefs else "")
    pass
    skill_hits = match_skills(query, skill_roots()) if (query or "").strip() else []
    if skill_hits:
        out += (f"\n【技能库命中 {len(skill_hits)} 个】用 tool(action=use, name=...) "
                "加载完整指南：\n"
                + "\n".join(f"  {h['name']} — {h['desc']}" for h in skill_hits))
    return out


async def _invoke(name: str, args: dict, ctx: "ToolContext") -> str:
    pass
    pass
    pass
    if (name or "").strip() == "tool":
        return err("tool 不允许调用 tool（禁止多跳绕过）")
    reg = _REGISTRY.get("reg")
    if reg is None:
        return err("工具目录不可用")
    pass
    if name in reg.tools:
        if not _visible(name, ctx):
            return err(f"工具 {name} 在当前项目不可用（属于其它项目的插件）")
        return await reg.execute(name, args or {}, ctx)
    pass
    pass
    roots = skill_roots()
    idx = skill_index(roots)
    if name in idx or f"skill__{name}" in idx:
        return ("[已按 skill 指南加载（等价 tool(action=use)）]\n"
                + use_skill(name, roots))
    pass
    pass
    pass
    project = getattr(ctx, "project_dir", lambda: "")() or ""
    if ctx.mcp and ctx.mcp.knows(name, project):
        return await ctx.mcp.call(name, args or {}, project)
    hint = _build_error_hint(name, reg, ctx)
    return json.dumps({"error": f"工具不存在: {name}", "hint": hint},
                      ensure_ascii=False)


def _build_error_hint(name: str, reg, ctx) -> str:
    pass
    for s in reg.schemas:
        f = s["function"]
        if name.lower() in f["name"].lower() or f["name"].lower() in name.lower():
            return "你可能想调用: " + _format_full_signature(f["name"], s)
    pass
    if ctx.mcp:
        project = getattr(ctx, "project_dir", lambda: "")() or ""
        for summary in ctx.mcp.mcp_summary(project):
            for tool_name in summary.get("tools", []):
                full = f"mcp__{summary['server']}__{tool_name}"
                if name.lower() in full.lower() or full.lower() in name.lower():
                    schema = ctx.mcp.get_tool_schema(full, project)
                    if schema:
                        return "你可能想调用: " + _format_full_signature(full, schema)
    return "请先调用 tool(action=search) 查询可用工具"


_REGISTRY: dict = {}


def _build_tool_description(reg, mcp=None, stats_text: str = "",
                            total: int | None = None, project: str = "") -> str:
    desc = (
        "工具目录。action=search 按关键词搜索内置工具、MCP 工具与技能库"
        "（命中的完整签名会加入本轮可直接调用的工具）；"
        "action=invoke 直接调用任意内置工具或 MCP 工具（给 name + args，无需先搜）；"
        "action=use 加载某个 skill 的完整操作指南（给 name，形如 skill__xxx）。\n"
        "核心工具平时已直接可用，本工具用于发现/调用不在核心清单里的能力。"
        "MCP 工具名格式 mcp__服务器__工具，skill 名格式 skill__名称。\n"
    )
    if stats_text:
        desc += f"\n【本次命中统计】共 {total} 个：{stats_text}\n"
        desc += "若已注入的工具仍不满足，缩小范围、加更精确的关键词再次 search。\n"
    pass
    if reg:
        builtin = reg.builtin_summary(project=project)
        if builtin:
            desc += "\n【内置扩展工具】（需 action=search 或 action=invoke）：\n"
            for t in builtin:
                desc += f"  {t['name']}({t['params']}) — {t['description']}\n"
    pass
    if mcp:
        summaries = mcp.mcp_summary(project)
        if summaries:
            desc += "\n【MCP 服务器】（全部需 search 或 invoke，格式 mcp__服务器__工具）：\n"
            for s in summaries:
                status = "已连接" if s["connected"] else "未连接"
                tools_str = ", ".join(s["tools"][:8])
                if len(s["tools"]) > 8:
                    tools_str += f" ...等 {len(s['tools'])} 个"
                desc += f"  {s['server']}({s['tool_count']}个工具, {status}): {tools_str}\n"
        else:
            desc += "\n【MCP 服务器】：无\n"
    pass
    pass
    skill_cat = catalog_text()
    if skill_cat:
        desc += ("\n【技能库】（action=use 加载全文，name 直接用下列标识）：\n"
                 + skill_cat + "\n")
    pass
    popular = []
    if reg:
        popular.extend(reg.popular_builtin_tools(limit=5))
    if mcp:
        popular.extend(mcp.popular_mcp_tools(limit=5, project=project))
    if popular:
        desc += "\n【常用工具热榜】（按调用次数排序，可直接 action=invoke）：\n"
        for t in popular:
            desc += (f"  {t['name']}({t['params']}) — {t['description']}"
                     f" (调用{t['call_count']}次)\n")
    desc += "\n关键词空格分隔多个词，search 时留空=列出全部。"
    return desc


def update_dynamic_schemas(reg, mcp=None, project: str = "") -> None:
    desc = _build_tool_description(reg, mcp, project=project)
    for s in reg.schemas:
        if s["function"]["name"] == "tool":
            s["function"]["description"] = desc


def register(reg: "ToolRegistry") -> None:
    _REGISTRY["reg"] = reg
    reg.register(
        "tool",
        "工具目录（发现 + 调用 + 技能）。action=search 按关键词搜索内置工具、MCP 工具与技能库，"
        "命中的完整签名会加入本轮可调工具；action=invoke 直接调用任意工具或 MCP 工具"
        "（name + args，无需先搜；参数错误会返回完整签名供修正）；"
        "action=use 加载 skill 的完整操作指南（name=skill__名称）。"
        "核心工具平时已直接可用，本工具用于发现/调用不在核心清单里的能力。",
        {"action": {"type": "string", "enum": ["search", "invoke", "use"],
                    "description": "search=搜索目录，invoke=调用工具，use=加载 skill 指南"},
         "query": {"type": "string",
                   "description": "action=search：关键词，空格分隔多个词，空=列出全部"},
         "name": {"type": "string",
                  "description": "action=invoke/use：工具名（MCP 为 mcp__server__tool）"
                                 "或 skill 名（skill__名称）"},
         "args": {"type": "object", "description": "action=invoke：该工具的参数对象"}},
        tool_cmd, ["action"])

