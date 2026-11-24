# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""An engine session's own hub principal: web only, for one run, until it expires (SP-LOOPS
Phase 6).

The worker mints one of these for each engine session, so a loop reaches `vibey_search` and
`vibey_fetch` through the hub (ADR-0102) without its environment ever holding a SearXNG address,
a Brave key, the host token or the agent token. What it may do is fixed here, not granted:

- it holds exactly `{HubScope.WEB}` (`SESSION_SCOPES`), so it is refused every other hub action,
  `view`-only reads included, which the agent principal holds and a session does not;
- it is honoured only while `now < expires_at`: expiry is exclusive, so at the expiry instant the
  principal is already expired;
- the scope rule itself has one owner, `HubScopePolicy.permits`, which the policy here asks.

A session principal's name begins `session:` (`SESSION_PRINCIPAL_PREFIX`), so it can never be
read as a paired device's or the agent's. Minting, the token file and revocation are the
application's and infrastructure's; nothing here knows a token.

Pure: no I/O, no clock, no async. The caller passes `now`.
"""

import math
from dataclasses import dataclass
from typing import Final
from uuid import UUID

from vibey.domain.hub_scope import HUB_SCOPES, HubAction, HubScope
from vibey.domain.interfaces.session_principal_interface import (
    SessionPrincipalInterface,
    SessionPrincipalPolicyInterface,
)

SESSION_SCOPES: Final[frozenset[HubScope]] = frozenset({HubScope.WEB})
"""The only scopes a session principal ever holds."""

SESSION_PRINCIPAL_PREFIX: Final = "session:"
"""How every session principal's name begins; something must follow it."""


@dataclass(frozen=True, slots=True)
class SessionPrincipal:
    """One engine session's web-only principal. Its scopes are not a field: no constructor
    argument and no `replace` can widen them.

    Declared by `interfaces/session_principal_interface.py::SessionPrincipalInterface`."""

    name: str
    run_id: UUID
    expires_at: float

    def __post_init__(self) -> None:
        if not self.name.startswith(SESSION_PRINCIPAL_PREFIX) or self.name == (
            SESSION_PRINCIPAL_PREFIX
        ):
            raise ValueError(
                f"a session principal's name is {SESSION_PRINCIPAL_PREFIX!r} and an id after it"
            )
        if not math.isfinite(self.expires_at):
            raise ValueError("a session principal's expiry is a finite instant")

    @property
    def scopes(self) -> frozenset[HubScope]:
        """Always `SESSION_SCOPES`, exactly `{HubScope.WEB}`."""
        return SESSION_SCOPES


class SessionPrincipalPolicy:
    """What a session principal may do, and until when. Pure.

    Declared by `interfaces/session_principal_interface.py::SessionPrincipalPolicyInterface`."""

    def permits(self, principal: SessionPrincipalInterface, action: HubAction, now: float) -> bool:
        """True only when the principal has not expired and the hub's scope policy says its
        scopes cover `action` -- for a session principal, `WEB_SEARCH` and `WEB_FETCH`."""
        return not self.expired(principal, now) and HUB_SCOPES.permits(principal.scopes, action)

    def expired(self, principal: SessionPrincipalInterface, now: float) -> bool:
        """True from the expiry instant on (`now >= expires_at`)."""
        return now >= principal.expires_at


SESSION_PRINCIPALS: Final[SessionPrincipalPolicyInterface] = SessionPrincipalPolicy()
"""The policy every hub adapter consults for a session principal. Stateless, so one serves."""

_SEAM: Final[type[SessionPrincipalInterface]] = SessionPrincipal
"""Checks, under `mypy --strict`, that the value object meets its interface."""
