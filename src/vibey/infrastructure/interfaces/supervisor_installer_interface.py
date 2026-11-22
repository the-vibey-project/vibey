# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `vibey/infrastructure/supervisor_installer.py` (ADR-0016). Declares only."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from vibey.application.acp.dto import UnitOutcome
    from vibey.domain.supervisor import SupervisedService, SupervisorPaths, SupervisorSettings


@runtime_checkable
class SupervisorInstallerInterface(Protocol):
    """Resolves a supervised unit's paths and writes its file, for `vibey supervisor install`
    and for `vibey acp`."""

    def paths(self, settings: SupervisorSettings, repo: Path) -> SupervisorPaths:
        """Every place a plan needs, absolute. Raises ValueError, naming the key to change,
        for `vibey` not found, a path on volatile storage or in a linked worktree (10.h), or a
        delivery bridge missing from `repo`."""
        ...

    def env_file(self, path: Path, template: str) -> bool:
        """Create `path` from `template`, readable by its owner alone, never through a link;
        whether it was created (False when anything already has that name)."""
        ...

    def write(
        self,
        services: Sequence[SupervisedService],
        settings: SupervisorSettings,
        *,
        out: Path | None,
        overwrite: bool,
        path_env: str,
    ) -> tuple[UnitOutcome, ...]:
        """Write each service's unit into `out`, or the service manager's own directory, one
        outcome per service: `created`, `unchanged`, `updated` (only with `overwrite`),
        `kept-differing` (an existing unit left as it is, without `overwrite`) or `failed`.
        Atomic, mode 0644, never through a symbolic link. Raises ValueError, before writing
        anything, for a value no unit can carry."""
        ...
