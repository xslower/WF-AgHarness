from __future__ import annotations

from app.agent.profiles.default import SYSTEM_PROMPT


def test_delegation_contract_present():
    for phrase in ("子 Agent 自身按轮计费", "≥3 个互不依赖的只读调用",
                   "单/两个廉价只读调用", "主会话只做决策",
                   "测试/门禁闭环", "自行定位、修复",
                   "禁止工具", "阶段总结", "路径:行号",
                   "action=extend", "已落盘的完整历史", "服务重启后凭 id"):
        assert phrase in SYSTEM_PROMPT, phrase


def test_deprecated_delegation_phrases_do_not_come_back():
    for phrase in ("一律同批 spawn 给 subagent", "status=paused",
                   "一律 spawn 给 subagent", "extend 已废弃"):
        assert phrase not in SYSTEM_PROMPT, phrase


def test_extend_after_done_is_documented():
    assert "done 只是本轮收尾" in SYSTEM_PROMPT
    assert "不用重开、不用重做" in SYSTEM_PROMPT


def test_code_map_contract_present():
    for phrase in ("grep(outline=true", "读功能区代码前先查代码地图",
                   "行号范围", "spawn 时带 hints", "hints` 数组"):
        assert phrase in SYSTEM_PROMPT, phrase


def test_batch_and_multi_read_contract_present():
    for phrase in ("同一轮一次性", "跑完整批再回传", "path 可传数组",
                   "f_read 的 path 可传数组", "最多 8 个", "相关片段"):
        assert phrase in SYSTEM_PROMPT, phrase
    assert "最多 3 个" not in SYSTEM_PROMPT


def test_pytest_incremental_loop_contract():
    for phrase in ("-q --tb=line", "--maxfail", "所有**报错方法", "一次性把所有报错方法都改完",
                   "pytest --lf", "lastfailed", "唯一真源",
                   "再跑一次全量收尾", "禁止改一点就重跑全量"):
        assert phrase in SYSTEM_PROMPT, phrase


def test_pytest_timeout_budget_is_300s():
    assert "超过 300s 才按目录/文件拆开跑" in SYSTEM_PROMPT
    assert "超过 60s 就按目录/文件拆开跑" not in SYSTEM_PROMPT
