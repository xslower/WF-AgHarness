from __future__ import annotations

from typing import Optional

from .errors import WorkflowError
from .nodes import build_default_nodes
from .nodes.registry import NodeRegistry

MAX_STEPS = 50000
"""单次运行的节点执行总步数上限（防跑飞的最后一道保险）。

为什么从 1000 提到 50000：它数的是**整次运行的总步数**，而 map 200 项 × 5 个 body
节点就是 1000 步 —— 会先撞到这里，报「超过最大步数」，错误信息把人往死循环上带，
真正的原因只是图比较大。单节点的进入次数由 DEFAULT_NODE_VISITS 管（默认 1000），
那才是拦死循环的主力，这里只当兜底。
"""

DEFAULT_NODE_VISITS = 1000
"""节点没写 `maxVisits` 时的默认进入次数（含首轮）。

只是防死循环的兜底：真正要控回边轮次就在节点上写 maxVisits。到上限不是错误，
按「正常结束」处理（有 false 走 false，没有就结束整条链）并记一条 warning ——
投研里「队列跑完即空」是正常结束，报 failed 会让人以为整批白跑了。
"""

CONTROL_TYPES = {"condition", "loop", "map", "human"}
"""带分支/子链的节点：出现任意一个就走旧遍历（支持回到上游的回边），不启用 DAG 调度。

`human` 必须在这里：它有两个分支（批准/驳回），若被当成普通节点参与 DAG 调度，
两个分支会被同时执行 —— 闸门就没意义了。
"""

HUMAN_MODES = ("ask", "auto-approve", "auto-reject", "deny")
"""人工闸门策略：询问 / 自动批准 / 自动驳回（定时与测试用）/ 直接拒绝（无人值守）。"""

MAX_SUBFLOW_DEPTH = 3
"""workflow 节点最大嵌套层数。再深就不是「拆图」而是「藏错」了。"""

_DEFAULT_NODES: Optional[NodeRegistry] = None


def default_nodes() -> NodeRegistry:
    global _DEFAULT_NODES
    if _DEFAULT_NODES is None:
        _DEFAULT_NODES = build_default_nodes()
    return _DEFAULT_NODES



def pick_output(rec, spec: str) -> str:
    target = (spec or "final").strip()
    if target.startswith("node:"):
        target = target[5:].strip()
    if target in ("", "final"):
        return rec.final or ""
    state = rec.node_states.get(target)
    if state is None:
        raise WorkflowError(
            f"子工作流「{rec.wf_name}」没有节点 {target}，"
            f"output 只能是 final 或 node:<节点id>")
    return state.get("output", "")

