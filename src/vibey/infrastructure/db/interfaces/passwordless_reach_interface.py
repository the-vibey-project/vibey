# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for asking whether the app DSN's database admits a password-less login.

Mirrors `vibey/infrastructure/db/passwordless_reach.py` (ADR-0016). Interfaces declare;
they never consume.
"""

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:  # the finding record lives beside its probe
    from vibey.infrastructure.db.passwordless_reach import PasswordlessReachFinding


@runtime_checkable
class PasswordlessReachProbeInterface(Protocol):
    """Tries the app DSN's database with no password, as the DSN's role and as the OS
    user the worker runs as."""

    def endpoints(self, dsn: str) -> tuple[tuple[str, int], ...]:
        """Where to knock: the DSN's host, plus the local sockets when it is local."""
        ...

    def roles(self, dsn: str) -> tuple[str, ...]:
        """Who to knock as: the DSN's role, then the OS user."""
        ...

    def database(self, dsn: str) -> str:
        """The database the DSN names, or libpq's default."""
        ...

    async def probe(self, dsn: str) -> "PasswordlessReachFinding":
        """WARN when any password-less attempt was let in; PASS when attempts were made
        and every one was refused; UNKNOWN when none could reach the server."""
        ...
