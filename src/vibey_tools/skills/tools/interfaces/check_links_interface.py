# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract `tools/check_links.py` implements (ADR-0016)."""

from __future__ import annotations

from typing import Protocol


class LinkCheckerInterface(Protocol):
    """Checks this tenant's documentation links, offline, and reports what is wrong."""

    def problems(self) -> list[str]:
        """Every violation found, one human-readable line each; empty when clean."""
        ...
