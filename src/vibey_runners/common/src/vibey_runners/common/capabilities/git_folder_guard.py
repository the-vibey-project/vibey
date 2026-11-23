# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Which entry is a marketplace's own `.git`, decided by file identity (SP-LOOPS; from the
automated security review).

The lock's digest leaves the root's `.git` out (git rewrites it without the content changing),
so the loaders must never read anything inside it. Comparing path text is not enough: on a
case-insensitive or normalising file system (macOS by default, Windows) `.GIT`, `.Git` or a
normalisation variant names the same folder. So the root's `.git` is identified by
`(st_dev, st_ino)`, and a candidate is inside it when it, or any parent up to the root, has that
identity. A case-folded, NFKC-normalised name test is a second, cheap layer that holds even where
the stat seam is faked. The digest uses the same rule through `is_root_git`, so the digest and the
loaders agree on exactly which entry is the root's git folder: on a case-sensitive file system a
sibling `.GIT` is another folder and is hashed; on a case-insensitive one it is the same folder
and is left out. With no `root/.git` there is nothing to stat or skip.

Declared by `interfaces/git_folder_guard_interface.py::GitFolderGuardInterface`.
"""

from __future__ import annotations

import os
import unicodedata
from collections.abc import Callable
from pathlib import Path
from typing import Final

GIT_NAME: Final = ".git"


class GitFolderGuard:
    """Declared by `interfaces/git_folder_guard_interface.py::GitFolderGuardInterface`."""

    def __init__(self, stat: Callable[[Path], os.stat_result] = os.stat) -> None:
        self._stat = stat

    def is_root_git(self, root: Path, entry: Path) -> bool:
        if not self._git_name(entry.name):
            return False
        git = self._identity(root / GIT_NAME)
        return git is not None and self._identity(entry) == git

    def inside(self, root: Path, candidate: Path, *, any_depth: bool = False) -> bool:
        try:
            parts = candidate.relative_to(root).parts
        except ValueError:
            return False
        if any(self._git_name(part) for part in (parts if any_depth else parts[:1])):
            return True
        git = self._identity(root / GIT_NAME)
        if git is None:
            return False
        path = candidate
        while path != root:
            if self._identity(path) == git:
                return True
            path = path.parent
        return False

    @staticmethod
    def _git_name(name: str) -> bool:
        return unicodedata.normalize("NFKC", name).casefold() == GIT_NAME

    def _identity(self, path: Path) -> tuple[int, int] | None:
        try:
            status = self._stat(path)
        except OSError:
            return None
        return status.st_dev, status.st_ino
