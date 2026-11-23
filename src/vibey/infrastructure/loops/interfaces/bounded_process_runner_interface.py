# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over running one command with bounded output and a whole-group kill (SP-LOOPS Task 7
review finding 5). Implemented by `bounded_process_runner.py`. Interfaces declare; they never
consume."""

from __future__ import annotations

import subprocess  # nosec B404 - names the result type only
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class BoundedProcessRunnerInterface(Protocol):
    def run(
        self, argv: Sequence[str], env: Mapping[str, str], cwd: Path, timeout: float
    ) -> subprocess.CompletedProcess[str]:
        """Runs `argv` (never through a shell) with exactly `env`, in `cwd`, with no stdin, in
        a process group of its own. Returns at most the first `output_bytes` of its stdout and
        the last `output_bytes` of its stderr. Past `timeout` seconds the whole group is killed
        and `subprocess.TimeoutExpired` raised; any other exception while it waits (a Ctrl-C)
        kills the whole group too and is raised again; `FileNotFoundError` when `argv[0]` is not
        there."""
        ...
