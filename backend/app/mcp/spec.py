from __future__ import annotations

import logging
import os
from pathlib import Path

from ..config import McpServerCfg
from ..store import layout
from ..util.jsonx import read_json, write_json

logger = logging.getLogger("harness.mcp")

pass
_SECRET_HINTS = ("TOKEN", "KEY", "SECRET", "PASSWORD")

pass
GITHUB_TOKEN_VARS = ("GITHUB_TOKEN", "GITHUB_PERSONAL_ACCESS_TOKEN")


def is_placeholder(value) -> bool:
    return (isinstance(value, str) and value.startswith("${")
            and value.endswith("}") and len(value) > 3)


def lookup_env(name: str) -> str:
    v = os.environ.get(name, "")
    if v:
        return v
    if name in GITHUB_TOKEN_VARS:
        from ..github.client import token
        return token()
    return ""


def resolve_env(cfg: McpServerCfg) -> tuple[McpServerCfg, list[str]]:
    missing: list[str] = []

    def one(raw: str) -> str:
        if not is_placeholder(raw):
            return raw
        name = raw[2:-1]
        real = lookup_env(name)
        if not real:
            missing.append(name)
        return real

    out = cfg.model_copy(deep=True)
    out.env = {k: one(v) for k, v in (cfg.env or {}).items()}
    out.args = [one(a) for a in (cfg.args or [])]
    return out, missing


def effective(name: str, cfg: McpServerCfg) -> McpServerCfg:
    out, missing = resolve_env(cfg)
    if not out.enabled:
        out.disabled, out.disabled_reason = True, out.disabled_reason or "已手动停用"
    elif missing:
        out.disabled = True
        out.disabled_reason = "缺少环境变量 " + ", ".join(dict.fromkeys(missing))
    return out


def parse_servers(raw: dict, fallback: str = "") -> dict[str, McpServerCfg]:
    if not isinstance(raw, dict):
        return {}
    servers = raw.get("servers")
    items = servers if isinstance(servers, dict) else {fallback: raw}
    out: dict[str, McpServerCfg] = {}
    for name, body in items.items():
        if not isinstance(body, dict):
            continue
        key = str(body.get("name") or name or fallback).strip()
        if not key:
            continue
        try:
            out[key] = McpServerCfg(**body)
        except Exception as e:
            logger.warning("MCP 定义解析失败 %s: %s", key, e)
    return out


def load_file(path: Path) -> dict[str, McpServerCfg]:
    data = read_json(path, None)
    if data is None:
        return {}
    return parse_servers(data, path.stem)


def load_dir(directory: Path) -> dict[str, McpServerCfg]:
    out: dict[str, McpServerCfg] = {}
    if not directory.is_dir():
        return out
    for p in sorted(directory.glob("*.json")):
        if p.name.startswith("."):
            continue
        for name, cfg in load_file(p).items():
            out.setdefault(name, cfg)
    return out


def save_file(directory: Path, name: str, cfg: McpServerCfg) -> Path:
    body = cfg.model_dump()
    body["name"] = name
    path = directory / f"{name}.json"
    write_json(path, body)
    return path


def delete_file(directory: Path, name: str) -> bool:
    path = directory / f"{name}.json"
    if not path.is_file():
        return False
    path.unlink()
    return True


def global_servers() -> dict[str, McpServerCfg]:
    return load_dir(layout.mcp_dir())


def project_servers(project: str) -> dict[str, McpServerCfg]:
    from ..project import config as project_config
    return project_config.read_project_mcp(project)


def public(cfg: McpServerCfg) -> dict:
    from ..store import vault
    d = cfg.model_dump()
    d["env"] = {k: (vault.MASKED if any(h in k.upper() for h in _SECRET_HINTS)
                    and v and not is_placeholder(v) else v)
                for k, v in (cfg.env or {}).items()}
    d["headers"] = {k: (vault.MASKED if any(h in k.upper() for h in _SECRET_HINTS)
                        and v else v) for k, v in (cfg.headers or {}).items()}
    return d


def merge_masked(new: dict, old: McpServerCfg) -> dict:
    from ..store import vault
    body = dict(new)
    for field in ("env", "headers"):
        incoming = body.get(field) or {}
        previous = getattr(old, field, {}) or {}
        body[field] = {k: (previous.get(k, "") if v == vault.MASKED else v)
                       for k, v in incoming.items()}
    return body


def migrate_legacy_config(store=None) -> list[str]:
    path = layout.config_json()
    raw = read_json(path, None)
    if not isinstance(raw, dict) or "mcpServers" not in raw:
        return []
    legacy = raw.pop("mcpServers") or {}
    moved: list[str] = []
    target = layout.mcp_dir()
    for name, body in (legacy.items() if isinstance(legacy, dict) else []):
        if not isinstance(body, dict):
            continue
        cfg = McpServerCfg(**body)
        cfg, missing = resolve_env(cfg)
        for k, v in list((cfg.env or {}).items()):
            if any(h in k.upper() for h in _SECRET_HINTS) and v:
                if store is not None and k in GITHUB_TOKEN_VARS \
                        and not store.config.settings.githubToken:
                    store.config.settings.githubToken = v
                    moved.append(k)
                cfg.env[k] = "${GITHUB_TOKEN}" if k in GITHUB_TOKEN_VARS else v
        if not (target / f"{name}.json").is_file():
            save_file(target, str(name), cfg)
    pass
    backup = path.with_name(path.name + ".bak-mcp-migrate")
    if not backup.is_file():
        write_json(backup, {**raw, "mcpServers": legacy})
    write_json(path, raw)
    if store is not None and moved:
        store.save()
    logger.info("MCP 配置已迁移到 %s：%s", target, list(legacy) if isinstance(legacy, dict) else [])
    return list(legacy) if isinstance(legacy, dict) else []
