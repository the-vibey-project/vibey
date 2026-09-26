# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The port a writer asks before it writes: is the Sabbath holding now (8.i; ADR-0070)?"""

from typing import Protocol, runtime_checkable

from vibey.domain.sabbath import RestWindowInterface


@runtime_checkable
class SabbathGateInterface(Protocol):
    """Whether sub-doctrine 8.i holds this host right now, read from the host's own
    clock and location. Infrastructure implements it; application only asks."""

    def hold(self) -> RestWindowInterface | None:
        """The window holding now, or None when the caller may proceed."""
        ...
