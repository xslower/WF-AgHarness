from __future__ import annotations

import json

from app.tools.builtin.web import _empty_result, _format_rows, _label_sources


class _Engine:
    def __init__(self, label):
        self.label = label


def _row(title="标题", url="https://a.com", snippet="摘要", **kw):
    pass
    base = {"title": title, "url": url, "snippet": snippet,
            "sources": ["百度"], "trust": "medium", "hits": 1}
    base.update(kw)
    return base


pass
def test_label_sources_maps_index_to_label():
    merged = [{"sources": [0, 2]}]
    _label_sources(merged, [_Engine("百度"), _Engine("搜狗"), _Engine("360")])
    assert merged[0]["sources"] == ["百度", "360"]


def test_label_sources_drops_out_of_range_index():
    merged = [{"sources": [0, 99]}]
    _label_sources(merged, [_Engine("百度")])
    assert merged[0]["sources"] == ["百度"]


pass
def test_empty_result_plain_failure():
    out = json.loads(_empty_result({"baidu": "timeout"}))
    assert "timeout" in out["error"]
    assert "反爬" not in out["error"]


def test_empty_result_without_errors_mentions_structure():
    out = json.loads(_empty_result({}))
    assert "页面结构" in out["error"]


def test_empty_result_antibot_gives_wait_hint():
    out = json.loads(_empty_result({"baidu": "触发反爬验证"}))
    assert "过几分钟再搜" in out["error"]
    assert "不用改选择器" in out["error"]


def test_empty_result_rate_limit_also_hinted():
    out = json.loads(_empty_result({"sogou": "限流"}))
    assert "过几分钟再搜" in out["error"]


pass
def _format(top, merged_len=None, picked=None, pages=1, mapping=None,
            errors=None):
    return _format_rows(
        top,
        len(top) if merged_len is None else merged_len,
        picked if picked is not None else [_Engine("百度")],
        pages,
        mapping if mapping is not None else {},
        errors if errors is not None else {})


def test_rows_have_no_source_label():
    out = _format([_row(sources=["百度", "搜狗"], host="bbs.csdn.net", trust="high")])
    assert out.startswith("[1] 标题")
    assert "来源" not in out
    assert "百度" not in out and "搜狗" not in out
    assert "置信度" not in out
    assert "https://a.com" in out


def test_row_omits_blank_snippet_line():
    out = _format([_row(snippet="")])
    lines = out.split("\n")
    assert lines[0] == "[1] 标题"
    assert lines[1].strip() == "https://a.com"
    assert lines[2].strip() == "" or lines[2].startswith("共 ")


def test_row_keeps_snippet_when_present():
    out = _format([_row(snippet="这是摘要")])
    assert "这是摘要" in out


def test_footer_reports_counts():
    out = _format([_row()], merged_len=42, pages=2)
    assert "共 1 个引擎 × 2 页" in out
    assert "去重后 42 条" in out


def test_footer_mentions_url_resolution():
    out = _format([_row()], mapping={"https://sogou.com/link?u=1": "https://real.com"})
    assert "还原为真实地址" in out


def test_footer_lists_unavailable_engines_with_reason():
    out = _format([_row()], errors={"baidu": "timeout 8s"})
    assert "部分引擎不可用" in out and "baidu" in out and "timeout" in out


def test_trust_note_only_when_sparse_and_all_low():
    assert "置信度" not in _format([_row()])
    assert "置信度" not in _format([_row(trust="low")] * 2, merged_len=20)
    low = [_row(trust="low") for _ in range(2)]
    out = _format(low, merged_len=2)
    assert "置信度都低" in out and "换个更具体的搜索词" in out
    mixed = [_row(trust="low"), _row(trust="high")]
    assert "置信度都低" not in _format(mixed, merged_len=2)


def test_row_order_preserved():
    out = _format([_row(title="甲"), _row(title="乙")])
    lines = out.split("\n")
    assert lines[0].startswith("[1] 甲")
    assert lines[3].startswith("[2] 乙")
