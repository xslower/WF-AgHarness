from __future__ import annotations

from dataclasses import dataclass, field
import logging
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

from ...provider.spec import QUEUE_CHILD, QUEUE_PARENT, QUEUE_SUMMARY
from ...util.registry import Registry

logger = logging.getLogger("harness.node_registry")

pass
pass
pass
pass
pass
WF_NODE_DEFAULT_MODEL = QUEUE_SUMMARY


def node_model(node: dict) -> str:
    return str(node.get("model") or WF_NODE_DEFAULT_MODEL).strip() or WF_NODE_DEFAULT_MODEL


@dataclass(frozen=True)
class NodeField:

    key: str
    label: str
    kind: str = "text"
    options: tuple[str, ...] = ()
    required: bool = False
    placeholder: str = ""

    def to_dict(self) -> dict:
        return {"key": self.key, "label": self.label, "kind": self.kind,
                "options": list(self.options), "required": self.required,
                "placeholder": self.placeholder}


def wf_model_field(label: str = "模型（与会话同一套选择）") -> NodeField:
    return NodeField("model", label, "model",
                     placeholder=f"留空={QUEUE_SUMMARY} 队列；{QUEUE_PARENT} / "
                                 f"{QUEUE_CHILD} / {QUEUE_SUMMARY} / providerName/modelId")


NodeRunner = Callable[[dict, "NodeContext", dict], Awaitable[tuple[str, Optional[str]]]]


@dataclass(frozen=True)
class NodeSpec:

    type: str
    label: str
    run: NodeRunner
    fields: tuple[NodeField, ...] = ()
    required: tuple[str, ...] = ()
    group: str = "通用"
    desc: str = ""
    pass
    pass
    pass
    branch_keys: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"type": self.type, "label": self.label, "group": self.group,
                "desc": self.desc, "branch_keys": list(self.branch_keys),
                "fields": [f.to_dict() for f in self.fields]}


@dataclass
class NodeContext:

    workspace: str = ""
    gateway: Any = None
    tools: Any = None
    mcp: Any = None
    agent_runner: Any = None
    run_id: str = ""
    wf_name: str = ""
    artifacts_dir: Path | None = None
    log_json_error: Callable[..., None] | None = None
    substitute: Callable[..., str] | None = None
    eval_expr: Callable[[str, dict], bool] | None = None
    traverse: Callable[..., Awaitable[None]] | None = None
    extras: dict = field(default_factory=dict)
    pass
    pass
    report_file: Callable[..., None] | None = None
    pass
    node_id: str = ""
    pass
    run_warn: Callable[[str, str, str], None] | None = None

    @property
    def cwd(self) -> str:
        return self.workspace or "."

    def report(self, path: str | Path) -> None:
        if self.report_file is None:
            return
        try:
            self.report_file(str(path), self.node_id)
        except Exception:
            logger.debug("report_file 失败: %s", path, exc_info=True)

    def warn(self, message: str, code: str = "", node: str = "") -> None:
        if self.run_warn is None:
            return
        try:
            self.run_warn(code or "node-warn", str(message), node or self.node_id)
        except Exception:
            logger.debug("run_warn 失败: %s", code, exc_info=True)

    def tool_ctx(self):
        from ...tools import ToolContext
        ctx = ToolContext(self.cwd)
        pass
        pass
        ctx.allow_internal = True
        pass
        pass
        pass
        ctx.report_file = self.report if self.report_file else None
        return ctx

    def sub(self, text: str, vars: dict, long_ref: bool = False) -> str:
        if self.substitute is None:
            return str(text)
        return self.substitute(text, vars, long_ref)

    def sub_path(self, text: str, vars: dict) -> str:
        if self.substitute is None:
            return str(text)
        try:
            return self.substitute(text, vars, False, True)
        except TypeError:
            return self.substitute(text, vars, False)

    def eval_condition(self, expr: str, vars: dict) -> bool:
        if self.eval_expr is None:
            return False
        return self.eval_expr(expr, vars)


class NodeRegistry:

    def __init__(self, registry: Registry[NodeSpec] | None = None) -> None:
        self._registry = registry or Registry("workflow.nodes", key=lambda s: s.type)

    def register(self, spec: NodeSpec) -> NodeSpec:
        return self._registry.register(spec)

    def try_register(self, spec: NodeSpec, source: str = "") -> bool:
        return self._registry.try_register(spec, source)

    def get(self, node_type: str) -> NodeSpec | None:
        return self._registry.get(node_type)

    def types(self) -> list[str]:
        return self._registry.keys()

    def all(self) -> list[NodeSpec]:
        return self._registry.all()

    def errors(self) -> dict[str, str]:
        return self._registry.errors()

    def freeze(self) -> None:
        self._registry.freeze()

    def catalog(self) -> list[dict]:
        return [s.to_dict() for s in self._registry.all()]

