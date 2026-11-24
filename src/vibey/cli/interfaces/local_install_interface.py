# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind `vibey install --database` and `vibey install --model`.

Mirrors `vibey/cli/local_install.py` (ADR-0016). Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LocalInstallCommandInterface(Protocol):
    def database(
        self, *, db_name: str, owner_role: str, app_role: str, admin_user: str | None
    ) -> int:
        """Make the local database, its two roles and its migrations; the exit code."""
        ...

    def model(self, *, wait_seconds: float) -> int:
        """Pull the model the local loop runs into Ollama, unless it is there; the exit code."""
        ...
