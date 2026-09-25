# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Pairing devices with a running hub, listing them, and revoking them (ADR-0068).

Only the host offers a pairing: it chooses the scopes and receives a 6-digit code and a
pairing URI to show as a QR code. A device claims the offer by sending the code; the
first correct claim spends it and receives a new per-device key, once. Wrong codes are
counted, and `MAX_WRONG_CLAIMS` of them withdraw every open offer, so a guesser gets a
handful of tries in a million, not two minutes of them.

Offers live only in the running process: a code nobody claimed dies with the hub. The
paired devices live in the owner-only registry (`devices.py`), and every pairing and
revocation is appended to the ledger (`pairing_ledger.py`) before it is reported done.
Revocation removes the device from the registry first, so the device is refused from its
next request whether or not the ledger write succeeds; the ledger write follows.
"""

import secrets
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Final

from vibey.domain.hub_pairing import (
    CODE_DIGITS,
    HUB_PAIRING,
    MAX_WRONG_CLAIMS,
    PairingOffer,
    PairingRefused,
)
from vibey.domain.hub_scope import HubScope
from vibey.domain.interfaces.hub_pairing_interface import HubPairingPolicyInterface
from vibey.domain.ledger import EventKind
from vibey.infrastructure.hub.devices import PairedDevice
from vibey.infrastructure.hub.interfaces.devices_interface import DeviceRegistryInterface
from vibey.infrastructure.hub.interfaces.pairing_interface import PairingLedgerInterface

KEY_BYTES: Final = 32
"""A device key's length, in random bytes."""

MAX_DEVICE_NAME: Final = 64
"""The longest name a device may give itself."""


def _digits() -> str:
    """A fresh code from the operating system's CSPRNG.

    Module-level by design: the default of `HubPairing`'s `digits` seam, which tests
    replace. A class would add a name and nothing else (ADR-0016's last resort)."""
    return f"{secrets.randbelow(10**CODE_DIGITS):0{CODE_DIGITS}d}"


def _key() -> str:
    """A fresh device key. The default of `HubPairing`'s `key` seam, as `_digits`."""
    return secrets.token_urlsafe(KEY_BYTES)


def _device_id() -> str:
    """A fresh device id. The default of `HubPairing`'s `device_id` seam, as `_digits`."""
    return secrets.token_hex(8)


class HubPairing:
    """Offers, claims, lists and revokes pairings for one running hub.

    Declared by `interfaces/pairing_interface.py::HubPairingInterface`."""

    def __init__(
        self,
        registry: DeviceRegistryInterface,
        ledger: PairingLedgerInterface,
        *,
        clock: Callable[[], float],
        fingerprint: str,
        address: tuple[str, int],
        policy: HubPairingPolicyInterface = HUB_PAIRING,
        digits: Callable[[], str] = _digits,
        key: Callable[[], str] = _key,
        device_id: Callable[[], str] = _device_id,
    ) -> None:
        self._registry = registry
        self._ledger = ledger
        self._clock = clock
        self._fingerprint = fingerprint
        self._address = address
        self._policy = policy
        self._digits = digits
        self._key = key
        self._device_id = device_id
        self._offers: list[PairingOffer] = []
        self._wrong = 0

    def offer(self, scopes: frozenset[HubScope]) -> dict[str, object]:
        """A new offer of `scopes`: its code, when it expires, and the pairing URI."""
        now = self._clock()
        offer = self._policy.offer(self._digits(), scopes, now)
        self._offers = [o for o in self._offers if o.expires_at > now and o.code != offer.code]
        self._offers.append(offer)
        host, port = self._address
        return {
            "code": offer.code,
            "expires_at": offer.expires_at,
            "scopes": sorted(s.value for s in scopes),
            "fingerprint": self._fingerprint,
            "uri": self._policy.uri(
                host=host, port=port, fingerprint=self._fingerprint, code=offer.code
            ),
        }

    async def claim(self, code: str, name: str) -> dict[str, object]:
        """Spends the offer `code` names and pairs a device called `name`: its id, its key
        (shown this once) and its scopes. A wrong, spent or expired code is refused."""
        if not name or len(name) > MAX_DEVICE_NAME or not name.isprintable():
            raise PairingRefused(f"a device name is 1 to {MAX_DEVICE_NAME} printable characters")
        now = self._clock()
        offer = next((o for o in self._offers if self._policy.claims(o, code, now)), None)
        if offer is None:
            self._wrong += 1
            if self._wrong >= MAX_WRONG_CLAIMS:
                self._offers, self._wrong = [], 0
            raise PairingRefused("that code is not one this hub is offering")
        self._offers.remove(offer)
        device = PairedDevice(
            device_id=self._device_id(),
            name=name,
            scopes=offer.scopes,
            key=self._key(),
            paired_at=now,
        )
        self._registry.add(device)
        await self._ledger.record(
            EventKind.HUB_DEVICE_PAIRED,
            self._payload(device, by="host"),
            datetime.fromtimestamp(now, UTC),
        )
        return {
            "device_id": device.device_id,
            "key": device.key,
            "scopes": sorted(s.value for s in device.scopes),
            "fingerprint": self._fingerprint,
        }

    def devices(self) -> list[dict[str, object]]:
        """Every paired device, without its key."""
        return [
            {
                "device_id": d.device_id,
                "name": d.name,
                "scopes": sorted(s.value for s in d.scopes),
                "paired_at": d.paired_at,
            }
            for d in self._registry.all()
        ]

    async def revoke(self, device_id: str) -> bool:
        """Revokes the device: refused from its next request. False when it was not paired."""
        device = self._registry.remove(device_id)
        if device is None:
            return False
        await self._ledger.record(
            EventKind.HUB_DEVICE_REVOKED,
            self._payload(device, by="host"),
            datetime.fromtimestamp(self._clock(), UTC),
        )
        return True

    @staticmethod
    def _payload(device: PairedDevice, *, by: str) -> dict[str, object]:
        return {
            "device_id": device.device_id,
            "name": device.name,
            "scopes": sorted(s.value for s in device.scopes),
            "by": by,
        }
