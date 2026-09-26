# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for the sovereign heartbeat's timer, stood up from the tree (vibey ADR-0016).

Nothing here loads or unloads a unit unless it is asked to in so many words (`load=True`,
`apply=True`); every other call reads or writes files only.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

from vibey_gh.interfaces.sovereign_runner_interface import RunnerFileInterface


@runtime_checkable
class BeatRecordInterface(Protocol):
    """What one `sovereign --beat` did, as `heartbeat status` reads it back."""

    @property
    def at(self) -> float:
        """When, in seconds since the epoch."""
        ...

    @property
    def published(self) -> bool: ...

    @property
    def resting_until(self) -> float | None:
        """While the Sabbath holds (8.i), the epoch second it ends; otherwise None."""
        ...

    @property
    def reason(self) -> str:
        """Why it published or withheld, including what a refused push said."""
        ...

    def write(self, path: Path) -> None:
        """Atomically, so a status read never sees half a record."""
        ...


@runtime_checkable
class HeartbeatPlanInterface(Protocol):
    """Everything one heartbeat install writes, and what the timer runs."""

    @property
    def label(self) -> str: ...

    @property
    def scheduler(self) -> str:
        """`launchd` or `systemd`."""
        ...

    @property
    def remote_url(self) -> str:
        """The repository the heartbeat is published to, as the clone's `origin`."""
        ...

    @property
    def python(self) -> str: ...

    @property
    def clone(self) -> Path:
        """The repository the timer owns and pushes from."""
        ...

    @property
    def log(self) -> Path: ...

    @property
    def record(self) -> Path:
        """Where each beat records what it did, for `status` to read."""
        ...

    @property
    def interval_minutes(self) -> int: ...

    @property
    def files(self) -> Sequence[RunnerFileInterface]:
        """The clone's gate and configuration, then the unit or units."""
        ...


@runtime_checkable
class HeartbeatTimerInterface(Protocol):
    """Renders, installs, reports on and removes the heartbeat timer the tree declares."""

    def clone_dir(self) -> tuple[Path | None, str]:
        """(the repository the heartbeat is pushed from, problem)."""
        ...

    def interval_minutes(self) -> tuple[int, str]:
        """(minutes between beats, problem): at least one, at most half the trust window."""
        ...

    def render(self, python: str | None = None) -> tuple[HeartbeatPlanInterface | None, str]:
        """The plan, or `(None, problem)`. Refuses an interpreter, a `vibey_gh`, a log or a
        clone under a temporary directory or inside a git work tree, naming the key that
        moves it. `python` overrides the declared or running interpreter."""
        ...

    def install(self, plan: HeartbeatPlanInterface, *, load: bool) -> tuple[list[str], bool]:
        """Create or repair the clone and write its gate; refuse unless that gate lets a
        synthetic heartbeat through; then write the units and, with `load`, (re)load them.
        One line per act, and whether everything asked for happened."""
        ...

    def next_steps(self, plan: HeartbeatPlanInterface) -> list[str]:
        """The exact commands that load what `install` wrote, in order."""
        ...

    def status(self) -> tuple[list[str], bool]:
        """Installed and current, the clone and its gate's answer to a synthetic heartbeat,
        loaded (and lingering, under systemd), and the last beat's age and result; healthy
        only when all hold and the last beat was published inside the trust window."""
        ...

    def uninstall(self, *, apply: bool) -> list[str]:
        """Unload the timer and move its units and its clone aside; without `apply`, only say
        so."""
        ...
