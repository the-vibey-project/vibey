# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for finding access without scram-sha-256 to the roles that could rewrite
the ledger.

Mirrors `vibey/infrastructure/db/local_auth.py` (ADR-0016, ADR-0055). Interfaces
declare; they never consume.
"""

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from vibey.infrastructure.db.migrator import OwnedConnection

if TYPE_CHECKING:  # pragma: no cover - typing only
    from vibey.infrastructure.db.local_auth import LocalAuthFinding


@runtime_checkable
class LocalAuthProbeInterface(Protocol):
    """Attempts password-less connections as the owner and every superuser, and reads
    pg_hba where it may."""

    def endpoints(self, app_url: str) -> tuple[tuple[str, int], ...]:
        """The (host or socket directory, port) pairs a probe knocks on."""
        ...

    async def probe(self, app: OwnedConnection, app_url: str) -> "LocalAuthFinding":
        """PASS only when every attempt was refused, pg_hba was read clean and passwords
        are stored as SCRAM verifiers; FAIL when one was let in, a rule would let one in
        without scram-sha-256 (trust, peer, ident, md5 or password -- sub-doctrine 10.j),
        or password_encryption is not scram-sha-256; UNKNOWN otherwise."""
        ...
