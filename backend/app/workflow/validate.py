from __future__ import annotations

import glob
from pathlib import Path

from .errors import WorkflowError
from .nodes.registry import NodeRegistry
from .constants import CONTROL_TYPES, default_nodes


def _children_map(wf_nodes: list[dict]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for n in wf_nodes:
        kids: list[str] = []
        for k in ("next", "true", "false", "body"):
            v = n.get(k)
            if isinstance(v, list):
                kids += [str(x) for x in v if x]
            elif v:
                kids.append(str(v))
        kids += [str(x) for x in (n.get("parallel_next") or []) if x]
        out[str(n.get("id"))] = kids
    return out


def _require_common_join(node_id: str, targets: list[str],
                         join_ids: set[str],
                         children: dict[str, list[str]],
                         has_control: bool = True) -> None:
    if not has_control or len(targets) < 2:
        return
    reach: list[set[str]] = [set() for _ in targets]
    for idx, t in enumerate(targets):
        seen: set[str] = set()
        stack = [t]
        while stack:
            cur = stack.pop()
            if cur in seen or cur not in children:
                continue
            seen.add(cur)
            stack.extend(children[cur])
        reach[idx] = seen & join_ids
    common = set.intersection(*reach) if reach else set()
    if not common:
        raise WorkflowError(
            f"节点 {node_id} 接了多个后继（{', '.join(targets)}），但这张图含 "
            "condition / human / map —— 这种图里的每条分支都必须能汇合到**同一个** "
            "`join` 节点（否则分支会在普通节点撞车并被执行两次）。"
            "要么在下游加一个 join，要么改回 map / 把这一段拆成子工作流")


class ValidateMixin:
    @staticmethod
    def _normalize(wf: dict) -> dict:
        for n in wf.get("nodes") or []:
            nxt = n.get("next")
            if isinstance(nxt, list):
                targets = [str(x) for x in nxt if x]
                if len(targets) == 1:
                    n["next"] = targets[0]
                else:
                    n["parallel_next"] = targets
                    n.pop("next", None)
            elif nxt is not None and not isinstance(nxt, str):
                raise WorkflowError(
                    f"节点 {n.get('id')} 的 next 只能是节点 id 字符串或数组"
                    f"（收到 {type(nxt).__name__}）")
        return wf

    @staticmethod
    @staticmethod
    def validate_structure(wf: dict) -> None:
        ValidateMixin._check_meta(wf)
        ids = ValidateMixin._check_node_ids(wf["nodes"])
        pass
        ValidateMixin._check_deprecated(wf["nodes"])
        ValidateMixin._check_graph(wf["nodes"], ids, wf.get("edges"))

    @staticmethod
    def _check_meta(wf: dict) -> None:
        if not wf.get("name"):
            raise WorkflowError("缺少 name")
        wf_nodes = wf.get("nodes")
        if not isinstance(wf_nodes, list) or not wf_nodes:
            raise WorkflowError("nodes 必须是非空列表")
        inputs = wf.get("inputs")
        if inputs is not None and not isinstance(inputs, list):
            raise WorkflowError("inputs 必须是列表 [{name, desc, type}]")

    @staticmethod
    def _check_node_ids(wf_nodes: list[dict]) -> set[str]:
        ids: set[str] = set()
        for n in wf_nodes:
            if not n.get("id") or n["id"] in ids:
                raise WorkflowError(f"节点 id 缺失或重复: {n.get('id')}")
            ids.add(n["id"])
        return ids

    @staticmethod
    def _check_deprecated(wf_nodes: list[dict]) -> None:
        for n in wf_nodes:
            if n.get("type") == "while":
                raise WorkflowError(
                    f"节点 {n['id']} 使用了已下线的 while：请改成 condition 回边 —— "
                    "body 末节点 next 指向 condition，condition 的 true 指回 body 起点、"
                    "false 接后续，并给节点加 maxVisits 防止不收敛")

    @staticmethod
    def _check_graph(wf_nodes: list[dict], ids: set[str],
                     edges: list | None) -> None:
        has_control = any(n.get("type") in CONTROL_TYPES for n in wf_nodes)
        ValidateMixin._check_refs(wf_nodes, ids, has_control)
        ValidateMixin._check_edges(edges, ids)
        pass
        if not has_control:
            ValidateMixin._topology(wf_nodes, edges or [])

    @staticmethod
    def _check_refs(wf_nodes: list[dict], ids: set[str], has_control: bool) -> None:
        join_ids = {str(n["id"]) for n in wf_nodes
                    if str(n.get("type") or "") == "join"}
        children = _children_map(wf_nodes)
        for n in wf_nodes:
            for k in ("next", "true", "false", "body"):
                val = n.get(k)
                if isinstance(val, list):
                    for one in val:
                        if one not in ids:
                            raise WorkflowError(
                                f"节点 {n['id']} 的 {k} 指向不存在的 {one}")
                    _require_common_join(n["id"], [str(x) for x in val],
                                         join_ids, children, has_control)
                    continue
                if val and val not in ids:
                    raise WorkflowError(f"节点 {n['id']} 的 {k} 指向不存在的 {val}")
        pass
        if has_control:
            for n in wf_nodes:
                targets = [str(x) for x in (n.get("parallel_next") or [])]
                if targets:
                    _require_common_join(n["id"], targets, join_ids,
                                         children, has_control)

    @staticmethod
    def _check_edges(edges: list | None, ids: set[str]) -> None:
        if edges is None:
            return
        if not isinstance(edges, list):
            raise WorkflowError("edges 必须是连线数组")
        for e in edges:
            if not isinstance(e, dict):
                raise WorkflowError("edges 的每一项必须是对象")
            src, dst = e.get("source"), e.get("target")
            if src not in ids or dst not in ids:
                raise WorkflowError(f"连线指向不存在的节点: {src} -> {dst}")
    def validate_docs(self, wf_nodes: list[dict]) -> None:
        if not wf_nodes:
            return
        base = Path(self.workspace) if self.workspace else Path.cwd()
        missing: list[str] = []
        for n in wf_nodes:
            if str(n.get("type") or "") not in ("llm", "subagent"):
                continue
            raw = n.get("docs")
            if not raw:
                continue
            for entry in (x.strip() for x in str(raw).splitlines()):
                if not entry or "${" in entry:
                    continue
                pat = Path(entry).expanduser()
                if not pat.is_absolute():
                    pat = base / pat
                if any(ch in str(pat) for ch in "*?["):
                    pass
                    if glob.glob(str(pat), recursive=True):
                        continue
                    probe = str(pat)
                    for ch in "*?[":
                        probe = probe.split(ch)[0]
                    parent = Path(probe).parent if probe else base
                    if parent.is_dir():
                        continue
                    missing.append(f"{entry}（节点 {n.get('id')}，父目录 {parent} 不存在）")
                    continue
                if not pat.is_file() and not pat.is_dir():
                    missing.append(f"{entry}（节点 {n.get('id')}，解析为 {pat}）")
        if missing:
            raise WorkflowError(
                "docs 路径不存在（相对路径按项目工作目录解析）：\n  "
                + "\n  ".join(missing)
                + "\n修好再保存，否则运行到该节点才报错、前面几步白烧。")

    @staticmethod
    def _graph_edges(wf_nodes: list[dict], edges: list[dict] | None) -> list[tuple[str, str]]:
        if edges:
            return [(str(e["source"]), str(e["target"])) for e in edges]
        out: list[tuple[str, str]] = []
        for n in wf_nodes:
            if n.get("next"):
                out.append((str(n["id"]), str(n["next"])))
            for k in ("true", "false", "body"):
                if n.get(k):
                    out.append((str(n["id"]), str(n[k])))
            for target in (n.get("parallel_next") or []):
                out.append((str(n["id"]), target))
        return out

    @staticmethod
    def _topology(wf_nodes: list[dict], edges: list[dict] | None = None
                  ) -> tuple[list[str], dict[str, list[str]], dict[str, list[str]]]:
        ids = [str(n["id"]) for n in wf_nodes]
        children: dict[str, list[str]] = {i: [] for i in ids}
        parents: dict[str, list[str]] = {i: [] for i in ids}
        for src, dst in ValidateMixin._graph_edges(wf_nodes, edges):
            if src not in children or dst not in parents:
                continue
            if dst not in children[src]:
                children[src].append(dst)
                parents[dst].append(src)
        indeg = {i: len(parents[i]) for i in ids}
        ready = [i for i in ids if indeg[i] == 0]
        order: list[str] = []
        while ready:
            cur = ready.pop(0)
            order.append(cur)
            for nxt in children[cur]:
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    ready.append(nxt)
        if len(order) != len(ids):
            raise WorkflowError("工作流存在环，不能按并行 DAG 执行")
        return order, parents, children

    @staticmethod
    def _is_parallel_graph(wf: dict) -> bool:
        if wf.get("edges"):
            return True
        return any(
            len([x for x in (n.get("next"), n.get("true"),
                             n.get("false"), n.get("body")) if x]) > 1
            or len(n.get("parallel_next") or []) > 0
            for n in wf.get("nodes", []))

    @staticmethod
    def validate(wf: dict, nodes: NodeRegistry | None = None) -> None:
        nodes = nodes or default_nodes()
        ValidateMixin.validate_structure(wf)
        for n in wf["nodes"]:
            nid = n.get("id")
            node_type = n.get("type")
            spec = nodes.get(node_type)
            if spec is None:
                hint = "（节点没写 type）" if not node_type else ""
                raise WorkflowError(
                    f"节点 {nid} 的 type 无法识别：{node_type!r}{hint}。"
                    "可选类型：" + ", ".join(sorted(nodes.types())))
            for key in spec.required:
                if not n.get(key):
                    raise WorkflowError(f"{node_type} 节点 {nid} 缺少 {key}")
            if node_type == "human":
                from .nodes.human import parse_options
                has_out = (n.get("true") or n.get("false") or n.get("next")
                           or any(t for _, t in parse_options(n.get("options"))))
                if not has_out:
                    raise WorkflowError(
                        f"human 节点 {nid} 没有任何出口：true/false（分支目标）、"
                        "next（统一后续）、或 options 里写「按钮=目标节点id」，"
                        "三样必须至少写一样")
