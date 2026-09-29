# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam of `cli/supervisor.py` (ADR-0016). Interfaces declare; they never consume."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


class SupervisorCommandInterface(Protocol):
    """`vibey supervisor` and its `vibey doctor` lines (#1189)."""

    def install(self, *, platform: str, repo: Path, out: Path | None, config: Path | None) -> int:
        """Write the units and print the operator's commands that load them. 0, 2 on an
        unknown platform, 78 on a setting no service could run with."""
        ...

    def status(self, *, platform: str, config: Path | None) -> int:
        """Print each service's state; 0 only when every one is running."""
        ...

    def doctor_lines(self) -> tuple[list[str], bool]:
        """What `vibey doctor` prints, and False when a line is a FAIL."""
        ...

    def exec_(self, env_file: Path, argv: Sequence[str]) -> int:
        """Replace this process with `argv`, in the environment the file declares. Returns
        only when it could not: 2 with no command, 78 on the file, 127 on the command."""
        ...
