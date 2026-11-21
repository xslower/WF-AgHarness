from __future__ import annotations

import json

from fastapi import APIRouter, Depends

from ...store import layout

router = APIRouter()


@router.get("/api/themes")
def themes_list():
    out: list[dict] = []
    for p in sorted(layout.themes_dir().glob("*.json")):
        try:
            data = json.loads(p.read_text("utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict):
            out.append({**data, "id": data.get("id") or p.stem,
                        "source": data.get("source") or "data/themes"})
    return {"themes": out}
