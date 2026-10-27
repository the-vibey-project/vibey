# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind where `vibey doctor`'s output goes (ADR-0016).

Mirrors `vibey/cli/doctor_output.py`. Interfaces declare; they never consume. The types the
seams are declared over are imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Sequence

    from vibey.infrastructure.postgres import PostgresStatus


@runtime_checkable
class DoctorOutputInterface(Protocol):
    """Where `vibey doctor` puts what it finds: the lines it always printed, or one document.

    Every call carries the exact text the line has always had, so the text implementation
    prints it unchanged; the JSON implementation keeps the structure the caller already held.
    """

    def note(self, text: str) -> None:
        """A `note:` line. In JSON it goes to stderr, and is in the document's `notes`."""
        ...

    def error(self, text: str) -> None:
        """A refusal before any check ran. Text: stdout, as ever. JSON: stderr, no document."""
        ...

    def say(self, text: str) -> None:
        """One line. The JSON implementation reads it with its one grammar."""
        ...

    def lines(self, lines: Sequence[str]) -> None:
        """Lines a section returned as text, each read the same way `say` reads one."""
        ...

    def engine(self, engine_id: str, installed: bool, version: str | None, auth_ok: bool) -> None:
        """An engine's preflight line; the checks that follow belong to it."""
        ...

    def engine_detail(self, detail: str) -> None:
        """The `detail:` line of the engine just reported."""
        ...

    def conformance(self, name: str, ok: bool, detail: str) -> None:
        """One conformance check of the engine just reported."""
        ...

    def recorded(self, engine_id: str, kind: str) -> None:
        """`engine_health` or `preflight` was written for the engine just reported."""
        ...

    def postgres(self, status: PostgresStatus) -> None:
        """The local PostgreSQL line."""
        ...

    def postgres_detail(self, detail: str) -> None:
        """The `detail:` line printed when an install did not leave PostgreSQL ready."""
        ...

    def cluster_check(self, mark: str, name: str, detail: str) -> None:
        """One check of the in-cluster preflight."""
        ...

    async def captured(self, run: Callable[[], Awaitable[bool]]) -> bool:
        """Run a section that prints its own lines and report whether it passed. JSON reads
        what it printed; text lets it print."""
        ...

    def captured_sync(self, run: Callable[[], bool]) -> bool:
        """`captured`, for a section that is not async."""
        ...

    def finish(self, ok: bool) -> None:
        """Everything has been said. `ok` is whether the process exits 0. JSON prints the
        document here; text prints nothing more."""
        ...
