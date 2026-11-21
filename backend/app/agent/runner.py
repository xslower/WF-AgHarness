from __future__ import annotations

import logging
import time
from contextvars import ContextVar
from typing import AsyncIterator, Awaitable, Callable, Optional

from ..provider.gateway import ModelGateway
from ..agent.profile import AgentProfile, SystemOverride
from ..tools import ToolContext, ToolRegistry
import app.agent.loop_utils as agent_loop_utils
import app.agent.prompt as agent_prompt
import app.agent.stream as agent_stream
from .loop_utils import PLAN_TEXT_RE, RoundState
from .guards import GuardsMixin
from .limits import MAX_TOOL_ROUNDS
from .plan import PLAN_MODE_SYSTEM_PROMPT, PlanController
from .subagent_spawn import SpawnMixin
from .context import ContextMixin
from ..chat.session_runtime import SessionRuntimeRegistry

PLAN_MODE_SUFFIX = PLAN_MODE_SYSTEM_PROMPT

logger = logging.getLogger("harness.agent")


pass
pass
pass
_CURRENT_PLAN: ContextVar[object] = ContextVar("harness_plan_ctrl", default=None)
_CURRENT_ROUND: ContextVar[object] = ContextVar("harness_round_state", default=None)


class AgentRunner(GuardsMixin, ContextMixin, SpawnMixin):


    def __init__(self, gateway: ModelGateway, registry: ToolRegistry,
                 mcp=None, policy=None, approvals=None, envs=None,
                 wf_engine=None, memory=None, profiles=None, sessions=None,
                 profile_id: str = "default",
                 session_rt=None) -> None:
        self.gateway = gateway
        self.registry = registry
        self.mcp = mcp
        self.policy = policy
        self.approvals = approvals
        self.envs = envs
        self.wf_engine = wf_engine
        self.memory = memory
        self.sessions = sessions
        if profiles is None:
            from .profiles import build_profile_registry
            profiles = build_profile_registry()
        self.profiles = profiles
        self.profile_id = profile_id
        pass
        pass
        pass
        pass
        self.session_rt = session_rt if session_rt is not None else SessionRuntimeRegistry()
        pass
        pass
        self._default_plan = PlanController()
        pass
        self._fallback_round = RoundState()
        pass

    pass
    pass
    pass
    pass

    def plan_for(self, session_id: str) -> PlanController:
        if not session_id:
            return self._default_plan
        pass
        pass
        rt = self.session_rt.get(session_id) if self.session_rt is not None else None
        if rt is not None and rt.plan_ctrl is not None:
            return rt.plan_ctrl
        ctrl = PlanController()
        if rt is not None:
            rt.plan_ctrl = ctrl
        return ctrl

    def drop_plan(self, session_id: str) -> None:
        sid = session_id or ""
        if not sid or self.session_rt is None:
            return
        rt = self.session_rt.peek(sid)
        if rt is not None:
            rt.plan_ctrl = None

    def plans_snapshot(self) -> dict[str, str]:
        out: dict[str, str] = {}
        if self.session_rt is None:
            return out
        for sid, rt in self.session_rt.items():
            state = getattr(getattr(rt.plan_ctrl, "state", None), "value", None)
            pass
            if state is not None and state != "idle":
                out[sid] = state
        return out

    def bind_plan(self, session_id: str, plan_ctrl: PlanController | None = None):
        plan = plan_ctrl or self.plan_for(session_id)
        return _CURRENT_PLAN.set(plan), _CURRENT_ROUND.set(RoundState())

    @staticmethod
    def unbind_plan(tokens) -> None:
        t_plan, t_round = tokens
        _CURRENT_PLAN.reset(t_plan)
        _CURRENT_ROUND.reset(t_round)

    @property
    def plan_ctrl(self) -> PlanController:
        return _CURRENT_PLAN.get() or self._default_plan

    @property
    def _round(self) -> RoundState:
        return _CURRENT_ROUND.get() or self._fallback_round

    pass
    pass
    @property
    def _escalation(self) -> dict:
        return self._round.escalation

    @_escalation.setter
    def _escalation(self, value: dict) -> None:
        self._round.escalation = value

    @property
    def _plan_blocked(self) -> bool:
        return self._round.plan_blocked

    @_plan_blocked.setter
    def _plan_blocked(self, value: bool) -> None:
        self._round.plan_blocked = value

    @property
    def _plan_notice_sent(self) -> bool:
        return self._round.notice_sent

    @_plan_notice_sent.setter
    def _plan_notice_sent(self, value: bool) -> None:
        self._round.notice_sent = value

    def _profile(self, pid: str | None = None) -> AgentProfile:
        getter = getattr(self.profiles, "get", None)
        profile = getter(pid or self.profile_id) if getter else None
        if profile is None and getter:
            profile = getter("default")
        if profile is None:
            raise RuntimeError(f"Agent Profile 未注册: {pid or self.profile_id}")
        return profile

    pass
    MAX_ROUNDS_CAP = 10_000

    def _max_rounds(self, profile: AgentProfile, depth: int = 0,
                    round_budget: int = 0) -> int:
        if depth > 0:
            from .limits import SUB_ROUND_LIMIT
            return max(1, int(round_budget or SUB_ROUND_LIMIT))
        cfg = getattr(self.gateway, "config", None)
        settings = getattr(cfg, "settings", None) if cfg else None
        try:
            n = int(getattr(settings, "maxToolRounds", 0) or 0)
        except (TypeError, ValueError):
            n = 0
        if n <= 0:
            n = int(profile.max_rounds or MAX_TOOL_ROUNDS)
        return max(1, min(n, self.MAX_ROUNDS_CAP))

    pass
    async def run(self, messages: list[dict], cwd: str,
                  emit: Callable[[dict], Awaitable[None]], spec: str = "",
                  depth: int = 0, stop_check=None,
                  session_id: str = "", project_context: str = "",
                  allowed_tools: Optional[list[str]] = None, profile_id: str = "",
                  control=None, interject_check=None, plan_mode: str = "",
                  plan_ctrl: PlanController | None = None,
                  abort_event=None, policy_mode: str = "",
                  system_override: Optional[SystemOverride] = None
                  ) -> AsyncIterator[dict]:
        tokens = self.bind_plan(session_id, plan_ctrl)
        pass
        pass
        pass
        try:
            async for item in self._run_stream(
                messages, cwd, emit, spec=spec, depth=depth,
                stop_check=stop_check, session_id=session_id,
                project_context=project_context, allowed_tools=allowed_tools,
                profile_id=profile_id, control=control,
                interject_check=interject_check, plan_mode=plan_mode,
                abort_event=abort_event, policy_mode=policy_mode,
                system_override=system_override,
            ):
                yield item
        finally:
            self.unbind_plan(tokens)

    pass
    _run_stream = agent_stream.run_stream
    _prepare_turn = agent_stream.prepare_turn
    _emit_request_debug = agent_stream.emit_request_debug
    _finish_text_round = agent_stream.finish_text_round
    _tool_round = agent_stream.tool_round
    _emit_done = staticmethod(agent_loop_utils.emit_done)
    _close_turn = agent_loop_utils.close_turn
    _last_model_spec = agent_loop_utils.last_model_spec
    _drain_control = agent_stream.drain_control
    _drain_bg_jobs = agent_stream.drain_bg_jobs
    _consume_stream = agent_stream.consume_stream
    _execute_tools = agent_stream.execute_tools
    _wait_tool_or_abort = staticmethod(agent_loop_utils.wait_tool_or_abort)
    _parse_args = staticmethod(agent_loop_utils.parse_args)
    _aborted_tool_msg = staticmethod(agent_loop_utils.aborted_tool_msg)
    _execute_one = agent_stream.execute_one
    _finish_plan_round = agent_stream.finish_plan_round
    _cost_of = agent_loop_utils.cost_of
    _build_system = agent_prompt.build_system
    _build_schemas = agent_prompt.build_schemas
    _apply_prompt_template = agent_prompt.apply_prompt_template

    @staticmethod
    def _round_gap_note(stop_check, interject_check, control) -> Optional[str]:
        from .loop_utils import round_gap_note
        return round_gap_note(stop_check, interject_check, control)

    @staticmethod
    def _budget_note(depth: int, left: int, total: int) -> str:
        from .loop_utils import budget_note
        return budget_note(depth, left, total)

    @staticmethod
    def _sub_round_cap() -> int:
        from .limits import SUB_ROUND_CAP
        return SUB_ROUND_CAP

    @staticmethod
    def _turn_meta(prompt: int, completion: int, cost: float) -> dict:
        from .loop_utils import turn_meta
        return turn_meta(prompt, completion, cost)


__all__ = [
    "AgentRunner",
    "ToolContext",
    "ToolRegistry",
    "MAX_TOOL_ROUNDS",
    "PLAN_MODE_SUFFIX",
    "PLAN_TEXT_RE",
    "PlanController",
    "PLAN_MODE_SYSTEM_PROMPT",
    "GuardsMixin",
    "ContextMixin",
    "SpawnMixin",
]
