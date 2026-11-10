"""Split a bill, in whole cents, between diners."""

from __future__ import annotations


def split_evenly(total_cents: int, people: int) -> list[int]:
    """One share per person, in cents."""
    if people < 1:
        raise ValueError("people must be at least 1")
    share = round(total_cents / people)
    return [share] * people
