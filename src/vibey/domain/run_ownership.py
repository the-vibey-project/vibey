# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Whose command a run on the workflows is: request ids the hub mints for one principal (ADR-0085).

The hub's `GET /api/v1/workflows/runs/{request_id}` hands back a run's output, and a request
id is not a secret: the run carries it in its name on the forge, which anyone may read on a
public repository. So a request id the hub mints names its starter as well as the run:

    <nonce>-<tag>    tag = HMAC-SHA256(key, "vibey.workflows.run" NUL owner NUL nonce)

with `NONCE_CHARS` hex characters of nonce and the first `TAG_CHARS` hex characters of the
tag -- 57 characters, inside `RemoteCommand.REQUEST_ID`. Only the hub holds the key, so only
the hub can mint an id that verifies for an owner, and a device asking for an id that does not
verify for its own name is told what it would be told of a run that does not exist. Nothing
is stored: the id carries its owner, so a hub restarted half-way reads it the same.

Pure: no I/O, no clock, no randomness. The caller supplies the key and the nonce.
"""

import hashlib
import hmac
import re
from typing import Final

NONCE_CHARS: Final = 24
"""Hex characters of nonce in a minted id: 96 random bits, so two runs never share one."""

TAG_CHARS: Final = 32
"""Hex characters of the HMAC kept in a minted id: 128 bits, beyond guessing."""

MIN_KEY_BYTES: Final = 32
"""The shortest key the hub may mint with: as long as the HMAC-SHA256 output."""

PURPOSE: Final = b"vibey.workflows.run"
"""Domain separation: a tag made under this key for anything else never reads as this."""

_NONCE: Final = re.compile(rf"[0-9a-f]{{{NONCE_CHARS}}}")
_MINTED: Final = re.compile(rf"([0-9a-f]{{{NONCE_CHARS}}})-([0-9a-f]{{{TAG_CHARS}}})")


class RunOwnership:
    """Mints request ids bound to the principal that started the run, and says whether an
    id was minted for a given principal.

    Declared by `interfaces/run_ownership_interface.py::RunOwnershipInterface`."""

    def __init__(self, key: bytes) -> None:
        if len(key) < MIN_KEY_BYTES:
            raise ValueError(f"a run ownership key is at least {MIN_KEY_BYTES} bytes")
        self._key = key

    def mint(self, owner: str, nonce: str) -> str:
        """The request id for a run `owner` starts, from a fresh hex `nonce`."""
        if not _NONCE.fullmatch(nonce):
            raise ValueError(f"a run nonce is {NONCE_CHARS} lowercase hex characters")
        return f"{nonce}-{self._tag(owner, nonce)}"

    def owns(self, owner: str, request_id: str) -> bool:
        """True only when `request_id` was minted for `owner` under this key; the tag is
        compared in constant time."""
        minted = _MINTED.fullmatch(request_id)
        if minted is None:
            return False
        nonce, tag = minted.groups()
        return hmac.compare_digest(tag, self._tag(owner, nonce))

    def _tag(self, owner: str, nonce: str) -> str:
        message = b"\x00".join((PURPOSE, owner.encode(), nonce.encode()))
        return hmac.new(self._key, message, hashlib.sha256).hexdigest()[:TAG_CHARS]
