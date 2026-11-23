# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over `[inputs]`: who may set how much a project's run inputs hold (SP-LOOPS Phase 3,
ADR-0018 and ADR-0101). Interfaces declare; they never consume."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from vibey.application.dto import TrustedRunInputsSettings


@runtime_checkable
class RunInputsSettingsLoaderInterface(Protocol):
    def load(self, user_config: Path, project_config: Path | None) -> TrustedRunInputsSettings:
        """The limits from `user_config`'s `[inputs]` (the person's own `vibey.toml`; a missing
        file or table is the defaults). A non-empty `[inputs]` in `project_config` is ignored
        and named in one notice; a project file that is absent, has no such table, or is the
        person's own file changes nothing. Raises `ConfigError` naming the person's file for a
        table that cannot be read or a value `RunInputsSettings.from_table` refuses."""
        ...
