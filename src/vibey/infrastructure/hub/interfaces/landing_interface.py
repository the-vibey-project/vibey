# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind the page a browser gets at the hub's front door.

Mirrors `vibey/infrastructure/hub/landing.py` (ADR-0016). Interfaces declare; they never
consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class HubLandingPageInterface(Protocol):
    """A page with no data in it, and the one policy that lets it be styled."""

    def render(self) -> str:
        """The HTML document."""
        ...

    def content_security_policy(self) -> str:
        """The policy this page is served under: the hub's own, plus its one style block."""
        ...
