# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for whether the pre-commit framework's own hooks are installed in a clone (ADR-0016)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from vibey_gh.config import GhConfig


@runtime_checkable
class HookInspectorInterface(Protocol):
    """Reads the framework's hook files from the clone's git common directory."""

    def common_dir(self, cfg: GhConfig) -> Path | None:
        """The git common directory (shared by every linked worktree), or None outside a clone."""
        ...

    def stages(self, cfg: GhConfig) -> dict[str, str]:
        """Each framework stage's state: `installed`, `missing` or `foreign`.

        Empty when the repository declares no pre-commit framework or this is not a clone:
        there is then nothing to say about, and a clone is not accused of lacking hooks the
        repository never asked for.
        """
        ...

    def problems(self, cfg: GhConfig) -> list[str]:
        """One sentence per stage that is not `installed`, each naming the command that fixes it."""
        ...
