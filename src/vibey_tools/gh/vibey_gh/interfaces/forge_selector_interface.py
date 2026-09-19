# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam that turns `[platform]` into a forge adapter (vibey ADR-0016; #138).

It is the only code that reads `[platform] kind`, and so the only code that knows which
adapters exist. Everything else asks it for "this repository's forge" and gets a
`ForgeAdapterInterface` back, never a class named after a platform.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vibey_gh.config import GhConfig
from vibey_gh.forge import ForgeKind
from vibey_gh.interfaces.forge_adapter_interface import ForgeAdapterInterface


@runtime_checkable
class ForgeSelectorInterface(Protocol):
    """Picks the adapter for the forge a repository's configuration names."""

    @property
    def kinds(self) -> frozenset[ForgeKind]:
        """Every kind this selector can build an adapter for, and no other."""
        ...

    def select(self, cfg: GhConfig) -> ForgeAdapterInterface:
        """The adapter for `cfg.platform`, bound to the repository at `cfg.root`.

        Builds it and asks the forge nothing. Raises `ValueError` saying the adapter is not
        implemented yet when `cfg.platform.kind` names a forge this selector has no adapter
        for, rather than handing back one that would drive the wrong forge.
        """
        ...
