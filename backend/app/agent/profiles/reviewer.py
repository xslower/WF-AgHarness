from __future__ import annotations

from ...agent.profile import AgentProfile
from ...provider.spec import QUEUE_CHILD
from ..limits import REVIEWER_MAX_ROUNDS

REVIEWER_SYSTEM_PROMPT = """你是代码审阅子 Agent，只读检查、不修改文件。
规则：
- 先读相关文件，再给出问题清单（按严重程度排序）。
- 每条问题给出 文件路径:行号、原因与建议。
- 回答用中文，简洁，不要输出与审阅无关的内容。"""

REVIEWER_PROFILE = AgentProfile(
    id="reviewer",
    system_prompt=REVIEWER_SYSTEM_PROMPT,
    allowed_tools=("f_read", "search_files", "grep"),
    max_rounds=REVIEWER_MAX_ROUNDS,
    spec=QUEUE_CHILD,
    plan_mode="off",
    max_spawn_depth=0,
    subagent_profile="default",
)
