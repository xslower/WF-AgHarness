from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from app.workflow import WorkflowEngine
from app.workflow.human import HumanGate, PendingGate


WF = [
    {"id": "h1", "type": "human", "title": "确认", "options": "批准\\n驳回",
     "true": "w1", "false": "w2"},
    {"id": "w1", "type": "write", "path": "go.txt", "content": "go"},
    {"id": "w2", "type": "write", "path": "stop.txt", "content": "stop"},
]


def test_open_writes_gate_file(tmp_path):
    gate = HumanGate(run_dir=lambda rid: tmp_path / rid)
    g = gate.open("r1", "h1", title="确认", ask="要点吗", options=["批准", "驳回"])
    p = tmp_path / "r1" / "gates" / "h1.json"
    assert p.is_file()
    data = json.loads(p.read_text("utf-8"))
    assert data["title"] == "确认"
    assert data["options"] == ["批准", "驳回"]
    assert data["decided"] is False
    assert g.path == p


def test_decide_persists_answer(tmp_path):
    gate = HumanGate(run_dir=lambda rid: tmp_path / rid)
    gate.open("r1", "h1", options=["批准", "驳回"])
    assert gate.decide("r1", "h1", "驳回", "不行") is True
    data = json.loads((tmp_path / "r1" / "gates" / "h1.json").read_text("utf-8"))
    assert data["decided"] is True
    assert data["choice"] == "驳回"
    assert data["comment"] == "不行"


def test_decision_survives_restart(tmp_path):
    first = HumanGate(run_dir=lambda rid: tmp_path / rid)
    first.open("r1", "h1", options=["批准", "驳回"])
    first.decide("r1", "h1", "批准")

    second = HumanGate(run_dir=lambda rid: tmp_path / rid)
    g = second.open("r1", "h1", options=["批准", "驳回"])
    assert g.decided is True, "上一轮已点的答案必须被补齐"
    assert g.choice == "批准"


def test_decide_after_restart_rehydrates(tmp_path):
    first = HumanGate(run_dir=lambda rid: tmp_path / rid)
    first.open("r1", "h1", options=["批准", "驳回"])

    second = HumanGate(run_dir=lambda rid: tmp_path / rid)
    assert second.decide("r1", "h1", "驳回") is True
    data = json.loads((tmp_path / "r1" / "gates" / "h1.json").read_text("utf-8"))
    assert data["choice"] == "驳回"


def test_invalid_choice_rejected(tmp_path):
    gate = HumanGate(run_dir=lambda rid: tmp_path / rid)
    gate.open("r1", "h1", options=["批准", "驳回"])
    assert gate.decide("r1", "h1", "拒绝") is False
    assert gate.pending("r1") is not None, "被拒后闸门应仍在挂起"


async def test_wait_picks_up_cross_process_answer(tmp_path):
    gate = HumanGate(run_dir=lambda rid: tmp_path / rid)
    g = gate.open("r1", "h1", options=["批准", "驳回"])

    async def other_process_decides():
        await asyncio.sleep(0.1)
        pass
        data = json.loads(g.path.read_text("utf-8"))
        data.update({"decided": True, "choice": "驳回", "comment": "远端"})
        g.path.write_text(json.dumps(data, ensure_ascii=False), "utf-8")

    task = asyncio.create_task(other_process_decides())
    got = await gate.wait(g, timeout=5)
    await task
    assert got.decided is True
    assert got.choice == "驳回"


async def test_wait_timeout_still_returns_undecided(tmp_path):
    gate = HumanGate(run_dir=lambda rid: tmp_path / rid)
    g = gate.open("r1", "h1", options=["批准"])
    got = await gate.wait(g, timeout=0.3)
    assert got.decided is False


async def test_no_run_dir_degrades_to_memory():
    gate = HumanGate()
    g = gate.open("r1", "h1", options=["批准"])
    assert g.path is None
    assert gate.decide("r1", "h1", "批准") is True
    got = await gate.wait(g, timeout=1)
    assert got.decided is True


def test_carry_gates_moves_answer_to_new_run(tmp_path):
    from app.store.runs import RunStore
    store = RunStore(str(tmp_path / "proj"))
    store.prepare("old", "wf")
    store.prepare("new", "wf")
    old_dir = store.gates_dir("old")
    old_dir.mkdir(parents=True, exist_ok=True)
    (old_dir / "h1.json").write_text(json.dumps(
        {"node_id": "h1", "options": ["批准"], "choice": "批准", "decided": True},
        ensure_ascii=False), "utf-8")

    assert store.carry_gates("old", "new") == 1
    carried = json.loads((store.gates_dir("new") / "h1.json").read_text("utf-8"))
    assert carried["choice"] == "批准"
    pass
    assert store.carry_gates("new", "new") == 0
    assert store.carry_gates("missing", "new") == 0
