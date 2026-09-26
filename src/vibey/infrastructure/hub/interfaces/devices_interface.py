# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind the paired-device registry.

Mirrors `vibey/infrastructure/hub/devices.py` (ADR-0016). Interfaces declare; they never
consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.infrastructure.hub.devices import PairedDevice


@runtime_checkable
class DeviceRegistryInterface(Protocol):
    """The paired devices, read afresh on every call so a revocation binds at once."""

    def all(self) -> tuple[PairedDevice, ...]:
        """Every paired device."""
        ...

    def get(self, device_id: str) -> PairedDevice | None:
        """The device with `device_id`, or `None`."""
        ...

    def add(self, device: PairedDevice) -> None:
        """Adds a device; an id already paired is refused."""
        ...

    def remove(self, device_id: str) -> PairedDevice | None:
        """Removes and returns the device, or `None` when it was not paired."""
        ...
