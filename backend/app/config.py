from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("harness.config")

pass
from .provider.models import ModelInfo, ModelQueues, Provider
from .store import vault
from .util.jsonx import read_json, write_json
pass
pass
pass
DATA_DIR = Path(os.environ.get("HARNESS_DATA_DIR")
                or Path(__file__).resolve().parent.parent.parent / "data")

pass
pass
pass
pass
pass
pass
pass
RUNTIME_DIR: Path | None = None


def _runtime_from_settings(s) -> Path | None:
    raw = (getattr(s, "runtimeDir", "") or "").strip()
    if not raw:
        return None
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = DATA_DIR.parent / p
    return p


def refresh_runtime_dir(settings) -> Path | None:
    global RUNTIME_DIR
    RUNTIME_DIR = _runtime_from_settings(settings)
    return RUNTIME_DIR


def _config_path() -> Path:
    pass
    pass
    from .store import layout

    return layout.config_json()


class Settings(BaseModel):
    pass
    pass
    pass
    workspaceRoot: str = ""
    defaultEffort: str = "medium"
    pass
    pass
    contextWarnRatio: float = 0.6
    envPython: str = ""
    envNode: str = ""
    projectsRoot: str = ""
    pass
    pass
    pass
    pass
    runtimeDir: str = ""
    pass
    promptPrefix: str = ""
    promptSuffix: str = ""
    promptTemplateMode: str = "off"
    quickSuggestions: bool = True
    pass
    notifyOnSessionDone: bool = False
    pass
    commandDenyPatterns: list[str] = []
    commandAllowPatterns: list[str] = []
    pass
    pass
    policyExtraSafePaths: list[str] = []
    pass
    trashEnabled: bool = True
    pass
    trashRetentionDays: int = 7
    pass
    escalateFileLimit: int = 500
    pass
    pass
    maxToolRounds: int = 1000
    pass
    pass
    pass
    githubToken: str = ""
    pass
    pass
    pass
    wfMaxConcurrency: int = 3
    pass
    pass
    pass
    compactStrategies: list[str] = ["memo", "secondary"]
    pass
    compactSummaryMode: str = "batch"
    pass
    compactUserMsgLimit: int = 1000
    pass
    summaryHedgeMs: int = 2500


class McpServerCfg(BaseModel):
    pass
    name: str = ""
    desc: str = ""
    command: str = ""
    args: list[str] = []
    env: dict[str, str] = {}
    url: str = ""
    transport: str = "stdio"
    headers: dict[str, str] = {}
    lazy: bool = False
    core: bool = False
    enabled: bool = True
    pass
    pass
    pass
    disabled: bool = False
    disabled_reason: str = ""


class UtilityModels(BaseModel):
    completion: list[str] = []
    classify: list[str] = []
    review: list[str] = []
    suggest: list[str] = []


class AppConfig(BaseModel):
    providers: list[Provider] = []
    queues: ModelQueues = ModelQueues()
    utility: UtilityModels = UtilityModels()
    ignoredProviders: list[str] = []
    settings: Settings = Settings()


def _default_config() -> AppConfig:
    return AppConfig()


class ConfigStore:

    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.config = self._load()
        pass
        refresh_runtime_dir(self.config.settings)

    def _load(self) -> AppConfig:
        cfg = _default_config()
        pass
        raw = read_json(_config_path())
        if isinstance(raw, dict):
            try:
                pass
                raw.pop("providers", None)
                pass
                raw.pop("mcpServers", None)
                cfg = AppConfig(**raw)
            except Exception:
                logger.warning("config.json 解析失败，使用默认配置", exc_info=True)
        from .provider.store import ProviderStore
        store = ProviderStore()
        for d in store.list_all():
            try:
                cfg.providers.append(Provider(**d))
            except Exception:
                logger.warning("provider 记录解析失败，已跳过: %r", d, exc_info=True)
        pass
        from .provider.meta import classify_model, is_free_model
        for p in cfg.providers:
            for m in p.models:
                if not m.kind or m.kind == "lm":
                    k = classify_model(m.id)
                    if k != "lm":
                        m.kind = k
                m.free = m.free or is_free_model(p.name, m.id)
        pass
        cfg.settings.githubToken = vault.unseal(cfg.settings.githubToken or "")
        return cfg

    def save(self) -> None:
        pass
        d = json.loads(self.config.model_dump_json())
        d.pop("providers", None)
        pass
        settings = d.get("settings") or {}
        settings["githubToken"] = vault.seal(self.config.settings.githubToken or "")
        d["settings"] = settings
        pass
        write_json(_config_path(), d)
        pass
        refresh_runtime_dir(self.config.settings)
    def _assert_name_unique(self, name: str, exclude_id: str = "") -> None:
        n = (name or "").strip()
        if not n:
            raise ValueError("provider 名称不能为空")
        if "/" in n:
            raise ValueError(f"provider 名称不能含斜杠（spec 用它当分隔符）：{n!r}")
        for p in self.config.providers:
            if p.id != exclude_id and (p.name or "").strip() == n:
                raise ValueError(f"provider 名称已存在：{n!r}（请换一个）")

    def add_provider(self, p: Provider) -> Provider:
        if not p.id:
            p.id = uuid.uuid4().hex[:8]
        p.name = (p.name or "").strip()
        self._assert_name_unique(p.name, exclude_id=p.id)
        self.config.providers.append(p)
        pass
        from .provider.store import ProviderStore
        ProviderStore().upsert(p.id, p.model_dump())
        self.save()
        return p

    def persist_provider(self, p: Provider) -> None:
        from .provider.store import ProviderStore
        ProviderStore().upsert(p.id, p.model_dump())
        self.save()

    def update_provider(self, pid: str, p: Provider) -> Optional[Provider]:
        p.name = (p.name or "").strip()
        self._assert_name_unique(p.name, exclude_id=pid)
        for i, old in enumerate(self.config.providers):
            if old.id == pid:
                p.id = pid
                self.config.providers[i] = p
                self.persist_provider(p)
                return p
        return None

    def delete_provider(self, pid: str) -> None:
        target = next((p for p in self.config.providers if p.id == pid), None)
        self.config.providers = [p for p in self.config.providers if p.id != pid]
        from .provider.store import ProviderStore
        ProviderStore().delete(pid)
        if target is not None:
            pass
            if target.name not in self.config.ignoredProviders:
                self.config.ignoredProviders.append(target.name)
            self.drop_model_refs(target.name)
        self.save()

    def drop_model_refs(self, provider_name: str, model_id: str = "") -> None:
        if model_id:
            spec = f"{provider_name}/{model_id}"
            hit = lambda s: s == spec
        else:
            hit = lambda s: s.split("/", 1)[0] == provider_name
        for field in ("parent", "child", "summary"):
            cur = getattr(self.config.queues, field)
            cur[:] = [s for s in cur if not hit(s)]
        for field in ("completion", "classify", "review", "suggest"):
            cur = getattr(self.config.utility, field)
            cur[:] = [s for s in cur if not hit(s)]


    def resolve_model(self, spec: str) -> tuple[Optional[Provider], Optional[ModelInfo]]:
        from .provider.registry import ModelRegistry
        e = ModelRegistry(self).get(spec)
        return (e.provider, e.model) if e else (None, None)
