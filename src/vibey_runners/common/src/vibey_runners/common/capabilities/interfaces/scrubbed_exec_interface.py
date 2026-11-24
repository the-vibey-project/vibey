# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam a runner starts a local MCP server through, with only the variables the person
allowed (SP-LOOPS Phase 4, R7)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol, runtime_checkable


@runtime_checkable
class ScrubbedExecInterface(Protocol):
    def run(self, argv: Sequence[str], environ: Mapping[str, str]) -> int:
        """Parse `--allow NAME` (repeatable), then `--`, then the command; resolve the command
        on `environ`'s own `PATH`; then replace this process with it, its environment holding
        only the allowed names that `environ` has. Returns only on refusal: 2 for a malformed
        argv, 78 for an allowed name that carries a secret, 127 for a command not found. What
        it writes names variables and the command, never a value."""
        ...
