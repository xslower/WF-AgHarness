from __future__ import annotations


def providers(items) -> list[dict]:
    if not isinstance(items, list):
        return []
    out: list[dict] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        pid = str(it.get("id") or "").strip()
        if not pid:
            raise ValueError("providers 段每一项都必须有 id")
        row = {"id": pid, "name": str(it.get("name") or pid),
               "kind": str(it.get("kind") or "env_preset"),
               "base_url": str(it.get("base_url") or it.get("baseUrl") or ""),
               "env_keys": [str(k) for k in (it.get("env_keys") or it.get("envKeys") or [])],
               "notes": str(it.get("notes") or ""),
               "source": ""}
        for k in ("adapter", "filtered_import", "free_rules", "config_schema",
                  "daily_free_quota", "daily_refresh"):
            if k in it:
                row[k] = it[k]
        out.append(row)
    return out


def requested_provider_keys(items) -> list[str]:
    if not isinstance(items, list):
        return []
    out: list[str] = []
    for it in items:
        name = str(it).strip() if not isinstance(it, dict) else str(
            it.get("name") or it.get("provider") or "").strip()
        if not name:
            raise ValueError("requested_provider_keys 段每一项都要有 provider 名")
        if name not in out:
            out.append(name)
    return out


def outbound_switches(items) -> list[dict]:
    if not isinstance(items, list):
        return []
    out: list[dict] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        name = str(it.get("provider") or "").strip()
        if not name:
            raise ValueError("outbound_switches 段每一项都必须有 provider（provider 名）")
        out.append({"provider": name,
                    "setup": str(it.get("setup") or "switch"),
                    "handler": str(it.get("handler") or "handle")})
    return out
