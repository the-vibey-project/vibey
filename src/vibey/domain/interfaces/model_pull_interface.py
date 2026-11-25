# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for turning Ollama's pull stream into readable lines.

Mirrors `vibey/domain/model_pull.py` (ADR-0016). Interfaces declare; they never consume.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable


@runtime_checkable
class PullProgressInterface(Protocol):
    def line(self, event: Mapping[str, object]) -> str | None:
        """The line to print for one pull event, or None when it adds nothing."""
        ...
