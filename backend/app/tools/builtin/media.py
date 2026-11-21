from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import time
from typing import TYPE_CHECKING

from ...store import layout
from .. import cascade

logger = logging.getLogger("harness.tools.media")

if TYPE_CHECKING:
    from .. import ToolContext, ToolRegistry


def make_gen_image(gateway):
    async def gen_image(prompt: str, ctx: "ToolContext",
                        size: str = "1024x1024", n: int = 1,
                        model: str = "") -> str:
        async def system() -> str:
            if gateway is None:
                return json.dumps({"error": "生图服务不可用（未注入模型网关）"},
                                  ensure_ascii=False)
            result = await gateway.generate_image(prompt, spec=model, size=size, n=n)
            return json.dumps(result, ensure_ascii=False)

        return await cascade.run("gen_image",
                                 {"prompt": prompt, "size": size, "n": n,
                                  "model": model}, ctx, system)
    return gen_image


def make_asr(gateway):
    async def asr(file_path: str, ctx: "ToolContext",
                  language: str = "", model: str = "") -> str:
        async def system() -> str:
            if gateway is None:
                return json.dumps({"error": "ASR 服务不可用（未注入模型网关）"},
                                  ensure_ascii=False)
            result = await gateway.transcribe_audio(file_path, spec=model,
                                                    language=language)
            return json.dumps(result, ensure_ascii=False)

        return await cascade.run("asr",
                                 {"file_path": file_path, "language": language,
                                  "model": model}, ctx, system)
    return asr


def make_embed(gateway):
    async def embed(texts: list[str], ctx: "ToolContext", model: str = "") -> str:
        async def system() -> str:
            if gateway is None:
                return json.dumps({"error": "向量服务不可用（未注入模型网关）"},
                                  ensure_ascii=False)
            result = await gateway.embed(texts, spec=model)
            return json.dumps(result, ensure_ascii=False)

        return await cascade.run("embed",
                                 {"texts": texts, "model": model}, ctx, system)
    return embed


def make_ocr(gateway):
    async def ocr(file_path: str, ctx: "ToolContext",
                  prompt: str = "识别图片中的所有文字", model: str = "") -> str:
        async def system() -> str:
            if gateway is None:
                return json.dumps({"error": "OCR 服务不可用（未注入模型网关）"},
                                  ensure_ascii=False)
            result = await gateway.ocr_image(file_path, prompt=prompt, spec=model)
            return json.dumps(result, ensure_ascii=False)

        return await cascade.run("ocr",
                                 {"file_path": file_path, "prompt": prompt,
                                  "model": model}, ctx, system)
    return ocr


async def screenshot(ctx: "ToolContext", display: str = ":0") -> str:
    out_dir = layout.images_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"screenshot_{int(time.time())}.png"
    env = {**os.environ, "DISPLAY": display}

    for build in _SCREENSHOT_CMDS:
        if await asyncio.to_thread(_try_screenshot, build(out_path), out_path, env):
            size = out_path.stat().st_size
            return json.dumps({"path": str(out_path), "size": size},
                              ensure_ascii=False)

    return json.dumps({"error": "截图失败：未找到可用的截图工具（gnome-screenshot/scrot/import）或无 DISPLAY"},
                      ensure_ascii=False)


pass
_SCREENSHOT_CMDS = (
    lambda p: ["gnome-screenshot", "-f", str(p)],
    lambda p: ["scrot", str(p)],
    lambda p: ["import", "-window", "root", str(p)],
)


def _try_screenshot(argv: list[str], out_path, env: dict) -> bool:
    try:
        subprocess.run(argv, capture_output=True, timeout=10, env=env)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False
    try:
        return out_path.exists() and out_path.stat().st_size > 0
    except OSError:
        return False


async def system_info(ctx: "ToolContext") -> str:
    import platform
    info = {
        "os": platform.platform(),
        "python": platform.python_version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
    }
    info["cpu_count"] = os.cpu_count()
    try:
        with open("/proc/meminfo") as f:
            memlines = f.read()
        mem = {}
        for line in memlines.splitlines():
            parts = line.split(":")
            if len(parts) == 2:
                mem[parts[0].strip()] = parts[1].strip()
        info["memory"] = mem
    except OSError:
        logger.debug("读取 /proc/meminfo 失败", exc_info=True)
    try:
        disk = os.statvfs(ctx.cwd)
        info["disk"] = {
            "total": disk.f_blocks * disk.f_frsize,
            "free": disk.f_bavail * disk.f_frsize,
        }
    except OSError:
        logger.debug("statvfs 失败: %s", ctx.cwd, exc_info=True)
    return json.dumps(info, ensure_ascii=False)


def register(reg: "ToolRegistry", gateway=None) -> None:
    pass
    pass
    reg.register(
        "gen_image",
        "生成图片（文生图）。prompt 写画面描述；size 如 1024x1024；n 为张数（1-4）；"
        "model 可选（providerId/modelId，不传自动选 image 模型）。",
        {"prompt": {"type": "string", "description": "画面描述"},
         "size": {"type": "string", "description": "尺寸，如 1024x1024"},
         "n": {"type": "integer", "description": "生成张数 1-4，默认 1"},
         "model": {"type": "string", "description": "生图模型 spec，可选"}},
        make_gen_image(gateway), ["prompt"])
    reg.register(
        "asr",
        "语音识别（ASR）。file_path 为音频文件路径；language 可选（如 zh/en）；"
        "model 可选（providerId/modelId，不传自动选 asr 模型）。",
        {"file_path": {"type": "string", "description": "音频文件路径"},
         "language": {"type": "string", "description": "语言提示，如 zh/en，可选"},
         "model": {"type": "string", "description": "ASR 模型 spec，可选"}},
        make_asr(gateway), ["file_path"])
    reg.register(
        "ocr",
        "图片文字识别（OCR）。file_path 为图片路径；prompt 可选（识别要求，"
        "默认「识别图片中的所有文字」）；model 可选（不传自动选 kind=ocr 模型）。",
        {"file_path": {"type": "string", "description": "图片文件路径"},
         "prompt": {"type": "string", "description": "识别要求，可选"},
         "model": {"type": "string", "description": "OCR 模型 spec，可选"}},
        make_ocr(gateway), ["file_path"])
    reg.register(
        "embed",
        "文本向量化（embedding）。texts 为待向量化文本列表（单次建议 ≤64 条）；"
        "model 可选（providerId/modelId，不传自动选 kind=embedding 模型）。"
        "返回 model/dim/count；不同模型向量不可混用，后续检索必须用同一个 model。",
        {"texts": {"type": "array", "items": {"type": "string"},
                   "description": "待向量化的文本列表"},
         "model": {"type": "string",
                   "description": "向量模型 spec，可选（不传自动选 embedding 模型）"}},
        make_embed(gateway), ["texts"])
    reg.register(
        "screenshot",
        "截取屏幕截图，保存到 data/images/ 并返回路径。display 可选（默认 :0）",
        {"display": {"type": "string", "description": "X11 DISPLAY，默认 :0"}},
        screenshot, [])
    reg.register(
        "system_info",
        "获取系统信息（OS、CPU、内存、磁盘使用情况）",
        {}, system_info, [])
