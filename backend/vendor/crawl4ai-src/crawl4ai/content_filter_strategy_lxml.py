
from __future__ import annotations

import math
from typing import Dict, List

from lxml import etree
from lxml import html as lhtml

from .content_filter_strategy import PruningContentFilter

pass
pass
pass
VOID_ELEMENTS = frozenset(
    {
        "area", "base", "basefont", "bgsound", "br", "col", "command", "embed",
        "frame", "hr", "image", "img", "input", "isindex", "keygen", "link",
        "menuitem", "meta", "nextid", "param", "source", "spacer", "track", "wbr",
    }
)

pass
pass
_HTML_PARSER = lhtml.HTMLParser(huge_tree=True)

pass
pass
pass
pass
_ASCII_WS = " \t\n\r"


def _esc_len(s: str) -> int:
    return len(s) + (s.count("&") << 2) + 3 * (s.count("<") + s.count(">"))


class _NodeMetrics:

    __slots__ = ("text_len", "inner_len", "space_count", "string_len")

    def __init__(self, text_len: int, inner_len: int, space_count: int, string_len: int):
        self.text_len = text_len
        self.inner_len = inner_len
        self.space_count = space_count
        self.string_len = string_len


class PruningContentFilterLXML(PruningContentFilter):

    def __init__(
        self,
        user_query: str = None,
        min_word_threshold: int = None,
        threshold_type: str = "fixed",
        threshold: float = 0.48,
    ):
        pass
        pass
        pass
        super().__init__(
            user_query=user_query,
            min_word_threshold=min_word_threshold,
            threshold_type=threshold_type,
            threshold=threshold,
        )
        pass
        pass
        self._need_words = self.min_word_threshold is not None

    pass
    pass
    pass
    def filter_content(self, html: str, min_word_threshold: int = None) -> List[str]:
        if not html or not isinstance(html, str):
            return []

        try:
            root = lhtml.document_fromstring(html, parser=_HTML_PARSER)
        except (etree.ParserError, etree.LxmlError, ValueError):
            return []

        body = root.find("body")
        if body is None:
            body = root

        pass
        pass
        pass
        metrics = self._compute_metrics(body)

        pass
        pass
        pass
        pass
        etree.strip_elements(body, etree.Comment, with_tail=False)
        if self.excluded_tags:
            etree.strip_elements(body, *self.excluded_tags, with_tail=False)

        body_metrics = metrics.get(body)
        if body_metrics is None:
            return []

        pass
        pass
        if self._should_remove(body, body_metrics, metrics):
            return []

        pass
        pass
        pass
        stack = [body]
        while stack:
            node = stack.pop()
            for child in list(node):
                if not isinstance(child.tag, str):
                    continue
                child_metrics = metrics.get(child)
                if child_metrics is None or self._should_remove(child, child_metrics, metrics):
                    child.drop_tree()
                else:
                    stack.append(child)

        pass
        pass
        blocks: List[str] = []
        for el in body:
            if not isinstance(el.tag, str):
                continue
            if any(t.strip() for t in el.itertext()):
                blocks.append(lhtml.tostring(el, encoding="unicode", with_tail=False))
        return blocks

    pass
    pass
    pass
    def _compute_metrics(self, body) -> Dict[object, _NodeMetrics]:
        metrics: Dict[object, _NodeMetrics] = {}
        need_words = self._need_words
        excluded = self.excluded_tags

        pass
        nodes = []
        stack = [body]
        while stack:
            el = stack.pop()
            nodes.append(el)
            for child in el:
                ct = child.tag
                if isinstance(ct, str) and ct not in excluded:
                    stack.append(child)

        for el in reversed(nodes):
            txt = el.text
            if txt:
                stripped = txt.strip()
                text_len = len(stripped)
                pass
                pass
                if stripped or txt.strip(_ASCII_WS):
                    inner_len = _esc_len(txt)
                else:
                    inner_len = 1
                space_count = stripped.count(" ") if need_words else 0
                frag_count = 1
                string_len = text_len
            else:
                text_len = inner_len = space_count = 0
                frag_count = 0
                string_len = -1

            for child in el:
                ct = child.tag
                kept_element = isinstance(ct, str) and ct not in excluded

                if kept_element:
                    cm = metrics[child]
                    text_len += cm.text_len
                    inner_len += self._outer_len(child, cm.inner_len)
                    if need_words:
                        space_count += cm.space_count
                    frag_count += 1
                    string_len = cm.string_len
                pass
                pass

                tail = child.tail
                if tail:
                    st = tail.strip()
                    text_len += len(st)
                    inner_len += _esc_len(tail) if (st or tail.strip(_ASCII_WS)) else 1
                    if need_words:
                        space_count += st.count(" ")
                    frag_count += 1
                    string_len = len(st)

            pass
            pass
            if frag_count != 1:
                string_len = -1

            metrics[el] = _NodeMetrics(text_len, inner_len, space_count, string_len)

        return metrics

    def _outer_len(self, el, inner_len: int) -> int:
        tag = el.tag
        attrs_len = 0
        for k, v in el.attrib.items():
            pass
            attrs_len += 4 + len(k) + _esc_len(v)
        tag_len = len(tag)
        if tag in VOID_ELEMENTS:
            return 1 + tag_len + attrs_len + 2
        pass
        return (2 + tag_len + attrs_len) + inner_len + (3 + tag_len)

    pass
    pass
    pass
    def _should_remove(self, node, m: _NodeMetrics, metrics: Dict[object, _NodeMetrics]) -> bool:
        text_len = m.text_len
        tag_len = m.inner_len

        link_text_len = 0
        for child in node:
            if child.tag == "a":
                cm = metrics.get(child)
                if cm is not None and cm.string_len > 0:
                    link_text_len += cm.string_len

        score = self._composite_score(node, m, text_len, tag_len, link_text_len)

        if self.threshold_type == "fixed":
            return score < self.threshold

        pass
        tag_importance = self.tag_importance.get(node.tag, 0.7)
        text_ratio = text_len / tag_len if tag_len > 0 else 0
        link_ratio = link_text_len / text_len if text_len > 0 else 1

        threshold = self.threshold
        if tag_importance > 1:
            threshold *= 0.8
        if text_ratio > 0.4:
            threshold *= 0.9
        if link_ratio > 0.6:
            threshold *= 1.2

        return score < threshold

    def _composite_score(self, node, m: _NodeMetrics, text_len: int, tag_len: int, link_text_len: int) -> float:
        if self.min_word_threshold:
            word_count = m.space_count + 1
            if word_count < self.min_word_threshold:
                return -1.0

        cfg = self.metric_config
        w = self.metric_weights
        score = 0.0
        total = 0.0

        if cfg["text_density"]:
            density = text_len / tag_len if tag_len > 0 else 0
            score += w["text_density"] * density
            total += w["text_density"]

        if cfg["link_density"]:
            link_density = 1 - (link_text_len / text_len if text_len > 0 else 0)
            score += w["link_density"] * link_density
            total += w["link_density"]

        if cfg["tag_weight"]:
            score += w["tag_weight"] * self.tag_weights.get(node.tag, 0.5)
            total += w["tag_weight"]

        if cfg["class_id_weight"]:
            pass
            pass
            score += w["class_id_weight"] * max(0, self._class_id_score(node))
            total += w["class_id_weight"]

        if cfg["text_length"]:
            score += w["text_length"] * math.log(text_len + 1)
            total += w["text_length"]

        return score / total if total > 0 else 0

    def _class_id_score(self, node) -> float:
        score = 0.0
        cls = node.get("class")
        if cls is not None and self.negative_patterns.match(cls):
            score -= 0.5
        node_id = node.get("id")
        if node_id is not None and self.negative_patterns.match(node_id):
            score -= 0.5
        return score
