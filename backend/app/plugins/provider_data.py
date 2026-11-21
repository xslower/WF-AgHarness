from __future__ import annotations

from . import package as pkgmod


def plugin_presets(installs) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for rec in installs.list_plugins(""):
        try:
            pkg = pkgmod.load_package_from_text(rec.get("manifest") or "",
                                                rec.get("id") or "")
        except ValueError:
            continue
        for item in pkg.providers:
            pid = item.get("id") or ""
            if not pid or pid in seen:
                continue
            seen.add(pid)
            row = dict(item)
            row["source"] = f"plugin:{rec.get('id') or ''}"
            out.append(row)
    return out
