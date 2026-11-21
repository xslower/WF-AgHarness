from __future__ import annotations

import app.tools.builtin.web.channels as channels
import app.tools.builtin.web.engines as engines
import app.tools.builtin.web.health as health
import app.tools.builtin.web.merge as merge
import app.tools.builtin.web.pacing as pacing
import app.tools.builtin.web.pagekind as pagekind
import app.tools.builtin.web.paths as paths
import app.tools.builtin.web.query as query
import app.tools.builtin.web.relevance as relevance
import app.tools.builtin.web.resolve as resolve
import app.tools.builtin.web.trust as trust
from .channels import (browser_session, detect_antibot, fetch_doc,
                       search_one_engine, search_one_page,
                       _fetch_html, _search_via_browser)
from .interact import interact_page
from .engines import BAIDU, BING, SOGOU, SO360, parse_wiki_json, select_engines
from .extract import _html_to_md
from .merge import content_key, merge_results, rank_results, select_top
from .open import _debug_opts, is_url, open_page, web_fetch
from .pagekind import is_blocked, is_dict, is_nav, is_noise
from .query import has_term, split
from .relevance import grade, judge, score_items, terms
from .resolve import enrich, remerge_by_real_url, resolve_many
from .tool import (WEB_SCHEMA, _SERP_MAX_ITEMS, _empty_result, _format_rows,
                   _is_tool_error, _label_sources, _parse_serp, crawl4ai_path,
                   drop_ads, ensure_crawl4ai, register, web_search_aggregate,
                   web_search_html)

__all__ = [
    "channels", "engines", "health", "merge", "pacing", "pagekind", "paths",
    "query", "relevance", "resolve", "trust",
    "WEB_SCHEMA", "register", "web_fetch", "open_page", "is_url", "_debug_opts",
    "web_search_aggregate", "web_search_html", "drop_ads", "ensure_crawl4ai",
    "crawl4ai_path", "interact_page", "_html_to_md", "fetch_doc",
    "split", "has_term", "is_nav", "is_dict", "is_noise", "is_blocked",
    "grade", "judge", "score_items", "terms", "select_top", "content_key",
]
