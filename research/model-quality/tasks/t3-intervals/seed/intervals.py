"""Merge overlapping ranges of numbers."""

from __future__ import annotations

Interval = tuple[int, int]


def merge(intervals: list[Interval]) -> list[Interval]:
    """Merge ranges that overlap or touch; return them sorted by start."""
    merged: list[Interval] = []
    for start, end in sorted(intervals):
        if merged and start < merged[-1][1]:
            last_start, last_end = merged[-1]
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged
