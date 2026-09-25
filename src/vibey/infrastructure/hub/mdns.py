# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Advertising the hub on the LAN as `_vibey._tcp` (mDNS/DNS-SD, ADR-0068).

A device finds the hub by browsing `_vibey._tcp.local.`: the advertisement carries the
instance name, the port, the certificate fingerprint and the API version, so a client can
show which computer it found and check, before pairing, that the fingerprint matches the
QR code. The advertisement says where the hub is; it grants nothing -- every request is
still authenticated, and a device still has to pair.

Only a hub that listens on the LAN advertises. `vibey serve` on loopback (the default)
never calls this: announcing a service nobody on the LAN can reach would be a false
statement about the computer (10.f). `zeroconf` ships in the optional `hub` extra and is
imported only when advertising starts, so every other `vibey` command works without it.
"""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from vibey.infrastructure.hub.interfaces.mdns_interface import AdvertisementInterface

SERVICE_TYPE: Final = "_vibey._tcp.local."


def _zeroconf() -> Any:
    """The `zeroconf` module, imported on first use.

    Module-level by design: the default of `MdnsAdvertiser`'s `module` seam, which tests
    replace with a fake. A class would add a name and nothing else (ADR-0016)."""
    import zeroconf
    import zeroconf.asyncio  # noqa: F401 - binds `zeroconf.asyncio` for the caller

    return zeroconf


class Advertisement:
    """One running advertisement; `close` withdraws it.

    Declared by `interfaces/mdns_interface.py::AdvertisementInterface`."""

    def __init__(self, zc: Any, info: Any) -> None:
        self._zc = zc
        self._info = info

    async def close(self) -> None:
        await self._zc.async_unregister_service(self._info)
        await self._zc.async_close()


class MdnsAdvertiser:
    """Announces a hub listening on the LAN.

    Declared by `interfaces/mdns_interface.py::MdnsAdvertiserInterface`."""

    def __init__(self, *, module: Callable[[], Any] = _zeroconf) -> None:
        self._module = module

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
        """Registers the service and returns the handle that withdraws it. Loopback
        addresses are never announced; with none left the call refuses, since an
        advertisement nobody can reach says something false."""
        packed = [
            ipaddress.ip_address(a).packed
            for a in addresses
            if not ipaddress.ip_address(a).is_loopback
        ]
        if not packed:
            raise ValueError("nothing on the LAN to advertise: every address is loopback")
        zeroconf = self._module()
        info = zeroconf.ServiceInfo(
            SERVICE_TYPE,
            f"{instance}.{SERVICE_TYPE}",
            addresses=packed,
            port=port,
            properties={"fp": fingerprint, "api": api_version, "tls": "1"},
            server=f"{server.removesuffix('.local').removesuffix('.')}.local.",
        )
        zc = zeroconf.asyncio.AsyncZeroconf()
        await zc.async_register_service(info)
        return Advertisement(zc, info)

    @staticmethod
    def lan_addresses(names: frozenset[str]) -> list[str]:
        """The IP addresses among `names` that are not loopback, sorted."""
        found: list[str] = []
        for name in names:
            try:
                address = ipaddress.ip_address(name)
            except ValueError:
                continue
            if not address.is_loopback:
                found.append(str(address))
        return sorted(found)

    @staticmethod
    def instance() -> str:
        """This computer's short host name, the instance name a browser shows."""
        return socket.gethostname().split(".")[0] or "vibey"
