from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass, field
from typing import Any

from ..jsonfix import loads_lenient
from .path import StructError, plain, same_value
from .ini import IniDoc

__all__ = ["Style", "dump", "load", "verify", "yaml_available"]

_INDENT_RE = re.compile(r"\n([ \t]+)\S")


def yaml_available() -> str:
    try:
        import ruamel.yaml
        return "ruamel"
    except ImportError:
        try:
            import yaml
            return "pyyaml"
        except ImportError:
            return ""


@dataclass
class Style:

    fmt: str
    eol: str = "\n"
    trailing: bool = True
    indent: str = "  "
    ensure_ascii: bool = False
    yaml_engine: str = ""
    yaml_indent: tuple[int, int, int] = (2, 4, 2)
    meta: dict = field(default_factory=dict)


def _detect_indent(text: str) -> str:
    for line in text.splitlines():
        if not line.strip():
            continue
        m = re.match(r"^([ \t]+)", line)
        if m:
            return "\t" if "\t" in m.group(1) else " " * len(m.group(1))
    return "  "


def _detect_ensure_ascii(text: str) -> bool:
    return "\\u" in text and not any(ord(c) > 0x2E80 for c in text[:2000])


def _style(fmt: str, text: str) -> Style:
    st = Style(fmt=fmt)
    if not text:
        return st
    st.eol = "\r\n" if "\r\n" in text else "\n"
    st.trailing = text.endswith(("\n", "\r"))
    st.indent = _detect_indent(text)
    st.ensure_ascii = _detect_ensure_ascii(text)
    if fmt == "yaml":
        st.yaml_engine = yaml_available()
        st.yaml_indent = _detect_yaml_indent(text)
    return st


def _detect_yaml_indent(text: str) -> tuple[int, int, int]:
    map_ind, seq_ind, offset = 2, 4, 2
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^( +)(- )", line)
        if m:
            off = len(m.group(1))
            offset, seq_ind = off, off + 2
            break
        m = re.match(r"^( +)\S", line)
        if m:
            map_ind = len(m.group(1))
            break
    return map_ind, seq_ind, offset


def _ruamel(style: Style):
    if style.yaml_engine == "ruamel":
        from ruamel.yaml import YAML
        y = YAML(typ="rt")
        y.preserve_quotes = True
        y.width = 4096
        y.indent(mapping=style.yaml_indent[0], sequence=style.yaml_indent[1],
                 offset=style.yaml_indent[2])
        return y
    import yaml
    return yaml


pass

def load(text: str, fmt: str) -> tuple[Any, Style]:
    style = _style(fmt, text)
    if fmt == "ini":
        doc = IniDoc(text)
        return doc, style
    if not text.strip():
        return ([] if fmt == "jsonl" else {}), style
    if fmt == "jsonl":
        return _load_jsonl(text), style
    if fmt == "json":
        return _load_json(text), style
    if fmt == "yaml":
        return _load_yaml(text, style), style
    raise StructError(f"不支持的格式：{fmt}")


def _boom(fmt: str, err: str) -> StructError:
    return StructError(f"原文件不是合法 {fmt}（{err}）；先用 f_read 看一遍，"
                       f"或传 op=replace 整份重写" if fmt != "ini" else
                       f"原 INI 解析失败：{err}")


def _load_json(text: str) -> Any:
    try:
        return json.loads(text)
    except ValueError:
        pass
    value, err, _note = loads_lenient(text, scene="raw")
    if err:
        raise _boom("json", err)
    return value


def _load_jsonl(text: str) -> list:
    items: list = []
    for i, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            items.append(json.loads(line))
            continue
        except ValueError:
            pass
        value, err, _note = loads_lenient(line, scene="raw")
        if err:
            raise StructError(f"JSONL 第 {i} 行解析失败（{err}）")
        items.append(value)
    return items


def _load_yaml(text: str, style: Style) -> Any:
    if style.yaml_engine == "ruamel":
        try:
            return _ruamel(style).load(text)
        except Exception as e:
            raise _boom("yaml", str(e)) from None
    from ..yamlfix import loads_yaml_lenient
    value, err, _note = loads_yaml_lenient(text)
    if err:
        raise _boom("yaml", err)
    return value


pass

def dump(doc: Any, style: Style) -> str:
    fmt = style.fmt
    if fmt == "ini":
        return _fit(doc.render(), style)
    if fmt == "jsonl":
        body = "\n".join(json.dumps(x, ensure_ascii=style.ensure_ascii) for x in doc)
        return _fit(body, style)
    if fmt == "json":
        try:
            body = json.dumps(doc, ensure_ascii=style.ensure_ascii,
                              indent=style.indent, allow_nan=False)
        except (TypeError, ValueError) as e:
            raise StructError(
                f"这个值无法写成 JSON（{e}）。常见原因：nan/inf 不能出现在 JSON 里，"
                "改用 null 或写成字符串；不能序列化的对象请确认它是纯 dict/list/str/数字/布尔") from None
        return _fit(body, style)
    if fmt == "yaml":
        return _fit(_dump_yaml(doc, style), style)
    raise StructError(f"不支持的格式：{fmt}")


def _dump_yaml(doc: Any, style: Style) -> str:
    doc = _quote_ambiguous(doc, style)
    engine = _ruamel(style)
    if style.yaml_engine == "ruamel":
        buf = io.StringIO()
        engine.dump(doc, buf)
        return buf.getvalue().rstrip("\n")
    return engine.safe_dump(doc, allow_unicode=True, sort_keys=False,
                           default_flow_style=False, width=4096).rstrip("\n")


_SAFE_LOAD = None


def _is_ambiguous(s: str) -> bool:
    global _SAFE_LOAD
    try:
        if _SAFE_LOAD is None:
            import yaml
            _SAFE_LOAD = yaml.safe_load
        got = _SAFE_LOAD(s)
    except Exception:
        return True
    return not (isinstance(got, str) and got == s)


def _quote_ambiguous(doc: Any, style: Style) -> Any:
    if style.yaml_engine != "ruamel" or isinstance(doc, (str, bytes)):
        return doc
    try:
        from ruamel.yaml.scalarstring import DoubleQuotedScalarString as DQ
    except ImportError:
        return doc
    if isinstance(doc, dict):
        for k in list(doc):
            v = doc[k]
            if isinstance(v, str) and not isinstance(v, DQ) and _is_ambiguous(v):
                doc[k] = DQ(v)
            else:
                _quote_ambiguous(v, style)
    elif isinstance(doc, list):
        for i, v in enumerate(doc):
            if isinstance(v, str) and not isinstance(v, DQ) and _is_ambiguous(v):
                doc[i] = DQ(v)
            else:
                _quote_ambiguous(v, style)
    return doc


def _fit(body: str, style: Style) -> str:
    body = body.replace("\r\n", "\n").replace("\r", "\n")
    if style.eol != "\n":
        body = body.replace("\n", style.eol)
    if style.trailing and not body.endswith(style.eol):
        body += style.eol
    if not style.trailing:
        body = body.rstrip("\r\n")
    return body


pass

def verify(text: str, style: Style, expected: Any) -> str | None:
    try:
        got = IniDoc(text).mapping() if style.fmt == "ini" else load(text, style.fmt)[0]
    except Exception as e:
        return f"写回自检失败：生成的文件读不回来（{type(e).__name__}: {e}）"
    if same_value(plain(got), plain(expected)):
        return None
    return ("写回自检失败：落盘后再读回的值与预期不一致"
            "（可能被序列化器改写了，如 yes/on 变成布尔）。未写入。")
