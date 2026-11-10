"""Tip handling on top of billsplit."""

from __future__ import annotations

from billsplit import split_evenly


def add_tip(total_cents: int, percent: int) -> int:
    """The bill plus a percentage tip, rounded half up to a whole cent."""
    return total_cents + (total_cents * percent + 50) // 100


def split_with_tip(total_cents: int, people: int, percent: int) -> list[int]:
    return split_evenly(add_tip(total_cents, percent), people)
