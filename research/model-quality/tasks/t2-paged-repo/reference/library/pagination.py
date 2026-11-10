import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Page:
    items: list[Any]
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool


def paginate(items: list[Any], page: int, page_size: int) -> Page:
    if page < 1:
        raise ValueError("page must be >= 1")
    if not 1 <= page_size <= 100:
        raise ValueError("page_size must be between 1 and 100")
    total = len(items)
    total_pages = math.ceil(total / page_size)
    start = (page - 1) * page_size
    return Page(
        items=items[start : start + page_size],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )
