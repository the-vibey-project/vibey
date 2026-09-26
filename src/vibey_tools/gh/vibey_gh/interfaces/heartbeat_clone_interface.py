# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for the repository the heartbeat timer owns and pushes from (vibey ADR-0016)."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class HeartbeatCloneInterface(Protocol):
    """A clone with no working tree: the repository's remote, the runner's own credential,
    a pre-push gate rendered by the timer's vibey-gh, and the declared configuration."""

    @property
    def path(self) -> Path: ...

    @property
    def hook_path(self) -> Path:
        """Where its pre-push gate lives: `core.hooksPath` names this directory, so no global
        hooks path can stand in for it."""
        ...

    @property
    def config_path(self) -> Path:
        """Its copy of the declaring checkout's `.vibey-gh.toml`, which the beat reads."""
        ...

    def settings(self) -> Mapping[str, tuple[str, ...]]:
        """Every git setting the clone must hold, as `git config --local --get-all` lists it."""
        ...

    def ensure(self) -> tuple[list[str], str]:
        """Create the clone if it is missing and set whatever differs: one line per act, and
        the problem that stopped it, or `""`."""
        ...

    def problems(self) -> list[str]:
        """`missing:` or `drift:` for the repository and each setting; `[]` when it holds."""
        ...

    def gate_check(self) -> str:
        """Hand the clone's own pre-push hook a synthetic heartbeat, exactly as a push would,
        and `""` only when its scope decision printed `carries-no-code`; otherwise what it
        said instead."""
        ...
