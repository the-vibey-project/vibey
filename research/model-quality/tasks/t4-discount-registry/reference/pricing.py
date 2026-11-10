"""Order pricing. All money is integer cents; nothing here uses floats."""

from __future__ import annotations

from discounts import apply_discount

OrderLine = tuple[str, int, int]  # (name, unit price in cents, quantity)


def price_order(
    items: list[OrderLine], code: str | None = None, tax_rate_pct: int = 0
) -> dict[str, int]:
    """Total an order: subtotal, discount from a promo code, tax on the discounted amount."""
    subtotal = 0
    count = 0
    for _name, unit_cents, qty in items:
        subtotal += unit_cents * qty
        count += qty

    discount = apply_discount(code, subtotal, count)
    taxable = subtotal - discount
    tax = taxable * tax_rate_pct // 100
    return {
        "subtotal": subtotal,
        "discount": discount,
        "tax": tax,
        "total": taxable + tax,
    }
