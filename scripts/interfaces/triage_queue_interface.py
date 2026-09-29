# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts `scripts/triage_queue.py` implements. Interfaces declare; they never consume.

GitHub is the source of an issue's content and labels; PostgreSQL's `triaged_ticket` table is
the ordering and lease authority before a Vibey project exists (migration 0020). A *forge*
runs `gh`; a *ticket source* reads the open triaged issues through it; a *ticket store* is the
table.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol


class ForgeInterface(Protocol):
    """GitHub through its CLI."""

    def gh(self, *args: str) -> str:
        """`gh ARGS`' standard output. Raises RuntimeError when `gh` fails."""
        ...


class TicketInterface(Protocol):
    """One open triaged issue as GitHub reported it."""

    @property
    def repository(self) -> str: ...

    @property
    def number(self) -> int: ...

    @property
    def title(self) -> str: ...

    @property
    def body(self) -> str: ...

    @property
    def url(self) -> str: ...

    @property
    def priority(self) -> int: ...

    @property
    def bumped(self) -> bool: ...

    @property
    def updated_at(self) -> datetime: ...


class TicketListingInterface(Protocol):
    """What one read of the forge returned, and whether it is the whole set."""

    @property
    def tickets(self) -> Sequence[TicketInterface]: ...

    @property
    def complete(self) -> bool:
        """True only when the read provably returned every open triaged issue. A listing cut
        off at its limit is not: an issue beyond the limit is unknown, not closed (10.g)."""
        ...


class TicketSourceInterface(Protocol):
    """The open, triaged issues of one repository."""

    def tickets(self) -> TicketListingInterface: ...


class TicketStoreInterface(Protocol):
    """The `triaged_ticket` table for one repository."""

    def reap(self) -> int:
        """Return every lease that has run out to `ready`. The count of rows returned."""
        ...

    def reconcile(self, tickets: Sequence[TicketInterface], *, complete: bool) -> list[int]:
        """Upsert what GitHub reported. When `complete`, a claimable row whose issue is no
        longer open and triaged is retired to `blocked`; the retired issue numbers are
        returned. When not `complete`, nothing is retired and the list is empty."""
        ...

    def claim(self, owner: str, lease_seconds: int) -> dict[str, object] | None:
        """Lease the first `ready` ticket in priority order, or None when there is none."""
        ...

    def release(self, issue_number: int) -> None:
        """Hand a lease back: `leased` -> `ready`. A row in any other state is untouched."""
        ...

    def set_state(self, issue_number: int, state: str, *, project_id: str | None = None) -> None:
        """Move a ticket to `state`, recording `project_id` when one is given."""
        ...

    def in_flight(self) -> list[dict[str, object]]:
        """Every `dispatched` ticket, in claim order, with its recorded project id."""
        ...
