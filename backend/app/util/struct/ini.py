from __future__ import annotations

import re

_HEADER = re.compile(r"^\s*\[(.+)\]\s*$")
_KEY = re.compile(r"^(\s*)([^=:;#\s][^=:]*?)(\s*[=:]\s*)(.*)$")


class IniError(ValueError):
    pass


def _split_inline(rest: str) -> tuple[str, str]:
    m = re.search(r"\s[;#]", rest)
    if not m:
        return rest.strip(), ""
    return rest[:m.start()].strip(), rest[m.start():].rstrip()


def ini_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list, tuple)):
        raise IniError(f"INI 的值只能是标量，收到 {type(value).__name__}；"
                       "要写嵌套结构请用 json / yaml 文件")
    return str(value)


class IniDoc:

    def __init__(self, text: str = "") -> None:
        self.eol = "\r\n" if "\r\n" in text else "\n"
        self.lines: list[str] = text.split(self.eol) if text else []
        if self.lines and self.lines[-1] == "":
            self.lines.pop()
        self.expected = self.mapping()

    pass

    def _section(self, name: str) -> tuple[int, int] | None:
        want = name.strip().lower()
        for i, line in enumerate(self.lines):
            m = _HEADER.match(line)
            if not m or m.group(1).strip().lower() != want:
                continue
            j = i + 1
            while j < len(self.lines) and not _HEADER.match(self.lines[j]):
                j += 1
            return i + 1, j
        return None

    def _is_cont(self, i: int) -> bool:
        line = self.lines[i]
        return bool(line[:1].isspace() and line.strip()
                    and line.lstrip()[:1] not in ";#")

    def _entries(self) -> list[dict]:
        out: list[dict] = []
        section = ""
        i, n = 0, len(self.lines)
        while i < n:
            head = _HEADER.match(self.lines[i])
            if head:
                section = head.group(1).strip()
                i += 1
                continue
            key = _KEY.match(self.lines[i]) if section else None
            if not key:
                i += 1
                continue
            last = i
            while last + 1 < n and self._is_cont(last + 1):
                last += 1
            value, comment = _split_inline(key.group(4))
            out.append({"section": section, "key": key.group(2).strip(),
                        "first": i, "last": last, "lead": key.group(1),
                        "prefix": key.group(1) + key.group(2) + key.group(3),
                        "value": value, "comment": comment})
            i = last + 1
        return out

    def _find(self, section: str, key: str, entries: list[dict]) -> dict | None:
        same_sec = [e for e in entries if e["section"].lower() == section.strip().lower()]
        for e in same_sec:
            if e["key"] == key:
                return e
        want = key.strip().lower()
        for e in same_sec:
            if e["key"].lower() == want:
                return e
        return None

    def mapping(self) -> dict[str, dict[str, str]]:
        out: dict[str, dict[str, str]] = {}
        for e in self._entries():
            body = e["value"]
            extra = [self.lines[k].strip() for k in range(e["first"] + 1, e["last"] + 1)]
            out.setdefault(e["section"], {})[e["key"]] = "\n".join([body] + extra).strip()
        return out

    def keys_of(self, section: str) -> list[str]:
        return [e["key"] for e in self._entries()
                if e["section"].lower() == section.strip().lower()]

    pass

    def set(self, section: str, key: str, value) -> None:
        text = ini_value(value)
        entries = self._entries()
        hit = self._find(section, key, entries)
        if hit:
            self._replace(hit, text)
        else:
            self._insert(section, key, text, entries)
        self.expected = self.mapping()

    def _replace(self, ent: dict, text: str) -> None:
        indent = ent["lead"] + "  "
        rows = [ent["prefix"] + text.split("\n")[0] + ent["comment"]]
        rows += [indent + line for line in text.split("\n")[1:]]
        self.lines[ent["first"]:ent["last"] + 1] = rows

    def _insert(self, section: str, key: str, text: str, entries: list[dict]) -> None:
        span = self._section(section)
        if span is None:
            self._new_section(section, key, text)
            return
        start, end = span
        same = [e for e in entries
                if e["section"].lower() == section.strip().lower()]
        pos = same[-1]["last"] + 1 if same else start
        rows = [f"{key} = {text.split(chr(10))[0]}"]
        rows += ["  " + line for line in text.split("\n")[1:]]
        self.lines[pos:pos] = rows

    def _new_section(self, section: str, key: str, text: str) -> None:
        if self.lines and self.lines[-1].strip():
            self.lines.append("")
        self.lines += [f"[{section}]", f"{key} = {text.split(chr(10))[0]}"]
        self.lines += ["  " + line for line in text.split("\n")[1:]]

    def delete(self, section: str, key: str) -> None:
        ent = self._find(section, key, self._entries())
        if not ent:
            have = ", ".join(self.keys_of(section)) or "（该段没有键）"
            raise IniError(f"[{section}] 里没有键 {key!r}；现有键：{have}")
        del self.lines[ent["first"]:ent["last"] + 1]
        self.expected = self.mapping()

    def render(self) -> str:
        if not self.lines:
            return ""
        return self.eol.join(self.lines) + self.eol

    @classmethod
    def from_mapping(cls, data: dict) -> "IniDoc":
        doc = cls("")
        for section, body in (data or {}).items():
            if not isinstance(body, dict):
                raise IniError(f"新建 INI 时 {section!r} 的值必须是对象，"
                               f"收到 {type(body).__name__}")
            for key, value in body.items():
                doc.set(str(section), str(key), value)
        return doc
