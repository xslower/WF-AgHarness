from __future__ import annotations

from ...agent.profile import AgentProfile
from ...provider.spec import QUEUE_CHILD

RESEARCHER_SYSTEM_PROMPT = """你是研究子 Agent，负责收集资料、核对事实并给出要点。
规则：
- 优先读本地文件，再联网检索补充；两者冲突时以本地/官方来源为准。
- 输出要点列表，标注来源（文件路径或 URL）。
- 回答用中文，不臆造数据；查不到就明确说明。"""

RESEARCHER_PROFILE = AgentProfile(
    id="researcher",
    system_prompt=RESEARCHER_SYSTEM_PROMPT,
    allowed_tools=("f_read", "search_files", "grep", "web"),
    max_rounds=20,
    spec=QUEUE_CHILD,
    plan_mode="off",
    max_spawn_depth=0,
    subagent_profile="default",
)
