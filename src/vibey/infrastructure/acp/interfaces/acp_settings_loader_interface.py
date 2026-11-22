# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `vibey/infrastructure/acp/acp_settings_loader.py` (ADR-0016). Declares only."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from vibey.domain.acp.settings import AcpSettings


@runtime_checkable
class AcpSettingsLoaderInterface(Protocol):
    """Reads `[acp]`; refuses an unknown key or an out-of-bound value by name."""

    def load(self, path: Path) -> AcpSettings:
        """The table in `path`, or every default when the file or the table is absent."""
        ...

    def load_trusted(self, user: Path, project: Path) -> AcpSettings:
        """`vibey acp`'s settings: the user's `[acp]` in `user` (their configuration folder),
        narrowed -- never widened -- by the project's in `project` (ADR-0101). Either file may
        be absent; a malformed one is still a `ConfigError`."""
        ...

    def from_mapping(self, section: Mapping[str, object]) -> AcpSettings:
        """The table as already parsed; `ConfigError` names the offending key."""
        ...

    def hub_settings(self, path: Path) -> AcpSettings:
        """The defaults with only the keys the hub reads (`HUB_KEYS`) taken from `path`, each
        checked; the editor's keys are never read, so a mistake in one never stops the hub."""
        ...
