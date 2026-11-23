# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam that says which entry is a marketplace's own `.git` (SP-LOOPS Tasks 4 and 5)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class GitFolderGuardInterface(Protocol):
    def is_root_git(self, root: Path, entry: Path) -> bool:
        """Whether `entry`, listed directly in `root`, is `root`'s own `.git`: its name folds to
        `.git` and it is the same file (device and inode) as `root/.git`. The lock's digest
        leaves out exactly these entries."""
        ...

    def inside(self, root: Path, candidate: Path, *, any_depth: bool = False) -> bool:
        """Whether `candidate` (under `root`) is `root`'s `.git` or inside it: refused when a
        part of its path below `root` folds to `.git` (the first part, or any part with
        `any_depth`), or when it or a parent up to `root` is the same file as `root/.git`. With
        no `root/.git` only the name rule applies."""
        ...
