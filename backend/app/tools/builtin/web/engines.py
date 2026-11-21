from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, quote_plus, unquote, urlsplit


@dataclass(frozen=True)
class Engine:
    id: str
    label: str
    url: str
    sel: str = ""
    link_sel: str = "h3 a"
    title_sel: str = ""
    step: int = 10
    param: str = "pn"
    start: int = 0
    kind: str = "html"
    browser_ok: bool = True
    pace: bool = False
    alts: tuple = ()

    def page_url(self, query: str, page: int) -> str:
        if self.kind == "wiki":
            return _wiki_url(query, page)
        base = self.url.replace("{q}", quote_plus(query))
        if page <= 1:
            return base
        if self.param == "page":
            return f"{base}&page={page}"
        val = self.start + self.step * (page - 1)
        return f"{base}&{self.param}={val}"


pass
WIKI_PAGE_SIZE = 5


def _wiki_url(query: str, page: int = 1) -> str:
    q = quote_plus(query)
    offset = WIKI_PAGE_SIZE * max(0, page - 1)
    return ("https://zh.wikipedia.org/w/api.php?action=query&format=json"
            f"&generator=search&gsrsearch={q}&gsrlimit={WIKI_PAGE_SIZE}"
            f"&gsroffset={offset}&prop=extracts"
            "&exintro=1&explaintext=1&exlimit=max")


BAIDU = Engine(
    id="baidu", label="百度",
    url="https://www.baidu.com/s?wd={q}", sel="div.result, div.c-container",
    param="pn", start=0, step=10,
)
pass
pass
pass
pass
SOGOU_WEIXIN = Engine(
    id="sogou", label="搜狗",
    url="https://weixin.sogou.com/weixin?query={q}&type=2",
    sel="ul.news-list li", link_sel="h3 a",
    param="page", start=1, browser_ok=False, pace=True,
)
SOGOU = Engine(
    id="sogou", label="搜狗",
    url="https://www.sogou.com/web?query={q}", sel="div.vrwrap, div.rb",
    param="page", start=1, browser_ok=False, pace=True,
    alts=(SOGOU_WEIXIN,),
)
pass
pass
pass
pass
SO360_MOBILE = Engine(
    id="so360", label="360",
    url="https://m.so.com/s?q={q}", sel="div.res-list",
    link_sel="a.alink", title_sel="h3",
    param="pn", start=1, step=1, browser_ok=False, pace=True,
)
SO360 = Engine(
    id="so360", label="360",
    url="https://www.so.com/s?q={q}", sel="li.res-list",
    link_sel="h3 a",
    param="pn", start=1, step=1, browser_ok=False, pace=True,
    alts=(SO360_MOBILE,),
)
BING = Engine(
    id="bing", label="Bing",
    url="https://www.bing.com/search?q={q}", sel="li.b_algo", link_sel="h2 a",
    param="first", start=1, step=10,
)
WIKI = Engine(id="wiki", label="维基百科", url="", kind="wiki")

pass
pass
pass
pass
DEFAULT_ENGINES: tuple[Engine, ...] = (BAIDU, BING, SOGOU, SO360)

ALL_ENGINES: dict[str, Engine] = {e.id: e for e in
                                 (BAIDU, SOGOU, SO360, BING, WIKI)}


def select_engines(names: list[str] | None) -> list[Engine]:
    if not names:
        return list(DEFAULT_ENGINES)
    out: list[Engine] = []
    for n in names:
        e = ALL_ENGINES.get((n or "").strip().lower())
        if e is not None and e not in out:
            out.append(e)
    return out or list(DEFAULT_ENGINES)


def parse_wiki_json(raw: str) -> list[dict]:
    import json as _json

    try:
        data = _json.loads(raw or "{}")
    except ValueError:
        return []
    pages = ((data.get("query") or {}).get("pages") or {})
    rows: list[dict] = []
    pass
    for page in sorted(pages.values(), key=lambda p: p.get("index", 999)):
        title = (page.get("title") or "").strip()
        if not title:
            continue
        extract = (page.get("extract") or "").strip().replace("\n", " ")
        rows.append({
            "title": title,
            "url": "https://zh.wikipedia.org/wiki/"
                   + quote_plus(title.replace(" ", "_")),
            "snippet": extract[:300],
        })
    return rows


def unwrap_jump_url(url: str) -> str:
    try:
        q = parse_qs(urlsplit(url or "").query)
    except ValueError:
        return ""
    for key in ("u", "url", "target"):
        vals = q.get(key) or []
        if vals:
            real = unquote(vals[0]).strip()
            if real.startswith(("http://", "https://")):
                return real
    return ""
