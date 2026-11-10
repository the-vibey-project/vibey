"""Price quotes, cached because the table lookup is slow in production."""

from __future__ import annotations

from memo import Memo

BASE = {"apple": 40, "pear": 55, "plum": 70}


@Memo
def quote(sku: str, qty: int = 1, discount: int = 0) -> int:
    """Total price in cents for qty units, less a percentage discount."""
    gross = BASE[sku] * qty
    return gross - gross * discount // 100
