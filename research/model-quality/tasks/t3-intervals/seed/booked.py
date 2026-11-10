"""How much of a timeline a set of bookings covers."""

from __future__ import annotations

from intervals import Interval, merge


def covered_length(intervals: list[Interval]) -> int:
    return sum(end - start for start, end in merge(intervals))
