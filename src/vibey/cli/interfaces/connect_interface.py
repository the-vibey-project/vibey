# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for `vibey connect`: registering vibey with frontier LLM clients (ADR-0100)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable


@runtime_checkable
class ConnectCommandInterface(Protocol):
    def run(
        self,
        *,
        clients: Sequence[str] | None,
        yes: bool,
        dry_run: bool,
        list_clients: bool,
    ) -> None:
        """List supported clients, preview the registration plan, or apply it with backup."""
        ...
