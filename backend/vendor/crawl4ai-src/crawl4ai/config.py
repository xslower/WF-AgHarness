import os
from dotenv import load_dotenv

load_dotenv()

pass
DEFAULT_PROVIDER = "openai/gpt-4o"
DEFAULT_PROVIDER_API_KEY = "OPENAI_API_KEY"
MODEL_REPO_BRANCH = "new-release-0.0.2"
pass
PROVIDER_MODELS = {
    "ollama/llama3": "no-token-needed",
    "groq/llama3-70b-8192": os.getenv("GROQ_API_KEY"),
    "groq/llama3-8b-8192": os.getenv("GROQ_API_KEY"),
    "openai/gpt-4o-mini": os.getenv("OPENAI_API_KEY"),
    "openai/gpt-4o": os.getenv("OPENAI_API_KEY"),
    "openai/o1-mini": os.getenv("OPENAI_API_KEY"),
    "openai/o1-preview": os.getenv("OPENAI_API_KEY"),
    "openai/o3-mini": os.getenv("OPENAI_API_KEY"),
    "openai/o3-mini-high": os.getenv("OPENAI_API_KEY"),
    "anthropic/claude-3-haiku-20240307": os.getenv("ANTHROPIC_API_KEY"),
    "anthropic/claude-3-opus-20240229": os.getenv("ANTHROPIC_API_KEY"),
    "anthropic/claude-3-sonnet-20240229": os.getenv("ANTHROPIC_API_KEY"),
    "anthropic/claude-3-5-sonnet-20240620": os.getenv("ANTHROPIC_API_KEY"),
    "gemini/gemini-pro": os.getenv("GEMINI_API_KEY"),
    'gemini/gemini-1.5-pro': os.getenv("GEMINI_API_KEY"),
    'gemini/gemini-2.0-flash': os.getenv("GEMINI_API_KEY"),
    'gemini/gemini-2.0-flash-exp': os.getenv("GEMINI_API_KEY"),
    'gemini/gemini-2.0-flash-lite-preview-02-05': os.getenv("GEMINI_API_KEY"),
    "deepseek/deepseek-chat": os.getenv("DEEPSEEK_API_KEY"),
}
PROVIDER_MODELS_PREFIXES = {
    "ollama": "no-token-needed",
    "groq": os.getenv("GROQ_API_KEY"),
    "openai": os.getenv("OPENAI_API_KEY"),
    "anthropic": os.getenv("ANTHROPIC_API_KEY"),
    "gemini": os.getenv("GEMINI_API_KEY"),
    "deepseek": os.getenv("DEEPSEEK_API_KEY"),
    "bedrock": None,
}

pass
CHUNK_TOKEN_THRESHOLD = 2**11
OVERLAP_RATE = 0.1
WORD_TOKEN_RATE = 1.3

pass
MIN_WORD_THRESHOLD = 1
IMAGE_DESCRIPTION_MIN_WORD_THRESHOLD = 1

IMPORTANT_ATTRS = ["src", "href", "alt", "title", "width", "height", "class", "id", "rowspan", "colspan"]
ONLY_TEXT_ELIGIBLE_TAGS = [
    "b",
    "i",
    "u",
    "span",
    "del",
    "ins",
    "sub",
    "sup",
    "strong",
    "em",
    "code",
    "kbd",
    "var",
    "s",
    "q",
    "abbr",
    "cite",
    "dfn",
    "time",
    "small",
    "mark",
]
SOCIAL_MEDIA_DOMAINS = [
    "facebook.com",
    "twitter.com",
    "x.com",
    "linkedin.com",
    "instagram.com",
    "pinterest.com",
    "tiktok.com",
    "snapchat.com",
    "reddit.com",
]

pass
pass
pass
pass
pass
pass
pass
pass
IMAGE_SCORE_THRESHOLD = 2

MAX_METRICS_HISTORY = 1000

NEED_MIGRATION = True
URL_LOG_SHORTEN_LENGTH = 30
SHOW_DEPRECATION_WARNINGS = True
SCREENSHOT_HEIGHT_TRESHOLD = 10000
PAGE_TIMEOUT = 60000
DOWNLOAD_PAGE_TIMEOUT = 60000

pass
HTML_EXAMPLE_DELIMITER = "=== HTML EXAMPLE {index} ==="

pass
USER_SETTINGS = {
    "DEFAULT_LLM_PROVIDER": {
        "default": "openai/gpt-4o",
        "description": "Default LLM provider in 'company/model' format (e.g., 'openai/gpt-4o', 'anthropic/claude-3-sonnet')",
        "type": "string"
    },
    "DEFAULT_LLM_PROVIDER_TOKEN": {
        "default": "",
        "description": "API token for the default LLM provider",
        "type": "string",
        "secret": True
    },
    "VERBOSE": {
        "default": False,
        "description": "Enable verbose output for all commands",
        "type": "boolean"
    },
    "BROWSER_HEADLESS": {
        "default": True,
        "description": "Run browser in headless mode by default",
        "type": "boolean"
    },
    "BROWSER_TYPE": {
        "default": "chromium",
        "description": "Default browser type (chromium or firefox)",
        "type": "string",
        "options": ["chromium", "firefox"]
    },
    "CACHE_MODE": {
        "default": "bypass",
        "description": "Default cache mode (bypass, use, or refresh)",
        "type": "string",
        "options": ["bypass", "use", "refresh"]
    },
    "USER_AGENT_MODE": {
        "default": "default",
        "description": "Default user agent mode (default, random, or mobile)",
        "type": "string",
        "options": ["default", "random", "mobile"]
    },
    "JSON_ENSURE_ASCII": {
        "default": True,
        "description": "Whether to escape non-ASCII characters in JSON output (False preserves Unicode like 'š', True escapes as '\\u0161')",
        "type": "boolean"
    }
}
