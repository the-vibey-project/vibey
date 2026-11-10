"""Promo-code discount rules, one small function per code, looked up through a registry."""

from __future__ import annotations

from collections.abc import Callable

#: A rule takes (subtotal_cents, item_count) and returns the discount in cents (before capping).
DiscountRule = Callable[[int, int], int]


def _save10(subtotal: int, count: int) -> int:
    return subtotal * 10 // 100


def _save25(subtotal: int, count: int) -> int:
    return subtotal * 25 // 100 if subtotal >= 10000 else 0


def _bulk(subtotal: int, count: int) -> int:
    return 500 * (count // 5)


def _flat5(subtotal: int, count: int) -> int:
    return 500


def _halfoff(subtotal: int, count: int) -> int:
    return min(subtotal // 2, 2000)


DISCOUNT_RULES: dict[str, DiscountRule] = {
    "SAVE10": _save10,
    "SAVE25": _save25,
    "BULK": _bulk,
    "FLAT5": _flat5,
    "HALFOFF": _halfoff,
}


def apply_discount(code: str | None, subtotal_cents: int, item_count: int) -> int:
    """Discount in cents for a promo code: 0 for None or unknown codes, never above the subtotal."""
    if code is None:
        return 0
    rule = DISCOUNT_RULES.get(code.strip().upper())
    if rule is None:
        return 0
    return min(rule(subtotal_cents, item_count), subtotal_cents)
