from __future__ import annotations

import logging
import re

logger = logging.getLogger("harness.tools.web.extract")


def _plain(html: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text)


def _html_to_md(html: str) -> str:
    try:
        import html2text
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.body_width = 0
        return h.handle(html)
    except Exception:
        logger.debug("html2text 提取失败，回退裸去标签", exc_info=True)
        return _plain(html)
