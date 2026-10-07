"""Candidate interface — stdlib-only so the explorer can import without pulling in vibey."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class CandidateInterface(Protocol):
    """Read-only contract for a candidate discovered by the explorer.

    Provenance fields (*source_url*, *source_kind*) are immutable so the source link
    can never be lost.  *offer* is text, never a payment instruction (doctrine 10.b).
    """

    source_url: str
    source_kind: str
    title: str
    asks: str
    offer: str
    repository: str
    found_at: "datetime | None"

    def intake_arguments(self) -> tuple[str, ...]:
        """Return the exact ``vibey new`` flags that would recreate this candidate."""
        ...
