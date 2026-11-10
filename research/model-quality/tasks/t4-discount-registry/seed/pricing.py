"""Order pricing. All money is integer cents; nothing here uses floats."""

from __future__ import annotations

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

    discount = 0
    if code is not None:
        c = code.strip().upper()
        if c == "SAVE10":
            discount = subtotal * 10 // 100
        elif c == "SAVE25":
            # Only for orders of $100.00 or more.
            if subtotal >= 10000:
                discount = subtotal * 25 // 100
        elif c == "BULK":
            # $5.00 off for every complete group of five items.
            discount = 500 * (count // 5)
        elif c == "FLAT5":
            discount = 500
        elif c == "HALFOFF":
            # Half off, but never more than $20.00.
            discount = min(subtotal // 2, 2000)
        # Any other code is silently ignored.

    discount = min(discount, subtotal)

    taxable = subtotal - discount
    tax = taxable * tax_rate_pct // 100
    return {
        "subtotal": subtotal,
        "discount": discount,
        "tax": tax,
        "total": taxable + tax,
    }
