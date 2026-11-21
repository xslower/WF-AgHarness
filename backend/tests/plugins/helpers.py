from __future__ import annotations

import json
from pathlib import Path

import yaml


def mk_project(root: Path, name: str = "proj") -> Path:
    p = root / name
    (p / ".agent").mkdir(parents=True, exist_ok=True)
    return p


def mk_package(proj: Path, *, pid: str = "demo",
               kinds=("workflow",), files: dict | None = None,
               providers=None, config=None, entry=None, mode="release",
               tool_scope="system") -> Path:
    pkg = proj / ".agent" / "plugins" / pid
    pkg.mkdir(parents=True, exist_ok=True)
    manifest = {"id": pid, "name": pid, "version": "1.0.0",
                "kinds": list(kinds), "mode": mode}
    if entry is not None:
        manifest["entry"] = entry
    if providers is not None:
        manifest["providers"] = providers
    if config is not None:
        manifest["config"] = config
    payload = files if files is not None else {
        "workflows/a.json": json.dumps({"name": "a", "nodes": []})}
    tool_names = [Path(rel).stem for rel in payload
                  if rel.startswith("tools/") and rel.endswith(".py")]
    if tool_names:
        manifest["tools"] = [{"name": n, "scope": tool_scope} for n in tool_names]
    (pkg / "plugin.yaml").write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), "utf-8")
    for rel, content in payload.items():
        f = pkg / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            f.write_bytes(content)
        else:
            f.write_text(content, "utf-8")
    return pkg


HANDLER_SRC = '''
async def handle(req, host):
    if req["path"] == "/echo":
        return {"method": req["method"], "query": req["query"],
                "json": req["json"]}
    if req["path"] == "/cfg":
        return {"api_base": host.config("api_base")}
    if req["path"] == "/data":
        return {"value": host.data.get("progress")}
    if req["path"] == "/save":
        host.data.set("progress", host.json(req).get("progress"))
        return {"saved": True}
    if req["path"] == "/boom":
        raise RuntimeError("插件自己炸了")
    if req["path"] == "/status":
        return 418, {"teapot": True}
    if req["path"] == "/stream":
        async def gen():
            yield b"data: one\\n\\n"
            yield b"data: two\\n\\n"
        return gen()
    return 404, {"error": "no route"}
'''


def api_package(proj: Path, pid: str = "demo", cfg=None) -> Path:
    pkg = mk_package(proj, pid=pid, kinds=("api",), files={
        "api/router.py": HANDLER_SRC,
        "index.html": ("<html><head></head><body>"
                       "<a href='{{base}}&static=page.html'>go</a>"
                       "<script src='{{base}}&static=res/app.js'></script>"
                       "</body></html>"),
        "page.html": "<html>page {{id}}</html>",
        "res/app.js": "var p = window.plugin || {};",
        "res/pic.bin": b"\x00\x01\x02",
    }, config=cfg, entry="index.html")
    return pkg


TOOL_SRC = '''
def register(reg):
    reg.tool("demo_tool", "演示工具", {"x": {"type": "string"}}, run)

def run(x: str = "", ctx=None):
    return "demo:" + x
'''


def tool_package(proj: Path, pid: str = "demo", src: str = TOOL_SRC) -> Path:
    return mk_package(proj, pid=pid, kinds=("tool",),
                      files={"tools/my_tool.py": src})
