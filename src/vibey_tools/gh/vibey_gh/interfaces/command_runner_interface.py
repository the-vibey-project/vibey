# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for running one fixed external command (ADR-0016)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class CommandResult:
    """What a command did. `returncode` 127 means it could not be started at all."""

    returncode: int
    stdout: str = ""
    stderr: str = ""

    @property
    def output(self) -> str:
        return "\n".join(part for part in (self.stdout.strip(), self.stderr.strip()) if part)


@runtime_checkable
class CommandRunnerInterface(Protocol):
    """Runs an argv, never a shell string, so a test never touches the real machine."""

    def run(
        self, argv: Sequence[str], cwd: Path, env: Mapping[str, str] | None = None
    ) -> CommandResult:
        """Run `argv` in `cwd`; `env` is added to the inherited environment."""
        ...
