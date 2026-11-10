"""One-line summaries of a paged listing."""

from __future__ import annotations

from pager import page_count


def describe(total: int, size: int) -> str:
    pages = page_count(total, size)
    noun = "page" if pages == 1 else "pages"
    return f"{total} items, {pages} {noun}"
