# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""AesGcmStateCipher: what the `vibey-state` branch holds, sealed (ADR-0086).

A sealed snapshot is `VBYSTAT1`, a fresh 96-bit nonce, and the gzip of the snapshot's
canonical document encrypted with AES-256-GCM under the state key, the magic as associated
data. GCM authenticates as well as hides: a snapshot sealed under another key, or changed
by a single bit on the branch, does not open, and is reported as unreadable rather than
read as an empty or a partial state. The nonce is fresh per seal, so the same rows sealed
twice are different bytes; the sync compares what it opens, never what it pushes.
"""

import base64
import gzip
import secrets
from typing import Final

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from vibey.application.interfaces.state_sync import StateCipher
from vibey.domain.state_sync import SnapshotUnreadable

MAGIC: Final[bytes] = b"VBYSTAT1"
NONCE_BYTES: Final[int] = 12
KEY_BYTES: Final[int] = 32


class StateKey:
    """The state key's text form: 32 random bytes, base64url without padding."""

    @staticmethod
    def new() -> str:
        return base64.urlsafe_b64encode(secrets.token_bytes(KEY_BYTES)).rstrip(b"=").decode()

    @staticmethod
    def parse(text: str) -> bytes:
        cleaned = text.strip()
        try:
            key = base64.urlsafe_b64decode(cleaned + "=" * (-len(cleaned) % 4))
        except ValueError:
            key = b""
        if len(key) != KEY_BYTES:
            raise ValueError(
                f"the state key is {KEY_BYTES} bytes as base64url; `vibey state key --new` "
                "makes one"
            )
        return key


class AesGcmStateCipher(StateCipher):
    """Implements `application/interfaces/state_sync.py::StateCipher`."""

    def __init__(self, key: bytes) -> None:
        if len(key) != KEY_BYTES:
            raise ValueError(f"the state key must be {KEY_BYTES} bytes")
        self._aead = AESGCM(key)

    def seal(self, plaintext: bytes) -> bytes:
        nonce = secrets.token_bytes(NONCE_BYTES)
        packed = gzip.compress(plaintext, mtime=0)
        return MAGIC + nonce + self._aead.encrypt(nonce, packed, MAGIC)

    def open(self, sealed: bytes) -> bytes:
        if not sealed.startswith(MAGIC) or len(sealed) <= len(MAGIC) + NONCE_BYTES:
            raise SnapshotUnreadable("the branch does not hold a sealed vibey state")
        nonce = sealed[len(MAGIC) : len(MAGIC) + NONCE_BYTES]
        try:
            packed = self._aead.decrypt(nonce, sealed[len(MAGIC) + NONCE_BYTES :], MAGIC)
        except InvalidTag:
            raise SnapshotUnreadable(
                "the state key does not open the branch's state: it was sealed under another "
                "key, or changed after it was sealed"
            ) from None
        return gzip.decompress(packed)
