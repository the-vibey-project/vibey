# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Which engine session's principal a presented token names (SP-LOOPS Phase 6, Task 3).

The half of `SessionWebPrincipals` the hub needs. The worker mints and revokes; the hub only
finds, so it is given this alone -- over the same registry in its own state folder -- and never
a token source, the token files or a run deadline it has no use for. `SessionWebPrincipals`
finds through this same class, so there is one lookup, one digest and one expiry rule.

A token is digested with SHA-256 and the registry is asked for that digest; the principal it
names is honoured only while the session policy says it has not expired (`SESSION_PRINCIPALS`,
exclusive). A string no mint could have made -- empty, or anything but printable ASCII without
whitespace -- is unknown before it is hashed, so nothing a client sends can fail to encode.

Declared by `interfaces/session_token_lookup_interface.py::SessionTokenLookupInterface`.
"""

from __future__ import annotations

import hashlib
from typing import Final

from vibey.application.interfaces.session_web_principals_interface import (
    SessionPrincipalRegistryInterface,
)
from vibey.domain.interfaces.session_principal_interface import SessionPrincipalPolicyInterface
from vibey.domain.session_principal import SESSION_PRINCIPALS, SessionPrincipal

_PRINTABLE: Final = frozenset(chr(code) for code in range(0x21, 0x7F))
"""What a token may be made of: printable ASCII, no space, no line break -- so it survives a
file, a header and a `strip()` unchanged."""


class SessionTokenLookup:
    """Declared by `interfaces/session_token_lookup_interface.py::SessionTokenLookupInterface`."""

    def __init__(
        self,
        registry: SessionPrincipalRegistryInterface,
        policy: SessionPrincipalPolicyInterface = SESSION_PRINCIPALS,
    ) -> None:
        self._registry = registry
        self._policy = policy

    def lookup(self, token: str, now: float) -> SessionPrincipal | None:
        if not self.usable(token):
            return None
        principal = self._registry.find(self.digest(token))
        if principal is None or self._policy.expired(principal, now):
            return None
        return principal

    @staticmethod
    def usable(token: str) -> bool:
        """Whether `token` could be a session's: non-empty printable ASCII, no whitespace."""
        return bool(token) and _PRINTABLE.issuperset(token)

    @staticmethod
    def digest(token: str) -> str:
        """The name the registry knows `token` by: its SHA-256, in lower-case hex."""
        return hashlib.sha256(token.encode()).hexdigest()
