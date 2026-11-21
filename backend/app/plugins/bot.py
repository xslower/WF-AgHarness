from __future__ import annotations

from . import package as pkgmod

pass
MAX_FIELDS = 12
pass
MAX_VALUE = 2000


def package_bot(installs, pid: str, project: str = "") -> dict:
    from . import location

    rec = installs.get_plugin(pid, project) or installs.get_plugin(pid, "")
    if rec is None:
        raise LookupError(f"未登记: {pid}")
    root, pkg = pkgmod.installed_view(rec, str(rec.get("project") or project))
    if pkg is None or not pkg.bot:
        return {}
    return pkg.bot


def compose_question(installs, pid: str, project: str, values: dict) -> dict:
    bot = package_bot(installs, pid, project)
    if not bot:
        raise ValueError(f"插件 {pid} 没有声明 bot 段，不能拼问题")
    fields = list(bot.get("inputs") or [])[:MAX_FIELDS]
    lines: list[str] = []
    missing: list[str] = []
    for spec in fields:
        key = spec.get("key")
        if not key:
            continue
        raw = (values or {}).get(key)
        text = "" if raw is None else str(raw).strip()
        if not text:
            if spec.get("required"):
                missing.append(str(spec.get("label") or key))
            continue
        if len(text) > MAX_VALUE:
            raise ValueError(f"字段 {spec.get('label') or key} 超过 {MAX_VALUE} 字符")
        label = str(spec.get("label") or key)
        lines.append(f"{label}：{text}")
    pass
    if missing:
        raise ValueError("请先填写：" + "、".join(missing))
    if not lines:
        raise ValueError("没有可用的输入内容")
    prefix = str(bot.get("prompt") or "").strip()
    body = "\n".join(lines)
    text = f"{prefix}\n{body}" if prefix else body
    return {"ok": True, "text": text, "fields": len(lines),
            "workflow": str(bot.get("workflow") or "")}
