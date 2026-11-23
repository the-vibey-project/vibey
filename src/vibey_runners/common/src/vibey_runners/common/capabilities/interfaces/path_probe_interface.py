# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over "what is at this path", the same on every Python (SP-LOOPS Task 6 review)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Protocol, runtime_checkable


@runtime_checkable
class PathProbeInterface(Protocol):
    def kind(self, path: Path, *, follow: bool = True) -> Literal["file", "dir", "other"] | None:
        """`"file"`, `"dir"` or `"other"` from one `stat` (`lstat` when `follow` is False, so a
        symlink is `"other"`), or None when nothing is there (ENOENT, ENOTDIR, EBADF, ELOOP).
        Any other `OSError` -- a folder that cannot be searched -- is raised."""
        ...

    def real(self, path: Path) -> Path:
        """`path` made absolute with every symlink resolved, as far as it resolves; never raises
        for a symlink loop (3.12's `Path.resolve()` did), so a loop reaches `kind` as absent."""
        ...

    def is_dir(self, path: Path) -> bool:
        """`kind(path) == "dir"`; raises as `kind` does."""
        ...

    def is_file(self, path: Path) -> bool:
        """`kind(path) == "file"`; raises as `kind` does."""
        ...
