# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for the "LLM tooling" lines (SP-ACP).

Mirrors `vibey/cli/llm_tooling.py` (ADR-0016). Interfaces declare; they never consume.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable


@runtime_checkable
class LlmToolingSectionInterface(Protocol):
    def lines(self, client_ids: Sequence[str] | None = None) -> list[str]:
        """One cleaned `MARK client:surface state: detail` line per client and surface (every
        detected client's when none is named), or one `UNKNOWN` line when none is installed."""
        ...

    def doctor_lines(self) -> tuple[list[str], bool]:
        """The detected clients' lines as a doctor section, which never fails."""
        ...
