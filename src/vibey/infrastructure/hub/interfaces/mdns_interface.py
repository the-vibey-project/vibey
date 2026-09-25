# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind advertising the hub as `_vibey._tcp`.

Mirrors `vibey/infrastructure/hub/mdns.py` (ADR-0016). Interfaces declare; they never
consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence


@runtime_checkable
class AdvertisementInterface(Protocol):
    """A running advertisement."""

    async def close(self) -> None:
        """Withdraws the advertisement."""
        ...


@runtime_checkable
class MdnsAdvertiserInterface(Protocol):
    """Announces a hub that listens on the LAN; never a loopback one."""

    async def advertise(
        self,
        *,
        instance: str,
        server: str,
        port: int,
        addresses: Sequence[str],
        fingerprint: str,
        api_version: str,
    ) -> AdvertisementInterface:
        """Registers `_vibey._tcp` and returns the handle that withdraws it."""
        ...

    @staticmethod
    def lan_addresses(names: frozenset[str]) -> list[str]:
        """The non-loopback IP addresses among `names`."""
        ...

    @staticmethod
    def instance() -> str:
        """The instance name to advertise."""
        ...
