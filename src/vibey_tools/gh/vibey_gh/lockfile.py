# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Re-locking the project lockfile after a version bump.

A uv-managed project's lockfile pins its own package at the version the bump just
replaced — self-referencing, since `uv sync` installs the project editable. Leaving it
stale does not fail quietly: `uv lock --check` fails on that commit and *only* that
commit, which is exactly the one the promotion just produced.

The resolver is behind `LockfileInterface` rather than called inline because a real
`uv lock` downloads from an index. A branch whose only reader needs the network is not
reachable in an offline environment, and a coverage floor that only holds with network
access is not a floor.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class UvLockfile:
    """`uv.lock`, re-locked by `uv lock` — the default `LockfileInterface`.

    Both the filename and the resolver command are fields rather than literals: a
    project that locks with a different tool, or a different subcommand, configures this
    at the call site instead of forking the module (ADR-0018).
    """

    filename: str = "uv.lock"
    command: tuple[str, ...] = ("uv", "lock")

    def present(self, root: Path) -> bool:
        return (root / self.filename).is_file()

    def relock(self, root: Path) -> None:
        r = subprocess.run(
            list(self.command), cwd=root, capture_output=True, text=True, check=False
        )
        if r.returncode:
            raise RuntimeError(f"{' '.join(self.command)}: {r.stderr.strip()}")
