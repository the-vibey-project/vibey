"""Split a list of records into fixed-size pages."""

from __future__ import annotations


def page_count(total: int, size: int) -> int:
    """How many pages of `size` items are needed to show `total` items."""
    if size <= 0:
        raise ValueError("size must be positive")
    if total < 0:
        raise ValueError("total must not be negative")
    full, rest = divmod(total, size)
    return full + (1 if rest > 0 else 0)


def get_page[T](items: list[T], page: int, size: int) -> list[T]:
    """Return the items on a 1-based page."""
    pages = page_count(len(items), size)
    if page < 1 or page > pages:
        raise IndexError(f"page {page} is outside 1..{pages}")
    start = (page - 1) * size
    return items[start : start + size]
