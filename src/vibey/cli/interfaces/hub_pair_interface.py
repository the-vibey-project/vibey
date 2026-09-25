# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind `vibey hub pair | devices | revoke`.

Mirrors `vibey/cli/hub_pair.py` (ADR-0016). Interfaces declare; they never consume.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class HubPairCommandInterface(Protocol):
    """The host's side of pairing, through the running hub."""

    def pair(self, scopes: list[str]) -> None:
        """Offers a pairing of `scopes` and shows its QR code and code."""
        ...

    def devices(self) -> None:
        """Lists the paired devices."""
        ...

    def revoke(self, device_id: str) -> None:
        """Revokes a device."""
        ...
