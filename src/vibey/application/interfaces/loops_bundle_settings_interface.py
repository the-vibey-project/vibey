# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over `[loops]`: who may say what a loop is given (SP-LOOPS Task 3, ADR-0101)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from vibey.application.dto import TrustedLoopsBundle


@runtime_checkable
class LoopsBundleSettingsInterface(Protocol):
    def load(self, user_config: Path, project_config: Path | None) -> TrustedLoopsBundle:
        """The bundle from `user_config` (the person's own `vibey.toml`), narrowed by the
        `disable` list of `project_config`'s `[loops]`. Every other project key is dropped and
        named in the result's notices. A project file that is absent, or is the person's own
        file, changes nothing. Raises `ConfigError` naming the file for a table that cannot be
        read; a missing user file is the default bundle."""
        ...
