# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind reading `[hub]`.

Mirrors `vibey/infrastructure/hub/settings.py` (ADR-0016). Interfaces declare; they never
consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path

    from vibey.infrastructure.hub.settings import HubSettings


@runtime_checkable
class HubSettingsLoaderInterface(Protocol):
    """Reads `[hub]`; closed defaults for a missing file or table."""

    def load(self, path: Path) -> HubSettings:
        """`[hub]` from the vibey.toml at `path`. Raises `ConfigError` when malformed."""
        ...

    def load_trusted(self, user: Path, project: Path) -> HubSettings:
        """`[hub]` from the person's own vibey.toml at `user`, with `agent_scopes` narrowed by
        the project's at `project` (never widened; no other project key is heard). Raises
        `ConfigError` when either is malformed."""
        ...

    def from_table(self, table: dict[str, Any]) -> HubSettings:
        """`[hub]` from an already-parsed table."""
        ...
