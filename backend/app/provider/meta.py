from __future__ import annotations

import re

from .models import ModelInfo
from .presets import is_free_model


pass

IMAGE_PAT = re.compile(
    r"flux|stable-?diffusion|^sd[1-3x]|^sdxl|cogview|dall-?e|hunyuan-image|"
    r"seedream|wanx|kolors|sora|video-|hunyuan-video|wan2|image-?gen|"
    r"pic-?generator|diffusers|playground-v|ideogram|recraft|grok-?image|"
    r"z-?image|qwen-?image|image-?edit", re.I)
ASR_PAT = re.compile(
    r"whisper|asr|speech|tts|voice|sensevoice|paraformer|cosyvoice|"
    r"f5-?tts|fish-?audio|audio|bark|silero|realtime-?voice", re.I)
EMBED_PAT = re.compile(
    r"embedding|embed|bge|m3e|text-?embed|gte-|jina-|clip|rerank|"
    r"sparse-|dense-|conan-embedding", re.I)


def classify_model(mid: str) -> str:
    if re.search(r"ocr", mid, re.I):
        return "ocr"
    if re.search(r"-mt\b|hunyuan-mt|translat|translation", mid, re.I):
        return "mt"
    if IMAGE_PAT.search(mid):
        return "image"
    if EMBED_PAT.search(mid):
        return "embedding"
    if ASR_PAT.search(mid):
        return "asr"
    return "lm"


pass

MODEL_DESCRIPTIONS: list[tuple[str, str]] = [
    # OpenAI 系
    (r"^gpt-4o", "OpenAI 旗舰多模态，图文输入"),
    (r"^gpt-4\.1", "OpenAI 长上下文编码增强"),
    (r"^o[134]", "OpenAI 推理模型，深度思考"),
    (r"^gpt-4", "OpenAI 上代旗舰"),
    (r"dall-?e", "OpenAI 文生图"),
    (r"whisper", "OpenAI 语音识别"),
    (r"text-embedding", "OpenAI 文本向量"),
    # Anthropic / Google
    (r"^claude", "Anthropic Claude，长文与代码强"),
    (r"^gemini", "Google 多模态，超长上下文"),
    (r"^gemma", "Google 开源轻量模型"),
    # Meta / Mistral
    (r"^llama-?3", "Meta 开源，通用对话"),
    (r"^llama-?4", "Meta 最新开源多模态"),
    (r"mistral|mixtral", "Mistral 欧系，性价比高"),
    # 国产 LM
    (r"deepseek.*r", "DeepSeek 推理模型，数学/代码强"),
    (r"deepseek.*v", "DeepSeek 通用对话，性价比标杆"),
    (r"^glm-5\.3-flash", "智谱 GLM 5.3 轻量快速版"),
    (r"^glm-?[456]", "智谱 GLM，中英双语与代码"),
    (r"^qwen3", "通义千问 3 代，支持思考模式"),
    (r"^qwen.*(max|plus|turbo)", "通义千问在线版，按档位分速度"),
    (r"^qwen2\.5|qwen2", "通义千问 2.5 开源系"),
    (r"qvq", "通义视觉推理模型"),
    (r"^kimi|moonshot", "月之暗面 Kimi，超长文本"),
    (r"hunyuan-?(image|video|pic)", "腾讯混元生图/生视频"),
    (r"^hunyuan(-|turbo|standard|lite)", "腾讯混元通用对话"),
    (r"^minimax", "MiniMax，长上下文与语音见长"),
    (r"^abab", "MiniMax 对话模型旧系"),
    (r"^step-?[123]", "阶跃星辰 Step 系列"),
    (r"^ernie", "百度文心一言"),
    (r"^doubao", "字节豆包"),
    (r"^yi-?", "零一万物 Yi 系列"),
    (r"^baichuan", "百川对话模型"),
    (r"^spark", "讯飞星火"),
    (r"^internlm", "书生浦语，学术向"),
    (r"^aquila", "智源开源"),
    (r"mimo", "小米 MiMo，轻量推理"),
    (r"nemotron", "NVIDIA Nemotron 开源系"),
    (r"flint", "Flint 通用对话"),
    (r"^hy[34]", "HY 系列对话模型"),
    (r"big-?pickle|space-?bunny", "别名/中转模型"),
    # 多模态/视觉
    (r"^-?vl$|-vl-|vision|internvl|minicpm-v|cogvlm|GLM-4V|qvq",
     "视觉语言模型，看图理解"),
    # 生图/视频
    (r"flux", "Black Forest Labs 文生图，写实强"),
    (r"stable-?diffusion|^sd", "SD 系文生图"),
    (r"seedream|seededit", "字节即梦生图系"),
    (r"kolors", "快手可图文生图"),
    (r"wanx|wan2", "通义万相生图/生视频"),
    (r"cogview", "智谱文生图"),
    (r"sora|hunyuan-video|video-", "视频生成"),
    (r"ideogram", "Ideogram 文字渲染生图"),
    (r"recraft", "Recraft 矢量/设计生图"),
    # 向量/语音
    (r"bge", "智源 BGE 向量/检索"),
    (r"gte", "通义 GTE 向量"),
    (r"m3e", "M3E 中文向量"),
    (r"jina-embed", "Jina 向量，多语"),
    (r"rerank", "重排序模型，检索精排"),
    (r"clip", "图文对齐向量"),
    (r"sensevoice", "阿里语音识别，多语"),
    (r"paraformer", "阿里语音识别"),
    (r"cosyvoice", "阿里语音合成"),
    (r"fun-?asr|funasr", "阿里 FunASR 语音识别"),
    # 兜底
    (r"embed", "文本向量模型"),
    (r"reranker", "重排序模型"),
]


pass

pass
_CONTEXT_FAMILIES: list[tuple[str, int]] = [
    (r"qwen3-8b", 262_144),
    (r"-(0\.6|1\.7|4|7|8|9)b\b", 32_768),
    (r"-vl-|omni|captioner", 32_768),
    (r"embedding|reranker|bge", 8_192),
    (r"-32k", 32_768),
    (r"-128k", 131_072),
    (r"-256k", 262_144),
    (r"-1m", 1_000_000),
    (r"deepseek", 131_072),
    (r"glm-?[456]", 131_072),
    (r"kimi|moonshot", 131_072),
    (r"ernie", 131_072),
    (r"qwen", 131_072),
    (r"longcat|ling-|step-|minimax|xingchen|hy[34]|hunyuan|nemotron|flint|mimo",
     131_072),
]


def guess_context(mid: str) -> int:
    low = mid.lower()
    pass
    m = re.search(r"-(\d+)(k|m)\b", low)
    if m:
        n = int(m.group(1))
        return n * 1024 if m.group(2) == "k" else n * 1_000_000
    for pat, size in _CONTEXT_FAMILIES:
        if re.search(pat, low):
            return size
    return 65_536


def describe_model(mid: str) -> str:
    for pat, desc in MODEL_DESCRIPTIONS:
        if re.search(pat, mid, re.I):
            return desc
    return ""


pass

def make_model(mid: str, wire: str = "", *, free: bool = False,
               kind: str = ""):
    k = kind or classify_model(mid)
    return ModelInfo(
        id=mid, wireId=wire or "", kind=k, free=free,
        # 只有语言模型谈上下文长度；生图/ASR/向量给 1M 会让 UI 显成巨型上下文
        contextLength=guess_context(mid) if k == "lm" else 1_000_000,
    )
