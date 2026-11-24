# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Finding the session principal a presented token names (SP-LOOPS Phase 6, Task 3): the half of
`SessionWebPrincipals` the hub needs, which holds no token source, no token files and no run
deadline, because the hub never mints.

Over an in-memory registry; the registry's folder is `tests/infrastructure/hub/`'s. Module-level
test functions rather than a class with an interface beside it (ADR-0016)."""

from __future__ import annotations

import hashlib
from uuid import UUID

import pytest

from vibey.application.interfaces.session_token_lookup_interface import (
    SessionTokenLookupInterface,
)
from vibey.application.session_token_lookup import SessionTokenLookup
from vibey.domain.session_principal import SessionPrincipal

RUN = UUID("00000000-0000-4000-8000-000000000001")
TOKEN = "tok-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
PRINCIPAL = SessionPrincipal(name=f"session:{RUN}", run_id=RUN, expires_at=100.0)


class _Registry:
    def __init__(self, error: Exception | None = None) -> None:
        self.entries: dict[str, SessionPrincipal] = {}
        self.error = error
        self.asked: list[str] = []

    def record(self, digest: str, principal: SessionPrincipal) -> None:
        self.entries[digest] = principal

    def find(self, digest: str) -> SessionPrincipal | None:
        self.asked.append(digest)
        if self.error is not None:
            raise self.error
        return self.entries.get(digest)

    def forget(self, digest: str) -> bool:
        return self.entries.pop(digest, None) is not None


def _lookup(registry: _Registry) -> SessionTokenLookup:
    registry.record(hashlib.sha256(TOKEN.encode()).hexdigest(), PRINCIPAL)
    return SessionTokenLookup(registry)


def test_the_lookup_meets_its_seam() -> None:
    assert isinstance(SessionTokenLookup(_Registry()), SessionTokenLookupInterface)


def test_the_digest_is_the_tokens_sha256_in_lower_case_hex() -> None:
    assert SessionTokenLookup.digest(TOKEN) == hashlib.sha256(TOKEN.encode()).hexdigest()


def test_it_finds_the_principal_until_the_expiry_instant() -> None:
    lookup = _lookup(_Registry())
    assert lookup.lookup(TOKEN, 0.0) == PRINCIPAL
    assert lookup.lookup(TOKEN, 99.999) == PRINCIPAL
    assert lookup.lookup(TOKEN, 100.0) is None  # expiry is exclusive
    assert lookup.lookup(TOKEN + "x", 0.0) is None  # never minted


@pytest.mark.parametrize("token", ["", " ", "tok en", "tokén", "tok\nen", "\ud800"])
def test_a_token_no_mint_could_have_made_is_unknown_and_never_reaches_the_registry(
    token: str,
) -> None:
    """A minted token is printable ASCII with no whitespace, so anything else is refused here,
    before it is hashed: a string that cannot even be encoded never raises past the hub."""
    registry = _Registry()
    assert _lookup(registry).lookup(token, 0.0) is None
    assert registry.asked == []


@pytest.mark.parametrize(
    "token", ["tok-A", "!", "~" * 64, "".join(chr(c) for c in range(0x21, 0x7F))]
)
def test_every_printable_ascii_token_is_usable(token: str) -> None:
    assert SessionTokenLookup.usable(token)


@pytest.mark.parametrize("error", [PermissionError("/state/sessions/x.json"), ValueError("bad")])
def test_what_the_registry_raises_reaches_the_caller(error: Exception) -> None:
    """The caller (the hub's authenticator) decides what an unreadable registry means."""
    lookup = _lookup(_Registry(error=error))
    with pytest.raises(type(error)):
        lookup.lookup(TOKEN, 0.0)
