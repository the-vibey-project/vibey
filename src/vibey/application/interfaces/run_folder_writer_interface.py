# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam a run's inputs are written into its worktree through (SP-LOOPS Phase 3, fix round 1:
R-E). The run inputs service keeps the rules -- which inputs, the prompt text -- and every
folder made and file written goes through this port; the hardened writer lives in
`infrastructure/inputs/no_follow_files.py`. Interfaces declare; they never consume.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class RunFolderWriterInterface(Protocol):
    def made(self, root: Path, parts: Sequence[str]) -> Path:
        """`root / parts...`. `root` must already be a folder (it is followed: it is vibey's
        own). Each part below it is made 0700 when absent and refused (`InputStoreError`) when
        it is a symlink or anything but a folder: a worktree may be a cloned repository's, which
        can commit a folder as a symlink out of it."""
        ...

    def write(self, folder: Path, name: str, data: bytes) -> Path:
        """Writes `folder / name` (0600) afresh: to a temporary name opened `O_EXCL |
        O_NOFOLLOW`, then renamed into place, and returns the path. `name` must be one path
        segment; what is already there must be a regular file. A symlink there, a platform with
        no `O_NOFOLLOW`, or a failed write is an `InputStoreError`."""
        ...
