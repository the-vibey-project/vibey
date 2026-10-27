# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for where the managed hooks learn which `vibey_gh` source to execute (ADR-0016)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vibey_gh.config import GhConfig


@runtime_checkable
class HooksSelfSourceInterface(Protocol):
    """Keeps a clone's local git config in step with the repository's declared self source."""

    def declared(self, cfg: GhConfig) -> str | None:
        """`[install] self_source` when the repository explicitly declares it, else None."""
        ...

    def local(self, cfg: GhConfig) -> str | None:
        """This clone's `vibey-gh.self-source`, or None when unset (or git cannot say)."""
        ...

    def reconcile(self, cfg: GhConfig) -> str:
        """Copy a declared value into local config if unset; never overwrite a different one.

        Returns the outcome: `installed`, `unchanged`, or a sentence beginning `differs:` or
        `failed:` that says what was left alone and the command to change it.
        """
        ...

    def problems(self, cfg: GhConfig) -> list[str]:
        """Where the local value is missing, different from the declaration, or undeclared."""
        ...
