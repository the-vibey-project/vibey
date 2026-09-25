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
class RegisteredRunnerInterface(Protocol):
    """One self-hosted runner as the forge lists it for the repository."""

    @property
    def name(self) -> str: ...

    @property
    def online(self) -> bool: ...

    @property
    def busy(self) -> bool: ...

    @property
    def labels(self) -> tuple[str, ...]: ...


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

    def install(self, plan: RunnerPlanInterface, *, load: bool) -> tuple[list[str], bool]:
        """Write every file; with `load`, replace the running agent.

        One line per act, and whether everything asked for happened: false when launchd
        refused to load the agent.
        """
        ...

    def next_steps(self, plan: RunnerPlanInterface) -> list[str]:
        """The exact commands the operator runs after an install, in order."""
        ...

    def check(self, plan: RunnerPlanInterface) -> list[str]:
        """Every way the host differs from the tree, the credential included; [] when none."""
        ...

    def credential_problems(self, plan: RunnerPlanInterface) -> list[str]:
        """Why the runner's dedicated gh login is unusable by launchd, or rejected by the
        plan's host; [] only when GitHub accepts it. Never includes the token."""
        ...

    def registered_runners(
        self, plan: RunnerPlanInterface
    ) -> tuple[Sequence[RegisteredRunnerInterface], str]:
        """Every runner the forge lists for the plan's repository, read with the runner's own
        login, and `""`; or `((), problem)` when the listing could not be read. Never
        includes the token or anything the client said about it."""
        ...

    def strays(self, plan: RunnerPlanInterface) -> tuple[LaunchAgentUnitInterface, ...]:
        """Agents under `[runners] unit_prefix` that the tree no longer declares -- never the
        declared runner's, and never its heartbeat timer's."""
        ...

    def remove(self, units: Sequence[LaunchAgentUnitInterface], *, apply: bool) -> list[str]:
        """Unload each unit and move its plist aside; without `apply`, only say so."""
        ...

    def uninstall(self, plan: RunnerPlanInterface, *, apply: bool) -> list[str]:
        """Remove the declared agent and the files the install wrote; dry-run by default."""
        ...
