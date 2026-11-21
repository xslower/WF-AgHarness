from __future__ import annotations

import pytest

from app.workflow.preflight import (check_back_edges, check_reachability,
                                    is_warning)


def _run(wf):
    issues: list[str] = []
    check_reachability(wf, issues)
    check_back_edges(wf, issues)
    return issues


def test_unreachable_node_is_warning():
    wf = {"nodes": [
        {"id": "a", "type": "write", "path": "a.txt", "next": "b"},
        {"id": "b", "type": "write", "path": "b.txt"},
        {"id": "orphan", "type": "write", "path": "o.txt"},
    ]}
    issues = _run(wf)
    assert any("orphan" in x for x in issues)
    assert all(is_warning(x) for x in issues), "不可达不能拦启动"


def test_all_reachable_no_issue():
    wf = {"nodes": [
        {"id": "a", "type": "write", "next": "b"},
        {"id": "b", "type": "write"},
    ]}
    assert _run(wf) == []


def test_human_option_target_counts_as_edge():
    wf = {"nodes": [
        {"id": "h", "type": "human", "title": "t",
         "options": "批准\n回炉=w3", "true": "w1", "false": "w2"},
        {"id": "w1", "type": "write"},
        {"id": "w2", "type": "write"},
        {"id": "w3", "type": "write"},
    ]}
    assert _run(wf) == []


def test_edges_preferred_over_next():
    wf = {"nodes": [
        {"id": "a", "type": "write", "next": "b"},
        {"id": "b", "type": "write"},
    ], "edges": [{"source": "a", "target": "b"}]}
    assert _run(wf) == []


def test_no_reachable_sink_blocks():
    wf = {"nodes": [
        {"id": "a", "type": "condition", "expr": "1", "true": "a", "false": ""},
        {"id": "sink", "type": "write"},
    ]}
    issues = _run(wf)
    assert any("没有可达的终点" in x or "没有任何可达的终点" in x for x in issues)
    assert any(not is_warning(x) for x in issues)


def test_back_edge_without_max_visits_warns():
    wf = {"nodes": [
        {"id": "c", "type": "condition", "expr": "x", "true": "body", "false": "end"},
        {"id": "body", "type": "write", "next": "c"},
        {"id": "end", "type": "write"},
    ]}
    issues = _run(wf)
    assert any("maxVisits" in x for x in issues)
    assert all(is_warning(x) for x in issues), "回边缺 maxVisits 只提醒不拦"


def test_back_edge_with_max_visits_is_quiet():
    wf = {"nodes": [
        {"id": "c", "type": "condition", "expr": "x", "true": "body",
         "false": "end", "maxVisits": 5},
        {"id": "body", "type": "write", "next": "c"},
        {"id": "end", "type": "write"},
    ]}
    assert [x for x in _run(wf) if "maxVisits" in x] == []


def test_pure_dag_not_checked_for_back_edges():
    wf = {"nodes": [
        {"id": "a", "type": "write", "next": "b"},
        {"id": "b", "type": "write"},
    ]}
    assert [x for x in _run(wf) if "回边" in x] == []


def test_is_warning_marker():
    assert is_warning("警告：xxx") is True
    assert is_warning("节点 a 引用了不存在的变量") is False
