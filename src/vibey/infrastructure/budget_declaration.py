# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Writes the no-cap declaration into `vibey.toml` as `[budget] ultra_no_cap` (ADR-0063).

The file is the operator's, so it is edited as text: the one key's line is replaced, or
added under `[budget]`, or a `[budget]` table is appended -- every other line, comment
and order is left as it was. The result is parsed back before it is written; a file
that would not parse is refused and left untouched.

The file records the declaration; the ledger event decides it. A `true` here with no
`UltraNoCapChanged` event behind it is ignored by the worker and reported by
`vibey ultra status`.
"""

import re
import tomllib
from pathlib import Path
from typing import Final

_KEY: Final = "ultra_no_cap"
_TABLE: Final = re.compile(r"^\s*\[\s*budget\s*\]\s*(#.*)?$")
_ANY_TABLE: Final = re.compile(r"^\s*\[")
_KEY_LINE: Final = re.compile(rf"^\s*{_KEY}\s*=")


class VibeyTomlBudgetDeclaration:
    """Declared by `interfaces/budget_declaration_interface.py`."""

    def read(self, path: Path) -> bool:
        """The declared value; `False` for a missing, unreadable or malformed file."""
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            return False
        table = data.get("budget")
        return isinstance(table, dict) and table.get(_KEY) is True

    def write(self, path: Path, enabled: bool) -> None:
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        updated = self.edit(text, enabled)
        tomllib.loads(updated)  # refuses a result that would not parse
        path.write_text(updated, encoding="utf-8")

    def edit(self, text: str, enabled: bool) -> str:
        line = f"{_KEY} = {'true' if enabled else 'false'}"
        lines = text.splitlines()
        in_budget = False
        header = None
        for index, current in enumerate(lines):
            if _ANY_TABLE.match(current):
                in_budget = bool(_TABLE.match(current))
                if in_budget:
                    header = index
                continue
            if in_budget and _KEY_LINE.match(current):
                lines[index] = line
                return "\n".join(lines) + "\n"
        if header is not None:
            lines.insert(header + 1, line)
            return "\n".join(lines) + "\n"
        prefix = "\n".join(lines).rstrip("\n")
        return f"{prefix}\n\n[budget]\n{line}\n" if prefix else f"[budget]\n{line}\n"
