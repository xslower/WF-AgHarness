from __future__ import annotations

import ast
import difflib
import re
import sys
from pathlib import Path

from ..store import layout
from .constants import CONTROL_TYPES

VAR_RE = re.compile(r"(?<!\$)\$\{([^}]+?)\}")
pass
_SUFFIX_RE = re.compile(r"^(.*?)(?<!\$)(?:!(raw|json|py|url)|\|(json|py|url))$")
BUILTIN_VARS = {"prev", "__item__", "__i__", "__final__"}
pass
COMMENTABLE = {"code", "command"}

pass
BACKEND_ROOT = layout.BACKEND_ROOT
REPO_ROOT = layout.SOURCE_ROOT


def _strip_comment_lines(text: str) -> str:
    out = []
    for line in str(text).splitlines():
        s = line.strip()
        if s.startswith(("#", "//", "<!--")):
            continue
        out.append(line)
    return "\n".join(out)


def _var_key(raw: str) -> str:
    m = _SUFFIX_RE.match(raw)
    return m.group(1).strip() if m else raw.strip()


def _iter_strings(value, path: str = ""):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from _iter_strings(v, f"{path}.{k}" if path else str(k))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from _iter_strings(v, f"{path}[{i}]")


def _known_names(wf: dict) -> set[str]:
    names = set(BUILTIN_VARS)
    names.add("inputs")
    for n in wf.get("nodes") or []:
        if n.get("id"):
            names.add(str(n["id"]))
    return names


def _report_bad_input(nid: str, key: str, name: str, declared: set[str],
                      candidates: list[str], issues: list[str]) -> None:
    near = difflib.get_close_matches(name, candidates, n=1)
    hint = f"；是不是 {near[0]}？" if near else ""
    issues.append(
        f"节点 {nid} 的 {key} 引用了不存在的输入 ${{inputs.{name}}}"
        f"（已声明/本次传入：{', '.join(sorted(declared)) or '无'}）{hint}")


def _report_bad_var(nid: str, key: str, root: str, candidates: list[str],
                    issues: list[str]) -> None:
    near = difflib.get_close_matches(root, candidates, n=1)
    hint = f"；是不是「{near[0]}」？" if near else ""
    issues.append(
        f"节点 {nid} 的 {key} 引用了不存在的变量 ${{{root}}}"
        f"（可用：inputs.<名> / 节点 id / prev）{hint}")


def check_vars(wf: dict, issues: list[str], runtime_inputs=None,
               extra_names=None) -> None:
    declared = {str(i.get("name")) for i in (wf.get("inputs") or [])
                if isinstance(i, dict) and i.get("name")}
    if isinstance(runtime_inputs, dict):
        declared |= {str(k) for k in runtime_inputs}
    known = _known_names(wf) | {str(x) for x in (extra_names or ())}
    candidates = list(declared) + sorted(known, key=lambda s: s.lower())
    for n in wf.get("nodes") or []:
        nid = str(n.get("id") or "?")
        for key, text in _iter_strings({k: v for k, v in n.items()
                                        if k not in ("id", "type")}):
            target = _strip_comment_lines(text) if key.split(".")[-1] in COMMENTABLE else text
            for m in VAR_RE.finditer(target.replace("$${", "\0")):
                raw = _var_key(m.group(1))
                if not raw or "\0" in raw:
                    continue
                if raw.startswith("inputs."):
                    name = raw[7:].split(".")[0]
                    if name and name not in declared:
                        _report_bad_input(nid, key, name, declared, candidates, issues)
                    pass
                    pass
                    continue
                root = raw.split(".")[0]
                if root in known:
                    continue
                _report_bad_var(nid, key, root, candidates, issues)


def check_human(wf: dict, issues: list[str]) -> None:
    from .nodes.human import parse_options

    ids = {str(n.get("id")) for n in wf.get("nodes") or []}
    for n in wf.get("nodes") or []:
        if n.get("type") != "human":
            continue
        nid = n.get("id")
        pass
        targets = [t for _, t in parse_options(n.get("options")) if t]
        if not (n.get("true") or n.get("false") or n.get("next") or targets):
            issues.append(
                f"human 节点 {nid} 没有任何出口：true/false、next、"
                "或 options 里写「按钮=目标节点id」，三样至少写一样")
        for t in targets:
            if t not in ids:
                issues.append(f"human 节点 {nid} 的选项指向不存在的节点 {t}")


def check_docs(wf: dict, workspace: str, issues: list[str]) -> None:
    base = Path(workspace) if workspace else Path.cwd()
    for n in wf.get("nodes") or []:
        if str(n.get("type") or "") not in ("llm", "subagent"):
            continue
        for entry in str(n.get("docs") or "").splitlines():
            entry = entry.strip()
            if not entry or "${" in entry:
                continue
            p = Path(entry).expanduser()
            if not p.is_absolute():
                p = base / p
            if any(ch in str(p) for ch in "*?["):
                import glob as _glob
                if _glob.glob(str(p), recursive=True):
                    continue
                probe = str(p)
                for ch in "*?[":
                    probe = probe.split(ch)[0]
                if Path(probe).parent.is_dir():
                    continue
            elif p.exists():
                continue
            issues.append(f"节点 {n.get('id')} 的 docs 找不到：{entry}（解析为 {p}）")


def check_subflow(wf: dict, resolve, issues: list[str]) -> None:
    for n in wf.get("nodes") or []:
        if n.get("type") != "workflow":
            continue
        name = str(n.get("name") or "").strip()
        if not name or "${" in name:
            continue
        if resolve is None or resolve(name) is None:
            issues.append(
                f"workflow 节点 {n.get('id')} 的子工作流不存在: {name}"
                "（本项目与全局目录都没找到）")


def _import_roots(code: str) -> list[str]:
    src = VAR_RE.sub("X", code.replace("$${", "${"))
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    roots: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots += [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                continue
            if node.module:
                roots.append(node.module.split(".")[0])
    return list(dict.fromkeys(roots))


def _extra_sys_paths(code: str) -> list[str]:
    return re.findall(r"""sys\.path\.(?:insert|append)\(\s*\d*\s*,?\s*['"]([^'"]+)['"]""", code)


def check_code_imports(wf: dict, workspace: str, issues: list[str]) -> None:
    from importlib.machinery import PathFinder
    from importlib.util import find_spec
    base = Path(workspace) if workspace else Path.cwd()
    base_paths = [str(base), str(BACKEND_ROOT), str(REPO_ROOT), *map(str, sys.path)]
    for n in wf.get("nodes") or []:
        if n.get("type") != "code" or str(n.get("lang") or "python") != "python":
            continue
        code = str(n.get("code") or "")
        roots = _import_roots(code)
        if not roots:
            continue
        paths = list(base_paths)
        for extra in _extra_sys_paths(code):
            p = Path(extra)
            paths.append(str(p if p.is_absolute() else base / p))
        missing = []
        for m in roots:
            pass
            if m in sys.builtin_module_names:
                continue
            if find_spec(m) is not None:
                continue
            if PathFinder.find_spec(m, paths) is not None:
                continue
            missing.append(m)
        if missing:
            issues.append(
                f"code 节点 {n.get('id')} 依赖的模块找不到：{', '.join(missing)}"
                f"（解释器 {sys.version.split()[0]}，搜索路径含工作目录与仓库根）。"
                "如果依赖装在别的环境，请改用 exec 节点指定解释器")


def check_write_dirs(wf: dict, workspace: str, issues: list[str]) -> None:
    import os
    base = Path(workspace) if workspace else Path.cwd()
    for n in wf.get("nodes") or []:
        if n.get("type") != "write":
            continue
        raw = str(n.get("path") or "")
        if not raw or "${" in raw:
            continue
        p = Path(raw)
        if not p.is_absolute():
            p = base / p
        parent = p.parent
        while not parent.exists() and parent != parent.parent:
            parent = parent.parent
        if not os.access(parent, os.W_OK):
            issues.append(f"write 节点 {n.get('id')} 的输出目录不可写：{p.parent}")


def check_models(wf: dict, config, issues: list[str]) -> None:
    if config is None:
        return
    from ..provider.selection import check_spec
    model_types = ("llm", "condition", "subagent", "ocr", "image", "asr")
    for n in wf.get("nodes") or []:
        if str(n.get("type") or "") not in model_types:
            continue
        raw = str(n.get("model") or "").strip()
        if not raw or "${" in raw:
            continue
        _ok, err = check_spec(config, raw)
        if err:
            issues.append(f"节点 {n.get('id')} 的模型不可用：{err}")


def check_ops(wf: dict, workspace: str, issues: list[str]) -> None:
    from .ops import ops_for
    op_nodes = [n for n in wf.get("nodes") or []
                if str(n.get("type") or "") == "op"]
    if not op_nodes:
        return
    reg = ops_for(workspace)
    for where, err in reg.errors().items():
        issues.append(f"算子文件加载失败 {where}：{err[:200]}")
    for n in op_nodes:
        name = str(n.get("op") or "").strip()
        nid = n.get("id")
        if not name or "${" in name:
            continue
        if name in reg:
            continue
        near = difflib.get_close_matches(name, reg.names(), n=1)
        hint = f"；是不是 {near[0]}？" if near else ""
        issues.append(
            f"节点 {nid} 的算子 {name!r} 不存在"
            f"（已注册 {len(reg)} 个，放在 <项目>/.agent/ops/*.py）{hint}")


def check_reachability(wf: dict, issues: list[str]) -> None:
    from .validate import ValidateMixin

    nodes = wf.get("nodes") or []
    if not nodes:
        return
    ids = [str(n["id"]) for n in nodes]
    children: dict[str, list[str]] = {i: [] for i in ids}
    for src, dst in ValidateMixin._graph_edges(nodes, wf.get("edges")):
        if src in children and dst in children and dst not in children[src]:
            children[src].append(dst)
    pass
    pass
    from .nodes.human import parse_options
    for n in nodes:
        if n.get("type") != "human":
            continue
        src = str(n["id"])
        for _label, target in parse_options(n.get("options")):
            if target and target in children and target not in children[src]:
                children[src].append(target)

    entry = ids[0]
    seen = {entry}
    stack = [entry]
    while stack:
        cur = stack.pop()
        for nxt in children.get(cur, []):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)

    unreachable = [i for i in ids if i not in seen]
    if unreachable:
        pass
        pass
        pass
        pass
        issues.append(
            "警告：这些节点从入口走不到（不会执行）："
            + ", ".join(unreachable)
            + f"。入口是 {entry}；确认它们是不是忘了连线")

    sinks = [i for i in ids if not children.get(i)]
    if sinks and not any(i in seen for i in sinks):
        issues.append(
            "这张图没有任何可达的终点（sink）：跑完 final 会是空的。"
            f"入口 {entry} 能走到：{', '.join(sorted(seen)) or '无'}")


def check_back_edges(wf: dict, issues: list[str]) -> None:
    nodes = wf.get("nodes") or []
    has_control = any(n.get("type") in CONTROL_TYPES for n in nodes)
    if not has_control:
        return
    from .validate import ValidateMixin

    ids = {str(n["id"]) for n in nodes}
    order = {str(n["id"]): i for i, n in enumerate(nodes)}
    for src, dst in ValidateMixin._graph_edges(nodes, wf.get("edges")):
        if src not in ids or dst not in ids:
            continue
        pass
        if order[dst] >= order[src]:
            continue
        target = next((n for n in nodes if str(n["id"]) == dst), None)
        if target is None or target.get("maxVisits"):
            continue
        issues.append(
            f"警告：{src} → {dst} 是回边（指向上游），但 {dst} 没写 maxVisits。"
            "回边不收敛时会跑到默认上限 1000 次再结束，代价很大；"
            "建议给回边入口节点写 maxVisits")


def is_warning(issue: str) -> bool:
    return str(issue).startswith("警告：")


def check_workflow(wf: dict, *, inputs=None, preset_outputs=None, nodes=None,
                   workspace: str = "", resolve=None, global_dir=None,
                   human_mode: str = "ask", config=None) -> list[str]:
    issues: list[str] = []
    known_inputs = dict(inputs or {})
    if isinstance(preset_outputs, dict):
        pass
        known_inputs.update(preset_outputs)
    check_vars(wf, issues, runtime_inputs=known_inputs,
               extra_names=set(preset_outputs or {}) if isinstance(preset_outputs, dict) else set())
    check_human(wf, issues)
    check_models(wf, config, issues)
    check_docs(wf, workspace, issues)
    check_subflow(wf, resolve, issues)
    check_code_imports(wf, workspace, issues)
    check_write_dirs(wf, workspace, issues)
    check_ops(wf, workspace, issues)
    check_reachability(wf, issues)
    check_back_edges(wf, issues)
    pass
    has_control = any(n.get("type") in CONTROL_TYPES for n in wf.get("nodes") or [])
    if has_control:
        join_ids = {str(n.get("id")) for n in wf.get("nodes") or []
                    if str(n.get("type") or "") == "join"}
        for n in wf.get("nodes") or []:
            targets = set(map(str, n.get("parallel_next") or []))
            if targets and not (targets & join_ids):
                issues.append(
                    f"节点 {n.get('id')} 接了多个后继，但这张图含 condition/human/map；"
                    "这种图里的扇出必须汇合到 `join` 节点，否则改用 map 节点，"
                    "或把这一段拆成子工作流")
    if str(human_mode) == "deny":
        for n in wf.get("nodes") or []:
            if n.get("type") != "human":
                continue
            pass
            if str(n.get("auto") or "").strip().lower() in ("1", "true", "yes"):
                continue
            issues.append(
                f"这张图含人工闸门（节点 {n.get('id')}），当前是无人在场的运行方式"
                "（agent 工具/定时）。从画布运行，或传 human=auto-approve / auto-reject")
            break
    return issues
