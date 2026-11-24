# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Where an engine session's hub token comes from (SP-LOOPS Phase 6, Task 2): `TOKEN_BYTES`
random bytes, URL-safe, made the way the host's own hub token is (`local_token.py`). The maker
is injected so a test never depends on real randomness. Declared by
`interfaces/session_token_source_interface.py::SecretsSessionTokenSourceInterface`.
"""

from __future__ import annotations

import secrets
from collections.abc import Callable

from vibey.infrastructure.hub.local_token import TOKEN_BYTES


class SecretsSessionTokenSource:
    """Declared by `interfaces/session_token_source_interface.py::SecretsSessionTokenSourceInterface`."""

    def __init__(self, *, make: Callable[[int], str] = secrets.token_urlsafe) -> None:
        self._make = make

    def token(self) -> str:
        return self._make(TOKEN_BYTES)
