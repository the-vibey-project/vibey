# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind `vibey/infrastructure/state/settings.py` (ADR-0016, ADR-0086).
Interfaces declare; they never consume."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.state_sync import TableSpec


@runtime_checkable
class StateSyncSettingsInterface(Protocol):
    """Where the state syncs to, with what key, from which database."""

    @property
    def repository(self) -> str: ...

    @property
    def branch(self) -> str: ...

    @property
    def path(self) -> str: ...

    @property
    def pg_url(self) -> str: ...

    @property
    def key(self) -> str: ...

    @property
    def key_file(self) -> str: ...

    @property
    def tables(self) -> tuple[TableSpec, ...]: ...

    @property
    def attempts(self) -> int: ...


@runtime_checkable
class StateSyncSettingsLoaderInterface(Protocol):
    """Reads the settings from an environment."""

    def load(self, environ: Mapping[str, str]) -> StateSyncSettingsInterface: ...
