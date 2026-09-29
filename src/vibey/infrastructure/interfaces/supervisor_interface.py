# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `vibey/infrastructure/supervisor.py` (ADR-0016). Declares only."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from vibey.domain.supervisor import SupervisorSettings


@runtime_checkable
class SupervisorSettingsLoaderInterface(Protocol):
    """Reads `[supervisor]`; refuses an unknown key or a mistyped value by name."""

    def load(self, path: Path) -> SupervisorSettings:
        """The table in `path`, or every default when the file does not exist."""
        ...

    def from_mapping(self, section: Mapping[str, object]) -> SupervisorSettings: ...


@runtime_checkable
class SupervisorHostInterface(Protocol):
    """One platform's places, and its service manager's answer about one unit."""

    platform: str

    def unit_dir(self) -> Path:
        """Where the service manager looks for this user's units."""
        ...

    def unit_path(self, label: str, out: Path | None = None) -> Path: ...

    def default_log_dir(self) -> Path: ...

    def default_env_file(self) -> Path: ...

    def volatile_roots(self) -> tuple[str, ...]:
        """Directories a reboot or the system empties (10.h)."""
        ...

    def state(self, label: str) -> str:
        """`running`, `stopped...`, `not loaded`, or `unknown: ...`; never a guess."""
        ...

    def load_commands(self, labels: Sequence[str], units: Sequence[Path]) -> list[str]:
        """The operator's own commands that load the units; vibey never runs them."""
        ...
