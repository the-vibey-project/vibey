# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Whether a folder's volume folds case, asked of that volume (SP-ACP Task 11b-ii, review I-2).

macOS volumes are case-insensitive by default, but a case-sensitive APFS volume is common among
developers, so the platform alone is not the answer: `pathconf(path, _PC_CASE_SENSITIVE)` asks
the volume itself (1 sensitive, 0 not). Python's `os.pathconf_names` does not list that name, so
its number from `<sys/unistd.h>` is used. Elsewhere (Linux) case never folds; a volume that
cannot be asked (a folder that is gone) does not fold either: the exact comparison is the safe
one.

Declared by `interfaces/folder_case_interface.py`.
"""

from __future__ import annotations

import os
import sys
from typing import Final

PC_CASE_SENSITIVE: Final = 11
"""`_PC_CASE_SENSITIVE` in macOS's `<sys/unistd.h>`."""


class FolderCase:
    """Declared by `interfaces/folder_case_interface.py::FolderCaseInterface`."""

    def __init__(self, *, platform: str = sys.platform) -> None:
        self._platform = platform

    def folds(self, path: str) -> bool:
        if self._platform != "darwin":
            return False
        try:
            return os.pathconf(path, PC_CASE_SENSITIVE) == 0
        except OSError:
            return False


FOLDER_CASE: Final = FolderCase()
