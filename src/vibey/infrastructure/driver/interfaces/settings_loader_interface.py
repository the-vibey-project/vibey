# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `vibey/infrastructure/driver/settings_loader.py` (ADR-0016). Declares only."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from vibey.domain.failover import FailoverSettings


@runtime_checkable
class FailoverSettingsLoaderInterface(Protocol):
    def load(self, path: Path) -> FailoverSettings: ...

    def from_mapping(self, section: Mapping[str, object]) -> FailoverSettings: ...
