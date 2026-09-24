# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for standing the sovereign review runner up from the tree (vibey ADR-0016)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class RunnerFileInterface(Protocol):
    """One file the installer writes: where, exactly what, and whether it is executable."""

    @property
    def path(self) -> Path: ...

    @property
    def text(self) -> str: ...

    @property
    def executable(self) -> bool: ...


@runtime_checkable
class RunnerPlanInterface(Protocol):
    """Everything one install writes, resolved from `[runners]` against one home."""

    @property
    def label(self) -> str: ...

    @property
    def repository(self) -> str: ...

    @property
    def repo_url(self) -> str: ...

    @property
    def plist(self) -> Path: ...

    @property
    def files(self) -> Sequence[RunnerFileInterface]: ...


@runtime_checkable
class LaunchAgentUnitInterface(Protocol):
    """An installed LaunchAgent as its plist describes it."""

    @property
    def path(self) -> Path: ...

    @property
    def label(self) -> str: ...

    @property
    def repo_url(self) -> str: ...


@runtime_checkable
class SovereignRunnerInterface(Protocol):
    """Renders, installs, checks and removes the runner the tree declares.

    Nothing here loads or unloads a LaunchAgent unless it is asked to in so many words
    (`load=True`, `apply=True`); every other call reads or writes files only.
    """

    def render(self) -> tuple[RunnerPlanInterface | None, str]:
        """The plan, or `(None, problem)` when the configuration cannot produce one."""
        ...

    def install(self, plan: RunnerPlanInterface, *, load: bool) -> list[str]:
        """Write every file; with `load`, replace the running agent. One line per act."""
        ...

    def next_steps(self, plan: RunnerPlanInterface) -> list[str]:
        """The exact commands the operator runs after an install, in order."""
        ...

    def check(self, plan: RunnerPlanInterface) -> list[str]:
        """Every way the host differs from the tree, the credential included; [] when none."""
        ...

    def credential_problems(self) -> list[str]:
        """Why the runner's dedicated gh login is unusable by launchd; [] when it is usable."""
        ...

    def strays(self, plan: RunnerPlanInterface) -> tuple[LaunchAgentUnitInterface, ...]:
        """Agents under `[runners] unit_prefix` that the tree no longer declares."""
        ...

    def remove(self, units: Sequence[LaunchAgentUnitInterface], *, apply: bool) -> list[str]:
        """Unload each unit and move its plist aside; without `apply`, only say so."""
        ...

    def uninstall(self, plan: RunnerPlanInterface, *, apply: bool) -> list[str]:
        """Remove the declared agent and the files the install wrote; dry-run by default."""
        ...
