# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The `vibey` a session runs: the one installed beside this process's own Python (SP-LOOPS
Phase 6).

The runners ship in vibey's own package, so the `vibey` console script that belongs with a
runner -- or with the worker -- sits beside its own Python. A session does not have vibey's
environment on its PATH, and a bare `vibey` could find another installed copy, one that cannot
reach the hub; so the sibling script is run when it is there. Without one -- a runner installed
on its own -- the `vibey` on PATH is run, else the bare name. The local runner's web tools run
`search` and `fetch` with it, and the worker starts each claudeloop run's `vibey-web` connector
with it.

Declared by `interfaces/vibey_command_interface.py::VibeyCommandInterface`.
"""

from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Final


class VibeyCommand:
    """Declared by `interfaces/vibey_command_interface.py::VibeyCommandInterface`."""

    def __init__(
        self,
        *,
        executable: str = sys.executable,
        which: Callable[[str], str | None] = shutil.which,
    ) -> None:
        self._executable = executable
        self._which = which

    def resolve(self) -> str:
        sibling = Path(self._executable).parent / "vibey"
        if sibling.is_file() and os.access(sibling, os.X_OK):
            return str(sibling)
        return self._which("vibey") or "vibey"


VIBEY_COMMAND: Final[VibeyCommand] = VibeyCommand()
