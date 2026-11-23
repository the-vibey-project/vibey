# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind deciding where a hub credential may be sent.

Mirrors `vibey/domain/hub_target.py` (ADR-0016). Interfaces declare; they never consume.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class HubTargetPolicyInterface(Protocol):
    """This computer's loopback, by a fixed address literal, and nothing else."""

    def loopback_address(self, host: str) -> str | None:
        """The loopback literal to connect to for a record naming `host`, or None."""
        ...

    def lan_address(self, host: str) -> str | None:
        """The address literal to connect to for a host the person named on the command line:
        loopback, or a private-network address literal (never a name or a zone); else None."""
        ...
