# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Pairing a device with the hub, and what a paired device's request must prove (ADR-0068).

A device is never trusted for where it is (SD-01 §2: being on the network proves
nothing). It is trusted for what it holds:

- **Pairing.** The host shows a 6-digit code, valid for `PAIRING_TTL_SECONDS`, with the
  scopes the host chose (never empty: deny by default, 10.c). A device that presents the
  code in time receives a per-device key once; the code is spent by the first claim. The
  pairing URI the host shows as a QR code carries the hub's certificate fingerprint, so
  the device's first TLS connection trusts that certificate and no other.
- **Every request after.** A device signs each request: its id, a timestamp within
  `SIGNATURE_WINDOW_SECONDS` of the host's clock, a nonce it never reuses, and the
  SHA-256 of the body, over the method, path and query (`canonical`). There is no
  session, so every action -- a `spend` answer included -- is verified on its own, and a
  revoked device is refused at its next request.

Pure: no I/O, no clock, no randomness. The caller supplies the digits and the time.
"""

import hmac
from dataclasses import dataclass
from typing import Final
from urllib.parse import quote, urlencode

from vibey.domain.errors import VibeyError
from vibey.domain.hub_scope import HubScope

PAIRING_TTL_SECONDS: Final = 120.0
"""How long a pairing code is good for: two minutes (the plan's figure)."""

CODE_DIGITS: Final = 6
"""A pairing code's length, in decimal digits."""

MAX_WRONG_CLAIMS: Final = 5
"""Wrong codes the hub accepts before it withdraws every open offer: with a million
codes and five guesses, a guesser's chance is one in two hundred thousand."""

SIGNATURE_WINDOW_SECONDS: Final = 60.0
"""How far a signed request's timestamp may be from the host's clock, either way."""

PAIRING_SCHEME: Final = "vibey-pair"
"""The URI scheme the QR code carries."""


class PairingRefused(VibeyError):
    """A pairing claim or offer the hub will not honour: wrong, spent or expired code, or
    an offer that grants nothing."""


@dataclass(frozen=True, slots=True)
class PairingOffer:
    """A code the host is showing, the scopes a device claiming it receives, and until
    when it is good."""

    code: str
    scopes: frozenset[HubScope]
    expires_at: float


class HubPairingPolicy:
    """The rules for offering, claiming and signing. Pure.

    Declared by `interfaces/hub_pairing_interface.py::HubPairingPolicyInterface`."""

    def offer(self, digits: str, scopes: frozenset[HubScope], now: float) -> PairingOffer:
        """An offer of `scopes` under the code `digits`, good for `PAIRING_TTL_SECONDS`.
        Refuses a code that is not `CODE_DIGITS` decimal digits, and an empty grant: a
        device paired with nothing would hold a key that opens nothing, which is a key
        someone will later widen without a new pairing."""
        if len(digits) != CODE_DIGITS or not digits.isascii() or not digits.isdigit():
            raise PairingRefused(f"a pairing code is {CODE_DIGITS} decimal digits")
        if not scopes:
            raise PairingRefused("a pairing must grant at least one scope")
        return PairingOffer(code=digits, scopes=scopes, expires_at=now + PAIRING_TTL_SECONDS)

    def claims(self, offer: PairingOffer, code: str, now: float) -> bool:
        """True when `code` is the offer's and the offer has not expired. Compared in
        constant time, so a guesser learns nothing from how long a refusal takes."""
        return now < offer.expires_at and hmac.compare_digest(offer.code.encode(), code.encode())

    def fresh(self, timestamp: float, now: float) -> bool:
        """True when a signed request's `timestamp` is within the window of `now`."""
        return abs(now - timestamp) <= SIGNATURE_WINDOW_SECONDS

    def canonical(
        self,
        *,
        device_id: str,
        method: str,
        path: str,
        query: str,
        timestamp: str,
        nonce: str,
        body_sha256: str,
    ) -> bytes:
        """The bytes a device signs: one field per line, the method upper-cased. A field
        cannot carry a newline, so no two different requests share a canonical form."""
        fields = (device_id, method.upper(), path, query, timestamp, nonce, body_sha256)
        if any("\n" in field for field in fields):
            raise ValueError("a signed field cannot contain a newline")
        return "\n".join(fields).encode()

    def uri(self, *, host: str, port: int, fingerprint: str, code: str) -> str:
        """The pairing URI the QR code shows: where the hub is, the SHA-256 fingerprint of
        its certificate, the code, and the API version."""
        query = urlencode({"fp": fingerprint, "code": code, "v": "1"})
        shown = f"[{host}]" if ":" in host else host
        return f"{PAIRING_SCHEME}://{quote(shown, safe=':[]')}:{port}?{query}"


HUB_PAIRING: Final = HubPairingPolicy()
"""The policy every pairing adapter consults. Stateless, so one instance serves."""
