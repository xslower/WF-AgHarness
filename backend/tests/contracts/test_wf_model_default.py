from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TS = REPO / "frontend" / "src" / "kernel" / "model" / "modelSpec.ts"


def _ts_const(name: str) -> str:
    m = re.search(rf'export const {name}: QueueName = "(\w+)"', TS.read_text("utf-8"))
    assert m, f"{TS} 缺少常量 {name}"
    return m.group(1)


def test_workflow_node_default_is_summary_on_both_sides():
    from app.provider.spec import QUEUE_SUMMARY
    from app.workflow.nodes.registry import WF_NODE_DEFAULT_MODEL, node_model

    assert WF_NODE_DEFAULT_MODEL == QUEUE_SUMMARY == "summary"
    assert _ts_const("WF_NODE_DEFAULT_SPEC") == WF_NODE_DEFAULT_MODEL
    assert node_model({}) == "summary"
    assert node_model({"model": ""}) == "summary"
    assert node_model({"model": "  "}) == "summary"
    assert node_model({"model": " p/m "}) == "p/m"


def test_main_session_default_stays_parent():
    from app.provider.spec import QUEUE_PARENT

    assert _ts_const("DEFAULT_SPEC") == QUEUE_PARENT == "parent"
    assert _ts_const("DEFAULT_SPEC") != _ts_const("WF_NODE_DEFAULT_SPEC")


def test_three_node_types_declare_model_field():
    from app.workflow.constants import default_nodes

    reg = default_nodes()
    for t in ("llm", "condition", "subagent"):
        spec = reg.get(t)
        assert spec is not None, t
        field = next((f for f in spec.fields if f.key == "model"), None)
        assert field is not None, f"{t} 节点没有 model 字段，无法手动指定模型"
        assert field.kind == "model", f"{t}.model 必须是模型下拉，不是 {field.kind}"
