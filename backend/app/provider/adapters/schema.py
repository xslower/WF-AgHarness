from __future__ import annotations

from ..presets import preset_catalog

KIND_SCHEMAS: list[dict] = [
    {
        "kind": "openai_compatible",
        "label": "OpenAI 兼容",
        "adapter": "openai-compatible",
        "fields": [
            {"key": "name", "label": "名称", "type": "text", "required": True},
            {"key": "baseUrl", "label": "Base URL", "type": "text", "required": True,
             "placeholder": "https://api.example.com/v1"},
            {"key": "apiKey", "label": "API Key", "type": "password", "required": True},
            {"key": "note", "label": "说明", "type": "text", "required": False},
            {"key": "dailyFreeQuota", "label": "免费每日上限(tokens)",
             "type": "number", "required": False},
            {"key": "models", "label": "模型列表", "type": "models", "required": False},
        ],
    },
    {
        "kind": "env_preset",
        "label": "环境变量预设",
        "adapter": "openai-compatible",
        "fields": [
            {"key": "presetId", "label": "预设", "type": "select", "required": True,
             "options": [p["id"] for p in preset_catalog()]},
            {"key": "apiKey", "label": "API Key（覆盖环境变量）",
             "type": "password", "required": False},
            {"key": "autoImport", "label": "导入时自动拉取模型",
             "type": "boolean", "required": False},
        ],
    },
]


def provider_schema(external_presets: list[dict] | None = None) -> dict:
    presets = preset_catalog()
    if external_presets:
        seen = {p["id"] for p in presets}
        presets += [p for p in external_presets if p.get("id") not in seen]
    return {"kinds": KIND_SCHEMAS, "presets": presets}
