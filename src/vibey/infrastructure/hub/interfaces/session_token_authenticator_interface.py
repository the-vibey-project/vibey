# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over admitting an engine session's own token to the hub (SP-LOOPS Phase 6, Task 3).

Implemented by `session_token_authenticator.py`. Its one method, `authenticate`, is declared
once, by `HubAuthenticatorInterface`; this is the same seam under the session's own name.
Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vibey.infrastructure.hub.interfaces.authenticator_interface import (
    HubAuthenticatorInterface,
)


@runtime_checkable
class SessionTokenAuthenticatorInterface(HubAuthenticatorInterface, Protocol):
    """`authenticate`, as `HubAuthenticatorInterface` declares it: an engine session's
    `session:<run>` principal, holding only `web`, for a token its registry knows and has not
    seen expire -- else `None`, refused with 401."""
