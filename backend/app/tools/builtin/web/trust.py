from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger("harness.web.trust")

pass
TIER1: list[str] = [
    "docs.python.org", "developer.mozilla.org", "nodejs.org", "reactjs.org",
    "react.dev", "vitejs.dev", "vite.dev", "fastapi.tiangolo.com",
    "typescriptlang.org", "rust-lang.org", "go.dev", "kubernetes.io",
    "github.com", "stackoverflow.com", "serverfault.com", "superuser.com",
    "microsoft.com", "learn.microsoft.com", "apache.org", "nginx.org",
    "postgresql.org", "redis.io", "docker.com", "sqlite.org", "gnu.org",
    "kernel.org", "llvm.org", "openjdk.org", "spring.io", "pypi.org",
    "npmjs.com", "developer.android.com", "apple.com", "w3.org",
    "mysql.com", "mongodb.com", "grafana.com",
    "prometheus.io", "rabbitmq.com", "kafka.apache.org", "cn.vuejs.org",
    "angular.io", "svelte.dev", "nextjs.org", "tailwindcss.com",
    "ant.design", "arco.design", "tencent.com", "cloud.tencent.com",
    "aliyun.com", "huaweicloud.com", "docs.github.com",
]

pass
TIER2: list[str] = [
    "zhihu.com", "segmentfault.com", "juejin.cn", "cnblogs.com",
    "51cto.com", "infoq.cn", "oschina.net", "wikipedia.org",
    "zh.wikipedia.org", "runoob.com", "w3school.com.cn", "liaoxuefeng.com",
    "developer.aliyun.com", "baeldung.com",
    "digitalocean.com", "habr.com", "dev.to", "medium.com",
    "jianshu.com", "gitee.com", "csdn.net",
    "stackoverflow.blog", "redis.com.cn", "php.net", "laravel.com",
]

pass
BLACKLIST: list[str] = [
    "360doc.com", "doc88.com", "docin.com", "book118.com", "renrendoc.com",
    "taodocs.com", "max.book118.com", "wenku.baidu.com", "ishare.iask.sina.com.cn",
    "doc.xuehai.net", "bookzzk.com", "koduko.com", "codingdict.com",
    "titanwolf.org", "exceptionshub.com", "code.i-harness.com",
    "qastack.cn", "qa.1r1g.com", "cn.voidcc.com", "codenong.com",
    "ubuntuqa.com", "itbaoku.cn", "kokoer.com", "gushiciku.cn",
    "developpaper.com", "thinbug.com", "stackoverflow.org.cn",
    "zhihuiya.com", "5axxw.com", "pythonjishu.com", "pythonjishu.cn",
]

pass
WATER_PATTERNS: list[str] = [
    r"十大.{0,6}品牌", r"品牌排行", r"哪个品牌好", r"品牌推荐",
    r"值得信赖的品牌", r"排行榜", r"十大排行", r"优选品牌",
    r"加盟.{0,4}靠谱", r"口碑榜", r"品牌网", r"选购指南", r"品牌测评",
    r"最新.{0,8}推荐榜", r"权威发布", r"震惊", r"惊呆", r"不看后悔",
]

_WATER_RE = [re.compile(p) for p in WATER_PATTERNS]


def _overrides_path() -> Path:
    from .paths import logs_dir

    return logs_dir() / "web_trust.json"


def _load_overrides() -> dict:
    p = _overrides_path()
    if not p.is_file():
        return {}
    try:
        raw = json.loads(p.read_text("utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"顶层必须是对象，收到 {type(raw).__name__}")
        return {k: set(v) for k, v in raw.items() if isinstance(v, list)}
    except Exception as e:
        logger.warning("web_trust.json 读取失败，用户分级未生效: %s: %s", p, e)
        return {}


def domain_of(url: str) -> str:
    m = re.match(r"^[a-z]+://([^/]+)", url or "")
    host = (m.group(1) if m else (url or "")).lower()
    host = host.split(":")[0]
    return host[4:] if host.startswith("www.") else host


def _host_match(host: str, entry: str) -> bool:
    return host == entry or host.endswith("." + entry)


def trust_tier(url: str) -> int:
    ov = _load_overrides()
    host = domain_of(url)
    full = (url or "").lower()
    if any(b in full or _host_match(host, b) for b in ov.get("blacklist", set())):
        return -1
    if any(b in full or _host_match(host, b) for b in ov.get("tier1", set())):
        return 2
    if any(b in full or _host_match(host, b) for b in ov.get("tier2", set())):
        return 1
    if any(_host_match(host, b) for b in BLACKLIST):
        return -1
    if any(_host_match(host, b) for b in TIER1):
        return 2
    if any(_host_match(host, b) for b in TIER2):
        return 1
    return 0


def is_water(title: str, snippet: str) -> bool:
    text = f"{title or ''} {snippet or ''}"
    return any(r.search(text) for r in _WATER_RE)


def annotate(results: list[dict]) -> list[dict]:
    out: list[dict] = []
    for r in results:
        url = r.get("url", "")
        tier = trust_tier(url)
        if tier == -1:
            continue
        water = is_water(r.get("title", ""), r.get("snippet", ""))
        if water and tier < 2:
            r["trust"] = "low"
        else:
            r["trust"] = {2: "high", 1: "medium", 0: "medium"}[tier]
        out.append(r)
    pass
    order = {"high": 0, "medium": 1, "low": 2}
    out.sort(key=lambda r: order.get(r.get("trust", "medium"), 1))
    return out
