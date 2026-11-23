# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads the `---`-fenced frontmatter that opens a SKILL.md, stdlib only.

Not a YAML parser: the subset skills are written in. Top-level `key: value` lines; a value that is
plain (continued on indented lines, folded with spaces), double-quoted (JSON escapes), single-quoted
(`''` for a quote), or a `>` / `|` block scalar on the indented lines below. Blank lines and `#`
comment lines at the margin are allowed. Anything else -- no opening fence, no closing fence, an
indented line with no key above it, a line that is not `key: value`, a key given twice, a quoted
value that does not close -- is refused with a reason, which becomes the reason the skill is
skipped (Review Focus 5). The text is already capped by the reader, so no line or block is
unbounded. Declared by `interfaces/frontmatter_interface.py::SkillFrontmatterInterface`.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Final

from vibey_runners.common.capabilities.frontmatter_error import FrontmatterError

FENCE: Final = "---"
_KEY_LINE: Final = re.compile(r"([A-Za-z_][A-Za-z0-9_-]*):(?:[ \t]+(.*))?")
_BLOCK: Final = frozenset({">", ">-", ">+", "|", "|-", "|+"})


class SkillFrontmatter:
    """Declared by `interfaces/frontmatter_interface.py::SkillFrontmatterInterface`."""

    def parse(self, text: str) -> Mapping[str, str]:
        lines = text.lstrip("﻿").replace("\r\n", "\n").split("\n")
        if lines[0].rstrip() != FENCE:
            raise FrontmatterError("does not start with frontmatter (a --- line)")
        end = next((i for i in range(1, len(lines)) if lines[i].rstrip() == FENCE), None)
        if end is None:
            raise FrontmatterError("frontmatter is not closed (no second --- line)")
        raw: dict[str, tuple[str, list[str]]] = {}
        current: str | None = None
        for number, line in enumerate(lines[1:end], start=2):
            if line[:1] in (" ", "\t") or not line.strip():
                if current is None and line.strip():
                    raise FrontmatterError(f"malformed frontmatter at line {number}")
                if current is not None:
                    raw[current][1].append(line)
                continue
            if line.startswith("#"):
                continue
            match = _KEY_LINE.fullmatch(line.rstrip())
            if match is None or match.group(1) in raw:
                raise FrontmatterError(f"malformed frontmatter at line {number}")
            current = match.group(1)
            raw[current] = ((match.group(2) or "").strip(), [])
        return {key: self._value(key, first, rest) for key, (first, rest) in raw.items()}

    @classmethod
    def _value(cls, key: str, first: str, rest: Sequence[str]) -> str:
        if first in _BLOCK:
            return cls._block(first, [line.strip() for line in rest])
        joined = " ".join([first, *(line.strip() for line in rest if line.strip())]).strip()
        if joined.startswith('"'):
            return cls._double(key, joined)
        if joined.startswith("'"):
            return cls._single(key, joined)
        return joined

    @staticmethod
    def _block(style: str, body: list[str]) -> str:
        while body and not body[-1]:
            body.pop()
        if style.startswith("|"):
            return "\n".join(body)
        folded = ""
        for line in body:
            if not line:
                folded += "\n"
            else:
                folded += (" " if folded and not folded.endswith("\n") else "") + line
        return folded

    @staticmethod
    def _double(key: str, joined: str) -> str:
        try:
            # JSON text that starts with a quote and parses is a string, and only a string.
            value: str = json.loads(joined)
        except ValueError as exc:
            raise FrontmatterError(f"{key} is not a valid double-quoted string") from exc
        return value

    @staticmethod
    def _single(key: str, joined: str) -> str:
        inner = joined[1:-1]
        if len(joined) < 2 or not joined.endswith("'") or "'" in inner.replace("''", ""):
            raise FrontmatterError(f"{key} is not a valid single-quoted string")
        return inner.replace("''", "'")
