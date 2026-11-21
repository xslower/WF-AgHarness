from __future__ import annotations

from app.tools.builtin.web.merge import _absorb, _new_row, merge_results


def test_new_row_trims_and_initializes():
    row = _new_row({"title": " 标题 ", "url": " https://a.com ", "snippet": " s "},
                   g_idx=2, rank=3)
    assert row == {"title": "标题", "url": "https://a.com", "snippet": "s",
                   "sources": [2], "hits": 1, "best_rank": 3}


def test_new_row_tolerates_missing_fields():
    row = _new_row({}, g_idx=0, rank=0)
    assert row["title"] == "" and row["url"] == "" and row["snippet"] == ""


def test_absorb_keeps_longer_snippet():
    row = _new_row({"snippet": "短"}, 0, 0)
    _absorb(row, {"snippet": "更长的摘要"}, 1, 2)
    assert row["snippet"] == "更长的摘要"


def test_absorb_does_not_shorten_snippet():
    row = _new_row({"snippet": "很长的摘要内容"}, 0, 0)
    _absorb(row, {"snippet": "短"}, 1, 2)
    assert row["snippet"] == "很长的摘要内容"


def test_absorb_fills_missing_title():
    row = _new_row({"url": "https://a.com"}, 0, 0)
    _absorb(row, {"title": "真正的标题"}, 1, 2)
    assert row["title"] == "真正的标题"


def test_absorb_fills_missing_url():
    row = _new_row({"title": "t"}, 0, 0)
    _absorb(row, {"url": "https://a.com"}, 1, 2)
    assert row["url"] == "https://a.com"


def test_absorb_accumulates_sources_without_duplicates():
    row = _new_row({}, 0, 0)
    _absorb(row, {}, 1, 1)
    _absorb(row, {}, 1, 1)
    assert row["sources"] == [0, 1]
    assert row["hits"] == 3


def test_absorb_keeps_best_rank():
    row = _new_row({}, 0, 5)
    _absorb(row, {}, 1, 2)
    assert row["best_rank"] == 2
    _absorb(row, {}, 1, 9)
    assert row["best_rank"] == 2


def test_both_keys_registered_on_first_absorb():
    groups = [
        [{"title": "同一件事", "url": "https://a.com/x", "snippet": ""}],
        [{"title": "同一件事", "url": "https://sogou.com/link?u=1", "snippet": ""}],
    ]
    merged = merge_results(groups)
    assert len(merged) == 1
    assert merged[0]["sources"] == [0, 1]
