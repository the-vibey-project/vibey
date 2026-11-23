# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What is at a path, with the same answer on every Python (SP-LOOPS Task 6 review, must-fix 1).

`Path.is_file`, `is_dir` and `exists` changed in Python 3.14: they now answer False for every
`OSError`, where 3.12 raised every error but "not there". So a folder that cannot be searched read
as missing on 3.14 and raised on 3.12 -- a wrong "has no manifest", or a plugin skipped in silence.
This probe makes one `stat` (or `lstat`) call and treats only the errors 3.12's pathlib treated as
"not there" (`ABSENT`: ENOENT, ENOTDIR, EBADF, ELOOP) as an absent path; any other error is raised,
for the caller to name. Declared by `interfaces/path_probe_interface.py::PathProbeInterface`.
"""

from __future__ import annotations

import errno
import os
import stat as stat_module
from collections.abc import Callable
from pathlib import Path
from typing import Final, Literal

PathKind = Literal["file", "dir", "other"]
FILE: Final[PathKind] = "file"
DIR: Final[PathKind] = "dir"
OTHER: Final[PathKind] = "other"
ABSENT: Final = frozenset({errno.ENOENT, errno.ENOTDIR, errno.EBADF, errno.ELOOP})


class PathProbe:
    """Declared by `interfaces/path_probe_interface.py::PathProbeInterface`."""

    def __init__(
        self,
        stat: Callable[[Path], os.stat_result] = os.stat,
        lstat: Callable[[Path], os.stat_result] = os.lstat,
    ) -> None:
        self._stat = stat
        self._lstat = lstat

    def kind(self, path: Path, *, follow: bool = True) -> PathKind | None:
        try:
            mode = (self._stat if follow else self._lstat)(path).st_mode
        except OSError as exc:
            if exc.errno in ABSENT:
                return None
            raise
        if stat_module.S_ISREG(mode):
            return FILE
        if stat_module.S_ISDIR(mode):
            return DIR
        return OTHER

    def is_dir(self, path: Path) -> bool:
        return self.kind(path) == DIR

    def is_file(self, path: Path) -> bool:
        return self.kind(path) == FILE
