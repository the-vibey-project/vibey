# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Each engine session's own web-only hub principal: minted when the session starts, found by
the hub when the session searches, revoked when the session ends (SP-LOOPS Phase 6, Task 2; R1,
R4).

**Mint.** A fresh token from the source is written to `<run folder>/web-token` first -- the
file store refuses a folder that already holds one, so a run folder carries at most one grant,
and it refuses before anything is registered. Then the token's SHA-256 digest is registered as
`session:<run id>`, holding only `web` (`SessionPrincipal`), until the engine run deadline plus
`DEADLINE_MARGIN` after `now` (R4). A registry that cannot be written takes the token file with
it, so a refusal leaves nothing behind.

**Where the hub finds it.** The worker and the hub (`vibey serve`) are separate processes, so
the registry cannot be a map in the worker's memory. It is the hub's own owner-only state folder
(`infrastructure/hub/session_registry.py`), which the worker already reads to find a running hub
(`serving.json`) and the hub already reads afresh on every request for its paired devices
(`devices.json`): both processes run as the one account, on the one host. What is at rest there
is the digest and the principal, never the token; the only copy of the token is the run's own
file, which the session reads (R1). A 256-bit token's digest is not reversible, and looking an
entry up by it leaks nothing a timing probe could use.

**Revoke** forgets the digest first -- from then on the hub refuses the token -- and then removes
the file. **Lookup** digests the presented token and returns its principal only while it is
unexpired (`SESSION_PRINCIPALS`; expiry is exclusive).

The token is never logged, never put in an error message, and never in a repr: `SessionGrant`
keeps only the file's path and, out of its repr, the digest. Declared by
`interfaces/session_web_principals_interface.py::SessionWebPrincipalsInterface`.
"""

from __future__ import annotations

import hashlib
import math
from datetime import timedelta
from pathlib import Path
from typing import Final
from uuid import UUID

from vibey.application.dto import SessionGrant
from vibey.application.interfaces.observability import Logger
from vibey.application.interfaces.session_web_principals_interface import (
    SessionPrincipalRegistryInterface,
    SessionTokenFilesInterface,
    SessionTokenSourceInterface,
)
from vibey.application.loop_capabilities_service import DEADLINE_MARGIN
from vibey.domain.errors import SessionGrantRefused
from vibey.domain.interfaces.session_principal_interface import SessionPrincipalPolicyInterface
from vibey.domain.session_principal import (
    SESSION_PRINCIPAL_PREFIX,
    SESSION_PRINCIPALS,
    SessionPrincipal,
)

_PRINTABLE: Final = frozenset(chr(code) for code in range(0x21, 0x7F))
"""What a token may be made of: printable ASCII, no space, no line break -- so it survives a
file, a header and a `strip()` unchanged."""


class SessionWebPrincipals:
    """Declared by `interfaces/session_web_principals_interface.py::SessionWebPrincipalsInterface`."""

    def __init__(
        self,
        *,
        tokens: SessionTokenSourceInterface,
        files: SessionTokenFilesInterface,
        registry: SessionPrincipalRegistryInterface,
        run_deadline: timedelta,
        policy: SessionPrincipalPolicyInterface = SESSION_PRINCIPALS,
        logger: Logger | None = None,
    ) -> None:
        if run_deadline <= timedelta(0):
            raise ValueError(f"the engine run deadline must be positive, not {run_deadline}")
        self._tokens = tokens
        self._files = files
        self._registry = registry
        self._lifetime = (run_deadline + DEADLINE_MARGIN).total_seconds()
        self._policy = policy
        self._logger = logger

    def mint(self, run_id: UUID, folder: Path, now: float) -> SessionGrant:
        if not math.isfinite(now):
            raise SessionGrantRefused(f"a session for run {run_id} needs a finite instant as now")
        token = self._tokens.token()
        if not token or not _PRINTABLE.issuperset(token):
            # The token itself is never named, not even a bad one.
            raise SessionGrantRefused(
                f"the token source gave an unusable token for run {run_id}: a token is "
                "printable ASCII with no whitespace"
            )
        principal = SessionPrincipal(
            name=f"{SESSION_PRINCIPAL_PREFIX}{run_id}",
            run_id=run_id,
            expires_at=now + self._lifetime,
        )
        digest = self._digest(token)
        path = self._files.write(folder, token)
        try:
            self._registry.record(digest, principal)
        except BaseException:
            self._files.remove(path)
            raise
        return SessionGrant(token_file=path, principal=principal, digest=digest)

    def revoke(self, grant: SessionGrant) -> None:
        try:
            self._registry.forget(grant.digest)
        finally:
            if not self._files.remove(grant.token_file) and self._logger is not None:
                self._logger.warning(
                    "session_web_token_kept",
                    principal=grant.name,
                    token_file=str(grant.token_file),
                )

    def lookup(self, token: str, now: float) -> SessionPrincipal | None:
        if not token:
            return None
        principal = self._registry.find(self._digest(token))
        if principal is None or self._policy.expired(principal, now):
            return None
        return principal

    @staticmethod
    def _digest(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()
