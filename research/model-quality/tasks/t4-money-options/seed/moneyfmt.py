"""Format integer cents as a money string."""

from __future__ import annotations

SYMBOLS = {"USD": "$", "EUR": "€", "GBP": "£"}


def format_money(
    amount_cents: int,
    currency: str = "USD",
    symbol: bool = True,
    thousands: str = ",",
    decimals: int = 2,
    negative_style: str = "minus",
    width: int = 0,
) -> str:
    """Render amount_cents. 123456 -> "$1,234.56"; -123456 with negative_style="parens" -> "($1,234.56)"."""
    if decimals not in (0, 1, 2):
        raise ValueError("decimals must be 0, 1 or 2")
    if negative_style not in ("minus", "parens"):
        raise ValueError("negative_style must be 'minus' or 'parens'")

    negative = amount_cents < 0
    # Round the magnitude half up to the requested number of decimals.
    scale = 10 ** (2 - decimals)
    units = (abs(amount_cents) + scale // 2) // scale
    whole, frac = divmod(units, 10**decimals)

    digits = f"{whole:,}".replace(",", thousands)
    # With "." as the thousands separator the decimal point becomes ",".
    point = "," if thousands == "." else "."
    body = digits
    if decimals:
        body += point + str(frac).zfill(decimals)

    code = currency.upper()
    if symbol:
        body = SYMBOLS[code] + body if code in SYMBOLS else code + " " + body
    else:
        body = body + " " + code

    if negative:
        body = "-" + body if negative_style == "minus" else "(" + body + ")"
    return body.rjust(width)
