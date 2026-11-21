from __future__ import annotations

import re

pass
pass
ENV_PRESETS: list[dict] = [
    {"env_key": "OPENROUTER_API_KEY", "name": "openrouter", "base_url": "https://openrouter.ai/api/v1"},
    {"env_key": "SILICONFLOW_API_KEY", "name": "siliconflow", "base_url": "https://api.siliconflow.cn/v1"},
    {"env_key": "SILICONFLOW_API_KEY_2", "name": "siliconflow-2", "base_url": "https://api.siliconflow.cn/v1"},
    {"env_key": "DEEPSEEK_API_KEY", "name": "deepseek", "base_url": "https://api.deepseek.com/v1"},
    {"env_key": "MOONSHOT_API_KEY", "name": "moonshot", "base_url": "https://api.moonshot.cn/v1"},
    {"env_key": "GEMINI_API_KEY", "name": "gemini", "base_url": "https://generativelanguage.googleapis.com/v1beta/openai"},
    {"env_key": "GOOGLE_API_KEY", "name": "gemini", "base_url": "https://generativelanguage.googleapis.com/v1beta/openai"},
    {"env_key": "GROQ_API_KEY", "name": "groq", "base_url": "https://api.groq.com/openai/v1"},
    {"env_key": "TOGETHER_API_KEY", "name": "together", "base_url": "https://api.together.xyz/v1"},
    {"env_key": "DASHSCOPE_API_KEY", "name": "dashscope", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
    {"env_key": "SILIFLOW_KEY", "name": "siliconflow", "base_url": "https://api.siliconflow.cn/v1"},
    {"env_key": "OPENROUTER_KEY", "name": "openrouter", "base_url": "https://openrouter.ai/api/v1"},
    {"env_key": "BAIDU_KEY", "name": "qianfan", "base_url": "https://qianfan.baidubce.com/v2"},
    {"env_key": "QIANFAN_API_KEY", "name": "qianfan", "base_url": "https://qianfan.baidubce.com/v2"},
    {"env_key": "DOUBAO_KEY", "name": "ark", "base_url": "https://ark.cn-beijing.volces.com/api/v3"},
    {"env_key": "ARK_API_KEY", "name": "ark", "base_url": "https://ark.cn-beijing.volces.com/api/v3"},
    {"env_key": "ZHIPU_API_KEY", "name": "zhipu", "base_url": "https://open.bigmodel.cn/api/paas/v4"},
]


pass
pass
pass
PROVIDER_RULES: dict[str, dict] = {
    "siliconflow": {
        "import_mode": "free_ids",
        "free_ids": {
            "Qwen/Qwen3-8B", "Qwen/Qwen3.5-4B", "Qwen/Qwen2.5-7B-Instruct",
            "THUDM/GLM-4-9B-0414", "THUDM/GLM-Z1-9B-0414",
            "THUDM/GLM-4.1V-9B-Thinking",
            "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B",
            "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
            "deepseek-ai/DeepSeek-OCR",
            "tencent/Hunyuan-MT-7B",
            "PaddlePaddle/PaddleOCR-VL-1.5",
        },
        "filtered_import": True,
        "notes": "✓ 已按白名单只导入常驻免费模型（单价¥0，4B-9B 量级，多含 262K 上下文的 Qwen3-8B）；同名 Pro 版收费，注意区分。新用户 14 元代金券为一次性。",
    },
    "qianfan": {
        "import_pattern": r"ernie-(speed|lite|tiny)",
        "free_pattern": r"ernie-(speed|lite|tiny)",
        "filtered_import": True,
        "notes": "✓ ERNIE-Speed/Lite/Tiny 为长期免费档（QPS 上限 50）；ernie-4.5-turbo 系为收费（新用户额度到期后），未自动导入。",
    },
    "ark": {
        "import_pattern": r"^doubao-lite",
        "free_pattern": r"^doubao-lite",
        "filtered_import": True,
        "notes": "Doubao-Lite 每日免费 200 万 tokens（每日重置，部分模型 50 万/日）。⚠ 按模型名调用需先在火山控制台开通对应模型，否则 404；也可用 ep- 接入点 ID 作为模型名。",
    },
    "openrouter": {
        "import_pattern": r":free$",
        "free_pattern": r":free$",
        "filtered_import": True,
        "notes": "「:free」模型免费，但每日请求次数有限制。",
    },
}


def _compile(pattern: str | None) -> "re.Pattern | None":
    return re.compile(pattern, re.I) if pattern else None


pass
IMPORT_ONLY_PATTERNS: dict[str, "re.Pattern | None"] = {
    name: _compile(rule.get("import_pattern"))
    for name, rule in PROVIDER_RULES.items()
    if rule.get("import_pattern")
}

FREE_PATTERNS: dict[str, "re.Pattern"] = {
    name: _compile(rule["free_pattern"])
    for name, rule in PROVIDER_RULES.items()
    if rule.get("free_pattern")
}

SILICONFLOW_FREE_IDS = PROVIDER_RULES["siliconflow"]["free_ids"]

FILTERED_IMPORT = {name for name, rule in PROVIDER_RULES.items()
                   if rule.get("filtered_import")}

PROVIDER_NOTES: dict[str, str] = {name: rule["notes"]
                                  for name, rule in PROVIDER_RULES.items()
                                  if rule.get("notes")}


def _free_ids(name: str) -> set[str]:
    rule = PROVIDER_RULES.get(name) or {}
    return set(rule.get("free_ids") or ())


def import_filter(provider_name: str, mid: str) -> bool:
    rule = PROVIDER_RULES.get(provider_name)
    if rule is None:
        return True
    if rule.get("import_mode") == "free_ids":
        return mid in _free_ids(provider_name)
    pat = IMPORT_ONLY_PATTERNS.get(provider_name)
    return bool(pat and pat.search(mid))


def is_free_model(provider_name: str, mid: str) -> bool:
    rule = PROVIDER_RULES.get(provider_name)
    if rule is None:
        return False
    if rule.get("import_mode") == "free_ids":
        return mid in _free_ids(provider_name)
    pat = FREE_PATTERNS.get(provider_name)
    return bool(pat and pat.search(mid))


def preset_catalog() -> list[dict]:
    catalog: dict[str, dict] = {}
    for entry in ENV_PRESETS:
        name = entry["name"]
        if name in catalog:
            if entry["env_key"] not in catalog[name]["env_keys"]:
                catalog[name]["env_keys"].append(entry["env_key"])
            continue
        rule = PROVIDER_RULES.get(name) or {}
        catalog[name] = {
            "id": name,
            "name": name,
            "kind": "env_preset",
            "base_url": entry["base_url"],
            "env_keys": [entry["env_key"]],
            "notes": rule.get("notes", ""),
            "filtered_import": bool(rule.get("filtered_import")),
            "free_rules": {
                "free_ids": sorted(rule["free_ids"]) if rule.get("free_ids") else [],
                "free_pattern": rule.get("free_pattern", ""),
                "import_pattern": rule.get("import_pattern", ""),
            },
        }
    return list(catalog.values())
