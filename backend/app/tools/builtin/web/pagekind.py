from __future__ import annotations

import re
from urllib.parse import urlsplit

pass
_NAV_PATH = re.compile(
    r"^/?(index\.html?|index\.php)?$"
    r"|/(login|signin|sign_in|signup|sign-up|register|download|downloads)"
    r"(/|\.|$)",
    re.I,
)

pass
_SHALLOW_DEPTH = 1

pass
_DICT_HOSTS = (
    "baike.baidu.com", "zhidao.baidu.com", "baike.so.com", "baike.sogou.com",
    "dict.baidu.com", "dict.youdao.com", "iciba.com", "eudic.net",
    "koolearn.com", "hanyu.baidu.com", "zdic.net", "cidian.",
    "wikipedia.org/wiki/", "zh.wikipedia.org/wiki/", "shuxuele.com",
    "w3school.com.cn/tags/", "runoob.com/tags/",
)

pass
_DICT_TITLE = re.compile(
    r"是什么意思|怎么读|的翻译|读音|音标|词组|拼音|部首|笔顺|字义|词义"
    r"|_百度百科|百科$|词典|汉典|汉语国学|新华字典",
)

pass
pass
pass
_BLOCKED_URL = (
    "antispider", "captcha", "verify", "unusual_traffic", "/sorry/",
    "security-check", "security_check", "accessdenied", "access-denied",
    "rate-limit", "ratelimit",
)

pass
_MIN_TITLE = 10


def _host_path(url: str) -> tuple[str, str]:
    try:
        p = urlsplit(url or "")
    except ValueError:
        return "", ""
    host = (p.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host, p.path or "/"


def is_nav(url: str, title: str = "") -> bool:
    host, path = _host_path(url)
    if not host:
        return False
    depth = len([p for p in path.split("/") if p])
    if depth <= _SHALLOW_DEPTH and _NAV_PATH.search(path):
        return True
    if depth == 0:
        return True
    if len((title or "").strip()) <= _MIN_TITLE and depth <= _SHALLOW_DEPTH:
        return True
    return False


def is_dict(url: str, title: str = "") -> bool:
    low = (url or "").lower()
    if any(h in low for h in _DICT_HOSTS):
        return True
    return bool(_DICT_TITLE.search(title or ""))


def is_blocked(url: str) -> bool:
    low = (url or "").lower()
    return any(k in low for k in _BLOCKED_URL)


def is_noise(url: str, title: str = "") -> bool:
    return is_nav(url, title) or is_dict(url, title) or is_blocked(url)
