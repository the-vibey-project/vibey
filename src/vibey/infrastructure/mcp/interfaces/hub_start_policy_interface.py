# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for `HubGateway`'s bounded start seam (SP-ACP)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class BoundedHubStarterInterface(Protocol):
    def __call__(self) -> bool:
        """`HubGateway`'s `starter`: start the hub at most once per window, off the caller's
        thread, and raise `HubGatewayError` ("the hub is away") at once instead of waiting."""
        ...

    def join(self, timeout: float) -> None:
        """Wait up to `timeout` seconds for a start in flight to end (for an orderly exit)."""
        ...
