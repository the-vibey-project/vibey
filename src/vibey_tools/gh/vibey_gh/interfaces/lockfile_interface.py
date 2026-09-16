# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for the project lockfile a version bump invalidates (vibey ADR-0016)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class LockfileInterface(Protocol):
    """A lockfile that pins the project's own version and so goes stale on a bump.

    Injected into `vibey_gh.versioning.apply_version` so the re-lock is substitutable:
    the default implementation shells out to a real resolver, which reaches the network,
    and nothing that reaches the network can be the only reader of a branch in a package
    that declares a 100% coverage floor.
    """

    @property
    def filename(self) -> str:
        """The lockfile's name, relative to the project root — also what `apply_version`
        reports as written once a re-lock succeeds. Read-only, so an implementation is
        free to be a frozen value object."""
        ...

    def present(self, root: Path) -> bool:
        """Whether this project keeps such a lockfile. No lockfile, nothing to re-lock."""
        ...

    def relock(self, root: Path) -> None:
        """Rewrite the lockfile against the current manifests, or raise `RuntimeError`
        carrying the resolver's own diagnostics."""
        ...
