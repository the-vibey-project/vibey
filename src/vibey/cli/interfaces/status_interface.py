# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind `vibey status --json`'s document.

Mirrors `vibey/cli/status.py` (ADR-0016). Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.tui.dashboard import DashboardState


@runtime_checkable
class StatusPresenterInterface(Protocol):
    """Renders a project's dashboard state as the status document."""

    def document(self, state: DashboardState) -> dict[str, object]:
        """The keys `vibey status --json` prints and the hub's status route returns."""
        ...
