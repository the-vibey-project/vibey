# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind `vibey hub start | stop | status`.

Mirrors `vibey/cli/hub_engine.py` (ADR-0016). Interfaces declare; they never consume.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class HubEngineCommandInterface(Protocol):
    """Starting, stopping and asking about the one hub on this computer."""

    def status(self) -> None:
        """Says whether the hub runs and where; exit 3 when it does not."""
        ...

    def start(self, timeout: float) -> None:
        """Starts the hub detached unless one already runs; waits until it has said where
        it listens. Exit 1 when it does not come up."""
        ...

    def stop(self, timeout: float) -> None:
        """Asks the hub to stop (SIGTERM, never SIGKILL) and waits for it to go."""
        ...
