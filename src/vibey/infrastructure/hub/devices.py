# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Paired devices: where their keys live, and how a device's signed request is checked.

**The registry.** `<state_dir>/devices.json`, mode 0600 in the hub's 0700 directory,
holds each paired device's id, name, scopes and key -- the same trust as the host's own
token file beside it (`local_token.py`), since whoever reads either can act as its holder.
It is read on every request, so revoking a device (removing it here) refuses that
device's very next request, in this process and any other hub on the host. Pairing and
revocation are also written to the ledger (`pairing.py`); the registry is what
authentication reads, the ledger is the history.

**A device's request** carries four headers -- `x-vibey-device`, `x-vibey-timestamp`,
`x-vibey-nonce`, `x-vibey-signature` -- and the signature is HMAC-SHA256 under the
device's key over `HubPairingPolicy.canonical`, verified by vibey_bootstrap's
`verify_hmac_signature` (the dogfood rule). A stale timestamp, a nonce already seen from
that device, an unknown device or a wrong signature proves nothing.
"""

import hashlib
import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from vibey_bootstrap.auth.hmac import verify_hmac_signature

from vibey.application.dto import HubPrincipal
from vibey.domain.hub_pairing import HUB_PAIRING, SIGNATURE_WINDOW_SECONDS
from vibey.domain.hub_scope import HUB_SCOPES, HubScope
from vibey.domain.interfaces.hub_pairing_interface import HubPairingPolicyInterface
from vibey.infrastructure.hub.authenticator import HubRequest
from vibey.infrastructure.hub.interfaces.devices_interface import DeviceRegistryInterface

DEVICES_FILE: Final = "devices.json"

DEVICE_PREFIX: Final = "device:"
"""A device principal's name is this prefix and its id; the host's is `host`."""

MAX_NONCES: Final = 10_000
"""The most unexpired nonces remembered. When full, a new nonce is refused rather than
an old one forgotten: forgetting one would let its request be replayed."""

HEADERS: Final = ("x-vibey-device", "x-vibey-timestamp", "x-vibey-nonce", "x-vibey-signature")


@dataclass(frozen=True, slots=True)
class PairedDevice:
    """One device the host paired: its id, the name it gave, its scopes and its key."""

    device_id: str
    name: str
    scopes: frozenset[HubScope]
    key: str
    paired_at: float


class DeviceRegistry:
    """The paired devices, in an owner-only file read afresh on every call.

    Declared by `interfaces/devices_interface.py::DeviceRegistryInterface`."""

    def __init__(self, state_dir: Path) -> None:
        self._dir = state_dir

    def all(self) -> tuple[PairedDevice, ...]:
        """Every paired device; none when the file does not exist yet."""
        path = self._dir / DEVICES_FILE
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        except FileNotFoundError:
            return ()
        with os.fdopen(fd) as handle:
            self._owned(os.fstat(handle.fileno()), path)
            data = json.loads(handle.read())
        rows = data.get("devices") if isinstance(data, dict) else None
        if not isinstance(rows, list):
            raise ValueError(f"{path} does not list devices")
        return tuple(self._device(row, path) for row in rows)

    def get(self, device_id: str) -> PairedDevice | None:
        """The device with `device_id`, or `None`."""
        return next((d for d in self.all() if d.device_id == device_id), None)

    def add(self, device: PairedDevice) -> None:
        """Adds `device`; an id already paired is refused."""
        devices = self.all()
        if any(d.device_id == device.device_id for d in devices):
            raise ValueError(f"device {device.device_id} is already paired")
        self._write((*devices, device))

    def remove(self, device_id: str) -> PairedDevice | None:
        """Removes and returns the device, or `None` when it was not paired."""
        devices = self.all()
        found = next((d for d in devices if d.device_id == device_id), None)
        if found is not None:
            self._write(tuple(d for d in devices if d.device_id != device_id))
        return found

    def _write(self, devices: tuple[PairedDevice, ...]) -> None:
        self._dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._owned(os.lstat(self._dir), self._dir)
        staged = self._dir / f".{DEVICES_FILE}.{os.getpid()}.tmp"
        staged.unlink(missing_ok=True)
        fd = os.open(staged, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        rows = [
            {
                "id": d.device_id,
                "name": d.name,
                "scopes": sorted(s.value for s in d.scopes),
                "key": d.key,
                "paired_at": d.paired_at,
            }
            for d in devices
        ]
        with os.fdopen(fd, "w") as handle:
            handle.write(json.dumps({"devices": rows}, indent=2))
        staged.replace(self._dir / DEVICES_FILE)

    @staticmethod
    def _device(row: object, path: Path) -> PairedDevice:
        if not isinstance(row, dict):
            raise ValueError(f"{path} holds a device that is not an object")
        device_id, name, key = row.get("id"), row.get("name"), row.get("key")
        scopes, paired_at = row.get("scopes"), row.get("paired_at")
        if (
            not isinstance(device_id, str)
            or not isinstance(name, str)
            or not isinstance(key, str)
            or not isinstance(scopes, list)
            or not all(isinstance(s, str) for s in scopes)
            or not isinstance(paired_at, int | float)
        ):
            raise ValueError(f"{path} holds a malformed device")
        return PairedDevice(
            device_id=device_id,
            name=name,
            scopes=HUB_SCOPES.parse(frozenset(scopes)),
            key=key,
            paired_at=float(paired_at),
        )

    @staticmethod
    def _owned(status: os.stat_result, path: Path) -> None:
        if status.st_uid != os.getuid():
            raise PermissionError(f"{path} belongs to another account; refusing to use it")
        if status.st_mode & 0o077:
            raise PermissionError(f"{path} is open to other accounts; refusing to use it")


class DeviceAuthenticator:
    """Admits a request a paired device signed, and names the device's principal.

    Declared by `interfaces/authenticator_interface.py::HubAuthenticatorInterface`."""

    def __init__(
        self,
        registry: DeviceRegistryInterface,
        *,
        clock: Callable[[], float],
        policy: HubPairingPolicyInterface = HUB_PAIRING,
        max_nonces: int = MAX_NONCES,
    ) -> None:
        self._registry = registry
        self._clock = clock
        self._policy = policy
        self._max_nonces = max_nonces
        self._seen: dict[tuple[str, str], float] = {}

    async def authenticate(self, request: HubRequest) -> HubPrincipal | None:
        device_id, stamp, nonce, signature = (request.headers.get(h, "") for h in HEADERS)
        if not (device_id and stamp and nonce and signature):
            return None
        now = self._clock()
        try:
            timestamp = float(stamp)
            canonical = self._policy.canonical(
                device_id=device_id,
                method=request.method,
                path=request.path,
                query=request.query,
                timestamp=stamp,
                nonce=nonce,
                body_sha256=hashlib.sha256(request.body).hexdigest(),
            )
        except ValueError:
            return None
        if not self._policy.fresh(timestamp, now):
            return None
        device = self._registry.get(device_id)
        # vibey_bootstrap's constant-time HMAC-SHA256 verify (the dogfood rule).
        if device is None or not verify_hmac_signature(device.key, canonical, signature):
            return None
        if not self._remember(device_id, nonce, now):
            return None
        return HubPrincipal(name=f"{DEVICE_PREFIX}{device.device_id}", scopes=device.scopes)

    def _remember(self, device_id: str, nonce: str, now: float) -> bool:
        """Records the nonce; False when it was seen, or when the memory is full."""
        horizon = now - 2 * SIGNATURE_WINDOW_SECONDS
        for key in [k for k, at in self._seen.items() if at < horizon]:
            del self._seen[key]
        key = (device_id, nonce)
        if key in self._seen or len(self._seen) >= self._max_nonces:
            return False
        self._seen[key] = now
        return True
