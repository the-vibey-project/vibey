# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The `vibey` a session's web tools run `search` and `fetch` with.

qwenloop ships in vibey's own package, so the `vibey` console script that belongs with this
runner sits beside this runner's own Python. A session does not have vibey's environment on its
PATH, and a bare `vibey` could find another installed copy, one that cannot reach the hub; so the
sibling script is run when it is there (vibey finds its own launcher the same way). Without one
-- qwenloop installed on its own -- the `vibey` on PATH is run, else the bare name. Before
SP-LOOPS Phase 6 the worker named the command in the session's environment
(`WEBSEARCH_COMMAND`); a session is now given only the hub's address and its token file's path.

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
